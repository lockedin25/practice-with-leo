/* Leo case debrief: renders one attempt's evidence-based evaluation report.
 *
 * The page is a pure view: it fetches the owner-scoped report from the
 * attempt API and paints typed fields. Every value lands in the DOM through
 * textContent, so nothing from the model output or transcript is ever
 * interpreted as markup.
 */

const DIMENSION_LABELS = {
  structuring: "Structuring & Problem Definition",
  problem_solving: "Problem-Solving & Commercial Judgment",
  quantitative: "Quantitative Acumen",
  synthesis: "Synthesis & Recommendations",
  communication: "Communication & Personal Impact",
};

const state = { attemptId: null, checklistItems: [], checklistStatus: "missed" };

const el = {
  state: document.querySelector("#debrief-state"),
  stateSpinner: document.querySelector("#state-spinner"),
  stateTitle: document.querySelector("#state-title"),
  stateNote: document.querySelector("#state-note"),
  stateActions: document.querySelector("#state-actions"),
  stateRetry: document.querySelector("#state-retry"),
  report: document.querySelector("#debrief-report"),
  caseTitle: document.querySelector("#case-title"),
  subtitle: document.querySelector("#report-subtitle"),
  overallScore: document.querySelector("#overall-score"),
  overallValue: document.querySelector("#overall-value"),
  overallOutOf: document.querySelector("#overall-out-of"),
  overallNote: document.querySelector("#overall-note"),
  reliabilityState: document.querySelector("#reliability-state"),
  strengths: document.querySelector("#strength-list"),
  priorities: document.querySelector("#priority-list"),
  drill: document.querySelector("#drill-text"),
  dimensions: document.querySelector("#dimension-grid"),
  checklist: document.querySelector("#checklist"),
  checklistFilter: document.querySelector("#checklist-status-filter"),
  checklistSummary: document.querySelector("#checklist-summary"),
  checklistEmpty: document.querySelector("#checklist-empty"),
  versionNote: document.querySelector("#version-note"),
  signOut: document.querySelector("#sign-out"),
  // 10x Masterclass sections
  executiveSummaryCard: document.querySelector("#executive-summary-card"),
  executiveSummaryText: document.querySelector("#executive-summary-text"),
  mbbBadge: document.querySelector("#mbb-badge"),
  caseWantedCard: document.querySelector("#case-wanted-card"),
  caseCoreMechanism: document.querySelector("#case-core-mechanism"),
  casePivotalInsight: document.querySelector("#case-pivotal-insight"),
  caseCandidatePerformance: document.querySelector("#case-candidate-performance"),
  caseOptimalGap: document.querySelector("#case-optimal-gap"),
  goldenRewritesCard: document.querySelector("#golden-rewrites-card"),
  goldenRewritesList: document.querySelector("#golden-rewrites-list"),
  strengthsCard: document.querySelector("#strengths-card"),
  strengthsList: document.querySelector("#strengths-list"),
  developmentCard: document.querySelector("#development-card"),
  developmentList: document.querySelector("#development-list"),
  actionPlanCard: document.querySelector("#action-plan-card"),
  drillTitle: document.querySelector("#drill-title"),
  drillMeta: document.querySelector("#drill-meta"),
  drillPrompt: document.querySelector("#drill-prompt"),
  readingsList: document.querySelector("#readings-list"),
};

/* --- Fetching ------------------------------------------------------------ */

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  if (response.status === 401) {
    window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    throw new ApiError("Your session expired.", 401);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail || "Something went wrong.", response.status);
  }
  return response.json();
}

/* --- Small helpers ------------------------------------------------------- */

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

/* --- Labels --------------------------------------------------------------
 * One formatter for every enum the API hands over. The catalogue speaks
 * snake_case ("mergers_and_acquisitions", "saas_and_b2b_tech") and kebab-case
 * (case ids), and neither reads as English without this. Identical copies live
 * in profile.js and admin.js; the three scripts are never loaded together.
 */

const LABEL_ACRONYMS = new Map(Object.entries({
  saas: "SaaS", b2b: "B2B", b2c: "B2C", bnpl: "BNPL", fmcg: "FMCG",
  cpg: "CPG", msme: "MSME", qsr: "QSR", ev: "EV", ai: "AI", it: "IT",
  kpi: "KPI", ebitda: "EBITDA", mbb: "MBB",
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

/* Bands and ratings arrive as prose ("Top 1% MBB"), so a CSS hook needs the
 * punctuation stripped, not only the spaces. */
function slug(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

/* Knowledge-base references arrive as repository paths. Show the document, not
 * the path: "knowledge_base/methodology/02_issue_tree.md" -> "02 Issue Tree". */
function pathLabel(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  if (!raw.includes("/") && !raw.endsWith(".md")) return raw;
  return titleCase(raw.split("/").pop().replace(/\.md$/, ""));
}

function fillList(listElement, items, emptyText) {
  if (!items.length) {
    listElement.replaceChildren(node("li", "empty-note", emptyText));
    return;
  }
  listElement.replaceChildren(...items.map((text) => node("li", null, text)));
}

function evidenceBlock(citation) {
  const template = document.querySelector("#evidence-template");
  const figure = template.content.firstElementChild.cloneNode(true);
  figure.querySelector(".evidence-quote").textContent = `\u201c${citation.quote}\u201d`;
  figure.querySelector(".evidence-ref").textContent = `You said \u00b7 message ${citation.message_index + 1}`;
  return figure;
}

function showState(title, note, { spinner = false, retry = false } = {}) {
  el.report.classList.add("hidden");
  el.state.classList.remove("hidden");
  el.stateTitle.textContent = title;
  el.stateNote.textContent = note;
  el.stateSpinner.classList.toggle("hidden", !spinner);
  el.stateActions.classList.toggle("hidden", !retry);
  el.stateRetry.classList.toggle("hidden", !retry);
}

/* --- Rendering ----------------------------------------------------------- */

function renderHeader(attempt) {
  const caseInfo = attempt.case || {};
  el.caseTitle.textContent = caseInfo.title || "Your case";
  document.title = `Debrief \u00b7 ${caseInfo.title || "Leo"}`;
  const turns = attempt.messages?.filter((message) => message.role === "candidate").length ?? 0;
  const parts = [
    `${turns} candidate turn${turns === 1 ? "" : "s"}`,
    `${titleCase(attempt.mode)} mode`,
    caseInfo.difficulty ? `${titleCase(caseInfo.difficulty)} difficulty` : null,
  ].filter(Boolean);
  el.subtitle.textContent = parts.join(" \u00b7 ");
}

/* The five dimension names are listed in full immediately below, so the
 * footnote reports the count and any exclusion, not the whole roster. */
function renderReliability(report) {
  const complete = report.reliability === "complete";
  if (complete) {
    el.overallValue?.classList.remove("hidden");
    el.reliabilityState?.classList.add("hidden");
    return true;
  }

  el.overallValue?.classList.add("hidden");
  el.reliabilityState?.classList.remove("hidden");
  if (el.reliabilityState) el.reliabilityState.textContent = "Provisional evaluation";
  if (el.mbbBadge) {
    el.mbbBadge.textContent = "";
    el.mbbBadge.classList.add("hidden");
  }
  el.overallNote.textContent = report.retry_message || "Your transcript is saved. Please try the evaluation again later for a validated score.";
  return false;
}

function renderOverall(overall) {
  if (overall?.overall === null || overall?.overall === undefined) {
    el.overallScore.textContent = "\u2013";
    el.overallNote.textContent = "Not enough assessable work in this attempt to score it.";
    return;
  }
  el.overallScore.textContent = String(overall.overall);
  const assessed = overall.assessed_dimensions || [];
  const excluded = overall.excluded_dimensions || [];
  const base = `Weighted mean of ${assessed.length} assessed dimension${assessed.length === 1 ? "" : "s"}.`;
  const excludedNote = excluded.length
    ? ` ${excluded.map((name) => DIMENSION_LABELS[name] || titleCase(name)).join(", ")} had no assessable work, so the weight was redistributed.`
    : "";
  el.overallNote.textContent = `${base}${excludedNote}`;
}

/* The rating badge sits in the outcome panel beside the score; this card
 * carries the summary prose only. */
function renderExecutiveSummary(report, showBadge) {
  if (el.mbbBadge) {
    el.mbbBadge.textContent = showBadge ? (report.mbb_rating_badge || "") : "";
    el.mbbBadge.className = `mbb-badge badge-${slug(report.mbb_rating_badge)}`;
    el.mbbBadge.classList.toggle("hidden", !showBadge || !report.mbb_rating_badge);
  }
  if (!report.executive_summary) return;
  el.executiveSummaryCard?.classList.remove("hidden");
  if (el.executiveSummaryText) el.executiveSummaryText.textContent = report.executive_summary;
}

function renderCaseWantedToTest(report) {
  const data = report.what_the_case_wanted_to_test;
  if (!data || (!data.core_mechanism && !data.pivotal_insight)) return;
  el.caseWantedCard?.classList.remove("hidden");
  fillInsightSlot(el.caseCoreMechanism, data.core_mechanism);
  fillInsightSlot(el.casePivotalInsight, data.pivotal_insight);
  fillInsightSlot(el.caseCandidatePerformance, data.candidate_performance_summary);
  fillInsightSlot(el.caseOptimalGap, data.candidate_vs_optimal_gap);
}

/* A slot with no authored content would render an orphaned micro-label, so
 * empty items collapse instead of showing a blank line. */
function fillInsightSlot(slot, text) {
  if (!slot) return;
  slot.textContent = text || "";
  slot.closest(".masterclass-item")?.classList.toggle("hidden", !text);
}

function renderDimension(dimension) {
  const card = node("article", "card dimension-card");

  const header = node("header");
  header.append(node("p", "dimension-name", DIMENSION_LABELS[dimension.name] || titleCase(dimension.name)));
  const scoreLine = node("div", "dimension-score-line");
  scoreLine.append(
    node("span", "dimension-score", String(Math.round(dimension.score * 10) / 10)),
    node("span", "dimension-out-of", "/5"),
  );
  header.append(scoreLine);
  card.append(header);

  const track = node("div", "score-track", "");
  const fill = node("span", "score-fill");
  fill.style.width = `${Math.max(0, Math.min(5, dimension.score)) / 5 * 100}%`;
  track.setAttribute("role", "meter");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", "5");
  track.setAttribute("aria-valuenow", String(dimension.score));
  track.setAttribute("aria-label", `${DIMENSION_LABELS[dimension.name] || dimension.name} score`);
  track.append(fill);
  card.append(track);

  const bands = node("div", "dimension-bands");
  bands.append(node("span", `band band-${slug(dimension.band)}`, dimension.band));
  bands.append(node("span", `confidence-chip${dimension.confidence === "low" ? " is-low" : ""}`, `${dimension.confidence} confidence`));
  card.append(bands);

  if (dimension.observations?.length) {
    const section = node("div", "dimension-section");
    section.append(node("p", "dimension-label", "What Leo saw"));
    section.append(...renderItems(dimension.observations, "dimension-list"));
    card.append(section);
  }

  if (dimension.improvements?.length) {
    const section = node("div", "dimension-section");
    section.append(node("p", "dimension-label", "Do differently"));
    section.append(...renderItems(dimension.improvements, "dimension-list is-improvements"));
    card.append(section);
  }

  for (const citation of dimension.evidence || []) card.append(evidenceBlock(citation));
  return card;

  function renderItems(items, className) {
    const list = node("ul", className);
    list.replaceChildren(...items.map((text) => node("li", null, text)));
    return [list];
  }
}

function renderGoldenRewrites(report) {
  const rewrites = report.golden_rewrites;
  if (!rewrites?.length) return;
  el.goldenRewritesCard?.classList.remove("hidden");
  const container = el.goldenRewritesList;
  if (!container) return;
  container.replaceChildren(...rewrites.map((rw) => {
    const block = node("div", "rewrite-block");
    block.append(node("p", "rewrite-phase", titleCase(rw.phase || rw.stage || "Opening")));

    const comparison = node("div", "rewrite-comparison");
    const candidateCol = node("div", "rewrite-col rewrite-candidate");
    candidateCol.append(node("p", "micro-label", "What you said"));
    candidateCol.append(node("p", "rewrite-text", rw.candidate_turn || "(not captured)"));

    const partnerCol = node("div", "rewrite-col rewrite-partner");
    partnerCol.append(node("p", "micro-label", "Top 1% MBB delivery"));
    partnerCol.append(node("p", "rewrite-text", rw.mbb_partner_turn || rw.golden_mbb_turn || ""));

    comparison.append(candidateCol, partnerCol);
    block.append(comparison);

    const notes = rw.diagnostic_notes || rw.consulting_craft_delta || [];
    if (notes.length) {
      const notesList = node("ul", "rewrite-notes");
      notesList.replaceChildren(...notes.map((n) => node("li", null, n)));
      block.append(node("p", "micro-label", "Diagnostic notes"), notesList);
    }
    return block;
  }));
}

/* "What worked" already lists these claims at the top of the report. This card
 * only earns its space when the evaluator attached a verbatim quote or an
 * impact statement; with plain strings it repeated the summary word for word. */
function renderStrengths(report) {
  const items = (report.strengths || []).filter(
    (item) => item && typeof item === "object" && (item.verbatim_quote || item.impact),
  );
  if (!items.length) return;
  el.strengthsCard?.classList.remove("hidden");
  const container = el.strengthsList;
  if (!container) return;
  container.replaceChildren(...items.map((s) => {
    const item = node("div", "strength-item");
    item.append(node("p", "strength-claim", s.claim || s));
    if (s.verbatim_quote) {
      const fig = node("figure", "evidence");
      const bq = node("blockquote", "evidence-quote");
      bq.textContent = `\u201c${s.verbatim_quote}\u201d`;
      fig.append(bq);
      item.append(fig);
    }
    if (s.impact) item.append(node("p", "strength-impact", s.impact));
    return item;
  }));
}

/* Same rule as the strengths card: only when there is corrective guidance or a
 * priority to show beyond the "What to fix first" list. */
function renderDevelopmentAreas(report) {
  const items = (report.areas_for_development || []).filter(
    (item) => item && typeof item === "object" && (item.corrective_guidance || item.priority),
  );
  if (!items.length) return;
  el.developmentCard?.classList.remove("hidden");
  const container = el.developmentList;
  if (!container) return;
  container.replaceChildren(...items.map((d) => {
    const item = node("div", "dev-item");
    const header = node("div", "dev-header");
    header.append(node("p", "dev-gap", d.gap || d));
    header.append(node("span", `priority-badge is-${d.priority || "high"}`, (d.priority || "high").toUpperCase()));
    item.append(header);
    if (d.corrective_guidance) item.append(node("p", "dev-guidance", d.corrective_guidance));
    return item;
  }));
}

function renderActionPlan(report) {
  const drill = report.targeted_drill;
  const readings = report.suggested_readings;
  const hasDrill = Boolean(drill && typeof drill === "object" && drill.title);
  const hasReadings = Boolean(readings?.length);
  if (!hasDrill && !hasReadings) return;
  el.actionPlanCard?.classList.remove("hidden");
  /* The evaluator may return the drill as a bare prompt string, which is
   * already shown under "Next drill". Hide the half of the grid that has
   * nothing in it rather than leaving a labelled empty column. */
  document.querySelector("#drill-block")?.classList.toggle("hidden", !hasDrill);
  document.querySelector("#readings-block")?.classList.toggle("hidden", !hasReadings);
  if (hasDrill) {
    if (el.drillTitle) el.drillTitle.textContent = drill.title;
    if (el.drillMeta) el.drillMeta.textContent = `${Math.round((drill.duration_seconds || 120) / 60)} min \u00b7 ${drill.focus_area || "General"}`;
    if (el.drillPrompt) el.drillPrompt.textContent = drill.prompt || "";
  }
  if (hasReadings && el.readingsList) {
    el.readingsList.replaceChildren(...readings.map((r) => {
      const li = node("li", null);
      const path = typeof r === "string" ? r : r.path;
      const title = typeof r === "string" ? "" : r.title;
      const why = typeof r === "string" ? "" : (r.why_relevant || r.relevance_reason || "");
      li.textContent = title || titleCase(String(path || r).split("/").pop().replace(/\.md$/, ""));
      if (why) li.title = why;
      return li;
    }));
  }
}

function renderChecklist(items) {
  const marks = {
    demonstrated:
      '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path d="M5.5 12.6l4.2 4.2 8.8-9.6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    missed:
      '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>',
    not_applicable:
      '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M6 12h12" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>',
  };

  const allowedStatuses = new Set(["demonstrated", "missed", "not_applicable"]);
  state.checklistItems = (Array.isArray(items) ? items : [])
    .filter((item) => item && typeof item === "object" && item.title)
    .map((item) => ({
      ...item,
      status: allowedStatuses.has(item.status) ? item.status : "not_applicable",
    }));
  state.checklistStatus = el.checklistFilter?.value || "missed";

  const labels = {
    demonstrated: "Demonstrated",
    missed: "Missed",
    not_applicable: "Not applicable",
  };
  const counts = Object.fromEntries([...allowedStatuses].map((status) => [
    status,
    state.checklistItems.filter((item) => item.status === status).length,
  ]));

  for (const option of el.checklistFilter?.options || []) {
    if (labels[option.value]) option.textContent = `${labels[option.value]} (${counts[option.value] || 0})`;
  }

  renderChecklistView();

  function renderChecklistView() {
    const status = state.checklistStatus;
    const visible = state.checklistItems.filter((item) => item.status === status);
    const assessed = (counts.demonstrated || 0) + (counts.missed || 0);
    const summary = assessed
      ? `${counts.missed || 0} missed · ${counts.demonstrated || 0} demonstrated · ${counts.not_applicable || 0} not applicable`
      : "No assessable behaviour markers were recorded for this attempt.";
    if (el.checklistSummary) el.checklistSummary.textContent = summary;

    if (el.checklistEmpty) {
      el.checklistEmpty.classList.toggle("hidden", visible.length > 0);
      el.checklistEmpty.textContent = visible.length
        ? ""
        : `No ${labels[status].toLowerCase()} behaviours were recorded for this attempt.`;
    }

    el.checklist.replaceChildren(...visible.map((item, index) => {
      const row = node("li", `checklist-item is-${item.status}`);
      const hasDetail = Boolean(item.note || item.evidence?.length);
      const details = node(hasDetail ? "details" : "div", `checklist-details${hasDetail ? "" : " is-static"}`);
      if (hasDetail) details.open = index === 0 && item.status === "missed";

      const summary = node(hasDetail ? "summary" : "div", "checklist-summary");
      const mark = node("span", "checklist-mark");
      mark.innerHTML = marks[item.status] || marks.not_applicable;
      mark.setAttribute("aria-hidden", "true");
      summary.append(mark);
      summary.append(node("span", "checklist-title", item.title));
      summary.append(node("span", "checklist-status", labels[item.status]));
      if (hasDetail) summary.append(node("span", "checklist-disclosure"));
      details.append(summary);

      if (hasDetail) {
        const body = node("div", "checklist-detail-body");
        if (item.note) body.append(node("p", "checklist-note", item.note));
        for (const citation of item.evidence || []) body.append(evidenceBlock(citation));
        details.append(body);
      }

      row.append(details);
      return row;
    }));
  }
}

function renderReport(attempt, payload) {
  const report = payload.report;
  if (!report || typeof report !== "object") {
    throw new ApiError("The saved debrief is incomplete. Please retry.", 503);
  }
  showReport();
  renderHeader(attempt);
  const showHeadline = renderReliability(report);
  if (showHeadline) renderOverall(payload.overall);
  renderExecutiveSummary(report, showHeadline);

  /* The takeaway lists prefer the evaluator's own short summaries and fall
   * back to the claim/gap text of the detailed items. */
  const strengthTexts = (report.strengths || []).map((s) => (typeof s === "string" ? s : s.claim || ""));
  const priorityTexts = (report.areas_for_development || []).map((d) => (typeof d === "string" ? d : d.gap || ""));
  fillList(el.strengths, report.headline_strengths || strengthTexts, "No distinct strengths were recorded for this attempt.");
  fillList(el.priorities, report.priority_improvements || priorityTexts, "Nothing pressing was flagged this time.");

  const drillText = typeof report.targeted_drill === "object" ? report.targeted_drill?.prompt : report.targeted_drill;
  /* next_drill can be a knowledge-base path; a raw file path is not a drill. */
  el.drill.textContent = drillText || pathLabel(report.next_drill) || "Run another case to keep the momentum.";

  renderCaseWantedToTest(report);
  el.dimensions.replaceChildren(...(report.dimensions || []).map(renderDimension));
  renderGoldenRewrites(report);
  renderStrengths(report);
  renderDevelopmentAreas(report);
  renderActionPlan(report);
  renderChecklist(report.checklist || []);

  el.versionNote.textContent = `Evaluated by ${report.evaluator_version || "unknown version"} \u00b7 every quote above is verbatim from your transcript.`;
}

function showReport() {
  el.state.classList.add("hidden");
  el.stateSpinner.classList.add("hidden");
  el.report.classList.remove("hidden");
}

/* --- Loading -------------------------------------------------------------- */

async function load() {
  showState("Loading your debrief\u2026", "", { spinner: true });
  try {
    const [attempt, evaluation] = await Promise.all([
      request(`/api/attempts/${state.attemptId}`),
      request(`/api/attempts/${state.attemptId}/evaluation`),
    ]);
    renderReport(attempt, evaluation);
  } catch (error) {
    if (error.status === 409) {
      showState(
        "This practice has not ended yet.",
        "Finish the case with Leo first; the debrief appears here once you end the attempt.",
      );
      return;
    }
    if (error.status === 404) {
      showState("Debrief not found.", "This attempt does not exist under your account.");
      return;
    }
    if (error.status === 503) {
      showState(
        "Leo is still marking this case.",
        "The evaluator could not finish just now. Your transcript is safe; try again in a moment.",
        { retry: true },
      );
      return;
    }
    showState(error.message || "The debrief could not be loaded.", "", { retry: true });
  }
}

el.stateRetry.addEventListener("click", load);

el.checklistFilter?.addEventListener("change", () => {
  state.checklistStatus = el.checklistFilter.value;
  renderChecklist(state.checklistItems);
});

el.signOut.addEventListener("click", async () => {
  el.signOut.disabled = true;
  try {
    await fetch("/auth/logout", { method: "POST" });
  } finally {
    window.location.href = "/login";
  }
});

state.attemptId = window.location.pathname.split("/")[2];
if (state.attemptId) load();
else showState("Debrief not found.", "Open a debrief from your practice room.");
