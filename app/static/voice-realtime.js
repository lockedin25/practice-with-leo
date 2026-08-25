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
  // Microphone frames captured before the transcription socket was live. The
  // candidate starts talking the instant they press space, and the socket takes
  // a few hundred milliseconds to mint a credential and shake hands. Buffering
  // is what stops those opening words being lost.
  pendingFrames: [],
  // The microphone graph is built once per session and left running; this gate
  // decides whether its frames are forwarded. Re-acquiring the device per turn
  // restarted echo cancellation, noise suppression and auto gain each time, and
  // their convergence ramp landed exactly on the candidate's opening words.
  capturing: false,
  // Per-turn counters. A lost turn is otherwise invisible: the candidate only
  // sees "nothing was heard" and cannot tell whether the microphone, the socket
  // or the recogniser dropped it.
  stats: null,
  scribeReady: false,
  scribeReadyPromise: null,
  // Credentials for the NEXT utterance, fetched while Leo is still speaking so
  // the round trip is not on the critical path.
  nextSockets: null,
};

// Roughly 30 seconds at 50ms a frame. A cap only matters if the socket never
// comes up, in which case the turn is already failing.
const MAX_PENDING_FRAMES = 600;

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

function openSynthesisSocket(url) {
  // Opened before Leo has any words so the handshake overlaps the candidate
  // still speaking. By the time a sentence exists the socket is warm.
  const socket = new WebSocket(url);
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
function flushPendingFrames() {
  const frames = state.pendingFrames;
  state.pendingFrames = [];
  // In capture order: Scribe treats the stream as continuous audio.
  frames.forEach((frame) => sendAudio(frame));
}

function settleTranscript(reason) {
  const waiter = state.transcriptWaiter;
  if (!waiter) return;
  state.transcriptWaiter = null;
  window.clearTimeout(waiter.timer);
  waiter.resolve({ text: state.transcript.trim(), reason });
}

function attachScribeHandlers(socket) {
  socket.onmessage = (event) => {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch {
      return;
    }
    const type = payload.message_type || payload.type;
    if (type === "session_started") {
      // Proof the credential was accepted, not merely that a socket opened.
      socket.dispatchEvent(new Event("leo:scribe-ready"));
      return;
    }
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
  if (!state.scribeReady || !state.scribe || state.scribe.readyState !== WebSocket.OPEN) {
    // Hold it rather than drop it. This used to return, which silently discarded
    // whatever was said between pressing space and the socket coming up: the
    // utterance arrived clipped, or empty and reported as "nothing was heard".
    if (!commit && state.pendingFrames.length < MAX_PENDING_FRAMES) {
      state.pendingFrames.push(frame);
      if (state.stats) state.stats.buffered += 1;
    }
    return;
  }
  if (state.stats && !commit) state.stats.sent += 1;
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

/* Credentials for the next utterance, fetched off the critical path.
 *
 * Single-use tokens are consumed by the socket that uses them, so each
 * utterance needs its own pair. Fetching that pair while Leo is still talking
 * means pressing space rarely waits on a round trip. Tokens last fifteen
 * minutes; a stale one simply fails to connect and is replaced. */
async function prefetchSockets() {
  if (!state.active || state.nextSockets) return;
  try {
    state.nextSockets = await api(state.config.sockets_url, { method: "POST" });
  } catch {
    // Not worth surfacing: startRecording fetches on demand if this is absent.
    state.nextSockets = null;
  }
}

async function takeSockets() {
  const prefetched = state.nextSockets;
  state.nextSockets = null;
  // Start the following fetch now, not after the turn, so the next press is
  // also covered.
  const replenish = prefetchSockets();
  if (prefetched) return prefetched;
  await replenish;
  const fresh = state.nextSockets;
  state.nextSockets = null;
  return fresh || api(state.config.sockets_url, { method: "POST" });
}

/* Bring the transcription socket up behind an already-recording microphone.
 *
 * Resolves once session_started confirms the credential was accepted, which is
 * the point buffered audio can safely be flushed. A socket that merely opened
 * is not enough: a rejected token opens and then closes. */
function connectScribe(url) {
  return new Promise((resolve, reject) => {
    const socket = attachScribeHandlers(new WebSocket(url));
    let settled = false;
    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      fn(value);
    };
    const timer = window.setTimeout(
      () => finish(reject, new Error("The transcription service did not respond.")),
      8000,
    );
    socket.addEventListener("leo:scribe-ready", () => finish(resolve, socket), { once: true });
    socket.addEventListener("close", () =>
      finish(reject, new Error("Transcription could not start. Try again.")),
    );
    socket.addEventListener("error", () =>
      finish(reject, new Error("The transcription service could not be reached.")),
    );
  });
}

/* Build the capture graph once and leave it running for the session.
 *
 * Pressing space then costs nothing: no device acquisition, no worklet load, and
 * no audio-processing warm-up. Frames are produced continuously and simply
 * dropped on the floor while the gate is closed, so the stream the socket
 * receives is already converged rather than starting from cold. */
async function ensureMicrophone() {
  if (state.workletNode) return;
  if (!state.audioContext) state.audioContext = new AudioContext();
  if (state.audioContext.state === "suspended") await state.audioContext.resume();
  const [micStream] = await Promise.all([
    navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    }),
    state.audioContext.audioWorklet.addModule("/static/pcm-recorder.worklet.js"),
  ]);
  state.micStream = micStream;
  state.micSource = state.audioContext.createMediaStreamSource(micStream);
  state.workletNode = new AudioWorkletNode(state.audioContext, "pcm-recorder", {
    processorOptions: { targetSampleRate: state.config.sample_rate },
  });
  state.workletNode.port.onmessage = (event) => {
    if (state.capturing) sendAudio(event.data);
  };
  state.micSource.connect(state.workletNode);
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
  state.pendingFrames = [];
  state.scribeReady = false;
  window.clearTimeout(state.audioWatchdog);
  dispatch("leo:voice-caption", { text: "" });

  try {
    await ensureMicrophone();
  } catch (error) {
    console.error("Leo voice: microphone unavailable", error);
    setPhase("idle", { error: "The microphone could not be opened." });
    return;
  }

  // Capture starts HERE, before the socket exists. Everything spoken from now is
  // buffered by sendAudio and flushed the moment the socket confirms. Awaiting
  // the credential mint and the handshake first discarded roughly 1.7s of every
  // turn.
  state.capturing = true;
  state.stats = { startedAt: Date.now(), buffered: 0, sent: 0, socketReadyMs: null };
  setPhase("recording");

  // Kept as a promise so a short utterance can wait for it before committing
  // rather than committing into a socket that is not up yet.
  state.scribeReadyPromise = (async () => {
    const sockets = await takeSockets();
    const socket = await connectScribe(sockets.stt_url);
    state.scribe = socket;
    state.scribeReady = true;
    if (state.stats) state.stats.socketReadyMs = Date.now() - state.stats.startedAt;
    flushPendingFrames();
    // Warmed now so its handshake overlaps the rest of this utterance and Leo's
    // first sentence never waits on it.
    closeSynthesis();
    state.tts = openSynthesisSocket(sockets.tts_url);
  })();

  state.scribeReadyPromise.catch((error) => {
    console.error("Leo voice: transcription could not start", error);
    state.pendingFrames = [];
    state.capturing = false;
    state.scribe?.close();
    state.scribe = null;
    setPhase("idle", { error: error.message || "Voice could not start. Try again." });
  });
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
  // Close the gate but leave the microphone graph running. Tearing the device
  // down here is what forced a cold restart, and its audio-processing ramp, on
  // every single turn.
  state.capturing = false;

  if (discard) {
    state.pendingFrames = [];
    state.scribeReady = false;
    state.scribe?.close();
    state.scribe = null;
    state.transcript = "";
    dispatch("leo:voice-caption", { text: "" });
    setPhase("idle");
    return;
  }

  setPhase("transcribing");

  // A short utterance can end before the socket finished coming up. Committing
  // now would drop the whole turn, so wait for the handshake and the buffered
  // audio to land first. On failure the catch in startRecording has already
  // reported it and moved the state machine on.
  try {
    await state.scribeReadyPromise;
  } catch {
    return;
  }
  flushPendingFrames();

  // Commit marks the turn boundary. Everything before it is already streamed,
  // so only the final block is still in flight.
  sendAudio(new Int16Array(0), { commit: true });

  const { text, reason } = await waitForTranscript();
  state.scribe?.close();
  state.scribe = null;

  const stats = state.stats || {};
  console.info(
    "[leo voice] turn:",
    `spoke ${((Date.now() - (stats.startedAt || Date.now())) / 1000).toFixed(1)}s`,
    `| socket ready ${stats.socketReadyMs ?? "?"}ms`,
    `| frames buffered ${stats.buffered ?? 0} sent ${stats.sent ?? 0}`,
    `| ${reason} -> ${text ? `${text.split(/\s+/).length} words` : "EMPTY"}`,
  );

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
  // Leo is about to spend a couple of seconds thinking and speaking. Spend it
  // fetching the credential the next press will need.
  prefetchSockets();
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
  state.config = await api(`/api/attempts/${attemptId}/voice-realtime/session`, { method: "POST" });
  state.attemptId = attemptId;
  state.active = true;
  // Open the microphone now rather than on the first press. This is also where
  // a declined permission prompt surfaces, before any provider credential has
  // been spent, and it leaves the audio-processing chain converged well before
  // the candidate says anything.
  try {
    await ensureMicrophone();
  } catch (error) {
    state.active = false;
    state.config = null;
    setPhase("disconnected");
    throw new Error("Leo needs microphone access to run a spoken case.");
  }
  // Cover the first press as well as later ones.
  prefetchSockets();
  setPhase("idle");
}

async function end() {
  if (!state.active) return;
  state.active = false;
  state.pendingFrames = [];
  state.scribeReady = false;
  state.nextSockets = null;
  state.capturing = false;
  window.clearTimeout(state.audioWatchdog);
  settleTranscript("closed");
  // Leaving voice mode is the only point the microphone is released.
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
