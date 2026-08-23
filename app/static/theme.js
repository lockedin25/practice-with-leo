/* Shared light/dark preference. Loaded by every page before its own script so
 * the choice is applied once and behaves identically everywhere. */

const THEME_KEY = "casecall:theme";

function currentTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(THEME_KEY, theme);
}

if (localStorage.getItem(THEME_KEY)) applyTheme(currentTheme());

document.querySelector("#theme-toggle")?.addEventListener("click", () => {
  applyTheme(currentTheme() === "dark" ? "light" : "dark");
});
