/* ==========================================================================
   Contribute a case

   A conversation, not a form. The server owns the extraction state and the
   phase; this file owns the thread, the composer, and keeping the contributor
   oriented about how much further there is to go.
   ========================================================================== */

const els = {
  thread: document.querySelector("#thread"),
  startPanel: document.querySelector("#start-panel"),
  startButton: document.querySelector("#start-button"),
  composer: document.querySelector("#composer"),
  input: document.querySelector("#composer-input"),
  send: document.querySelector("#send-button"),
  submit: document.querySelector("#submit-button"),
  reset: document.querySelector("#reset-button"),
  pause: document.querySelector("#pause-button"),
  progress: document.querySelector("#progress"),
  track: document.querySelector("#phase-track"),
  missing: document.querySelector("#phase-missing"),
  trackerSummary: document.querySelector("#tracker-summary"),
  trackerList: document.querySelector("#tracker-list"),
  completionRule: document.querySelector("#completion-rule"),
  done: document.querySelector("#done-panel"),
};



let sessionId = null;
let busy = false;

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 401) {
    window.location.href = "/login?next=/contribute";
    throw new Error("Signed out");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Something went wrong. Try again.");
  return body;
}

function renderThread(messages) {
  els.thread.replaceChildren(
    ...messages.map((message) => {
      const turn = node("div", `turn turn-${message.role === "agent" ? "agent" : "you"}`);
      turn.append(
        node("p", "turn-who", message.role === "agent" ? "Leo" : "You"),
        node("p", "turn-body", message.content)
      );
      return turn;
    })
  );
  els.thread.scrollTop = els.thread.scrollHeight;
}

function renderCompletionTracker(view) {
  if (view.can_submit) {
    els.trackerSummary.textContent = "Ready for admin review";
  } else {
    const captured = Math.round((view.progress_score || 0) * 100);
    els.trackerSummary.textContent = `${captured}% of sections reviewed`;
  }
  els.completionRule.textContent = view.completion_rule || "";
  els.trackerList.replaceChildren(
    ...(view.completion_tracker || []).map((criterion) => {
      const item = node("li", `tracker-item is-${criterion.status}`);
      const copy = node("div", "tracker-copy");
      copy.append(
        node("span", "tracker-label", criterion.label),
        node("span", "tracker-progress", criterion.progress),
        node("span", "tracker-progress", Array.isArray(criterion.value) ? criterion.value.join(" · ") : criterion.value || "")
      );
      const role = criterion.discussion_complete ? "Discussion complete" : "Follow-up required";
      item.append(
        node("span", "tracker-mark", criterion.status === "captured" ? "✓" : criterion.status === "partial" ? "◐" : "○"),
        copy,
        node("span", "tracker-role", role)
      );
      return item;
    })
  );
}

function renderProgress(view) {
  els.progress.hidden = false;
  els.track.replaceChildren(...(view.question_tracker || []).map((question) => {
    const current = view.active_question?.id === question.id;
    const resolved = ["complete", "unavailable"].includes(question.status);
    const item = node("li", `phase-step${resolved ? " is-done" : ""}${current ? " is-current" : ""}`);
    item.append(node("span", "", `${question.label} · ${question.status === "complete" ? "Reviewed" : question.status === "unavailable" ? "Not recalled" : current ? "Current focus" : question.status === "partial" ? "In progress" : "Pending"}`));
    return item;
  }));
  renderCompletionTracker(view);

  const captured = Math.round((view.progress_score || 0) * 100);
  const facts = (view.completion_tracker || []).filter(row => Array.isArray(row.value) ? row.value.length : row.value).length;
  if (view.active_question) {
    const focus = view.active_question;
    els.missing.textContent = `${facts} fields captured · ${captured}% reviewed${view.can_submit ? " · Ready to submit" : ""}. Current focus: ${focus.label}. ${focus.missing_facets.length ? `Still needed: ${focus.missing_facets.join("; ")}.` : "Tell the story once; Leo will record every useful detail."}`;
  } else {
    els.missing.textContent = view.can_submit ? `${facts} fields captured · All sections reviewed. Submit when you are ready.` : "Every section has been discussed, but the core case details are still incomplete. Save your draft or add those details when you recall them.";
  }
}

function render(view) {
  sessionId = view.id;
  els.startPanel.hidden = true;
  els.composer.hidden = false;
  renderThread(view.messages || []);
  renderProgress(view);
  /* The server owns the weighted threshold. Missing enrichment fields may remain
   * when this becomes true; the synthesis pass completes them. */
  els.submit.hidden = !view.can_submit;
  els.input.value = view.draft || "";
}

function setBusy(state, label) {
  busy = state;
  els.send.disabled = state;
  els.submit.disabled = state;
  els.reset.disabled = state;
  els.pause.disabled = state;
  els.send.textContent = state ? label || "Sending…" : "Send";
}

function showError(message) {
  const existing = els.thread.querySelector(".turn-error");
  if (existing) existing.remove();
  const banner = node("div", "turn turn-error");
  banner.append(node("p", "turn-body", message));
  els.thread.append(banner);
  els.thread.scrollTop = els.thread.scrollHeight;
}

async function start() {
  setBusy(true, "Starting…");
  try {
    render(await request("/api/contributions", { method: "POST" }));
    els.input.focus();
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function send(event) {
  event.preventDefault();
  const content = els.input.value.trim();
  if (!content || busy || !sessionId) return;

  /* Show the contributor's own words immediately. The extraction turn is a long
   * call and a composer that just empties looks broken. */
  const pending = node("div", "turn turn-you");
  pending.append(node("p", "turn-who", "You"), node("p", "turn-body", content));
  els.thread.append(pending);
  els.thread.append(node("div", "turn turn-agent turn-thinking", "Leo is thinking…"));
  els.thread.scrollTop = els.thread.scrollHeight;
  els.input.value = "";
  setBusy(true);

  try {
    render(
      await request(`/api/contributions/${encodeURIComponent(sessionId)}/turn`, {
        method: "POST",
        body: JSON.stringify({ content }),
      })
    );
  } catch (error) {
    /* Put their words back in the box. Losing a long answer to a failed request
     * is the fastest way to lose the contributor as well. */
    pending.remove();
    els.thread.querySelector(".turn-thinking")?.remove();
    els.input.value = content;
    showError(error.message);
  } finally {
    setBusy(false);
    els.input.focus();
  }
}

async function submit() {
  if (busy || !sessionId) return;
  setBusy(true, "Submitting…");
  try {
    const result = await request(`/api/contributions/${encodeURIComponent(sessionId)}/submit`, {
      method: "POST",
      body: JSON.stringify({public_credit: document.querySelector("#public-credit").checked}),
    });
    els.composer.hidden = true;
    els.progress.hidden = true;
    els.done.hidden = false;
    els.done.replaceChildren(
      node("h2", "done-title", "Submitted, thank you"),
      node("p", "done-body", result.message),
      node(
        "p",
        "done-meta",
        "Every contributed case is reviewed by a person before it appears in the library."
      )
    );
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function pause() {
  if (busy || !sessionId) return;
  setBusy(true, "Saving…");
  try {
    await request(`/api/contributions/${encodeURIComponent(sessionId)}/pause`, {
      method: "POST",
      body: JSON.stringify({ draft: els.input.value }),
    });
    window.location.assign("/cases");
  } catch (error) {
    showError(error.message);
    setBusy(false);
  }
}

async function reset() {
  if (busy || !sessionId) return;
  const confirmed = window.confirm(
    "Start this contribution again? Your current reconstruction will be archived and cannot be restored."
  );
  if (!confirmed) return;
  setBusy(true, "Starting…");
  try {
    render(
      await request(`/api/contributions/${encodeURIComponent(sessionId)}/reset`, {
        method: "POST",
      })
    );
    els.input.focus();
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

els.startButton?.addEventListener("click", start);
els.composer?.addEventListener("submit", send);
els.submit?.addEventListener("click", submit);
els.pause?.addEventListener("click", pause);
els.reset?.addEventListener("click", reset);

/* Enter sends, Shift+Enter breaks the line. These answers run long, so the
 * newline has to stay easy to reach. */
els.input?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    els.composer.requestSubmit();
  }
});

/* Resume an unfinished conversation on load rather than making them start over. */
request("/api/contributions", { method: "POST" })
  .then((view) => {
    if ((view.messages || []).length > 1 || view.draft) render(view);
    else sessionId = view.id;
  })
  .catch(() => {
    /* Not signed in, or contribution is unavailable. The Start button reports it. */
  });
