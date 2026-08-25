/* Public landing-page client.
 *
 * The landing page shows a deliberately short starting path, never the whole
 * catalogue: the 69-scenario library and its filters live on /cases. Every
 * number on the page is derived from /api/cases so the marketing copy cannot
 * drift from the reservoir.
 *
 * Auth state is rendered into the shared header server side, so this file
 * never requests the signed-in user; an anonymous visit makes no failing
 * request at all.
 */

const grid = document.querySelector("#case-grid");
const libraryCount = document.querySelector("#library-count");
const proofCount = document.querySelector("#proof-case-count");

const PREVIEW_SIZE = 10;
const CORE_SCHOOL = "MBB Core";

/* The path climbs on purpose: two foundation diagnostics, a broad spread of
 * Round 1 staples, then advanced M&A and sustainability work. Ids missing
 * from the catalogue are backfilled from MBB Core, so the preview never
 * renders short because a case was renamed. */
const CURATED_IDS = [
  "meridian-cold-chain-v1",
  "harvest-table-v1",
  "clearcart-v1",
  "sunpeak-solar-v1",
  "metrolink-mobility-v1",
  "aster-diagnostics-v1",
  "bluecurrent-water-v1",
  "northstar-bank-v1",
  "orbit-learning-v1",
  "forge-components-v1",
];

const words = (value) => String(value || "").replace(/_/g, " ").trim();

/** "mergers_and_acquisitions" -> "Mergers and acquisitions" */
function sentenceCase(value) {
  const text = words(value);
  return text ? text[0].toUpperCase() + text.slice(1) : "";
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/** The curated slots first, then MBB Core, then anything, never duplicating. */
function startingPath(cases) {
  const byId = new Map(cases.map((item) => [item.id, item]));
  const chosen = [];
  const taken = new Set();

  const take = (item) => {
    if (!item || taken.has(item.id) || chosen.length >= PREVIEW_SIZE) return;
    taken.add(item.id);
    chosen.push(item);
  };

  CURATED_IDS.forEach((id) => take(byId.get(id)));
  cases.filter((item) => item.school === CORE_SCHOOL).forEach(take);
  cases.forEach(take);
  return chosen;
}

function pathRow(item, index) {
  const link = element("a", "path-case");
  link.href = `/practice?case=${encodeURIComponent(item.id)}`;

  const order = element("span", "path-index", String(index + 1).padStart(2, "0"));
  order.setAttribute("aria-hidden", "true");
  link.append(order);

  const main = element("span", "path-main");
  main.append(element("span", "path-title", item.title || "Untitled case"));
  const meta = [sentenceCase(item.category), sentenceCase(item.industry)].filter(Boolean).join(" · ");
  if (meta) main.append(element("span", "path-meta", meta));
  link.append(main);

  if (item.difficulty) {
    const level = element("span", "path-level", sentenceCase(item.difficulty));
    level.dataset.level = String(item.difficulty).toLowerCase();
    link.append(level);
  }

  const arrow = element("span", "arrow", "→");
  arrow.setAttribute("aria-hidden", "true");
  link.append(arrow);

  const row = element("li");
  row.append(link);
  return row;
}

function placeholder(message) {
  return element("li", "path-placeholder", message);
}

function renderPath(cases) {
  if (!grid) return;
  const chosen = startingPath(cases);
  if (!chosen.length) {
    grid.replaceChildren(placeholder("No cases are available right now."));
    return;
  }
  grid.replaceChildren(...chosen.map(pathRow));
}

/* One content rule for the whole product: the library total is every scenario,
 * of which MBB Core is a named subset. */
function libraryLine(cases) {
  const total = cases.length;
  const core = cases.filter((item) => item.school === CORE_SCHOOL).length;
  const rest = total - core;
  const schools = [...new Set(cases.map((item) => item.school).filter((name) => name && name !== CORE_SCHOOL))].sort();

  if (!core || !rest || !schools.length) {
    return `${total} scenarios in the full library.`;
  }

  const sources =
    schools.length > 1 ? `${schools.slice(0, -1).join(", ")}, and ${schools[schools.length - 1]}` : schools[0];
  return `${total} scenarios in the full library: ${core} MBB Core plus ${rest} exemplars from ${sources}.`;
}

fetch("/api/cases")
  .then((response) => (response.ok ? response.json() : Promise.reject(new Error("Case library unavailable"))))
  .then((payload) => {
    const cases = Array.isArray(payload.cases) ? payload.cases : [];
    renderPath(cases);
    if (!cases.length) return;
    if (proofCount) proofCount.textContent = String(cases.length);
    if (libraryCount) libraryCount.textContent = libraryLine(cases);
    document.querySelector("#browse-all-cases")?.replaceChildren(
      document.createTextNode(`Browse all ${cases.length} cases `),
      element("span", "arrow", "→"),
    );
  })
  .catch(() => {
    // Leave the server-rendered counts alone; only the path needs a fallback.
    grid?.replaceChildren(placeholder("The case library could not be loaded. Refresh to try again."));
  });
