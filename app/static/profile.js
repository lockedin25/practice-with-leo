/* Leo candidate profile: personal progress only, never cohort data. */

const state = {
  history: [],
  historyFilter: "all",
  historyExpanded: false,
};

const el = {
  title: document.querySelector("#profile-title"),
  subtitle: document.querySelector("#profile-subtitle"),
  avatarLarge: document.querySelector("#profile-avatar-large"),
  nextStepTitle: document.querySelector("#next-step-title"),
  nextStepDescription: document.querySelector("#next-step-description"),
  nextStepAction: document.querySelector("#next-step-action"),
  tiles: document.querySelector("#summary-tiles"),
  assessedCount: document.querySelector("#assessed-count"),
  performanceBars: document.querySelector("#performance-bars"),
  performanceEmpty: document.querySelector("#performance-empty"),
  overview: document.querySelector("#profile-overview"),
  developmentEmpty: document.querySelector("#development-empty"),
  developmentList: document.querySelector("#development-list"),
  developmentMore: document.querySelector("#development-more"),
  developmentMoreList: document.querySelector("#development-more-list"),
  developmentCount: document.querySelector("#development-count"),
  strengthList: document.querySelector("#strength-list"),
  strengthMore: document.querySelector("#strength-more"),
  strengthMoreList: document.querySelector("#strength-more-list"),
  strengthCount: document.querySelector("#strength-count"),
  historyCount: document.querySelector("#history-count"),
  historySummary: document.querySelector("#history-summary"),
  historyFilters: document.querySelector("#history-filters"),
  historyMore: document.querySelector("#history-more"),
  historyBody: document.querySelector("#history-body"),
  drawer: document.querySelector("#drawer"),
  drawerVeil: document.querySelector("#drawer-veil"),
  drawerTitle: document.querySelector("#drawer-title"),
  drawerMeta: document.querySelector("#drawer-meta"),
  drawerBody: document.querySelector("#drawer-body"),
  drawerClose: document.querySelector("#drawer-close"),
  drawerCta: document.querySelector("#drawer-cta-wrap"),
  drawerDebriefBtn: document.querySelector("#drawer-debrief-btn"),
  signOut: document.querySelector("#sign-out"),
  toasts: document.querySelector("#toasts"),
};

const AUDIO_CUE = /\[(?:warmly|confidently|patiently|empathetically|seriously|enthusiastically|excitedly|chuckles|laughing|sighs)\]\s*/gi;

const DIMENSION_DISPLAY_NAMES = {
  structuring: "Structuring",
  problem_solving: "Problem solving",
  quantitative: "Quantitative acumen",
  synthesis: "Synthesis",
  communication: "Communication",
};

/* --- Labels --------------------------------------------------------------
 * One formatter for every enum the API hands over. The catalogue speaks
 * snake_case ("mergers_and_acquisitions", "saas_and_b2b_tech") and kebab-case
 * (case ids), and neither reads as English without this. Identical copies live
 * in debrief.js and admin.js; the three scripts are never loaded together.
 */

const LABEL_ACRONYMS = new Map(Object.entries({
  saas: "SaaS", b2b: "B2B", b2c: "B2C", bnpl: "BNPL", fmcg: "FMCG",
  cpg: "CPG", msme: "MSME", qsr: "QSR", ev: "EV", ai: "AI", it: "IT",
  kpi: "KPI", ebitda: "EBITDA", mbb: "MBB", iim: "IIM", isb: "ISB",
  bcg: "BCG", "m&a": "M&A", roi: "ROI", "r&d": "R&D",
}));

const LABEL_MINOR = new Set([
  "and", "or", "of", "the", "a", "an", "to", "for", "in", "on", "at",
  "vs", "per", "with", "from",
]);

function titleCase(value) {
  const words = String(value ?? "").replace(/[_-]+/g, " ").trim().split(/\s+/);
  if (!words[0]) return "";
  return words
    .map((word, index) => {
      const key = word.toLowerCase();
      if (LABEL_ACRONYMS.has(key)) return LABEL_ACRONYMS.get(key);
      if (index > 0 && LABEL_MINOR.has(key)) return key;
      return key.charAt(0).toUpperCase() + key.slice(1);
    })
    .join(" ");
}

async function api(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (response.status === 401) {
    window.location.href = "/login?next=/profile";
    throw new Error("signed out");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Leo could not load your profile.");
  }
  return response.json();
}

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = text;
  return item;
}

function toast(message) {
  const item = node("div", "toast is-error", message);
  el.toasts?.append(item);
  window.setTimeout(() => item.remove(), 4500);
}

function parseUtc(value) {
  return value ? new Date(`${String(value).replace(" ", "T")}Z`) : null;
}

function relativeTime(value) {
  const date = parseUtc(value);
  if (!date || Number.isNaN(date.getTime())) return "Not recorded";
  const hours = Math.round((Date.now() - date.getTime()) / 3_600_000);
  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days} days ago`;
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function score(value) {
  return typeof value === "number" ? `${value.toFixed(1)} / 5` : "Not assessed";
}

function badgeClass(label) {
  return `mbb-badge badge-${String(label).toLowerCase().replace(/\s+/g, "-")}`;
}

function computeMbbBadge(val) {
  if (typeof val !== "number") return null;
  if (val >= 4.5) return "Distinction";
  if (val >= 3.8) return "Strong Pass";
  if (val >= 2.8) return "Meets Bar";
  if (val >= 2.0) return "Developing";
  return "Needs Practice";
}

function renderTiles(summary) {
  const completion = summary.attempts ? Math.round((summary.completed / summary.attempts) * 100) : 0;
  const avgScore = summary.average_feedback_score;
  const reports = summary.feedback_available;

  const tiles = [
    ["Cases practised", String(summary.attempts), `${summary.completed} completed, ${summary.in_progress} open`, false],
    ["Completion rate", `${completion}%`, `${summary.completed} of ${summary.attempts} finished`, false],
    ["Average score", score(avgScore), `${reports} debrief${reports === 1 ? "" : "s"} evaluated`, false],
    ["Standing", computeMbbBadge(avgScore) || "Not yet rated", "Against the MBB hiring bar", true],
  ];

  el.tiles?.replaceChildren(
    ...tiles.map(([label, value, note, isText]) => {
      const tile = node("article", "tile");
      tile.append(
        node("p", "tile-label", label),
        node("p", `tile-value${isText ? " is-text" : ""}`, String(value)),
        node("p", "tile-note", note),
      );
      return tile;
    }),
  );
}

function setActionLabel(action, label) {
  if (!action) return;
  action.replaceChildren(document.createTextNode(`${label} `), node("span", "arrow", "→"));
}

function renderNextStep(summary, attempts, developmentAreas) {
  const openAttempt = attempts.find((attempt) => !attempt.ended);
  const priority = developmentAreas?.[0]?.text;
  if (openAttempt) {
    if (el.nextStepTitle) el.nextStepTitle.textContent = `Resume ${openAttempt.case.title}`;
    if (el.nextStepDescription) {
      el.nextStepDescription.textContent = summary.in_progress === 1
        ? `You have one open case. Continue from ${titleCase(openAttempt.stage)} while the context is fresh.`
        : `You have ${summary.in_progress} open cases. Continue this one from ${titleCase(openAttempt.stage)} rather than starting another.`;
    }
    if (el.nextStepAction) {
      el.nextStepAction.href = `/practice?attempt=${encodeURIComponent(openAttempt.id)}`;
      setActionLabel(el.nextStepAction, "Resume case");
    }
    return;
  }

  if (priority) {
    if (el.nextStepTitle) el.nextStepTitle.textContent = "Turn your main feedback theme into a habit";
    if (el.nextStepDescription) el.nextStepDescription.textContent = priority;
  } else {
    if (el.nextStepTitle) el.nextStepTitle.textContent = "Start your next case";
    if (el.nextStepDescription) el.nextStepDescription.textContent = "Finish one case and Leo will turn the transcript into a personal competency profile.";
  }
  if (el.nextStepAction) {
    el.nextStepAction.href = "/cases";
    setActionLabel(el.nextStepAction, "Browse cases");
  }
}

function renderPerformance(rows) {
  const hasRows = rows.length > 0;
  el.performanceEmpty?.classList.toggle("hidden", hasRows);

  /* The counter reports the sample size behind the averages, which is the only
   * number that changes how much to trust them. */
  if (el.assessedCount) {
    const reports = Math.max(0, ...rows.map((row) => row.assessments || 0));
    el.assessedCount.textContent = `${reports} report${reports === 1 ? "" : "s"}`;
    el.assessedCount.classList.toggle("hidden", !hasRows);
    el.assessedCount.classList.toggle("is-live", hasRows);
  }

  el.performanceBars?.replaceChildren(
    ...rows.map((row) => {
      const scoreValue = Number(row.average_score);
      const card = node("article", "skill-card");
      const header = node("div", "skill-card-head");
      const track = node("div", "skill-track");
      const fill = node("div", "skill-fill");
      fill.style.width = `${Math.max(4, Math.min(100, (scoreValue / 5) * 100))}%`;
      track.append(fill);
      track.setAttribute("role", "meter");
      track.setAttribute("aria-valuemin", "0");
      track.setAttribute("aria-valuemax", "5");
      track.setAttribute("aria-valuenow", String(scoreValue));
      const displayName = DIMENSION_DISPLAY_NAMES[row.name] || titleCase(row.name);
      track.setAttribute("aria-label", `${displayName} average`);
      const gap = 3 - scoreValue;
      const benchmark = gap > 0.05
        ? `${gap.toFixed(1)} to the 3.0 bar`
        : gap < -0.05
          ? `${Math.abs(gap).toFixed(1)} above the 3.0 bar`
          : "At the 3.0 bar";
      header.append(
        node("p", "skill-name", displayName),
        node("p", "skill-score", `${scoreValue.toFixed(1)} / 5`),
      );
      card.append(header, track, node("p", "skill-context", benchmark));
      return card;
    }),
  );
}

/* One empty-state pattern, and only one at a time: either both pillars carry
 * themes, or the card shows a single empty panel. The page used to write
 * placeholder list items AND unhide the panel, so three sentences said the
 * same thing at once. */
function renderDevelopment(areas, strengths) {
  const strengthItems = normaliseThemes(strengths).filter(isCandidateStrength);
  const areaItems = normaliseThemes(areas);
  const isEmpty = !strengthItems.length && !areaItems.length;

  el.developmentEmpty?.classList.toggle("hidden", !isEmpty);
  el.overview?.classList.toggle("hidden", isEmpty);
  if (isEmpty) {
    el.strengthList?.replaceChildren();
    el.strengthMoreList?.replaceChildren();
    el.strengthMore?.classList.add("hidden");
    el.developmentList?.replaceChildren();
    el.developmentMoreList?.replaceChildren();
    el.developmentMore?.classList.add("hidden");
    return;
  }

  renderThemeList({
    list: el.strengthList,
    moreList: el.strengthMoreList,
    disclosure: el.strengthMore,
    count: el.strengthCount,
    items: strengthItems,
    emptyText: "No distinct candidate strengths are available yet.",
    visibleCount: 3,
    label: "strengths",
  });
  renderThemeList({
    list: el.developmentList,
    moreList: el.developmentMoreList,
    disclosure: el.developmentMore,
    count: el.developmentCount,
    items: areaItems,
    emptyText: "No priority focus areas are available yet.",
    visibleCount: 2,
    label: "focus areas",
  });
}

function normaliseThemes(items) {
  return (items || [])
    .map((item) => typeof item === "string" ? item : item?.text)
    .filter((item) => typeof item === "string" && item.trim())
    .map((item) => item.trim());
}

/* Operational notes are useful inside an individual debrief, but they are not
 * evidence of a candidate strength. Keep the profile focused on repeatable
 * performance signals. */
function isCandidateStrength(item) {
  return !/^(?:No candidate response was recorded|The attempt has been saved and can be restarted)/i.test(item);
}

function renderThemeList({ list, moreList, disclosure, count, items, emptyText, visibleCount, label }) {
  if (!list) return;
  if (!items.length) {
    list.replaceChildren(node("li", "is-empty", emptyText));
    moreList?.replaceChildren();
    disclosure?.classList.add("hidden");
    if (count) count.textContent = "";
    return;
  }

  const visible = items.slice(0, visibleCount);
  const overflow = items.slice(visibleCount);
  list.replaceChildren(...visible.map((item) => node("li", null, item)));
  moreList?.replaceChildren(...overflow.map((item) => node("li", null, item)));

  if (count) count.textContent = `${items.length} theme${items.length === 1 ? "" : "s"}`;
  if (!disclosure) return;
  disclosure.classList.toggle("hidden", !overflow.length);
  disclosure.open = false;
  const summary = disclosure.querySelector("summary");
  if (summary) summary.textContent = `Show ${overflow.length} more ${label}`;
}

function renderHistory(attempts) {
  state.history = Array.isArray(attempts) ? attempts : [];
  renderHistoryView();
}

function renderHistoryView() {
  const labels = {
    all: "all attempts",
    in_progress: "open attempts",
    completed: "completed attempts",
  };
  const filtered = state.history.filter((attempt) => {
    if (state.historyFilter === "in_progress") return !attempt.ended;
    if (state.historyFilter === "completed") return attempt.ended;
    return true;
  });
  const visibleAttempts = state.historyExpanded ? filtered : filtered.slice(0, 12);

  if (el.historyCount) {
    el.historyCount.textContent = String(filtered.length);
    el.historyCount.classList.toggle("is-live", filtered.length > 0);
  }
  if (el.historySummary) {
    el.historySummary.textContent = filtered.length > 12 && !state.historyExpanded
      ? `Showing the latest 12 of ${filtered.length} ${labels[state.historyFilter]}.`
      : `${filtered.length} ${labels[state.historyFilter]}.`;
  }
  for (const button of el.historyFilters?.querySelectorAll("[data-history-filter]") || []) {
    const selected = button.dataset.historyFilter === state.historyFilter;
    button.classList.toggle("is-active", selected);
    button.setAttribute("aria-pressed", String(selected));
  }
  if (el.historyMore) {
    el.historyMore.classList.toggle("hidden", filtered.length <= 12);
    el.historyMore.textContent = state.historyExpanded ? "Show fewer attempts" : `Show all ${filtered.length} attempts`;
  }

  if (!filtered.length) {
    const row = document.createElement("tr");
    const message = state.history.length
      ? `No ${labels[state.historyFilter]} yet.`
      : "Your case history appears here after your first attempt.";
    const cell = node("td", "table-empty", message);
    cell.colSpan = 6;
    row.append(cell);
    el.historyBody?.replaceChildren(row);
    return;
  }

  el.historyBody?.replaceChildren(
    ...visibleAttempts.map((attempt) => {
      const row = document.createElement("tr");

      const caseCell = document.createElement("td");
      caseCell.append(
        node("p", "history-case", attempt.case.title),
        node("p", "history-meta", `${attempt.case.school || "MBB Core"} · ${titleCase(attempt.case.category || "case")}`),
      );

      const stageCell = document.createElement("td");
      stageCell.append(
        node(
          "span",
          `pill ${attempt.ended ? "pill-done" : "pill-live"}`,
          attempt.ended ? "Complete" : titleCase(attempt.stage),
        ),
      );

      const feedbackScore = attempt.feedback ? _extractScore(attempt.feedback) : null;
      const scoreCell = node("td", "numeric");
      if (typeof feedbackScore === "number") {
        const rating = attempt.feedback?.mbb_rating_badge || computeMbbBadge(feedbackScore);
        scoreCell.append(node("p", "history-score", `${feedbackScore.toFixed(1)} / 5`));
        if (rating) scoreCell.append(node("span", badgeClass(rating), rating));
      } else {
        /* The stage pill already says whether this is open, so an unscored row
         * only needs to say what is missing. */
        scoreCell.append(node("p", "history-score", attempt.ended ? "Pending" : ""));
      }

      const actionCell = node("td", "actions");
      const actions = node("div", "table-actions-wrap");
      const debriefUrl = attempt.debrief_url || `/attempts/${attempt.id}/debrief`;
      if (attempt.ended) {
        const debriefLink = node("a", "btn btn-primary btn-sm table-action", "Debrief");
        debriefLink.href = debriefUrl;
        actions.append(debriefLink);
      } else {
        const resumeLink = node("a", "btn btn-primary btn-sm table-action", "Resume");
        resumeLink.href = `/practice?attempt=${encodeURIComponent(attempt.id)}`;
        actions.append(resumeLink);
      }
      const transcriptBtn = node("button", "btn btn-secondary btn-sm table-action", "Transcript");
      transcriptBtn.type = "button";
      transcriptBtn.addEventListener("click", () => openAttempt(attempt.id));
      actions.append(transcriptBtn);
      actionCell.append(actions);

      row.append(
        caseCell,
        stageCell,
        node("td", "numeric", String(attempt.candidate_turns)),
        scoreCell,
        node("td", null, relativeTime(attempt.updated_at)),
        actionCell,
      );
      return row;
    }),
  );
}

function _extractScore(feedback) {
  if (!feedback) return null;
  if (typeof feedback.overall_score === "number") return feedback.overall_score;
  const report = feedback.report;
  if (report && typeof report.overall_score === "number") return report.overall_score;
  return null;
}

function feedbackSection(label, values) {
  const section = document.createElement("section");
  section.className = "drawer-section";
  section.append(node("p", "micro-label", label));
  if (values?.length) {
    const list = document.createElement("ul");
    list.className = "drawer-list";
    list.append(...values.map((value) => node("li", null, value)));
    section.append(list);
  } else section.append(node("p", "muted-text", "None recorded for this attempt."));
  return section;
}

function closeDrawer() {
  el.drawer?.classList.add("hidden");
  el.drawerVeil?.classList.add("hidden");
}

async function openAttempt(attemptId) {
  try {
    const data = await api(`/api/me/practice-history/${attemptId}`);
    const report = data.feedback?.report;
    const debriefUrl = `/attempts/${attemptId}/debrief`;

    if (el.drawerTitle) el.drawerTitle.textContent = data.attempt.case.title;
    if (el.drawerMeta) {
      el.drawerMeta.replaceChildren(
        node("span", "meta-pill", data.attempt.ended ? "Complete" : titleCase(data.attempt.stage)),
        node("span", "meta-pill", `${titleCase(data.attempt.mode)} mode`),
        node("span", "meta-pill", relativeTime(data.attempt.updated_at)),
      );
    }
    /* The report only exists for an ended attempt, so the band is the one
     * place the debrief is offered from here. */
    el.drawerCta?.classList.toggle("hidden", !data.attempt.ended);
    if (el.drawerDebriefBtn) el.drawerDebriefBtn.href = debriefUrl;

    const sections = [];

    const drillText = report?.targeted_drill?.prompt || report?.next_drill;
    if (drillText) sections.push(feedbackSection("Next drill", [drillText]));

    const priorities = (report?.areas_for_development || []).map((item) =>
      typeof item === "string" ? item : [item.gap, item.corrective_guidance].filter(Boolean).join(" · "),
    );
    if (priorities.length) sections.push(feedbackSection("Priority improvements", priorities));

    const strengths = (report?.strengths || []).map((item) =>
      typeof item === "string" ? item : `${item.claim}${item.verbatim_quote ? ` ("${item.verbatim_quote}")` : ""}`,
    );
    if (strengths.length) sections.push(feedbackSection("Strengths", strengths));

    const transcriptSection = document.createElement("section");
    transcriptSection.className = "drawer-section";
    transcriptSection.append(node("p", "micro-label", `Transcript · ${data.transcript.length} messages`));
    const transcriptThread = node("div", "drawer-transcript");
    transcriptThread.append(
      ...data.transcript.map((message) => {
        const line = node("article", `review-message ${message.role}`);
        line.append(
          node("p", "review-role", message.role === "candidate" ? "You" : "Leo"),
          node("p", "review-copy", String(message.content).replace(AUDIO_CUE, "")),
        );
        return line;
      }),
    );
    transcriptSection.append(transcriptThread);
    sections.push(transcriptSection);

    el.drawerBody?.replaceChildren(...sections);
    el.drawerBody.scrollTop = 0;
    el.drawer?.classList.remove("hidden");
    el.drawerVeil?.classList.remove("hidden");
    el.drawer?.focus();
  } catch (error) {
    toast(error.message);
  }
}

el.drawerClose?.addEventListener("click", closeDrawer);
el.drawerVeil?.addEventListener("click", closeDrawer);
el.historyFilters?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-history-filter]");
  if (!button) return;
  state.historyFilter = button.dataset.historyFilter || "all";
  state.historyExpanded = false;
  renderHistoryView();
});
el.historyMore?.addEventListener("click", () => {
  state.historyExpanded = !state.historyExpanded;
  renderHistoryView();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && el.drawer && !el.drawer.classList.contains("hidden")) {
    closeDrawer();
  }
});

async function boot() {
  try {
    const data = await api("/api/me/profile");
    const displayName = data.user.name || data.user.email || "Candidate";
    const firstName = displayName.split(" ")[0];

    if (el.avatarLarge) {
      if (data.user.picture) {
        el.avatarLarge.style.backgroundImage = `url("${data.user.picture}")`;
        el.avatarLarge.textContent = "";
      } else {
        el.avatarLarge.textContent = displayName.trim()[0]?.toUpperCase() || "?";
      }
    }
    if (el.title) el.title.textContent = `${firstName}'s progress, in focus.`;
    if (el.subtitle) {
      el.subtitle.textContent = data.summary.attempts
        ? `${data.summary.attempts} attempts, ${data.summary.completed} completed, scored on the 1.0 to 5.0 MBB scale.`
        : "Start your first case and Leo builds your competency profile from the transcript.";
    }
    renderTiles(data.summary);
    const attempts = data.performance_history || data.recent_attempts || [];
    renderNextStep(data.summary, attempts, data.development_areas);
    renderPerformance(data.performance);
    renderDevelopment(data.development_areas, data.strengths);
    renderHistory(attempts);
    const requestedCaseId = new URLSearchParams(window.location.search).get("case");
    const requestedAttempt = attempts.find((attempt) => attempt.case.id === requestedCaseId);
    if (requestedAttempt) openAttempt(requestedAttempt.id);
  } catch (error) {
    toast(error.message);
  }
}

el.signOut?.addEventListener("click", async () => {
  el.signOut.disabled = true;
  try {
    await fetch("/auth/logout", { method: "POST" });
  } finally {
    window.location.href = "/login";
  }
});

boot();
