/* Leo admin console: cohort metrics, per-candidate rollups, and the full
 * transcript of any attempt rendered the way the candidate saw it. */

const state = { overview: null, users: [], attempts: [], filter: "", caseTitles: new Map() };

const el = {
  freshness: document.querySelector("#freshness"),
  refresh: document.querySelector("#refresh"),
  viewer: document.querySelector("#viewer"),
  signOut: document.querySelector("#sign-out"),
  tiles: document.querySelector("#tiles"),
  bars: document.querySelector("#bars"),
  chartTotal: document.querySelector("#chart-total"),
  axisStart: document.querySelector("#axis-start"),
  axisEnd: document.querySelector("#axis-end"),
  stageBreakdown: document.querySelector("#stage-breakdown"),
  caseBreakdown: document.querySelector("#case-breakdown"),
  usersBody: document.querySelector("#users-body"),
  usersCount: document.querySelector("#users-count"),
  attemptsBody: document.querySelector("#attempts-body"),
  attemptsCount: document.querySelector("#attempts-count"),
  userFilter: document.querySelector("#user-filter"),
  drawer: document.querySelector("#drawer"),
  drawerVeil: document.querySelector("#drawer-veil"),
  drawerTitle: document.querySelector("#drawer-title"),
  drawerMeta: document.querySelector("#drawer-meta"),
  drawerBody: document.querySelector("#drawer-body"),
  drawerClose: document.querySelector("#drawer-close"),
  toasts: document.querySelector("#toasts"),
};

/* --- Helpers ------------------------------------------------------------- */

async function api(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (response.status === 401) {
    window.location.href = "/login?next=/admin";
    throw new Error("signed out");
  }
  if (response.status === 403) {
    window.location.href = "/practice";
    throw new Error("not an administrator");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function toast(message, kind = "error") {
  const item = node("div", `toast is-${kind}`, message);
  el.toasts.append(item);
  window.setTimeout(() => {
    item.classList.add("is-leaving");
    item.addEventListener("animationend", () => item.remove(), { once: true });
  }, 5000);
}

/* SQLite hands back "YYYY-MM-DD HH:MM:SS" in UTC, which most browsers would
 * otherwise read as local time. */
function parseUtc(value) {
  if (!value) return null;
  const parsed = new Date(`${String(value).replace(" ", "T")}Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

const RELATIVE_STEPS = [
  [60, "s"],
  [3600, "min"],
  [86400, "h"],
];

function relativeTime(value) {
  const moment = parseUtc(value);
  if (!moment) return "Not recorded";
  const seconds = Math.max(0, (Date.now() - moment.getTime()) / 1000);
  if (seconds < 45) return "just now";
  for (const [limit, unit] of RELATIVE_STEPS) {
    if (seconds < limit * 60 && limit >= 60) {
      return `${Math.round(seconds / limit)} ${unit} ago`;
    }
  }
  const days = Math.round(seconds / 86400);
  if (days <= 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  return moment.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/* --- Labels --------------------------------------------------------------
 * One formatter for every enum the API hands over. The attempt rows speak
 * snake_case ("drill_down") and kebab-case (case ids), and neither reads as
 * English without this. Identical copies live in profile.js and debrief.js;
 * the three scripts are never loaded together.
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

/* The admin API returns case_id only, so the console used to show the slug
 * ("02 Airline Fleet Optimization") in place of the real case title
 * ("Low-Cost Airline Turnaround Time"). The catalogue is the only place the
 * title exists, so it is loaded once at boot and looked up here. The
 * de-slugged id stays as the fallback for a case that has left the library. */
const caseName = (caseId) => {
  const id = String(caseId || "");
  return state.caseTitles.get(id) || titleCase(id.replace(/-v\d+$/, "")) || "Unknown case";
};

const percent = (ratio) => `${Math.round((ratio || 0) * 100)}%`;

function personCell(person) {
  const wrap = node("div", "person");
  if (!person) {
    wrap.append(node("span", "pill pill-quiet", "Unattributed"));
    return wrap;
  }
  if (person.picture) {
    const image = document.createElement("img");
    image.className = "person-avatar";
    image.src = person.picture;
    image.alt = "";
    image.referrerPolicy = "no-referrer";
    wrap.append(image);
  } else {
    wrap.append(node("span", "person-avatar is-letter", (person.name || person.email || "?")[0].toUpperCase()));
  }
  const identity = node("div");
  identity.append(
    node("p", "person-name", person.name || person.email),
    node("p", "person-email", person.email),
  );
  wrap.append(identity);
  return wrap;
}

/* --- Rendering ---------------------------------------------------------- */

function renderViewer(user) {
  el.viewer.replaceChildren(...personCell(user).childNodes);
}

function renderTiles(totals) {
  const tiles = [
    ["Candidates", totals.users, `${totals.users_active_7d} active this week`],
    ["Attempts", totals.attempts, `${totals.attempts_7d} in the last 7 days`],
    ["Completed", totals.attempts_completed, `${percent(totals.completion_rate)} completion rate`],
    ["Turns per attempt", totals.avg_turns_per_attempt, `${totals.candidate_turns} turns in total`],
    ["Facts per attempt", totals.avg_facts_per_attempt, `${totals.facts_released} facts released`],
    ["Minutes per attempt", totals.avg_minutes_per_attempt, `${totals.attempts_in_progress} attempts open`],
  ];
  el.tiles.replaceChildren(
    ...tiles.map(([label, value, note]) => {
      const tile = node("article", "tile");
      tile.append(
        node("p", "tile-label", label),
        node("p", "tile-value", String(value ?? 0)),
        node("p", "tile-note", note),
      );
      return tile;
    }),
  );
}

function renderChart(daily) {
  const peak = Math.max(1, ...daily.map((day) => day.count));
  el.chartTotal.textContent = String(daily.reduce((sum, day) => sum + day.count, 0));
  el.bars.replaceChildren(
    ...daily.map((day) => {
      /* A quiet day still draws a trace on the baseline. Two bars in a row of
       * fourteen empty slots looked like a broken chart rather than a quiet
       * fortnight. */
      const modifier = day.count === 0 ? " is-zero" : day.count === peak ? " is-peak" : "";
      const bar = node("div", `bar${modifier}`);
      bar.style.height = day.count === 0 ? "2px" : `${Math.max(8, Math.round((day.count / peak) * 100))}%`;
      bar.title = `${day.date}: ${day.count} attempt${day.count === 1 ? "" : "s"}`;
      return bar;
    }),
  );
  const shortDate = (value) =>
    new Date(`${value}T00:00:00Z`).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  el.axisStart.textContent = daily.length ? shortDate(daily[0].date) : "";
  el.axisEnd.textContent = daily.length ? shortDate(daily[daily.length - 1].date) : "";
}

function renderBreakdown(target, rows, formatter = titleCase) {
  if (!rows.length) {
    target.replaceChildren(node("p", "tile-note", "Nothing recorded yet."));
    return;
  }
  const peak = Math.max(...rows.map((row) => row.count));
  target.replaceChildren(
    ...rows.map((row) => {
      const line = node("div", "breakdown-row");
      const track = node("div", "breakdown-track");
      const fill = node("div", "breakdown-fill");
      fill.style.width = `${Math.max(4, Math.round((row.count / peak) * 100))}%`;
      track.append(fill);
      line.append(
        node("p", "breakdown-label", formatter(row.key)),
        node("span", "breakdown-count", String(row.count)),
        track,
      );
      return line;
    }),
  );
}

function renderUsers(users) {
  el.usersCount.textContent = String(users.length);
  el.usersCount.classList.toggle("is-live", users.length > 0);

  if (!users.length) {
    el.usersBody.replaceChildren(emptyRow(6, "No one has signed in yet."));
    return;
  }

  el.usersBody.replaceChildren(
    ...users.map((user) => {
      const row = document.createElement("tr");
      const person = document.createElement("td");
      person.append(personCell(user));
      if (user.is_admin) person.querySelector(".person").append(node("span", "pill pill-done", "Admin"));

      row.append(
        person,
        cell(String(user.attempts), "numeric"),
        cell(`${user.attempts_completed} · ${percent(user.completion_rate)}`, "numeric"),
        cell(String(user.avg_turns), "numeric"),
        cell(String(user.facts_released), "numeric"),
        cell(relativeTime(user.last_login_at)),
      );
      return row;
    }),
  );
}

function renderFilter(users) {
  const selected = el.userFilter.value;
  el.userFilter.replaceChildren(
    Object.assign(document.createElement("option"), { value: "", textContent: "All candidates" }),
    ...users.map((user) =>
      Object.assign(document.createElement("option"), {
        value: user.id,
        textContent: `${user.name || user.email} (${user.attempts})`,
      }),
    ),
  );
  el.userFilter.value = selected;
}

function renderAttempts(attempts) {
  const rows = state.filter
    ? attempts.filter((attempt) => (attempt.user || {}).id === state.filter)
    : attempts;
  el.attemptsCount.textContent = String(rows.length);
  el.attemptsCount.classList.toggle("is-live", rows.length > 0);

  if (!rows.length) {
    el.attemptsBody.replaceChildren(emptyRow(8, "No attempts recorded yet."));
    return;
  }

  el.attemptsBody.replaceChildren(
    ...rows.map((attempt) => {
      const row = document.createElement("tr");
      row.className = "is-clickable";
      row.tabIndex = 0;
      const person = document.createElement("td");
      person.append(personCell(attempt.user));
      const status = document.createElement("td");
      status.append(
        node("span", `pill ${attempt.ended ? "pill-done" : "pill-live"}`, attempt.ended ? "Complete" : "In progress"),
      );

      row.append(
        person,
        cell(caseName(attempt.case_id)),
        cell(titleCase(attempt.stage)),
        cell(String(attempt.candidate_turns), "numeric"),
        cell(String(attempt.facts_released), "numeric"),
        cell(attempt.duration_minutes === null ? "–" : String(attempt.duration_minutes), "numeric"),
        cell(relativeTime(attempt.started_at || attempt.updated_at)),
        status,
      );
      const open = () => openTranscript(attempt.id);
      row.addEventListener("click", open);
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          open();
        }
      });
      return row;
    }),
  );
}

function cell(text, className) {
  const element = document.createElement("td");
  if (className) element.className = className;
  element.textContent = text;
  return element;
}

function emptyRow(columns, text) {
  const row = document.createElement("tr");
  const only = document.createElement("td");
  only.colSpan = columns;
  only.className = "table-empty";
  only.textContent = text;
  row.append(only);
  return row;
}

/* --- Transcript drawer -------------------------------------------------- */

let lastFocused = null;

async function openTranscript(attemptId) {
  lastFocused = document.activeElement;
  try {
    const data = await api(`/api/admin/attempts/${attemptId}`);
    renderDrawer(data);
  } catch (error) {
    toast(error.message);
  }
}

function renderDrawer({ attempt, messages, facts, scorecard, evaluation }) {
  el.drawerTitle.textContent = caseName(attempt.case_id);
  el.drawerMeta.replaceChildren(
    node("span", "tag tag-accent", attempt.user ? attempt.user.name || attempt.user.email : "Unattributed"),
    node("span", "tag", `${titleCase(attempt.stage)} reached`),
    node("span", "tag", `${attempt.candidate_turns} turns`),
    node("span", "tag", `${attempt.facts_released} facts`),
    node("span", "tag", attempt.duration_minutes === null ? "Duration unknown" : `${attempt.duration_minutes} min`),
    node("span", "tag", attempt.ended ? "Complete" : "In progress"),
  );

  const sections = [];

  const report = evaluation?.report;
  if (report) {
    const section = node("section", "drawer-section");
    section.append(node("p", "eyebrow", `Evaluator Debrief · ${evaluation.evaluator_version || "v1"}`));
    const grid = node("div", "scorecard-grid");
    if (Array.isArray(report.dimensions)) {
      grid.append(
        ...report.dimensions.map((dimension) => {
          const line = node("div", "scorecard-line");
          line.append(
            node("strong", null, titleCase(dimension.name)),
            node("span", "band band-strong", `${dimension.score}/10`),
          );
          return line;
        }),
      );
    }
    section.append(grid);
    if (report.headline_strengths?.length) {
      const drill = node("div", "next-drill");
      drill.append(node("p", "micro-label", "Key strengths"), node("p", null, report.headline_strengths.join(" · ")));
      section.append(drill);
    }
    if (report.priority_improvements?.length) {
      const drill = node("div", "next-drill");
      drill.append(node("p", "micro-label", "Priority improvements"), node("p", null, report.priority_improvements.join(" · ")));
      section.append(drill);
    }
    if (report.next_drill) {
      const drill = node("div", "next-drill");
      drill.append(node("p", "micro-label", "Next drill"), node("p", null, report.next_drill));
      section.append(drill);
    }
    sections.push(section);
  } else if (scorecard) {
    const section = node("section", "drawer-section");
    section.append(node("p", "eyebrow", "Scorecard"));
    const grid = node("div", "scorecard-grid");
    grid.append(
      ...scorecard.dimensions.map((dimension) => {
        const line = node("div", "scorecard-line");
        line.append(
          node("strong", null, dimension.name),
          node("span", `band band-${String(dimension.band).toLowerCase()}`, dimension.band),
        );
        return line;
      }),
    );
    section.append(grid);
    if (scorecard.next_drill) {
      const drill = node("div", "next-drill");
      drill.append(node("p", "micro-label", "Next drill"), node("p", null, scorecard.next_drill));
      section.append(drill);
    }
    sections.push(section);
  }

  const transcript = node("section", "drawer-section");
  transcript.append(node("p", "eyebrow", `Transcript · ${messages.length} messages`));
  const thread = node("div", "drawer-transcript");
  thread.append(...messages.map(buildMessage));
  transcript.append(thread);
  sections.push(transcript);

  const evidence = node("section", "drawer-section");
  evidence.append(node("p", "eyebrow", `Evidence released · ${facts.length}`));
  const list = node("div", "facts");
  if (facts.length) {
    list.append(
      ...facts.map((fact, index) => {
        const card = node("article", "fact");
        card.append(
          node("span", "fact-index", `${String(index + 1).padStart(2, "0")} · ${titleCase(fact.id.replace(/\./g, " "))}`),
          node("p", "fact-content", fact.content),
        );
        return card;
      }),
    );
  } else {
    const empty = node("div", "facts-empty");
    empty.append(node("strong", null, "Nothing was released"), node("span", null, "The candidate did not earn any case evidence."));
    list.append(empty);
  }
  evidence.append(list);
  sections.push(evidence);

  el.drawerBody.replaceChildren(...sections);
  el.drawerBody.scrollTop = 0;
  el.drawer.classList.remove("hidden");
  el.drawerVeil.classList.remove("hidden");
  el.drawer.focus();
}

function buildMessage(message) {
  const item = document.querySelector("#message-template").content.firstElementChild.cloneNode(true);
  item.classList.add(message.role);
  item.querySelector(".message-role").textContent = message.role === "candidate" ? "Candidate" : "Leo";
  item.querySelector(".message-content").textContent = message.content;
  return item;
}

function closeDrawer() {
  el.drawer.classList.add("hidden");
  el.drawerVeil.classList.add("hidden");
  lastFocused?.focus?.();
}

el.drawerClose.addEventListener("click", closeDrawer);
el.drawerVeil.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !el.drawer.classList.contains("hidden")) closeDrawer();
});

/* --- Boot --------------------------------------------------------------- */

el.userFilter.addEventListener("change", () => {
  state.filter = el.userFilter.value;
  renderAttempts(state.attempts);
});

el.refresh.addEventListener("click", () => refresh());

el.signOut.addEventListener("click", async () => {
  el.signOut.disabled = true;
  try {
    await fetch("/auth/logout", { method: "POST" });
  } finally {
    window.location.href = "/login";
  }
});

/* The case catalogue, keyed by id, so every attempt row can show the title a
 * candidate saw rather than the id it was stored under. */
async function loadCaseTitles() {
  if (state.caseTitles.size) return;
  try {
    const { cases } = await api("/api/cases");
    state.caseTitles = new Map((cases || []).map((item) => [item.id, item.title]));
  } catch {
    /* A missing catalogue is not worth failing the console over: caseName
     * falls back to the de-slugged id. */
  }
}

async function refresh() {
  el.refresh.disabled = true;
  try {
    await loadCaseTitles();
    const [overview, users, attempts] = await Promise.all([
      api("/api/admin/overview"),
      api("/api/admin/users"),
      api("/api/admin/attempts?limit=500"),
    ]);
    state.overview = overview;
    state.users = users.users;
    state.attempts = attempts.attempts;

    renderTiles(overview.totals);
    renderChart(overview.daily);
    renderBreakdown(el.stageBreakdown, overview.stage_reached);
    renderBreakdown(el.caseBreakdown, overview.case_mix, caseName);
    renderUsers(state.users);
    renderFilter(state.users);
    renderAttempts(state.attempts);

    const unattributed = overview.totals.unattributed_attempts;
    el.freshness.textContent = [
      `Updated ${new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`,
      `${attempts.total} attempts`,
      `${state.users.length} candidates`,
      unattributed ? `${unattributed} pre-sign-in attempts` : null,
    ]
      .filter(Boolean)
      .join(" · ");
    if (overview.truncated) toast("Showing the most recent 2,000 attempts only.", "warning");
  } catch (error) {
    el.freshness.textContent = "Could not load the console.";
    toast(error.message);
  } finally {
    el.refresh.disabled = false;
  }
}

async function boot() {
  try {
    const { user } = await api("/api/me");
    renderViewer(user);
  } catch {
    return;
  }
  await refresh();
}

boot();
