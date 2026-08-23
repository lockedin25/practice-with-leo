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
const DURATION_MINUTES = 30;
const STORAGE_SESSION = "casecall:session";
const MAX_COMPOSER_HEIGHT = 190;

const state = {
  viewer: null,
  attempt: null,
  renderedId: null,
  renderedCount: 0,
  knownFactIds: new Set(),
  phases: [],
  sending: false,
  startedAt: null,
  timerId: null,
  timeUpAnnounced: false,
  endArmedTimer: null,
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
  endButton: document.querySelector("#end-attempt"),
  restart: document.querySelector("#restart-attempt"),
  title: document.querySelector("#case-title"),
  tags: document.querySelector("#case-tags"),
  sessionMode: document.querySelector("#session-mode"),
  stepper: document.querySelector("#stepper"),
  stageCounter: document.querySelector("#stage-counter"),
  skills: document.querySelector("#skills-list"),
  facts: document.querySelector("#facts"),
  factsCounter: document.querySelector("#facts-counter"),
  rail: document.querySelector(".rail"),
  scorecard: document.querySelector("#scorecard"),
  scorecardStatus: document.querySelector("#scorecard-status"),
  scorecardBody: document.querySelector("#scorecard-content"),
  timer: document.querySelector("#timer"),
  timerValue: document.querySelector("#timer-value"),
  toasts: document.querySelector("#toasts"),
  userMenu: document.querySelector("#user-menu"),
  userChip: document.querySelector("#user-chip"),
  userSheet: document.querySelector("#user-sheet"),
  userAvatar: document.querySelector("#user-avatar"),
  userName: document.querySelector("#user-name"),
  userEmail: document.querySelector("#user-email"),
  adminLink: document.querySelector("#admin-link"),
  signOut: document.querySelector("#sign-out"),
};

/* --- API ---------------------------------------------------------------- */

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
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
    throw new ApiError(body.detail || "Something went wrong. Please try again.", response.status);
  }
  return response.json();
}

const startAttempt = (caseId = state.selectedCaseId) =>
  request("/api/attempts", {
    method: "POST",
    body: JSON.stringify({
      ...(caseId ? { case_id: caseId } : {}),
      mode: "realistic",
      duration_minutes: DURATION_MINUTES,
    }),
  });

/* --- Small helpers ------------------------------------------------------- */

const titleCase = (value) => String(value || "").replace(/(^|[\s·/-])([a-z])/g, (_, edge, char) => edge + char.toUpperCase());

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

/* --- Timer -------------------------------------------------------------- */

function startTimer(startedAt) {
  state.startedAt = startedAt;
  state.timeUpAnnounced = false;
  window.clearInterval(state.timerId);
  tickTimer();
  state.timerId = window.setInterval(tickTimer, 1000);
}

function stopTimer() {
  window.clearInterval(state.timerId);
  state.timerId = null;
}

function tickTimer() {
  const elapsed = Math.floor((Date.now() - state.startedAt) / 1000);
  const remaining = Math.max(0, DURATION_MINUTES * 60 - elapsed);
  const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
  const seconds = String(remaining % 60).padStart(2, "0");

  el.timerValue.textContent = `${minutes}:${seconds}`;
  el.timer.classList.toggle("is-warning", remaining <= 300 && remaining > 60);
  el.timer.classList.toggle("is-critical", remaining <= 60);

  if (remaining === 0 && !state.timeUpAnnounced) {
    state.timeUpAnnounced = true;
    stopTimer();
    if (!state.attempt?.ended) {
      toast("Time is up. Land your recommendation, then end the practice.", "warning");
    }
  }
}

/* --- Rendering ---------------------------------------------------------- */

function renderAttempt(attempt) {
  const isNewAttempt = state.renderedId !== attempt.id;
  state.attempt = attempt;
  state.selectedCaseId = attempt.case.id;

  setEndedState(attempt.ended);
  renderCaseHeader(attempt);
  renderStage(attempt);
  renderFacts(attempt.facts, isNewAttempt);
  syncMessages(attempt, isNewAttempt);
  state.renderedId = attempt.id;
}

function renderCaseHeader(attempt) {
  const { title, category, difficulty, supported_durations: durations, skills_tested: skills } = attempt.case;
  document.title = `${title} · Leo`;
  el.title.textContent = title;
  el.sessionMode.textContent = attempt.mode;

  const labels = [
    GENERIC_CATEGORIES.has(String(category).toLowerCase()) ? null : titleCase(category),
    `${titleCase(difficulty)} difficulty`,
    `${durations?.[0] ?? DURATION_MINUTES} minutes`,
    `${titleCase(attempt.mode)} mode`,
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

function renderFacts(facts, isNewAttempt) {
  if (isNewAttempt) state.knownFactIds = new Set();

  el.factsCounter.textContent = String(facts.length);
  el.factsCounter.classList.toggle("is-live", facts.length > 0);

  if (!facts.length) {
    const empty = node("div", "facts-empty");
    empty.append(
      node("strong", null, "Nothing released yet"),
      node("span", null, "Ask a sharp, specific question and Leo will hand over what it earns."),
    );
    el.facts.replaceChildren(empty);
    return;
  }

  el.facts.replaceChildren(
    ...facts.map((fact, position) => {
      const isNew = !state.knownFactIds.has(fact.id) && !isNewAttempt;
      const card = node("article", `fact${isNew ? " is-new" : ""}`);
      card.append(
        node("span", "fact-index", `${String(position + 1).padStart(2, "0")} · ${humanise(fact.id)}`),
        node("p", "fact-content", fact.content),
      );
      return card;
    }),
  );

  state.knownFactIds = new Set(facts.map((fact) => fact.id));
}

function buildMessage(message, index) {
  const template = document.querySelector("#message-template");
  const item = template.content.firstElementChild.cloneNode(true);
  item.classList.add(message.role);
  if (index === 0 && message.role === "interviewer") item.classList.add("is-opening");
  item.querySelector(".message-role").textContent = message.role === "candidate" ? "You" : "Leo";
  item.querySelector(".message-content").textContent = message.content;
  return item;
}

/* Append-only sync so existing bubbles never re-animate or flicker. */
function syncMessages(attempt, isNewAttempt) {
  const stale = isNewAttempt || attempt.messages.length < state.renderedCount;
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
  el.send.disabled = state.sending || !el.input.value.trim() || Boolean(state.attempt?.ended);
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
  if (!content || state.sending || !state.attempt || state.attempt.ended) return;
  sendTurn(content, crypto.randomUUID());
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
      startTimer(Date.now());
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
  if (ended) stopTimer();
  syncSendState();
}

function disarmEndButton() {
  window.clearTimeout(state.endArmedTimer);
  state.endArmedTimer = null;
  el.endButton.classList.remove("is-armed");
  el.endButton.textContent = "End practice";
}

el.endButton.addEventListener("click", async () => {
  if (!state.attempt || state.attempt.ended) return;

  if (!state.endArmedTimer) {
    el.endButton.classList.add("is-armed");
    el.endButton.textContent = "Confirm end";
    state.endArmedTimer = window.setTimeout(disarmEndButton, 6000);
    return;
  }

  disarmEndButton();
  el.endButton.disabled = true;
  try {
    const data = await request(`/api/attempts/${state.attempt.id}/end`, { method: "POST" });
    renderAttempt(data.attempt);
    scrollToLatest({ force: true, instant: true });
    renderScorecard(data.scorecard);
  } catch (error) {
    toast(error.message || "The practice could not be ended.", "error");
  } finally {
    el.endButton.disabled = false;
  }
});

function renderScorecard(scorecard) {
  const complete = scorecard.status === "complete";
  el.scorecardStatus.textContent = complete ? "Complete" : "Partial";
  el.scorecardStatus.classList.toggle("is-partial", !complete);

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

  el.scorecardBody.replaceChildren(...rows, drill);
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
    startTimer(Date.now());
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

el.userChip.addEventListener("click", (event) => {
  event.stopPropagation();
  setMenuOpen(el.userSheet.classList.contains("hidden"));
});

document.addEventListener("click", (event) => {
  if (!el.userMenu.contains(event.target)) setMenuOpen(false);
});

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

async function boot() {
  showTranscriptState("Connecting you to Leo…");
  syncSendState();
  await loadViewer();

  const requestedCaseId = new URLSearchParams(window.location.search).get("case");
  if (requestedCaseId) state.selectedCaseId = requestedCaseId;

  const stored = readSession();
  // A direct catalogue selection intentionally starts a new attempt. A reload
  // without a case query remains resumable, which avoids losing interview work.
  if (stored && !requestedCaseId) {
    try {
      const attempt = await request(`/api/attempts/${stored.id}`);
      const startedAt = Number(stored.startedAt) || Date.now();
      persistSession(attempt.id, startedAt, attempt.case.id);
      startTimer(startedAt);
      renderAttempt(attempt);
      if (attempt.ended) await restoreScorecard(attempt.id);
      else toast("Picked up where you left off.");
      el.input.focus();
      return;
    } catch {
      localStorage.removeItem(STORAGE_SESSION);
    }
  }

  try {
    const attempt = await startAttempt();
    persistSession(attempt.id, Date.now(), attempt.case.id);
    startTimer(Date.now());
    renderAttempt(attempt);
    el.input.focus();
  } catch (error) {
    el.title.textContent = "Case unavailable";
    showTranscriptState(error.message || "The case could not be loaded.", { spinner: false, retry: true });
  }
}

async function restoreScorecard(attemptId) {
  try {
    const data = await request(`/api/attempts/${attemptId}/end`, { method: "POST" });
    renderScorecard(data.scorecard);
  } catch {
    /* The transcript still stands on its own without the summary. */
  }
}

boot();
