/* Public landing-page client.
 *
 * The landing page fetches only the candidate-safe catalogue metadata. It never
 * creates an attempt or receives case facts; a practice session starts only
 * after the candidate explicitly selects a case.
 */
const grid = document.querySelector("#case-grid");
const counter = document.querySelector("#library-count");
const filters = [...document.querySelectorAll(".filter")];
let cases = [];
let activeFilter = "all";

const humanise = (value) => String(value || "")
  .replace(/_/g, " ")
  .replace(/\b\w/g, (letter) => letter.toUpperCase());

function visibleCases() {
  if (activeFilter === "all") return cases;
  if (activeFilter === "strategy") {
    return cases.filter((item) => ["market_entry", "mergers_and_acquisitions", "public_sector_strategy", "sustainability_strategy", "digital_transformation"].includes(item.category));
  }
  return cases.filter((item) => item.category === activeFilter);
}

function renderCases() {
  const visible = visibleCases();
  counter.textContent = `${visible.length} ${visible.length === 1 ? "case" : "cases"}`;
  if (!visible.length) {
    grid.replaceChildren(Object.assign(document.createElement("p"), { className: "loading", textContent: "No cases in this category yet." }));
    return;
  }

  grid.replaceChildren(...visible.map((item, index) => {
    const card = document.createElement("article");
    card.className = "case-card";
    card.style.setProperty("--order", index);
    const skills = (item.skills_tested || []).slice(0, 3).map((skill) => `<span>${humanise(skill)}</span>`).join("");
    card.innerHTML = `<div class="case-card-top"><span>${String(index + 1).padStart(2, "0")}</span><span>${humanise(item.difficulty)}</span></div><h3>${item.title}</h3><p class="case-category">${humanise(item.category)} · ${humanise(item.industry || "Business case")}</p><div class="case-skills">${skills}</div><a href="/practice?case=${encodeURIComponent(item.id)}">Begin case <span aria-hidden="true">→</span></a>`;
    return card;
  }));
}

filters.forEach((button) => button.addEventListener("click", () => {
  activeFilter = button.dataset.filter;
  filters.forEach((filter) => filter.classList.toggle("is-active", filter === button));
  renderCases();
}));

fetch("/api/cases")
  .then((response) => response.ok ? response.json() : Promise.reject(new Error("Case library unavailable")))
  .then((payload) => { cases = payload.cases || []; renderCases(); })
  .catch(() => { counter.textContent = "Temporarily unavailable"; grid.replaceChildren(Object.assign(document.createElement("p"), { className: "loading", textContent: "The case library could not be loaded. Please refresh to try again." })); });
