/* ==========================================================================
   Case Library

   The library is a practice pathway, not an inventory. A card carries only
   what picks a case: name, type, difficulty, the real decision question, and
   progress. Search and the Recommended / All switch are tier one; type and
   difficulty sit behind Filters; source sits behind that.
   ========================================================================== */

const els = {
  search: document.querySelector("#case-search"),
  searchClear: document.querySelector("#search-clear"),
  filtersToggle: document.querySelector("#filters-toggle"),
  filtersCount: document.querySelector("#filters-count"),
  filtersPanel: document.querySelector("#filters-panel"),
  filtersScrim: document.querySelector("#filters-scrim"),
  filtersClose: document.querySelector("#filters-close"),
  filtersClear: document.querySelector("#filters-clear"),
  filtersDone: document.querySelector("#filters-done"),
  typeChips: document.querySelector("#type-chips"),
  levelChips: document.querySelector("#level-chips"),
  sourceSelect: document.querySelector("#source-select"),
  personaSelect: document.querySelector("#persona-select"),
  sortSelect: document.querySelector("#sort-select"),
  viewSwitch: document.querySelector("#view-switch"),
  results: document.querySelector("#results-count"),
  resultsReset: document.querySelector("#results-reset"),
  scale: document.querySelector("#lib-scale"),
  rail: document.querySelector("#rail"),
  railTitle: document.querySelector("#rail-title"),
  railNote: document.querySelector("#rail-note"),
  railTrack: document.querySelector("#rail-track"),
  grid: document.querySelector("#cases-grid"),
};

const LEVELS = ["foundation", "intermediate", "advanced"];
const LEVEL_INDEX = { foundation: 0, intermediate: 1, advanced: 2 };

/* The interviewer persona is chosen here and applied when a case starts, because
 * an attempt's persona is fixed for its lifetime. The room reads this key, and it
 * is also stamped onto every start link so a shared or bookmarked URL keeps the
 * choice rather than silently reverting to the default. */
const PERSONA_IDS = ["coached", "realistic", "pressure"];
const STORAGE_PERSONA = "leo.persona";

function readPersona() {
  try {
    const stored = localStorage.getItem(STORAGE_PERSONA);
    if (PERSONA_IDS.includes(stored)) return stored;
  } catch {
    /* Blocked site data is not an error worth surfacing; fall back. */
  }
  return "realistic";
}

function writePersona(value) {
  if (!PERSONA_IDS.includes(value)) return;
  try {
    localStorage.setItem(STORAGE_PERSONA, value);
  } catch {
    /* The link stamping below still carries the choice for this page. */
  }
}

function withPersona(href) {
  if (!href || !href.startsWith("/practice")) return href;
  const separator = href.includes("?") ? "&" : "?";
  return `${href}${separator}persona=${encodeURIComponent(readPersona())}`;
}

/* The library used to surface which B-school each case came from. It no longer
 * does: the corpus is mixed-provenance, naming any one institution is inaccurate,
 * and it is not a claim the product should make publicly. The axis that actually
 * matters to a candidate is whether a case shipped with the product or came from
 * another candidate. */
const SOURCE_NAMES = {
  curated: "Curated",
  community: "Community",
};

const sourceOf = (item) => (item.source === "community" ? "community" : "curated");

let allCases = [];
let progressByCase = {};
let isSignedIn = false;

const state = {
  view: "recommended",
  sort: "recommended",
  query: "",
  types: new Set(),
  levels: new Set(),
  source: "all",
};

/* --- Label casing -------------------------------------------------------- */
/* Naive title casing produced "Saas And B2b Tech" and
   "Mergers_And_Acquisitions". One helper, used for every taxonomy string. */

const ACRONYMS = {
  saas: "SaaS",
  b2b: "B2B",
  b2c: "B2C",
  d2c: "D2C",
  bnpl: "BNPL",
  fmcg: "FMCG",
  cpg: "CPG",
  msme: "MSME",
  ev: "EV",
  ai: "AI",
  it: "IT",
  kpi: "KPI",
  ebitda: "EBITDA",
  iot: "IoT",
  mfi: "MFI",
  ipp: "IPP",
};

/* Labels the compositional rules cannot reach. */
const PHRASES = {
  mergers_and_acquisitions: "M&A",
  ecommerce_and_marketplaces: "E-commerce & Marketplaces",
  ecommerce_marketplace: "E-commerce Marketplace",
};

const MINOR_WORDS = new Set(["of", "the", "to", "for", "in", "on", "a", "an", "vs", "per"]);

function humanLabel(raw) {
  const key = String(raw ?? "").trim().toLowerCase().replace(/\s+/g, "_");
  if (!key) return "";
  if (PHRASES[key]) return PHRASES[key];

  const words = key.split(/[_\-\s]+/).filter(Boolean);
  return words
    .map((word, index) => {
      if (ACRONYMS[word]) return ACRONYMS[word];
      // A standalone "and" joining two parts of a label reads better as "&".
      if (word === "and" && index > 0 && index < words.length - 1) return "&";
      if (MINOR_WORDS.has(word) && index > 0) return word;
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(" ");
}

/* --- Small helpers ------------------------------------------------------- */

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function show(el, visible) {
  el?.classList.toggle("hidden", !visible);
}

function progressFor(id) {
  return progressByCase[id] || { status: "not_started", attempts_count: 0 };
}

function levelOf(item) {
  const level = String(item.difficulty || "intermediate").toLowerCase();
  return LEVELS.includes(level) ? level : "intermediate";
}

function levelIndex(item) {
  return LEVEL_INDEX[levelOf(item)] ?? 1;
}

function joinList(values) {
  if (values.length <= 1) return values.join("");
  return `${values.slice(0, -1).join(", ")} and ${values[values.length - 1]}`;
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function activeFilterCount() {
  return state.types.size + state.levels.size + (state.source === "all" ? 0 : 1);
}

function isNarrowed() {
  return Boolean(state.query.trim()) || activeFilterCount() > 0;
}

/* --- Recommendation ------------------------------------------------------ */
/* Resume first, then the difficulty the candidate is actually working at,
   then case types they have practised least. Deterministic: the same
   progress always produces the same order. */

function recommendationContext() {
  const solved = allCases.filter((item) => progressFor(item.id).status === "solved");
  const load = {};
  allCases.forEach((item) => {
    if (progressFor(item.id).status !== "not_started") {
      load[item.category] = (load[item.category] || 0) + 1;
    }
  });
  const highestSolved = solved.length ? Math.max(...solved.map(levelIndex)) : 0;
  const byVolume = solved.length >= 4 ? 2 : solved.length >= 1 ? 1 : 0;
  return {
    target: Math.min(2, Math.max(highestSolved, byVolume)),
    load,
    maxLoad: Math.max(0, ...Object.values(load)),
    solvedCount: solved.length,
    touchedCount: Object.values(load).reduce((sum, n) => sum + n, 0),
  };
}

function recommendScore(item, ctx) {
  const status = progressFor(item.id).status;
  let score = 0;
  if (status === "in_progress") score += 1000;
  else if (status === "solved") score -= 500;
  score += 60 - 22 * Math.abs(levelIndex(item) - ctx.target);
  score += 8 * (ctx.maxLoad - (ctx.load[item.category] || 0));
  if (sourceOf(item) === "curated") score += 6;
  return score;
}

function reasonFor(item, ctx) {
  if (progressFor(item.id).status === "in_progress") {
    return "You have an open attempt here. Pick up where you left off.";
  }
  if (!ctx.solvedCount) {
    return levelOf(item) === "foundation"
      ? "A clean first case: the numbers stay tractable while you build structure."
      : "A fair opening case for a candidate who already structures well.";
  }
  if (!ctx.load[item.category]) {
    return `New ground: no ${humanLabel(item.category)} case in your history yet.`;
  }
  if (levelIndex(item) === ctx.target) {
    return "Sits at the difficulty you are currently working at.";
  }
  return "Keeps your reps spread across case types.";
}

/* --- Filtering and sorting ---------------------------------------------- */

function matchesQuery(item, query) {
  if (!query) return true;
  const haystack = [
    item.title,
    item.summary,
    humanLabel(item.category),
    humanLabel(item.industry),
    item.category,
    item.industry,
    sourceOf(item),
    SOURCE_NAMES[sourceOf(item)] || "",
    item.difficulty,
    (item.skills_tested || []).join(" "),
    (item.firm_tags || []).join(" "),
    item.contributor_label || "",
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query);
}

function visibleCases() {
  const query = state.query.trim().toLowerCase();
  return allCases.filter((item) => {
    const status = progressFor(item.id).status;
    if (state.view === "in_progress" && status !== "in_progress") return false;
    if (state.view === "solved" && status !== "solved") return false;
    if (state.types.size && !state.types.has(item.category)) return false;
    if (state.levels.size && !state.levels.has(levelOf(item))) return false;
    if (state.source !== "all" && sourceOf(item) !== state.source) return false;
    return matchesQuery(item, query);
  });
}

function sortCases(items, ctx) {
  const byTitle = (a, b) => String(a.title).localeCompare(String(b.title));
  const copy = items.slice();
  switch (state.sort) {
    case "difficulty-asc":
      return copy.sort((a, b) => levelIndex(a) - levelIndex(b) || byTitle(a, b));
    case "difficulty-desc":
      return copy.sort((a, b) => levelIndex(b) - levelIndex(a) || byTitle(a, b));
    case "type":
      return copy.sort(
        (a, b) => humanLabel(a.category).localeCompare(humanLabel(b.category)) || byTitle(a, b)
      );
    case "title":
      return copy.sort(byTitle);
    default:
      return copy.sort((a, b) => recommendScore(b, ctx) - recommendScore(a, ctx) || byTitle(a, b));
  }
}

/* --- Cards --------------------------------------------------------------- */

const FALLBACK_SUMMARY =
  "Work a live executive decision with Leo, one earned fact at a time.";

function actionFor(item) {
  const progress = progressFor(item.id);
  if (progress.status === "in_progress") {
    return {
      label: "Resume case",
      href: progress.latest_attempt_id
        ? `/practice?attempt=${encodeURIComponent(progress.latest_attempt_id)}`
      : `/practice?case=${encodeURIComponent(item.id)}`,
    };
  }
  if (progress.status === "solved") return null;
  return {
    label: "Start case",
    href: `/practice?case=${encodeURIComponent(item.id)}`,
  };
}

function stateBadge(item) {
  const progress = progressFor(item.id);
  if (progress.status === "in_progress") {
    return '<span class="case-state case-state-in_progress">In progress</span>';
  }
  if (progress.status === "solved") {
    const score =
      typeof progress.best_score === "number" ? ` ${progress.best_score.toFixed(1)}/5` : "";
    return `<span class="case-state case-state-solved">Solved${esc(score)}</span>`;
  }
  return "";
}

function caseCard(item, options = {}) {
  const progress = progressFor(item.id);
  const level = levelOf(item);
  const action = actionFor(item);
  const wide = Boolean(options.wide);
  const origin = [
    esc(humanLabel(item.industry) || "General strategy"),
    esc(SOURCE_NAMES[sourceOf(item)]),
  ];

  const skills = wide
    ? (item.skills_tested || [])
        .slice(0, 4)
        .map((skill) => `<span class="case-skill">${esc(humanLabel(skill))}</span>`)
        .join("")
    : "";

  const debrief =
    progress.status === "solved" && progress.latest_attempt_id
      ? `<a class="case-secondary" href="/attempts/${encodeURIComponent(
          progress.latest_attempt_id
        )}/debrief">View debrief</a>`
      : "";

  const reset =
    isSignedIn && progress.status !== "not_started"
      ? `<button class="btn-reset-case" type="button" data-case-id="${esc(item.id)}">Reset test</button>`
      : "";

  const primaryAction = action
    ? `<a class="btn-start-case" href="${esc(withPersona(action.href))}" aria-label="${esc(
        `${action.label}: ${item.title}`
      )}">
        <span>${esc(action.label)}</span>
        <span class="arrow" aria-hidden="true">→</span>
      </a>`
    : "";

  return `
    <article class="case-card${wide ? " case-card-wide" : ""}" data-state="${esc(progress.status)}">
      <div class="case-head">
        <p class="case-kind">
          <span class="case-type">${esc(humanLabel(item.category))}</span>
          <span class="case-level case-level-${esc(level)}">${esc(humanLabel(level))}</span>
        </p>
        ${stateBadge(item)}
      </div>

      <h3 class="case-name">${esc(item.title)}</h3>
      <p class="case-question">${esc(item.summary || FALLBACK_SUMMARY)}</p>
      ${options.reason ? `<p class="case-reason">${esc(options.reason)}</p>` : ""}
      ${skills ? `<div class="case-skills">${skills}</div>` : ""}

      <p class="case-origin">${origin.join(" · ")}</p>
      <p class="case-origin">${esc(item.contributor_label || "Contributor not recorded")} · ${(item.firm_tags || []).map(esc).join(" · ") || "Firm not recorded"} · ${item.contributed_at ? esc(new Date(item.contributed_at).toLocaleDateString()) : "Contribution date not recorded"}</p>
      <div class="case-foot">
        ${primaryAction}
        ${debrief}
        ${reset}
      </div>
    </article>
  `;
}

/* --- Rendering ----------------------------------------------------------- */

function renderRail(ctx) {
  const eligible = state.view === "recommended" && !isNarrowed() && allCases.length > 0;
  if (!eligible) {
    show(els.rail, false);
    els.railTrack.innerHTML = "";
    return;
  }

  const picks = allCases
    .filter((item) => progressFor(item.id).status !== "solved")
    .sort((a, b) => recommendScore(b, ctx) - recommendScore(a, ctx) || String(a.title).localeCompare(String(b.title)))
    .slice(0, 3);

  if (!picks.length) {
    show(els.rail, false);
    return;
  }

  els.railTitle.textContent = isSignedIn ? "Recommended next" : "Start here";
  if (!isSignedIn) {
    els.railNote.textContent = "Sign in and Leo re-orders these from your own progress.";
  } else if (ctx.touchedCount) {
    els.railNote.textContent = `Built from the ${plural(ctx.touchedCount, "case")} you have worked so far.`;
  } else {
    els.railNote.textContent = "Your first three. These change as you complete cases.";
  }

  els.railTrack.innerHTML = picks
    .map((item) => caseCard(item, { wide: true, reason: reasonFor(item, ctx) }))
    .join("");
  show(els.rail, true);
  bindCardActions(els.railTrack);
}

function resultsCopy(count) {
  const total = allCases.length;
  if (!count) return "No cases match. Try fewer filters or a broader search term.";
  if (state.view === "in_progress") return `${plural(count, "case")} in progress.`;
  if (state.view === "solved") return `${plural(count, "case")} solved.`;
  if (isNarrowed()) return `${count} of ${total} cases match.`;
  if (state.sort === "recommended") {
    return isSignedIn
      ? `All ${total} case scenarios, ordered for you.`
      : `All ${total} case scenarios, gentlest first.`;
  }
  return `All ${total} case scenarios.`;
}

function emptyState() {
  if (state.view === "in_progress") {
    return `
      <div class="grid-state">
        <p class="grid-state-title">Nothing open right now</p>
        <p>Start a case and it will wait here until you come back to it.</p>
        <button class="btn btn-primary btn-sm" type="button" data-act="show-all">Browse all cases</button>
      </div>`;
  }
  if (state.view === "solved") {
    return `
      <div class="grid-state">
        <p class="grid-state-title">No completed cases yet</p>
        <p>Finish a case and Leo files the debrief here.</p>
        <button class="btn btn-primary btn-sm" type="button" data-act="show-all">Browse all cases</button>
      </div>`;
  }
  return `
    <div class="grid-state">
      <p class="grid-state-title">No cases match</p>
      <p>Nothing in the library fits that combination. Clearing the filters brings back all ${allCases.length} scenarios.</p>
      <button class="btn btn-primary btn-sm" type="button" data-act="clear-all">Clear search and filters</button>
    </div>`;
}

function singleResultAside(item) {
  const nearby = allCases
    .filter((other) => other.id !== item.id && other.category === item.category)
    .slice(0, 3);
  const links = nearby
    .map(
      (other) =>
        `<a href="/practice?case=${encodeURIComponent(other.id)}">${esc(other.title)}</a>`
    )
    .join("");
  return `
    <aside class="nudge">
      <p class="nudge-title">One match</p>
      <p class="nudge-note">${
        nearby.length
          ? `Other ${esc(humanLabel(item.category))} cases in the library:`
          : "Nothing else in the library sits close to this one."
      }</p>
      <div class="nudge-list">
        ${links}
        <button type="button" data-act="clear-all">Clear search and filters</button>
      </div>
    </aside>
  `;
}

function render() {
  const ctx = recommendationContext();
  const filtered = sortCases(visibleCases(), ctx);
  const count = filtered.length;

  els.grid.setAttribute("aria-busy", "false");

  const applied = activeFilterCount();
  els.results.textContent = resultsCopy(count);
  show(els.resultsReset, isNarrowed());
  els.filtersCount.textContent = String(applied);
  show(els.filtersCount, applied > 0);
  els.filtersToggle.setAttribute(
    "aria-label",
    applied ? `Filters, ${plural(applied, "filter")} applied` : "Filters"
  );

  renderRail(ctx);

  if (!count) {
    els.grid.dataset.density = "empty";
    els.grid.innerHTML = emptyState();
    bindCardActions(els.grid);
    return;
  }

  if (count === 1) {
    els.grid.dataset.density = "single";
    els.grid.innerHTML = caseCard(filtered[0], { wide: true }) + singleResultAside(filtered[0]);
    bindCardActions(els.grid);
    return;
  }

  els.grid.dataset.density = count === 2 ? "pair" : "many";
  els.grid.innerHTML = filtered.map((item) => caseCard(item)).join("");
  bindCardActions(els.grid);
}

/* --- Card side actions --------------------------------------------------- */

function bindCardActions(root) {
  root.querySelectorAll("[data-act='clear-all']").forEach((button) => {
    button.addEventListener("click", clearEverything);
  });
  root.querySelectorAll("[data-act='show-all']").forEach((button) => {
    button.addEventListener("click", () => setView("all"));
  });
  root.querySelectorAll(".btn-reset-case").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      const caseId = button.dataset.caseId;
      if (!caseId) return;
      if (!window.confirm("Reset this test? Your saved transcript and debrief will remain available.")) return;
      button.disabled = true;
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/reset`, {
          method: "POST",
        });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail || "Leo could not reset that case.");
        }
        const data = await response.json();
        progressByCase[caseId] = data.progress;
        render();
      } catch (error) {
        window.alert(error.message || "Leo could not reset that case.");
        button.disabled = false;
      }
    });
  });
}

/* --- Controls ------------------------------------------------------------ */

function setView(view) {
  state.view = view;
  els.viewSwitch.querySelectorAll(".view-tab").forEach((tab) => {
    const on = tab.dataset.view === view;
    tab.classList.toggle("is-active", on);
    tab.setAttribute("aria-pressed", on ? "true" : "false");
  });
  render();
}

function openFilters(open) {
  show(els.filtersPanel, open);
  show(els.filtersScrim, open);
  els.filtersToggle.setAttribute("aria-expanded", open ? "true" : "false");
  if (open) els.filtersPanel.querySelector(".filter-chip")?.focus();
}

function clearSearch({ focus = true } = {}) {
  state.query = "";
  els.search.value = "";
  show(els.searchClear, false);
  if (focus) els.search.focus();
  render();
}

function clearFilters() {
  state.types.clear();
  state.levels.clear();
  state.source = "all";
  if (els.sourceSelect) els.sourceSelect.value = "all";
  els.filtersPanel
    .querySelectorAll(".filter-chip")
    .forEach((chip) => chip.setAttribute("aria-pressed", "false"));
  render();
}

function clearEverything() {
  clearFilters();
  state.query = "";
  els.search.value = "";
  show(els.searchClear, false);
  setView("recommended");
}

function chipMarkup(value, label, count) {
  return `<button class="filter-chip" type="button" aria-pressed="false" data-value="${esc(value)}">
    <span>${esc(label)}</span><span class="filter-chip-count">${count}</span>
  </button>`;
}

function buildFilterControls() {
  const typeCounts = {};
  const levelCounts = {};
  const sourceCounts = {};
  allCases.forEach((item) => {
    typeCounts[item.category] = (typeCounts[item.category] || 0) + 1;
    levelCounts[levelOf(item)] = (levelCounts[levelOf(item)] || 0) + 1;
    const source = sourceOf(item);
    sourceCounts[source] = (sourceCounts[source] || 0) + 1;
  });

  els.typeChips.innerHTML = Object.entries(typeCounts)
    .sort((a, b) => b[1] - a[1] || humanLabel(a[0]).localeCompare(humanLabel(b[0])))
    .map(([value, count]) => chipMarkup(value, humanLabel(value), count))
    .join("");

  els.levelChips.innerHTML = LEVELS.filter((level) => levelCounts[level])
    .map((level) => chipMarkup(level, humanLabel(level), levelCounts[level]))
    .join("");

  // Curated first, and a source with no cases yet is simply not offered rather
  // than shown as an empty filter.
  const sources = ["curated", "community"].filter((key) => sourceCounts[key]);
  if (els.sourceSelect) {
    els.sourceSelect.innerHTML = [
      `<option value="all">Any source (${allCases.length})</option>`,
      ...sources.map(
        (key) =>
          `<option value="${esc(key)}">${esc(SOURCE_NAMES[key])} (${sourceCounts[key]})</option>`
      ),
    ].join("");
  }

  els.typeChips.querySelectorAll(".filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => toggleChip(chip, state.types));
  });
  els.levelChips.querySelectorAll(".filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => toggleChip(chip, state.levels));
  });
}

function toggleChip(chip, bucket) {
  const value = chip.dataset.value;
  const on = chip.getAttribute("aria-pressed") === "true";
  chip.setAttribute("aria-pressed", on ? "false" : "true");
  if (on) bucket.delete(value);
  else bucket.add(value);
  render();
}

/* Counts only. The previous version named the contributing institutions here,
 * which is exactly the claim the product no longer makes. */
function renderScale() {
  const total = allCases.length;
  const community = allCases.filter((item) => sourceOf(item) === "community").length;
  els.scale.textContent = community
    ? `${plural(total, "case scenario")}, all free: ${total - community} curated, ${community} contributed by the community.`
    : `${plural(total, "case scenario")}, all curated and all free.`;
}

/* --- Wiring -------------------------------------------------------------- */

els.viewSwitch?.querySelectorAll(".view-tab").forEach((tab) => {
  tab.addEventListener("click", () => setView(tab.dataset.view));
});

els.sortSelect?.addEventListener("change", (event) => {
  state.sort = event.target.value;
  render();
});

els.personaSelect?.addEventListener("change", (event) => {
  writePersona(event.target.value);
  // Re-render rather than mutate hrefs in place: the persona is stamped during
  // card construction, so a stale card would keep the previous choice.
  render();
});

els.sourceSelect?.addEventListener("change", (event) => {
  state.source = event.target.value;
  render();
});

let searchTimer = null;
els.search?.addEventListener("input", (event) => {
  const value = event.target.value;
  show(els.searchClear, Boolean(value));
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.query = value;
    render();
  }, 140);
});

els.searchClear?.addEventListener("click", () => clearSearch());

els.search?.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && els.search.value) {
    event.preventDefault();
    clearSearch();
  }
});

els.filtersToggle?.addEventListener("click", () => {
  openFilters(els.filtersToggle.getAttribute("aria-expanded") !== "true");
});
els.filtersClose?.addEventListener("click", () => {
  openFilters(false);
  els.filtersToggle.focus();
});
els.filtersScrim?.addEventListener("click", () => openFilters(false));
els.filtersDone?.addEventListener("click", () => {
  openFilters(false);
  els.filtersToggle.focus();
});
els.filtersClear?.addEventListener("click", clearFilters);
els.resultsReset?.addEventListener("click", clearEverything);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && els.filtersToggle?.getAttribute("aria-expanded") === "true") {
    openFilters(false);
    els.filtersToggle.focus();
    return;
  }
  const tag = (document.activeElement?.tagName || "").toLowerCase();
  if (event.key === "/" && !["input", "textarea", "select"].includes(tag)) {
    event.preventDefault();
    els.search?.focus();
  }
});

/* --- Data ---------------------------------------------------------------- */

Promise.all([
  fetch("/api/cases").then((res) =>
    res.ok ? res.json() : Promise.reject(new Error("Failed to load cases"))
  ),
  // Anonymous visitors are an expected state, not an error path.
  fetch("/api/me/case-progress")
    .then((res) => (res.ok ? res.json() : { progress: null }))
    .catch(() => ({ progress: null })),
])
  .then(([catalogue, saved]) => {
    allCases = catalogue.cases || [];
    isSignedIn = Array.isArray(saved.progress);
    progressByCase = Object.fromEntries(
      (saved.progress || []).map((entry) => [entry.case_id, entry])
    );

    document
      .querySelectorAll("[data-signed-in]")
      .forEach((el) => el.classList.toggle("hidden", !isSignedIn));

    // Reflect the stored choice before the first render, so the control and the
    // links it stamps cannot disagree on load.
    if (els.personaSelect) els.personaSelect.value = readPersona();

    renderScale();
    buildFilterControls();
    render();
  })
  .catch(() => {
    els.results.textContent = "The library did not load.";
    els.grid.setAttribute("aria-busy", "false");
    els.grid.dataset.density = "empty";
    els.grid.innerHTML = `
      <div class="grid-state">
        <p class="grid-state-title">The case library did not load</p>
        <p>Refresh the page to try again.</p>
      </div>`;
  });
