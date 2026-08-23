/* Sign-in page: carries the post-login destination and explains failures. */

const MESSAGES = {
  not_configured:
    "Google sign-in is not configured on this server yet. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env and restart.",
  denied: "Sign-in was cancelled, so nothing was shared with Leo.",
  invalid_response: "That sign-in attempt came back incomplete. Please try again.",
  state_mismatch: "That sign-in link did not match this browser session. Please try again.",
  state_expired: "That sign-in link expired. Please try again.",
  google_error: "Google could not complete the sign-in. Please try again in a moment.",
  domain_not_allowed: "This Leo deployment does not accept that email domain.",
};

const params = new URLSearchParams(window.location.search);
const button = document.querySelector("#google-button");
const alertBox = document.querySelector("#auth-alert");
const domainNote = document.querySelector("#domain-note");

const next = params.get("next");
const destination = next && next.startsWith("/") && !next.startsWith("//") ? next : "/practice";
button.href = `/auth/google/start?next=${encodeURIComponent(destination)}`;

const error = params.get("error");
if (error) {
  alertBox.textContent = MESSAGES[error] || "Sign-in did not complete. Please try again.";
  alertBox.classList.remove("hidden");
}

fetch("/api/auth/config")
  .then((response) => (response.ok ? response.json() : null))
  .then((config) => {
    if (!config) return;
    if (!config.google_configured) {
      button.classList.add("is-disabled");
      button.setAttribute("aria-disabled", "true");
      if (!error) {
        alertBox.textContent = MESSAGES.not_configured;
        alertBox.classList.remove("hidden");
      }
    }
    if (config.allowed_domains?.length) {
      domainNote.textContent = `Open to ${config.allowed_domains.join(", ")} accounts.`;
      domainNote.classList.remove("hidden");
    }
  })
  .catch(() => {
    /* The button still works; the server will report configuration problems. */
  });
