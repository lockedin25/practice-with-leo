/* Shared light/dark preference & global navbar auth setup.
 * Loaded by every page before its own script so the theme and navbar behave identically everywhere.
 */

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

// Apply immediately on load to prevent theme flash
applyTheme(currentTheme());

function bindThemeToggles() {
  document.querySelectorAll("#theme-toggle, .theme-toggle-btn").forEach((btn) => {
    btn.removeEventListener("click", toggleHandler);
    btn.addEventListener("click", toggleHandler);
  });
}

function toggleHandler() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
}

/* Account menu behaviour.
 *
 * The signed-in identity is rendered server side by the shell templates, so
 * this no longer requests /api/me. That request produced a 401 in the console
 * on every public page, ran up to four times on one page load, and flashed the
 * signed-out header before it resolved.
 */
function initGlobalNavbar() {
  const userMenu = document.querySelector("#user-menu");
  const userChip = document.querySelector("#user-chip");
  const userSheet = document.querySelector("#user-sheet");
  const signOutBtns = document.querySelectorAll("#sign-out, .sign-out-btn");

  if (userChip && userSheet && !userChip.dataset.navBound) {
    userChip.dataset.navBound = "true";
    userChip.addEventListener("click", (e) => {
      e.stopPropagation();
      const isHidden = userSheet.classList.toggle("hidden");
      userChip.setAttribute("aria-expanded", String(!isHidden));
    });

    document.addEventListener("click", (e) => {
      if (userMenu && !userMenu.contains(e.target)) {
        userSheet.classList.add("hidden");
        userChip.setAttribute("aria-expanded", "false");
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && userSheet && !userSheet.classList.contains("hidden")) {
        userSheet.classList.add("hidden");
        userChip.setAttribute("aria-expanded", "false");
      }
    });
  }

  signOutBtns.forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        await fetch("/auth/logout", { method: "POST" });
      } finally {
        window.location.href = "/login";
      }
    });
  });
}

/* Phone navigation. The inline nav links are hidden below 900px, so this
 * sheet is the only way to reach Practice room and Your progress there. */
function bindMobileNav() {
  const toggle = document.querySelector("#nav-menu-toggle");
  const sheet = document.querySelector("#nav-mobile");
  if (!toggle || !sheet || toggle.dataset.navBound) return;
  toggle.dataset.navBound = "true";

  const setOpen = (open) => {
    sheet.classList.toggle("hidden", !open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  };

  toggle.addEventListener("click", () => setOpen(sheet.classList.contains("hidden")));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setOpen(false);
  });
}

function initPage() {
  bindThemeToggles();
  bindMobileNav();
  initGlobalNavbar();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initPage);
} else {
  initPage();
}
