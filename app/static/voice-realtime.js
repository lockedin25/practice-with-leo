/*
 * Push-to-talk voice island.
 *
 * The candidate owns the turn boundary: space takes the floor, space yields it.
 *
 * The two directions are deliberately asymmetric. Recognition is BATCH: audio is
 * recorded to a buffer while the floor is held and uploaded in a single request
 * when it is yielded. Synthesis stays STREAMED, because there the candidate is
 * waiting and a clause can be spoken while the next is still being written.
 *
 * Streaming recognition was tried first and removed. Interim captions were never
 * useful mid-case, and it put a socket handshake, a consumed-on-connect
 * credential, a readiness race and commit semantics on the critical path of
 * every turn. Each of those lost a turn at least once. Recording to a buffer has
 * one failure mode, a failed upload, and it is visible.
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
  tts: null,
  active: false,

  // --- Recording -------------------------------------------------------
  // The utterance is held here in full. Nothing depends on a socket being up at
  // the right moment, which is the whole point of the batch design.
  recordedFrames: [],
  recordedSamples: 0,
  maxSamples: Infinity,
  recordingTicker: null,
  // The microphone graph is built once per session and left running; this gate
  // decides whether its frames are kept. Re-acquiring the device per turn
  // restarted echo cancellation, noise suppression and auto gain each time, and
  // their convergence ramp landed on the candidate's opening words.
  capturing: false,
  // Credentials for the next utterance, fetched while Leo is speaking so the
  // round trip is off the critical path.
  nextCredentials: null,

  // --- Synthesis -------------------------------------------------------
  // Audio chunks arrive faster than they play, so each is scheduled against the
  // end of the previous one rather than "now". That is what keeps it gapless.
  playHead: 0,
  sources: [],
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

/* --- Recording ---------------------------------------------------------- */

/* Build the capture graph once and leave it running for the session.
 *
 * Taking the floor then costs nothing: no device acquisition, no worklet load,
 * no audio-processing warm-up. Frames are produced continuously and discarded
 * while the gate is closed, so what lands in the buffer is already converged
 * rather than starting from cold. */
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
  state.workletNode.port.onmessage = (event) => captureFrame(event.data);
  state.micSource.connect(state.workletNode);
}

function teardownMicrophone() {
  if (state.workletNode?.port) state.workletNode.port.onmessage = null;
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

function captureFrame(frame) {
  if (!state.capturing) return;
  if (state.recordedSamples >= state.maxSamples) {
    // The cap is reached, so yield the floor rather than grow without bound.
    // Everything said up to here is kept and sent.
    stopRecording();
    return;
  }
  state.recordedFrames.push(frame);
  state.recordedSamples += frame.length;
}

const sampleRate = () => state.config?.sample_rate || 16000;
const recordedSeconds = () => state.recordedSamples / sampleRate();

/* A WAV container around the captured PCM.
 *
 * Scribe accepts wav directly, and writing the 44-byte header here avoids
 * shipping an encoder: the samples are already 16-bit mono at the capture rate,
 * so the file is a header followed by the frames concatenated. */
function encodeWav(frames, rate) {
  const samples = frames.reduce((total, frame) => total + frame.length, 0);
  const buffer = new ArrayBuffer(44 + samples * 2);
  const view = new DataView(buffer);
  const ascii = (offset, text) => {
    for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i));
  };
  ascii(0, "RIFF");
  view.setUint32(4, 36 + samples * 2, true);
  ascii(8, "WAVEfmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  ascii(36, "data");
  view.setUint32(40, samples * 2, true);

  let offset = 44;
  frames.forEach((frame) => {
    for (let i = 0; i < frame.length; i += 1) {
      view.setInt16(offset, frame[i], true);
      offset += 2;
    }
  });
  return new Blob([buffer], { type: "audio/wav" });
}

/* One request, straight from the browser to ElevenLabs on a short-lived token,
 * so the audio never passes through Leo's server. */
async function transcribe(blob, stt) {
  const form = new FormData();
  form.append("file", blob, "utterance.wav");
  form.append("model_id", stt.model_id);
  // A misheard figure is worse than a misheard word in a quantitative
  // interview, so recognition is biased toward this case's own numbers.
  (stt.keyterms || []).forEach((term) => form.append("keyterms", term));

  const response = await fetch(stt.url, { method: "POST", body: form });
  if (!response.ok) {
    let detail = "";
    try {
      detail = (await response.json())?.detail?.message || "";
    } catch {
      // A non-JSON error body carries nothing worth showing a candidate.
    }
    throw new Error(detail || `Transcription failed (${response.status}).`);
  }
  return String((await response.json()).text || "").trim();
}

/* --- Credentials -------------------------------------------------------- */

/* Single-use tokens are spent by the request or socket that uses them, so each
 * utterance needs its own pair. Fetching that pair while Leo is still talking
 * keeps the round trip off the critical path. Tokens last fifteen minutes; a
 * stale one simply fails and is replaced. */
async function prefetchCredentials() {
  if (!state.active || state.nextCredentials) return;
  try {
    state.nextCredentials = await api(state.config.sockets_url, { method: "POST" });
  } catch {
    // Not worth surfacing: takeCredentials fetches on demand if this is absent.
    state.nextCredentials = null;
  }
}

async function takeCredentials() {
  const ready = state.nextCredentials;
  state.nextCredentials = null;
  if (ready) {
    prefetchCredentials();
    return ready;
  }
  return api(state.config.sockets_url, { method: "POST" });
}

/* --- Holding and yielding the floor ------------------------------------- */

async function startRecording() {
  // Barge-in: the candidate speaking over Leo ends Leo's turn immediately.
  if (state.phase === "speaking") {
    stopPlayback();
    closeSynthesis();
  }
  window.clearTimeout(state.audioWatchdog);
  state.recordedFrames = [];
  state.recordedSamples = 0;
  state.audioArrived = false;
  state.maxSamples = (state.config.max_utterance_seconds || 120) * sampleRate();

  try {
    await ensureMicrophone();
  } catch (error) {
    console.error("Leo voice: microphone unavailable", error);
    setPhase("idle", { error: "The microphone could not be opened." });
    return;
  }

  // Capture begins here and nothing else has to succeed first. There is no
  // socket to wait for, which is what previously discarded the opening words.
  state.capturing = true;
  setPhase("recording");
  dispatch("leo:voice-caption", { text: "" });

  // A recording with no visible length is unnerving, and the cap has to be
  // legible before it is reached rather than after.
  window.clearInterval(state.recordingTicker);
  state.recordingTicker = window.setInterval(() => {
    if (!state.capturing) return;
    dispatch("leo:voice-recording", {
      seconds: recordedSeconds(),
      limit: state.config.max_utterance_seconds || 120,
    });
  }, 250);
}

async function stopRecording({ discard = false } = {}) {
  if (state.phase !== "recording") return;
  // Close the gate but leave the microphone graph running, so the next turn does
  // not restart the device and its audio processing from cold.
  state.capturing = false;
  window.clearInterval(state.recordingTicker);
  state.recordingTicker = null;

  const frames = state.recordedFrames;
  const seconds = recordedSeconds();
  state.recordedFrames = [];
  state.recordedSamples = 0;

  if (discard) {
    dispatch("leo:voice-caption", { text: "" });
    setPhase("idle");
    return;
  }

  // Two frames is a keypress, not an utterance. Uploading it wastes a request
  // and comes back empty, which reads to the candidate as a failure.
  if (seconds < 0.4) {
    setPhase("idle", { error: "That was too short to hear. Hold space while you speak." });
    return;
  }

  setPhase("transcribing");
  const started = Date.now();
  let text = "";
  let credentials;
  try {
    credentials = await takeCredentials();
    const blob = encodeWav(frames, sampleRate());
    text = await transcribe(blob, credentials.stt);
    console.info(
      "[leo voice] turn:",
      `recorded ${seconds.toFixed(1)}s`,
      `| upload+transcribe ${Date.now() - started}ms`,
      `| ${text ? `${text.split(/\s+/).length} words` : "EMPTY"}`,
    );
  } catch (error) {
    console.error("Leo voice: transcription failed", error);
    setPhase("idle", { error: error.message || "That did not reach the transcriber." });
    return;
  }

  if (!text) {
    setPhase("idle", { error: "Nothing was heard in that recording. Try again." });
    return;
  }

  dispatch("leo:voice-candidate", { text });
  // Warm the synthesis socket now, while the turn is being composed, so Leo's
  // first sentence does not wait on a handshake.
  closeSynthesis();
  state.tts = openSynthesisSocket(credentials.tts_url);
  // Leo is about to spend a couple of seconds thinking and speaking; spend it
  // fetching the credential the next press will need.
  prefetchCredentials();

  try {
    await streamTurn(text);
  } catch (error) {
    console.error("Leo voice: turn failed", error);
    setPhase("idle", { error: error.message });
  }
}

/* --- Public surface ----------------------------------------------------- */

async function start(attemptId) {
  if (state.active) return;
  setPhase("connecting");
  state.config = await api(`/api/attempts/${attemptId}/voice-realtime/session`, { method: "POST" });
  state.attemptId = attemptId;
  state.active = true;
  // Open the microphone now rather than on the first press. This is where a
  // declined permission prompt surfaces, before any credential is spent, and it
  // leaves the audio-processing chain converged before anything is said.
  try {
    await ensureMicrophone();
  } catch {
    state.active = false;
    state.config = null;
    setPhase("disconnected");
    throw new Error("Leo needs microphone access to run a spoken case.");
  }
  prefetchCredentials();
  setPhase("idle");
}

async function end() {
  if (!state.active) return;
  state.active = false;
  state.capturing = false;
  state.recordedFrames = [];
  state.recordedSamples = 0;
  state.nextCredentials = null;
  window.clearInterval(state.recordingTicker);
  window.clearTimeout(state.audioWatchdog);
  // Leaving voice mode is the only point the microphone is released.
  teardownMicrophone();
  stopPlayback();
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
  else if (["idle", "speaking"].includes(state.phase)) await startRecording();
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
