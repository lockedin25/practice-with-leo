/*
 * Push-to-talk voice island.
 *
 * The candidate holds the turn boundary: space starts speaking, space ends it.
 * Nothing in this file waits for a complete object. Microphone frames stream to
 * Scribe while the candidate is still talking, so the committed transcript is
 * ready roughly one network round trip after the spacebar. Leo's reply streams
 * back as server-sent events and is pushed into an already-open synthesis socket
 * one clause at a time, so the first sentence is audible while the second is
 * still being written.
 *
 * Exposes the same window.LeoVoice surface as the Agent island it replaces, so
 * app.js keeps one integration point.
 */

const dispatch = (name, detail = {}) => window.dispatchEvent(new CustomEvent(name, { detail }));

const state = {
  attemptId: null,
  config: null,
  phase: "idle", // idle | recording | transcribing | thinking | speaking
  audioContext: null,
  micStream: null,
  workletNode: null,
  micSource: null,
  scribe: null,
  tts: null,
  transcript: "",
  interim: "",
  // Scheduling clock for queued synthesis output. Audio chunks arrive faster
  // than they play, so each is scheduled against the end of the previous one
  // rather than "now", which is what keeps playback gapless.
  playHead: 0,
  sources: [],
  active: false,
  // Set by the transcription socket so the turn is driven by events rather
  // than by a polling interval.
  transcriptWaiter: null,
  transcriptError: null,
  // Whether synthesis has produced anything this turn. Without this a silent
  // but open socket would leave the HUD waiting on audio that never comes.
  audioArrived: false,
  speechBroken: false,
  audioWatchdog: null,
};

function setPhase(phase, extra = {}) {
  state.phase = phase;
  dispatch("leo:voice-status", { status: phase, ...extra });
}

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

/* --- Speech synthesis --------------------------------------------------- */

function pcmSampleRate(format) {
  const match = /pcm_(\d+)/.exec(format || "");
  return match ? Number(match[1]) : 24000;
}

function decodePcm16(base64, sampleRate) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const samples = new Int16Array(bytes.buffer, 0, Math.floor(bytes.length / 2));
  const buffer = state.audioContext.createBuffer(1, samples.length, sampleRate);
  const channel = buffer.getChannelData(0);
  for (let i = 0; i < samples.length; i += 1) channel[i] = samples[i] / 0x8000;
  return buffer;
}

function playChunk(base64) {
  if (!state.audioContext) return;
  const rate = pcmSampleRate(state.config.tts_output_format);
  let buffer;
  try {
    buffer = decodePcm16(base64, rate);
  } catch (error) {
    console.error("Leo voice: could not decode audio chunk", error);
    return;
  }
  const source = state.audioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(state.audioContext.destination);
  const now = state.audioContext.currentTime;
  // A late chunk must not be scheduled in the past, or it is dropped silently.
  const startAt = Math.max(now, state.playHead);
  source.start(startAt);
  state.playHead = startAt + buffer.duration;
  state.sources.push(source);
  source.onended = () => {
    state.sources = state.sources.filter((candidate) => candidate !== source);
    if (!state.sources.length && state.phase === "speaking") setPhase("idle");
  };
}

function stopPlayback() {
  state.sources.forEach((source) => {
    try {
      source.stop();
    } catch {
      // Already finished. Nothing to interrupt.
    }
  });
  state.sources = [];
  state.playHead = state.audioContext ? state.audioContext.currentTime : 0;
}

function openSynthesisSocket() {
  // Opened before Leo has any words so the handshake overlaps the candidate
  // still speaking. By the time a sentence exists the socket is warm.
  const socket = new WebSocket(state.config.tts_url);
  state.speechBroken = false;
  socket.onopen = () => {
    socket.send(
      JSON.stringify({
        text: " ",
        voice_settings: { stability: 0.5, similarity_boost: 0.75, speed: 1.0 },
      }),
    );
  };
  socket.onmessage = (event) => {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch {
      return;
    }
    if (payload.audio) {
      state.audioArrived = true;
      if (state.phase !== "speaking") setPhase("speaking");
      playChunk(payload.audio);
    }
  };
  // Without these the HUD would sit on "Leo is thinking" forever whenever
  // synthesis fails: no audio chunk ever arrives, so nothing moves the state
  // machine on. The reply text still reached the transcript, so the turn is
  // recoverable by reading rather than lost.
  socket.onerror = () => {
    console.error("Leo voice: synthesis socket error");
    markSpeechBroken("Leo's voice could not be reached. His reply is in the transcript.");
  };
  socket.onclose = (event) => {
    if (!event.wasClean && !state.audioArrived) {
      markSpeechBroken("Leo's voice dropped out. His reply is in the transcript.");
    }
  };
  return socket;
}

function markSpeechBroken(message) {
  if (state.speechBroken) return;
  state.speechBroken = true;
  state.tts = null;
  if (["thinking", "speaking", "transcribing"].includes(state.phase)) {
    setPhase("idle", { error: message });
  }
}

function speak(text) {
  if (!state.tts || state.tts.readyState !== WebSocket.OPEN || !text.trim()) return;
  // ElevenLabs requires a trailing space on every text chunk.
  state.tts.send(JSON.stringify({ text: `${text.trim()} ` }));
}

function flushSynthesis() {
  if (state.tts?.readyState === WebSocket.OPEN) {
    state.tts.send(JSON.stringify({ text: " ", flush: true }));
  }
  // An open socket that never answers is the one failure the error and close
  // handlers cannot catch. The whole reply has been sent by this point, so if
  // nothing has played shortly after the flush, speech is not coming.
  window.clearTimeout(state.audioWatchdog);
  state.audioWatchdog = window.setTimeout(() => {
    if (!state.audioArrived) {
      markSpeechBroken("Leo's voice did not respond. His reply is in the transcript.");
    }
  }, 6000);
}

function closeSynthesis() {
  if (state.tts?.readyState === WebSocket.OPEN) state.tts.send(JSON.stringify({ text: "" }));
  state.tts = null;
}

/* --- Turn streaming ----------------------------------------------------- */

const SENTENCE_END = /[.!?](\s|$)/;

async function streamTurn(text) {
  setPhase("thinking");
  const response = await fetch(state.config.turn_stream_url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: text, turn_id: crypto.randomUUID() }),
  });
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "That response did not reach Leo.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let raw = "";
  let pending = "";

  const emitSentences = () => {
    // Flush on a sentence boundary to keep prosody intact, or on a comma once
    // the clause is long enough that waiting would stall audio that could
    // already be playing.
    for (;;) {
      const match = SENTENCE_END.exec(pending);
      if (match) {
        const cut = match.index + 1;
        speak(pending.slice(0, cut));
        pending = pending.slice(cut).replace(/^\s+/, "");
        continue;
      }
      if (pending.length > 90) {
        const comma = pending.lastIndexOf(", ");
        if (comma > 30) {
          speak(pending.slice(0, comma + 1));
          pending = pending.slice(comma + 1).replace(/^\s+/, "");
          continue;
        }
      }
      return;
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    raw += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line. Keep any partial trailing frame
    // in the buffer until its terminator arrives.
    const frames = raw.split("\n\n");
    raw = frames.pop() || "";
    for (const frame of frames) {
      const nameLine = frame.match(/^event:\s*(.+)$/m);
      const dataLine = frame.match(/^data:\s*(.+)$/m);
      if (!nameLine || !dataLine) continue;
      let payload;
      try {
        payload = JSON.parse(dataLine[1]);
      } catch {
        continue;
      }
      if (nameLine[1] === "control") {
        // Facts are approved before Leo finishes speaking, so the side panel
        // fills while the answer is still arriving.
        dispatch("leo:voice-sync");
      } else if (nameLine[1] === "delta") {
        pending += payload.text || "";
        emitSentences();
      } else if (nameLine[1] === "error") {
        throw new Error(payload.detail || "Leo is temporarily unavailable.");
      } else if (nameLine[1] === "done") {
        if (pending.trim()) speak(pending);
        pending = "";
        flushSynthesis();
        dispatch("leo:voice-transcript", { attempt: payload.attempt });
        dispatch("leo:voice-sync");
      }
    }
  }
  if (pending.trim()) {
    speak(pending);
    flushSynthesis();
  }
}

/* --- Transcription ----------------------------------------------------- */

/* Resolved by the socket the moment a commit lands, so the turn never waits on
 * a polling interval, and settled on error or close so a dead socket cannot
 * hold the turn open until a timeout. */
function settleTranscript(reason) {
  const waiter = state.transcriptWaiter;
  if (!waiter) return;
  state.transcriptWaiter = null;
  window.clearTimeout(waiter.timer);
  waiter.resolve({ text: state.transcript.trim(), reason });
}

function openScribeSocket() {
  const socket = new WebSocket(state.config.stt_url);
  socket.onmessage = (event) => {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch {
      return;
    }
    const type = payload.message_type || payload.type;
    if (type === "partial_transcript") {
      state.interim = payload.text || payload.transcript || "";
      dispatch("leo:voice-caption", { text: `${state.transcript} ${state.interim}`.trim() });
      return;
    }
    if (type === "committed_transcript" || type === "final_transcript") {
      const text = payload.text || payload.transcript || "";
      if (text) state.transcript = `${state.transcript} ${text}`.trim();
      state.interim = "";
      dispatch("leo:voice-caption", { text: state.transcript });
      settleTranscript("committed");
      return;
    }
    if (typeof type === "string" && type.endsWith("_error")) {
      console.error("Leo voice: transcription error", payload);
      state.transcriptError = payload.message || "Transcription failed.";
      settleTranscript("error");
    }
  };
  socket.onerror = () => {
    console.error("Leo voice: transcription socket error");
    state.transcriptError = "The transcription service could not be reached.";
    settleTranscript("error");
  };
  // A close before the commit is acknowledged would otherwise leave the turn
  // waiting on a timeout for a socket that is already gone.
  socket.onclose = () => settleTranscript("closed");
  return socket;
}

function sendAudio(frame, { commit = false } = {}) {
  if (!state.scribe || state.scribe.readyState !== WebSocket.OPEN) return;
  let binary = "";
  const bytes = new Uint8Array(frame.buffer, frame.byteOffset, frame.byteLength);
  for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
  state.scribe.send(
    JSON.stringify({
      message_type: "input_audio_chunk",
      audio_base_64: btoa(binary),
      sample_rate: state.config.sample_rate,
      commit,
    }),
  );
}

async function startRecording() {
  // Barge-in: the candidate speaking over Leo ends Leo's turn immediately.
  if (state.phase === "speaking") {
    stopPlayback();
    closeSynthesis();
  }
  state.transcript = "";
  state.interim = "";
  state.transcriptError = null;
  state.audioArrived = false;
  window.clearTimeout(state.audioWatchdog);
  dispatch("leo:voice-caption", { text: "" });

  if (!state.audioContext) state.audioContext = new AudioContext();
  if (state.audioContext.state === "suspended") await state.audioContext.resume();

  state.micStream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  await state.audioContext.audioWorklet.addModule("/static/pcm-recorder.worklet.js");

  state.scribe = openScribeSocket();
  // Warm the synthesis socket now: its handshake costs nothing while the
  // candidate is still talking, and Leo's first sentence will not wait for it.
  if (!state.tts) state.tts = openSynthesisSocket();

  state.micSource = state.audioContext.createMediaStreamSource(state.micStream);
  state.workletNode = new AudioWorkletNode(state.audioContext, "pcm-recorder", {
    processorOptions: { targetSampleRate: state.config.sample_rate },
  });
  state.workletNode.port.onmessage = (event) => sendAudio(event.data);
  state.micSource.connect(state.workletNode);
  setPhase("recording");
}

function teardownMicrophone() {
  state.workletNode?.port && (state.workletNode.port.onmessage = null);
  try {
    state.micSource?.disconnect();
    state.workletNode?.disconnect();
  } catch {
    // Already disconnected by a prior stop.
  }
  state.micStream?.getTracks().forEach((track) => track.stop());
  state.micSource = null;
  state.workletNode = null;
  state.micStream = null;
}

async function stopRecording({ discard = false } = {}) {
  if (state.phase !== "recording") return;
  teardownMicrophone();

  if (discard) {
    state.scribe?.close();
    state.scribe = null;
    state.transcript = "";
    dispatch("leo:voice-caption", { text: "" });
    setPhase("idle");
    return;
  }

  setPhase("transcribing");
  // Commit marks the turn boundary. Everything before this is already
  // transcribed, so only the final block is still in flight.
  sendAudio(new Int16Array(0), { commit: true });

  const { text, reason } = await waitForTranscript();
  state.scribe?.close();
  state.scribe = null;

  if (!text) {
    // Distinguish a failure from genuine silence: telling someone "nothing was
    // heard" when the socket was refused sends them looking at their mic.
    const message =
      reason === "error" || reason === "closed"
        ? state.transcriptError || "Transcription was interrupted. Try again."
        : "Nothing was heard. Try again.";
    setPhase("idle", { error: message });
    return;
  }

  dispatch("leo:voice-candidate", { text });
  try {
    await streamTurn(text);
  } catch (error) {
    console.error("Leo voice: turn failed", error);
    setPhase("idle", { error: error.message });
  }
}

function waitForTranscript(timeoutMs = 5000) {
  // The commit acknowledgement is the only thing still outstanding, so this
  // normally settles in one round trip, driven by the socket rather than by a
  // poll. The timeout is a backstop for a socket that goes silent without
  // erroring or closing; it returns whatever was already heard.
  return new Promise((resolve) => {
    state.transcriptWaiter = {
      resolve,
      timer: window.setTimeout(() => settleTranscript("timeout"), timeoutMs),
    };
  });
}

/* --- Public surface ---------------------------------------------------- */

async function start(attemptId) {
  if (state.active) return;
  setPhase("connecting");
  // Ask for the microphone before minting provider credentials, so a declined
  // permission prompt costs nothing.
  const probe = await navigator.mediaDevices.getUserMedia({ audio: true });
  probe.getTracks().forEach((track) => track.stop());

  state.config = await api(`/api/attempts/${attemptId}/voice-realtime/session`, { method: "POST" });
  state.attemptId = attemptId;
  state.active = true;
  setPhase("idle");
}

async function end() {
  if (!state.active) return;
  state.active = false;
  window.clearTimeout(state.audioWatchdog);
  settleTranscript("closed");
  teardownMicrophone();
  stopPlayback();
  state.scribe?.close();
  state.scribe = null;
  closeSynthesis();
  if (state.audioContext) {
    await state.audioContext.close().catch(() => {});
    state.audioContext = null;
  }
  state.config = null;
  state.attemptId = null;
  setPhase("disconnected");
}

async function toggleTalking() {
  if (!state.active) return;
  if (state.phase === "recording") await stopRecording();
  else if (state.phase === "idle" || state.phase === "speaking") await startRecording();
}

window.LeoVoice = {
  start,
  end,
  toggleTalking,
  discardRecording: () => stopRecording({ discard: true }),
  get active() {
    return state.active;
  },
  get phase() {
    return state.phase;
  },
  get isRecording() {
    return state.phase === "recording";
  },
};
