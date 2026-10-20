/*
 * Small, lazy ElevenLabs voice island.
 *
 * Chat never imports this SDK or depends on it. In Custom LLM mode the server
 * writes canonical turns; in native mode the final SDK transcript events are
 * persisted immediately so the displayed text is exactly what was heard and
 * spoken.
 */

const SDK_URL = "https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.21.0/+esm";

let conversation = null;
let voiceSessionId = null;
let syncTimer = null;
let ending = false;
let nativeMode = false;
let transcriptQueue = Promise.resolve();

const dispatch = (name, detail = {}) => window.dispatchEvent(new CustomEvent(name, { detail }));

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Voice is temporarily unavailable.");
  }
  return response.json();
}

const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

async function updateLifecycle(event) {
  if (!voiceSessionId) return;
  try {
    await api(`/api/voice-sessions/${voiceSessionId}/lifecycle/${event}`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  } catch {
    // A lifecycle receipt is observability only. The token and Custom LLM
    // adapter remain the authoritative safety boundary.
  }
}

function recordNativeTranscript({ role, message, event_id: eventId }) {
  if (!nativeMode || !voiceSessionId || !message?.trim()) return Promise.resolve();
  const voiceSession = voiceSessionId;
  const body = {
    role: role === "user" ? "candidate" : "interviewer",
    content: message.trim(),
    event_id: eventId == null ? undefined : String(eventId),
  };
  // SDK events can arrive close together. Serialise writes so a candidate turn
  // is always stored before Leo's corresponding answer.
  transcriptQueue = transcriptQueue
    .then(() => api(`/api/voice-sessions/${voiceSession}/transcript`, {
      method: "POST",
      body: JSON.stringify(body),
    }))
    .then(() => dispatch("leo:voice-sync"))
    .catch(() => {
      // The call itself can continue if a transcript receipt briefly fails;
      // the post-call reconciliation remains available as a fallback.
    });
  return transcriptQueue;
}

function reconcileCustomCandidateTranscript(event) {
  if (nativeMode || !voiceSessionId) return Promise.resolve();
  const role = event?.role || event?.source;
  const content = event?.message?.trim();
  if (!content || !["user", "candidate"].includes(role)) return Promise.resolve();

  const voiceSession = voiceSessionId;
  const body = {
    role: "candidate",
    content,
    event_id: event.event_id == null ? undefined : String(event.event_id),
  };
  // A final SDK transcript can arrive just before its corresponding Custom
  // LLM callback finishes persisting the provisional turn. Retry only that
  // narrow race, then keep the attempt transcript identical to ElevenLabs ASR.
  transcriptQueue = transcriptQueue
    .then(async () => {
      for (let attempt = 0; attempt < 3; attempt += 1) {
        try {
          await api(`/api/voice-sessions/${voiceSession}/final-candidate-transcript`, {
            method: "POST",
            body: JSON.stringify(body),
          });
          dispatch("leo:voice-sync");
          return;
        } catch (error) {
          if (attempt === 2) throw error;
          await wait(250);
        }
      }
    })
    .catch(() => {
      // The Custom LLM callback remains the authoritative turn writer. A
      // reconciliation receipt can fail without interrupting the live call.
    });
  return transcriptQueue;
}

function startSync() {
  window.clearInterval(syncTimer);
  syncTimer = window.setInterval(() => dispatch("leo:voice-sync"), 1500);
}

function stopSync() {
  window.clearInterval(syncTimer);
  syncTimer = null;
}

async function loadConversationSdk() {
  const module = await import(SDK_URL);
  if (!module.Conversation) throw new Error("The voice client did not load.");
  return module.Conversation;
}

async function start(attemptId) {
  if (conversation) return;
  dispatch("leo:voice-status", { status: "connecting" });

  // Ask before creating a paid provider session. Stop this probe stream before
  // the SDK opens its own WebRTC microphone track.
  const previewStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  previewStream.getTracks().forEach((track) => track.stop());

  const [session, Conversation] = await Promise.all([
    api(`/api/attempts/${attemptId}/voice-sessions`, { method: "POST" }),
    loadConversationSdk(),
  ]);
  voiceSessionId = session.voice_session_id;
  nativeMode = session.voice_mode === "native";
  transcriptQueue = Promise.resolve();

  try {
    conversation = await Conversation.startSession({
      conversationToken: session.conversation_token,
      // ElevenLabs forwards this value as `user_id` to the Custom LLM.  It is
      // the durable link between a spoken final utterance and this browser's
      // local attempt; `participant_name` on the token alone is not enough.
      userId: voiceSessionId,
      // This signed binding is included on every Custom LLM request. It is
      // independent of the provider's prompt/history handling, so a longer
      // conversation cannot lose its route back to this exact Leo attempt.
      customLlmExtraBody: session.custom_llm_extra_body || undefined,
      dynamicVariables: {
        voice_session_id: voiceSessionId,
        voice_intro: session.voice_intro,
        ...(session.dynamic_variables || {}),
      },
      onConnect: async () => {
        await updateLifecycle("connected");
        dispatch("leo:voice-status", { status: "connected" });
        startSync();
      },
      onDisconnect: async () => {
        const event = ending ? "ended" : "disconnected";
        await updateLifecycle(event);
        conversation = null;
        voiceSessionId = null;
        nativeMode = false;
        ending = false;
        stopSync();
        dispatch("leo:voice-status", { status: "disconnected" });
        dispatch("leo:voice-sync");
      },
      onModeChange: ({ mode }) => {
        if (mode === "speaking" || mode === "listening") dispatch("leo:voice-status", { status: mode });
      },
      onMessage: (message) => {
        if (nativeMode) recordNativeTranscript(message);
        else {
          reconcileCustomCandidateTranscript(message);
          dispatch("leo:voice-sync");
        }
      },
      onError: (error) => {
        console.error("ElevenLabs Voice Error:", error);
        const detail = error?.message || (typeof error === "string" ? error : "Voice service disconnected");
        dispatch("leo:voice-status", { status: "disconnected", error: detail });
      },
    });
  } catch (error) {
    console.error("ElevenLabs Voice Start Failed:", error);
    await updateLifecycle("disconnected");
    conversation = null;
    voiceSessionId = null;
    nativeMode = false;
    dispatch("leo:voice-status", { status: "disconnected", error: error.message || "Voice session failed" });
    throw error;
  }
}

async function end() {
  if (!conversation) return;
  ending = true;
  await conversation.endSession();
}

window.LeoVoice = {
  start,
  end,
  get active() {
    return Boolean(conversation);
  },
};
