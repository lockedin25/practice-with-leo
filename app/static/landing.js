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
/* Cases that ship with the product, as opposed to community contributions. The
 * previous constant keyed off a B-school name, which the library no longer
 * surfaces. */
const CURATED_SOURCE = "curated";
const sourceOf = (item) => (item.source === "community" ? "community" : "curated");

/* The path climbs on purpose: two foundation diagnostics, a broad spread of
 * Round 1 staples, then advanced M&A and sustainability work. Ids missing
 * from the catalogue are backfilled from the curated set, so the preview never
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

/** The hand-picked slots first, then any curated case, then anything, never duplicating. */
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
  cases.filter((item) => sourceOf(item) === CURATED_SOURCE).forEach(take);
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

/* One content rule for the whole product: the library total is every scenario.
 * The split it reports is curated versus community, never the institutions the
 * source material came from. */
function libraryLine(cases) {
  const total = cases.length;
  const community = cases.filter((item) => sourceOf(item) === "community").length;
  if (!community) return `${total} scenarios in the full library, all free.`;
  return `${total} scenarios in the full library, all free: ${
    total - community
  } curated plus ${community} contributed by the community.`;
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
