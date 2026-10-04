/* Leo browser client.
 *
 * The server owns the case truth; this file owns the room: it keeps the
 * transcript, stage rail, evidence list and summary in sync, and never
 * leaves the candidate staring at a frozen screen while the interviewer
 * is thinking.
 */

/* The authored case package owns its phase list, so labels are looked up and
 * the rail is built from whatever the runtime reports rather than hardcoded. */
const PHASE_META = {
  clarification: { label: "Clarification", note: "Earn the context" },
  structure: { label: "Structure", note: "Lay out a tailored tree" },
  drill_down: { label: "Drill-down", note: "Test a branch against evidence" },
  analysis: { label: "Analysis", note: "Test a branch against evidence" },
  synthesis: { label: "Synthesis", note: "Answer first, then why" },
  recommendation: { label: "Recommendation", note: "Answer first, then why" },
};
const DEFAULT_PHASES = ["clarification", "drill_down", "synthesis"];
const GENERIC_CATEGORIES = new Set(["case interview", "case", "general"]);
const STORAGE_SESSION = "casecall:session";
const MAX_COMPOSER_HEIGHT = 190;
const MIN_SUBSTANTIVE_TURNS = 2;
const AUDIO_CUE = /\[(?:warmly|confidently|patiently|empathetically|seriously|enthusiastically|excitedly|chuckles|laughing|sighs)\]\s*/gi;

const state = {
  viewer: null,
  attempt: null,
  renderedId: null,
  renderedCount: 0,
  renderedMessages: [],
  knownFactIds: new Set(),
  // Facts released since the candidate's last turn, so the rail can mark them.
  newFactIds: new Set(),
  expandedFactIds: new Set(),
  factsSignature: "",
  phases: [],
  sending: false,
  ending: false,
  // Whether the room is in voice mode. The toggle's label and its action both
  // read this, so they cannot drift apart.
  voiceActive: false,
  endArmedTimer: null,
  endRedirectTimer: null,
  // A practice room is pinned to its chosen case, including after a reload.
  selectedCaseId: null,
};

const el = {
  transcript: document.querySelector("#transcript"),
  scroll: document.querySelector("#transcript-scroll"),
  messages: document.querySelector("#messages"),
  form: document.querySelector("#message-form"),
  input: document.querySelector("#candidate-message"),
  send: document.querySelector("#send-message"),
  endedBar: document.querySelector("#ended-bar"),
  closePrompt: document.querySelector("#case-close-prompt"),
  completeAttempt: document.querySelector("#complete-attempt"),
  completionNote: document.querySelector("#completion-note"),
  endButton: document.querySelector("#end-attempt"),
  restart: document.querySelector("#restart-attempt"),
  viewDebriefBtn: document.querySelector("#view-debrief-btn"),
  beginCase: document.querySelector("#begin-case"),
  title: document.querySelector("#case-title"),
  tags: document.querySelector("#case-tags"),
  stageLabel: document.querySelector("#case-stage-label"),
  sessionMode: document.querySelector("#session-mode"),
  sessionStatus: document.querySelector("#session-status-text"),
  stepper: document.querySelector("#stepper"),
  stageCounter: document.querySelector("#stage-counter"),
  skills: document.querySelector("#skills-list"),
  facts: document.querySelector("#facts"),
  factsCounter: document.querySelector("#facts-counter"),
  factTemplate: document.querySelector("#fact-template"),
  rail: document.querySelector(".rail"),
  railTabs: document.querySelector(".rail-tabs"),
  railTabEvidence: document.querySelector("#rail-tab-evidence"),
  railEvidenceCount: document.querySelector("#rail-evidence-count"),
  scorecard: document.querySelector("#scorecard"),
  scorecardStatus: document.querySelector("#scorecard-status"),
  scorecardBody: document.querySelector("#scorecard-content"),
  toasts: document.querySelector("#toasts"),
  userMenu: document.querySelector("#user-menu"),
  userChip: document.querySelector("#user-chip"),
  userSheet: document.querySelector("#user-sheet"),
  userAvatar: document.querySelector("#user-avatar"),
  userName: document.querySelector("#user-name"),
  userEmail: document.querySelector("#user-email"),
  adminLink: document.querySelector("#admin-link"),
  signOut: document.querySelector("#sign-out"),
  voiceControls: document.querySelector("#voice-controls"),
  voiceStatus: document.querySelector("#voice-status"),
  voiceToggle: document.querySelector("#voice-toggle"),
  voiceToggleLabel: document.querySelector("#voice-toggle-label"),
  voiceConsent: document.querySelector("#voice-consent"),
  voiceStart: document.querySelector("#voice-start"),
  voiceCancel: document.querySelector("#voice-cancel"),
  voiceHud: document.querySelector("#voice-hud"),
  voiceStatePill: document.querySelector("#voice-state-pill"),
  voiceStateLabel: document.querySelector("#voice-state-label"),
  voiceGuidance: document.querySelector("#voice-guidance"),
  voiceReturnChat: document.querySelector("#voice-return-chat"),
  voiceTalk: document.querySelector("#voice-talk"),
  voiceTalkLabel: document.querySelector("#voice-talk-label"),
  captionText: document.querySelector("#voice-caption-text"),
};

/* --- API ---------------------------------------------------------------- */

class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body || {};
  }
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 401) {
    // The session expired mid-case; the server keeps the transcript.
    window.location.href = "/login?next=/practice";
    throw new ApiError("Your session expired. Please sign in again.", 401);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail || "Something went wrong. Please try again.", response.status, body);
  }
  return response.json();
}

/* The interviewer persona is fixed for the life of an attempt, because the score
 * is only meaningful against a known disclosure regime. So it has to be chosen
 * before the attempt exists: an explicit ?persona= wins for a shared link, then
 * the choice the candidate last made in the library, then the neutral default. */
const PERSONA_IDS = ["coached", "realistic", "pressure"];
const STORAGE_PERSONA = "leo.persona";

function chosenPersona() {
  const requested = new URLSearchParams(window.location.search).get("persona");
  if (PERSONA_IDS.includes(requested)) return requested;
  try {
    const stored = localStorage.getItem(STORAGE_PERSONA);
    if (PERSONA_IDS.includes(stored)) return stored;
  } catch {
    /* Private browsing can throw on access; the default is a fine answer. */
  }
  return "realistic";
}

const startAttempt = (caseId = state.selectedCaseId) =>
  request("/api/attempts", {
    method: "POST",
    body: JSON.stringify({
      ...(caseId ? { case_id: caseId } : {}),
      mode: chosenPersona(),
    }),
  });

/* --- Small helpers ------------------------------------------------------- */

const titleCase = (value) =>
  String(value || "")
    .replace(/[-_]/g, " ")
    .trim()
    .replace(/\b\w+/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .replace(/\bAnd\b/g, "&");

const humanise = (id) =>
  String(id)
    .split(".")
    .map((part) => part.replace(/[-_]/g, " "))
    .join(" · ")
    .replace(/^./, (char) => char.toUpperCase());

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function toast(message, kind = "info") {
  const item = node("div", `toast${kind === "info" ? "" : ` is-${kind}`}`, message);
  el.toasts.append(item);
  window.setTimeout(() => {
    item.classList.add("is-leaving");
    item.addEventListener("animationend", () => item.remove(), { once: true });
  }, 4600);
}

/* --- Rendering ---------------------------------------------------------- */

function renderAttempt(attempt) {
  const isNewAttempt = state.renderedId !== attempt.id;
  state.attempt = attempt;
  state.selectedCaseId = attempt.case.id;

  setPhaseState(attempt);
  setEndedState(attempt.ended);
  setReadyToEndState(attempt);
  renderCaseHeader(attempt);
  renderStage(attempt);
  renderFacts(attempt.facts, isNewAttempt);
  syncMessages(attempt, isNewAttempt);
  state.renderedId = attempt.id;
}

/* Before the case opens the room is a briefing, not an interview. The two
 * states are driven from one body class so the toolbar, the clock, the
 * composer and the copy cannot drift apart. */
function setPhaseState(attempt) {
  const preCase = !attempt.case_started && !attempt.ended;
  const readyToEnd = Boolean(attempt.ready_to_end && !attempt.ended);
  document.body.classList.toggle("is-pre-case", preCase);
  document.body.classList.toggle("is-ended", Boolean(attempt.ended));
  document.body.classList.toggle("is-ready-to-end", readyToEnd);

  if (el.stageLabel) {
    el.stageLabel.textContent = attempt.ended
      ? "Practice complete"
      : readyToEnd
        ? "Interview complete"
        : preCase
          ? "Before we start"
          : "Live interview";
  }
  if (el.sessionStatus) {
    el.sessionStatus.textContent = attempt.ended
      ? "Practice ended"
      : readyToEnd
        ? "Ready to finish"
        : preCase
          ? "Waiting for you"
          : "Case in progress";
  }
  el.input.placeholder = preCase
    ? "Reply to Leo, or start the case when you are ready…"
    : "Ask Leo a question or talk through your reasoning…";
}

function renderCaseHeader(attempt) {
  const { title, category, difficulty, skills_tested: skills } = attempt.case;
  document.title = `${title} · Leo`;
  el.title.textContent = title;
  /* Show the persona's name, not the raw mode value. The candidate has to be able
   * to tell which interviewer produced their score. */
  el.sessionMode.textContent = attempt.persona?.label || attempt.mode;
  if (attempt.persona?.blurb) el.sessionMode.title = attempt.persona.blurb;

  /* Duration and mode are already stated by the clock and the toolbar chip, so
   * the header keeps only what identifies the case. */
  const labels = [
    GENERIC_CATEGORIES.has(String(category).toLowerCase()) ? null : titleCase(category),
    `${titleCase(difficulty)} difficulty`,
    attempt.persona?.label || null,
  ].filter(Boolean);

  el.tags.replaceChildren(
    ...labels.map((label, position) => node("span", position === 0 ? "tag tag-accent" : "tag", label)),
  );

  el.skills.replaceChildren(...(skills || []).map((skill) => node("li", null, skill)));
}

function phaseList(attempt) {
  const authored = attempt.case?.phases;
  const phases = Array.isArray(authored) && authored.length ? [...authored] : [...DEFAULT_PHASES];
  if (attempt.stage && !phases.includes(attempt.stage)) phases.push(attempt.stage);
  return phases;
}

function buildStep(phaseId) {
  const meta = PHASE_META[phaseId] || { label: humanise(phaseId), note: "" };
  const step = node("li", "step");
  step.dataset.stage = phaseId;

  const bullet = node("span", "step-bullet");
  bullet.setAttribute("aria-hidden", "true");
  bullet.innerHTML = '<svg viewBox="0 0 24 24" class="icon icon-check"><path d="M5.5 12.6l4.2 4.2 8.8-9.6" /></svg>';

  const body = node("span", "step-body");
  body.append(node("span", "step-label", meta.label));
  if (meta.note) body.append(node("span", "step-note", meta.note));

  step.append(bullet, body);
  return step;
}

function renderStage(attempt) {
  const phases = phaseList(attempt);
  if (phases.join("|") !== state.phases.join("|")) {
    state.phases = phases;
    el.stepper.replaceChildren(...phases.map(buildStep));
  }

  const index = Math.max(0, phases.indexOf(attempt.stage));
  el.stageCounter.textContent = `${index + 1}/${phases.length}`;

  el.stepper.querySelectorAll(".step").forEach((step, position) => {
    step.classList.toggle("is-done", position < index);
    step.classList.toggle("is-current", position === index);
    step.classList.toggle("is-upcoming", position > index);
    if (position === index) step.setAttribute("aria-current", "step");
    else step.removeAttribute("aria-current");
  });
}

/* --- Evidence rail ------------------------------------------------------- */
/* The rail is working memory, not a second transcript. Newest first, so the
 * fact that just landed never needs scrolling to; that one card is open and
 * emphasised, the rest collapse to a single summary line the candidate can
 * scan; identifiers are demoted into the expanded detail. */

const factCategory = (id) => titleCase(String(id).split(".")[0]);

function factSummary(content) {
  const text = String(content).replace(/\s+/g, " ").trim();
  const sentence = text.match(/^.*?[.!?](?=\s|$)/);
  const summary = (sentence ? sentence[0] : text).trim();
  return summary.length > 96 ? `${summary.slice(0, 95).trimEnd()}…` : summary;
}

function buildFact(fact, position, total) {
  const item = el.factTemplate.content.firstElementChild.cloneNode(true);
  const toggle = item.querySelector(".fact-toggle");
  const detail = item.querySelector(".fact-detail");
  const isLatest = position === total - 1;
  const expanded = isLatest || state.expandedFactIds.has(fact.id);

  item.dataset.factId = fact.id;
  item.classList.toggle("is-latest", isLatest);
  item.classList.toggle("is-new", state.newFactIds.has(fact.id));

  item.querySelector(".fact-category").textContent = isLatest
    ? `Latest · ${factCategory(fact.id)}`
    : factCategory(fact.id);
  item.querySelector(".fact-summary").textContent = factSummary(fact.content);
  item.querySelector(".fact-content").textContent = fact.content;
  item.querySelector(".fact-index").textContent = `${String(position + 1).padStart(2, "0")} · ${humanise(fact.id)}`;

  toggle.setAttribute("aria-expanded", String(expanded));
  detail.hidden = !expanded;
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    detail.hidden = !open;
    if (open) state.expandedFactIds.add(fact.id);
    else state.expandedFactIds.delete(fact.id);
  });

  return item;
}

function renderFacts(facts, isNewAttempt) {
  if (isNewAttempt) {
    state.knownFactIds = new Set();
    state.newFactIds = new Set();
    state.expandedFactIds = new Set();
  }

  const released = facts.filter((fact) => !state.knownFactIds.has(fact.id));
  if (released.length && !isNewAttempt) {
    state.newFactIds = new Set(released.map((fact) => fact.id));
  }
  state.knownFactIds = new Set(facts.map((fact) => fact.id));

  el.factsCounter.textContent = String(facts.length);
  el.factsCounter.classList.toggle("is-live", facts.length > 0);
  if (el.railEvidenceCount) el.railEvidenceCount.textContent = String(facts.length);
  if (el.railTabEvidence) {
    el.railTabEvidence.classList.toggle("has-new", state.newFactIds.size > 0);
  }

  /* A voice call resyncs every 1.5s. Rebuilding the list each time would
   * collapse whatever the candidate had just opened, so only the signature
   * changing earns a rebuild. */
  const signature = `${facts.map((fact) => fact.id).join("|")}#${[...state.newFactIds].join("|")}`;
  if (signature === state.factsSignature && !isNewAttempt) return;
  state.factsSignature = signature;

  if (!facts.length) {
    const empty = node("div", "facts-empty");
    empty.append(
      node("strong", null, "Nothing released yet"),
      node("span", null, "Ask a sharp, specific question and Leo hands over what it earns."),
    );
    el.facts.replaceChildren(empty);
    return;
  }

  const cards = facts.map((fact, position) => buildFact(fact, position, facts.length)).reverse();
  if (released.length && !isNewAttempt) cards[0]?.classList.add("is-entering");
  el.facts.replaceChildren(...cards);
  el.rail.scrollTop = 0;
}

function buildMessage(message, index) {
  const template = document.querySelector("#message-template");
  const item = template.content.firstElementChild.cloneNode(true);
  item.classList.add(message.role);
  if (index === 0 && message.role === "interviewer") item.classList.add("is-opening");
  item.querySelector(".message-role").textContent = message.role === "candidate" ? "You" : "Leo";
  // Hide legacy delivery annotations from transcripts created before the
  // Custom LLM speech path stopped treating them as literal words.
  item.querySelector(".message-content").textContent = String(message.content).replace(AUDIO_CUE, "");
  return item;
}

/* Append-only sync so existing bubbles never re-animate or flicker. */
function syncMessages(attempt, isNewAttempt) {
  const changedMessage = state.renderedMessages.some((message, index) => {
    const current = attempt.messages[index];
    return !current || current.role !== message.role || current.content !== message.content;
  });
  const stale = isNewAttempt || attempt.messages.length < state.renderedCount || changedMessage;
  /* Measured before the DOM grows, otherwise a long reply always reads as
   * "the candidate has scrolled away" and the transcript stops following. */
  const wasFollowing = isNearBottom();
  if (stale) {
    el.messages.replaceChildren();
    state.renderedCount = 0;
  }

  el.messages.querySelector(".is-typing")?.remove();
  el.messages.querySelector(".transcript-state")?.remove();
  adoptPendingTurn(attempt);
  el.messages.querySelectorAll("[data-pending]").forEach((item) => item.remove());

  const pending = attempt.messages.slice(state.renderedCount);
  if (pending.length) {
    el.messages.append(...pending.map((message, offset) => buildMessage(message, state.renderedCount + offset)));
    state.renderedCount = attempt.messages.length;
  }
  state.renderedMessages = attempt.messages.map(({ role, content }) => ({ role, content }));
  if (stale) {
    /* A fresh brief is read top-down; a resumed transcript resumes at the end. */
    if (attempt.messages.length <= 1) el.scroll.scrollTop = 0;
    else scrollToLatest({ force: true, instant: true });
  } else if (wasFollowing) {
    scrollToLatest({ force: true });
  }
}

/* The optimistic bubble already on screen is the same message the server just
 * stored, so keep the node and count it as rendered rather than replaying it. */
function adoptPendingTurn(attempt) {
  const pending = el.messages.querySelector("[data-pending]");
  if (!pending) return;
  const confirmed = attempt.messages[state.renderedCount];
  const text = pending.querySelector(".message-content").textContent;
  if (confirmed?.role === "candidate" && confirmed.content === text) {
    delete pending.dataset.pending;
    state.renderedCount += 1;
  }
}

function clearPending() {
  el.messages.querySelectorAll("[data-pending]").forEach((item) => item.remove());
  el.messages.querySelector(".is-typing")?.remove();
  el.messages.querySelector(".transcript-state")?.remove();
}

function showTranscriptState(text, { spinner = true, retry = false } = {}) {
  el.messages.replaceChildren();
  state.renderedCount = 0;
  state.renderedMessages = [];
  const wrap = node("div", "transcript-state");
  if (spinner) wrap.append(node("span", "orbit"));
  wrap.append(node("p", null, text));
  if (retry) {
    const button = node("button", "button button-solid", "Try again");
    button.type = "button";
    button.addEventListener("click", () => boot());
    wrap.append(button);
  }
  el.messages.append(wrap);
}

function isNearBottom(threshold = 160) {
  return el.scroll.scrollHeight - el.scroll.scrollTop - el.scroll.clientHeight <= threshold;
}

const prefersReducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function scrollToLatest({ force = false, instant = false } = {}) {
  if (!force && !isNearBottom()) return;
  const top = el.scroll.scrollHeight;
  /* A hidden tab never animates, so jump rather than queue a scroll that
   * would only land when the candidate comes back. */
  if (instant || document.hidden || prefersReducedMotion()) el.scroll.scrollTop = top;
  else el.scroll.scrollTo({ top, behavior: "smooth" });
}

el.scroll.addEventListener("scroll", () => {
  el.transcript.classList.toggle("is-scrolled", el.scroll.scrollTop > 6);
});

/* --- Composer ----------------------------------------------------------- */

function autoGrow() {
  el.input.style.height = "auto";
  el.input.style.height = `${Math.min(el.input.scrollHeight, MAX_COMPOSER_HEIGHT)}px`;
}

function syncSendState() {
  el.send.disabled =
    state.sending ||
    !el.input.value.trim() ||
    Boolean(state.attempt?.ended) ||
    Boolean(state.attempt?.ready_to_end);
}

el.input.addEventListener("input", () => {
  autoGrow();
  syncSendState();
});

el.input.addEventListener("keydown", (event) => {
  const send = event.key === "Enter" && (!event.shiftKey || event.metaKey || event.ctrlKey);
  if (!send) return;
  event.preventDefault();
  el.form.requestSubmit();
});

el.form.addEventListener("submit", (event) => {
  event.preventDefault();
  const content = el.input.value.trim();
  if (!content || state.sending || !state.attempt || state.attempt.ended || state.attempt.ready_to_end) return;
  sendTurn(content, crypto.randomUUID());
});

/* This is an explicit UI decision, not an inference from a keyword. The
 * onboarding model still owns the server-side readiness transition; the button
 * simply sends the same clear go-ahead a candidate would otherwise type. */
el.beginCase?.addEventListener("click", () => {
  if (!state.attempt || state.sending || state.attempt.ended || state.attempt.case_started) return;
  sendTurn("I'm ready to begin.", crypto.randomUUID());
});

function setSending(sending) {
  state.sending = sending;
  el.send.classList.toggle("is-sending", sending);
  el.messages.setAttribute("aria-busy", String(sending));
  syncSendState();
}

function showPendingTurn(content) {
  const pending = buildMessage({ role: "candidate", content }, state.renderedCount);
  pending.dataset.pending = "true";
  const typing = document.querySelector("#typing-template").content.firstElementChild.cloneNode(true);
  el.messages.append(pending, typing);
  scrollToLatest({ force: true });
}

async function sendTurn(content, turnId, hasRetried = false) {
  setSending(true);
  el.input.value = "";
  autoGrow();
  showPendingTurn(content);

  try {
    const data = await request(`/api/attempts/${state.attempt.id}/turn`, {
      method: "POST",
      body: JSON.stringify({ content, turn_id: turnId }),
    });
    renderAttempt(data.attempt);
    if (data.new_facts?.length) {
      toast(`${data.new_facts.length} new fact${data.new_facts.length > 1 ? "s" : ""} released`);
    }
  } catch (error) {
    const recoverable = !hasRetried && (error instanceof TypeError || error.status === 404);
    if (recoverable && (await recoverSession())) {
      return sendTurn(content, turnId, true);
    }
    clearPending();
    el.input.value = content;
    autoGrow();
    toast(error.message || "That response did not reach Leo.", "error");
  } finally {
    setSending(false);
    el.input.focus();
  }
}

/* A dev reload or a lost attempt should not cost the candidate their turn. */
async function recoverSession() {
  try {
    renderAttempt(await request(`/api/attempts/${state.attempt.id}`));
    return true;
  } catch (error) {
    if (error.status !== 404) return false;
    try {
      const attempt = await startAttempt();
      persistSession(attempt.id, Date.now(), attempt.case.id);
      renderAttempt(attempt);
      toast("Your previous session expired, so a fresh case has started.", "warning");
      return true;
    } catch {
      return false;
    }
  }
}

/* --- Ending and restarting ---------------------------------------------- */

function setEndedState(ended) {
  el.form.classList.toggle("hidden", Boolean(ended));
  el.endedBar.classList.toggle("hidden", !ended);
  el.endButton.classList.toggle("hidden", Boolean(ended));
  el.input.disabled = Boolean(ended);
  if (state.attempt) {
    const debriefUrl = `/attempts/${state.attempt.id}/debrief`;
    if (el.viewDebriefBtn) el.viewDebriefBtn.href = debriefUrl;
    if (el.dialogDebriefBtn) el.dialogDebriefBtn.href = debriefUrl;
  }
  if (ended) stopTimer();
  syncSendState();
}

function setReadyToEndState(attempt) {
  const ready = Boolean(attempt.ready_to_end && !attempt.ended);
  el.closePrompt?.classList.toggle("hidden", !ready);
  el.input.disabled = Boolean(attempt.ended || ready);
  if (el.voiceToggle) el.voiceToggle.disabled = ready;
  if (el.endButton && !state.endArmedTimer) {
    el.endButton.textContent = ready ? "End case" : "End practice";
  }
  if (ready && !state.endRedirectTimer && !state.ending) {
    // Let Leo's final message paint before replacing the room with the debrief.
    // The visible action remains available as an immediate fallback.
    state.endRedirectTimer = window.setTimeout(() => {
      state.endRedirectTimer = null;
      void finishAttempt();
    }, 700);
  } else if (!ready && state.endRedirectTimer) {
    window.clearTimeout(state.endRedirectTimer);
    state.endRedirectTimer = null;
  }
  syncSendState();
}

/* --- Voice mode --------------------------------------------------------- */

/* The caption is the state of the recording in progress, nothing else.
 *
 * It used to fall back to echoing the last transcript message, which meant the
 * HUD permanently mirrored the conversation below it. Recognition is now batch,
 * so there is no interim text to show either: what belongs here is how long the
 * candidate has been speaking and how much of the cap is left. Once a turn is
 * submitted the transcript below is the record. */
/* Roughly two lines at the caption's size. Long enough to confirm recognition
 * is tracking, short enough that the HUD never grows. */
const CAPTION_TAIL = 150;

function setVoiceCaption(text = "") {
  if (!el.captionText) return;
  let visible = text;
  if (visible.length > CAPTION_TAIL) {
    // Keep the tail, not the head. Thirty seconds into an answer, the opening
    // words are worthless; the point of a live caption is confirming that what
    // you just said was heard. Cut on a word boundary so it does not flicker
    // mid-word as each interim update arrives.
    const tail = visible.slice(-CAPTION_TAIL);
    const boundary = tail.indexOf(" ");
    visible = `…${boundary === -1 ? tail : tail.slice(boundary + 1)}`;
  }
  // Never innerHTML: this carries speech-recognition output.
  el.captionText.textContent = visible;
  el.captionText.classList.toggle("is-empty", !visible);
}

function clearVoiceCaption() {
  setVoiceCaption("");
}

function setVoiceState(status = "chat") {
  const active = [
    "connecting",
    "listening",
    "speaking",
    "idle",
    "recording",
    "transcribing",
    "thinking",
  ].includes(status);
  const labels = {
    chat: "Chat",
    connecting: "Connecting...",
    listening: "Leo is listening",
    speaking: "Leo is speaking",
    reconnecting: "Reconnecting...",
    // Push-to-talk states. The candidate owns the turn boundary, so the label
    // has to say whose turn it is at every moment.
    idle: "Press space to speak",
    recording: "Listening to you",
    transcribing: "Transcribing...",
    thinking: "Leo is thinking",
  };
  const guidance = {
    connecting: "Establishing encrypted WebRTC audio channel with Leo...",
    listening: "Speak naturally · Formulate hypotheses · Ask for facts",
    speaking: "Listen closely to the released evidence and interviewer steer",
    chat: "Chat mode",
    idle: "Press space to take the floor · press it again to send · Esc discards",
    recording: "Recording. Press space when you have finished speaking.",
    transcribing: "Transcribing your turn...",
    thinking: "Leo is composing an answer",
  };

  el.voiceStatus.textContent = labels[status] || "Chat";
  // The toggle used to be labelled from the last status event while its click
  // handler asked the island whether it was active. When those two disagreed the
  // button read "Return to chat" and opened the start-voice dialog. One flag now
  // drives both.
  state.voiceActive = active;
  // Write the label, not the button: textContent would delete the mic icon.
  if (el.voiceToggleLabel) {
    el.voiceToggleLabel.textContent = active ? "Return to chat" : "Start voice";
  } else {
    el.voiceToggle.textContent = active ? "Return to chat" : "Start voice";
  }
  el.form.classList.toggle("is-voice-active", active);

  const hud = el.voiceHud || el.voiceStage;
  if (hud) {
    hud.classList.toggle("hidden", !active);
    hud.className = `voice-hud ${active ? "" : "hidden"} is-${status}`;
  }
  if (el.voiceStateLabel) {
    el.voiceStateLabel.textContent = labels[status] || "Connecting with Leo...";
  }
  if (el.voiceGuidance && guidance[status]) {
    el.voiceGuidance.textContent = guidance[status];
  }
  if (el.voiceTalkLabel) {
    el.voiceTalkLabel.textContent = status === "recording" ? "Yield the floor" : "Hold the floor";
  }
  if (el.voiceTalk) {
    el.voiceTalk.classList.toggle("is-recording", status === "recording");
    // Leo's turn is not interruptible by the button, only by barge-in, so the
    // control is disabled while a transcript or an answer is still resolving.
    el.voiceTalk.disabled = ["connecting", "transcribing", "thinking"].includes(status);
  }

  // Interim speech belongs to the turn being spoken. Leaving the last utterance
  // on screen while Leo answers reads as though he is still hearing it.
  if (!["recording", "transcribing"].includes(status)) clearVoiceCaption();
  if (active) {
    scrollToLatest({ force: true });
  }
}

/* Which transport the server has configured. "realtime" is push-to-talk over
 * raw Scribe and TTS sockets; "custom" and "native" are the ElevenLabs Agent. */
let voiceMode = null;

async function loadVoiceAvailability() {
  try {
    const voice = await request("/api/voice/status");
    el.voiceControls.classList.toggle("hidden", !voice.ready);
    if (!voice.ready) {
      setVoiceState("chat");
      return;
    }
    voiceMode = voice.mode;
    // Import the island only once voice is known to work, so a chat-only
    // deployment never downloads a transport it cannot use.
    await import(voiceMode === "realtime" ? "/static/voice-realtime.js" : "/static/voice.js");
    // Push-to-talk only exists in realtime mode. The Agent transports detect
    // turns themselves, so a floor control there would be a lie.
    const pushToTalk = voiceMode === "realtime";
    el.voiceTalk?.classList.toggle("hidden", !pushToTalk);
    if (el.voiceToggle) {
      el.voiceToggle.title = pushToTalk
        ? "Start a spoken case. Press space to take and yield the floor."
        : "Start a spoken case with Leo.";
    }
  } catch {
    // Voice is progressive enhancement. A failed capability check must never
    // prevent the established text room from loading.
    el.voiceControls.classList.add("hidden");
  }
}

async function returnToChat() {
  try {
    await window.LeoVoice?.end?.();
  } finally {
    setVoiceState("chat");
    if (!state.attempt?.ended) el.input.focus();
  }
}

el.voiceReturnChat?.addEventListener("click", returnToChat);

el.voiceToggle.addEventListener("click", async () => {
  // Either source saying voice is on means leave it. returnToChat is safe to
  // call when it is already off, so the worst case is a no-op, whereas guessing
  // wrong the other way reopens the consent dialog mid-call.
  if (state.voiceActive || window.LeoVoice?.active) {
    await returnToChat();
    return;
  }
  if (typeof el.voiceConsent.showModal === "function") el.voiceConsent.showModal();
  else await startVoice();
});

el.voiceCancel.addEventListener("click", () => el.voiceConsent.close());
el.voiceStart.addEventListener("click", async () => {
  el.voiceConsent.close();
  await startVoice();
});

async function startVoice() {
  if (!state.attempt || state.attempt.ended || state.attempt.ready_to_end || !window.LeoVoice) return;
  setVoiceState("connecting");
  el.voiceToggle.disabled = true;
  try {
    await window.LeoVoice.start(state.attempt.id);
  } catch (error) {
    setVoiceState("chat");
    toast(error.message || "Voice could not start. You can continue in chat.", "error");
  } finally {
    el.voiceToggle.disabled = false;
  }
}

window.addEventListener("leo:voice-status", (event) => {
  const status = event.detail?.status;
  const errorReason = event.detail?.error;
  if (status === "disconnected") {
    setVoiceState("chat");
    if (!state.attempt?.ended) {
      toast(errorReason ? `Voice disconnected: ${errorReason}` : "Voice ended. You can continue in chat.", "warning");
    }
    return;
  }
  if ((status === "connected" || status === "listening") && state.attempt?.ready_to_end) {
    void returnToChat();
    return;
  }
  if (status === "connected") setVoiceState("listening");
  if (
    ["speaking", "listening", "connecting", "idle", "recording", "transcribing", "thinking"].includes(
      status,
    )
  ) {
    setVoiceState(status);
  }
  if (errorReason && status !== "disconnected") toast(errorReason, "warning");
});

/* --- Push-to-talk ------------------------------------------------------- */

/* Live transcription of the candidate, before any turn has been submitted. */
window.addEventListener("leo:voice-caption", (event) => {
  setVoiceCaption(event.detail?.text || "");
});

const clock = (seconds) => {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
};

/* Recording length against the cap. A recording with no visible length is
 * unnerving, and the limit has to be legible before it is reached. */
window.addEventListener("leo:voice-recording", (event) => {
  const { seconds = 0, limit = 120 } = event.detail || {};
  const remaining = limit - seconds;
  setVoiceCaption(
    remaining <= 15
      ? `Recording ${clock(seconds)} · ${clock(remaining)} left before this turn is sent`
      : `Recording ${clock(seconds)} of ${clock(limit)}`,
  );
});

/* The transcript the candidate committed, shown before Leo's reply lands. */
window.addEventListener("leo:voice-candidate", (event) => {
  const text = event.detail?.text;
  if (text) showPendingTurn(text);
});

window.addEventListener("leo:voice-transcript", (event) => {
  const attempt = event.detail?.attempt;
  if (attempt) renderAttempt(attempt);
});

/* A space typed into the composer must stay a space. Push-to-talk only claims
 * the key when focus is not in a field and voice is actually live. */
function spacebarIsForTalking(event) {
  if (event.code !== "Space" || event.repeat) return false;
  if (event.metaKey || event.ctrlKey || event.altKey) return false;
  if (!window.LeoVoice?.active || typeof window.LeoVoice.toggleTalking !== "function") return false;
  const target = event.target;
  if (!target) return true;
  if (target.isContentEditable) return false;
  return !["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(target.tagName);
}

document.addEventListener("keydown", async (event) => {
  if (event.key === "Escape" && window.LeoVoice?.isRecording) {
    event.preventDefault();
    await window.LeoVoice.discardRecording();
    return;
  }
  if (!spacebarIsForTalking(event)) return;
  // Without this the transcript pane scrolls on every turn.
  event.preventDefault();
  await window.LeoVoice.toggleTalking();
});

el.voiceTalk?.addEventListener("click", async () => {
  if (window.LeoVoice?.active) await window.LeoVoice.toggleTalking();
});

window.addEventListener("leo:voice-sync", async () => {
  if (!state.attempt || state.attempt.ended) return;
  try {
    const updated = await request(`/api/attempts/${state.attempt.id}`);
    renderAttempt(updated);
  } catch {
    // The provider can disconnect independently; the chat UI remains usable.
  }
});

function endDisposition() {
  return state.attempt?.substantive_turns >= MIN_SUBSTANTIVE_TURNS ? "scored" : "abandoned";
}

function disarmEndButton() {
  window.clearTimeout(state.endArmedTimer);
  state.endArmedTimer = null;
  el.endButton.classList.remove("is-armed");
  el.endButton.textContent = state.attempt?.ready_to_end ? "End case" : "End practice";
}

async function finishAttempt() {
  if (!state.attempt || state.attempt.ended || state.ending) return;

  window.clearTimeout(state.endRedirectTimer);
  state.endRedirectTimer = null;
  state.ending = true;
  disarmEndButton();
  el.endButton.disabled = true;
  if (el.completeAttempt) {
    el.completeAttempt.disabled = true;
    el.completeAttempt.classList.add("is-loading");
    const label = el.completeAttempt.querySelector(".case-close-action-label");
    if (label) label.textContent = "Opening your debrief";
  }
  try {
    await returnToChat();
    const data = await request(`/api/attempts/${state.attempt.id}/end`, {
      method: "POST",
      body: JSON.stringify({ disposition: endDisposition() }),
    });
    window.location.href = data.next_url || data.debrief_url || "/profile";
  } catch (error) {
    toast(error.message || "The practice could not be ended.", "error");
    el.endButton.disabled = false;
    if (el.completeAttempt) {
      el.completeAttempt.disabled = false;
      el.completeAttempt.classList.remove("is-loading");
      const label = el.completeAttempt.querySelector(".case-close-action-label");
      if (label) label.textContent = "Try opening debrief again";
    }
  } finally {
    state.ending = false;
  }
}

el.completeAttempt?.addEventListener("click", finishAttempt);

el.endButton.addEventListener("click", async () => {
  if (!state.attempt || state.attempt.ended || state.ending) return;

  if (state.attempt.ready_to_end) {
    await finishAttempt();
    return;
  }

  if (!state.endArmedTimer) {
    el.endButton.classList.add("is-armed");
    el.endButton.textContent = endDisposition() === "abandoned" ? "Save without scoring" : "Confirm end";
    state.endArmedTimer = window.setTimeout(disarmEndButton, 6000);
    return;
  }

  await finishAttempt();
});

function renderScorecard(scorecard) {
  const debriefUrl = `/attempts/${state.attempt.id}/debrief`;
  const complete = scorecard.status === "complete";
  el.scorecardStatus.textContent = complete ? "Complete" : "Partial";
  el.scorecardStatus.classList.toggle("is-partial", !complete);

  const ctaWrap = node("div", "debrief-rail-cta");
  ctaWrap.style.padding = "10px";
  ctaWrap.style.margin = "10px 0";
  ctaWrap.style.background = "var(--brand-tint)";
  ctaWrap.style.borderRadius = "var(--r-md)";
  ctaWrap.style.border = "1px solid var(--line-base)";

  const ctaBtn = node("a", "btn btn-primary btn-sm", "View 10x Debrief Report →");
  ctaBtn.href = debriefUrl;
  ctaBtn.style.display = "block";
  ctaBtn.style.textAlign = "center";
  ctaBtn.style.width = "100%";
  ctaBtn.style.background = "var(--brand-primary)";
  ctaBtn.style.color = "#ffffff";
  ctaWrap.append(ctaBtn);

  const rows = scorecard.dimensions.map((dimension) => {
    const row = node("div", "score-row");
    const head = node("div", "score-head");
    head.append(
      node("p", "score-name", dimension.name),
      node("span", `band band-${dimension.band.toLowerCase()}`, dimension.band),
    );
    row.append(head, node("p", "score-evidence", dimension.evidence));
    return row;
  });

  const drill = node("div", "next-drill");
  drill.append(node("p", "micro-label", "Next drill"), node("p", null, scorecard.next_drill));

  el.scorecardBody.replaceChildren(ctaWrap, ...rows, drill);
  el.scorecard.classList.remove("hidden");
  el.rail.prepend(el.scorecard);
  el.rail.scrollTop = 0;
}

el.restart.addEventListener("click", async () => {
  el.restart.disabled = true;
  el.scorecard.classList.add("hidden");
  el.rail.append(el.scorecard);
  showTranscriptState("Setting up a fresh case…");
  try {
    const attempt = await startAttempt();
    persistSession(attempt.id, Date.now(), attempt.case.id);
    renderAttempt(attempt);
    el.input.focus();
  } catch (error) {
    toast(error.message || "A new case could not be started.", "error");
    showTranscriptState("That case could not be loaded.", { spinner: false, retry: true });
  } finally {
    el.restart.disabled = false;
  }
});

/* --- Signed-in candidate ------------------------------------------------ */

async function loadViewer() {
  try {
    const { user } = await request("/api/me");
    state.viewer = user;
    renderViewer(user);
  } catch {
    /* A 401 has already redirected; anything else leaves the menu hidden. */
  }
}

function renderViewer(user) {
  const initial = (user.name || user.email || "?").trim()[0].toUpperCase();
  if (user.picture) {
    el.userAvatar.style.backgroundImage = `url("${user.picture}")`;
    el.userAvatar.textContent = "";
  } else {
    el.userAvatar.textContent = initial;
  }
  el.userName.textContent = user.name || user.email;
  el.userEmail.textContent = user.email;
  el.adminLink.classList.toggle("hidden", !user.is_admin);
  el.userMenu.classList.remove("hidden");
}

function setMenuOpen(open) {
  el.userSheet.classList.toggle("hidden", !open);
  el.userChip.setAttribute("aria-expanded", String(open));
}

if (el.userChip && !el.userChip.dataset.navBound) {
  el.userChip.dataset.navBound = "true";
  el.userChip.addEventListener("click", (event) => {
    event.stopPropagation();
    setMenuOpen(el.userSheet.classList.contains("hidden"));
  });

  document.addEventListener("click", (event) => {
    if (!el.userMenu.contains(event.target)) setMenuOpen(false);
  });
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") setMenuOpen(false);
});

el.signOut.addEventListener("click", async () => {
  el.signOut.disabled = true;
  try {
    await fetch("/auth/logout", { method: "POST" });
  } finally {
    // The transcript stays on the server; only this browser's session ends.
    localStorage.removeItem(STORAGE_SESSION);
    window.location.href = "/login";
  }
});

/* --- Session persistence ------------------------------------------------ */

function persistSession(id, startedAt, caseId) {
  localStorage.setItem(STORAGE_SESSION, JSON.stringify({ id, startedAt, caseId }));
}

function readSession() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_SESSION) || "null");
    return stored && typeof stored.id === "string" ? stored : null;
  } catch {
    return null;
  }
}

/* --- Boot --------------------------------------------------------------- */

async function boot() {  showTranscriptState("Connecting you to Leo…");
  syncSendState();
  await loadViewer();
  await loadVoiceAvailability();

  const requestedCaseId = new URLSearchParams(window.location.search).get("case");
  const requestedAttemptId = new URLSearchParams(window.location.search).get("attempt");
  if (requestedCaseId) state.selectedCaseId = requestedCaseId;

  // The Case Library supplies this durable attempt ID for an in-progress case.
  // It takes precedence over browser-local state, so a candidate can resume on
  // another device without accidentally creating a duplicate attempt.
  if (requestedAttemptId) {
    try {
      const attempt = await request(`/api/attempts/${requestedAttemptId}`);
      const startedAt = Date.now();
      persistSession(attempt.id, startedAt, attempt.case.id);
      renderAttempt(attempt);
      if (attempt.ended) {
        window.location.href = `/attempts/${attempt.id}/debrief`;
        return;
      }
      el.input.focus();
      return;
    } catch (error) {
      toast(error.message || "That saved case could not be resumed.", "error");
    }
  }

  const stored = readSession();
  // A direct catalogue selection intentionally starts a new attempt. A reload
  // without a case query remains resumable, which avoids losing interview work.
  if (stored && !requestedCaseId) {
    try {
      const attempt = await request(`/api/attempts/${stored.id}`);
      const startedAt = Number(stored.startedAt) || Date.now();
      persistSession(attempt.id, startedAt, attempt.case.id);
      renderAttempt(attempt);
      if (attempt.ended) {
        // An ended attempt lives on its debrief page; that page handles
        // generating a missing report and falling back gracefully.
        window.location.href = `/attempts/${attempt.id}/debrief`;
        return;
      }
      toast("Picked up where you left off.");
      el.input.focus();
      return;
    } catch {
      localStorage.removeItem(STORAGE_SESSION);
    }
  }

  try {
    const attempt = await startAttempt();
    persistSession(attempt.id, Date.now(), attempt.case.id);
    renderAttempt(attempt);
    el.input.focus();
  } catch (error) {
    // A conflict here means this exact case is already open under an attempt
    // id we didn't have locally (another tab, a cleared/other-device session).
    // Resume that attempt instead of dead-ending the candidate on the 409.
    const openAttemptId = error.status === 409 ? error.body?.attempt_id : null;
    if (openAttemptId) {
      try {
        const attempt = await request(`/api/attempts/${openAttemptId}`);
        persistSession(attempt.id, Date.now(), attempt.case.id);
        renderAttempt(attempt);
        if (attempt.ended) {
          window.location.href = `/attempts/${attempt.id}/debrief`;
          return;
        }
        toast("Picked up where you left off.");
        el.input.focus();
        return;
      } catch {
        /* Fall through to the conflict error below. */
      }
    }
    el.title.textContent = "Case unavailable";
    showTranscriptState(error.message || "The case could not be loaded.", { spinner: false, retry: true });
  }
}

boot();
