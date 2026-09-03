# Campaign Roadmap — from Persona Feedback to Shippable Work

This is a dispatch plan for the findings in `docs/campaign/FEEDBACK.md`.
Items are deliberately narrow: one worker should be able to implement and
verify each in about 25 minutes. Order is intentional: every P0 trust or
availability blocker is handled before the highest-delight learning-loop work.

## Contract guardrails

- Keep `GET /api/attempts/{id}/evaluation` at `200` with the existing full
  `EvaluationReport` payload when a report is ready. New reliability metadata
  must be additive, so existing debrief consumers continue to work.
- Preserve the five contractual dimension keys and their 1.0–5.0 values. An
  incomplete or fallback result may be useful coaching, but it must not be
  presented as a comparable headline score or MBB badge.
- Keep transcript evidence candidate-safe: citations may point only to the
  candidate's own recorded messages, never hidden facts or evaluator internals.

## Ordered backlog

### 1. [P0] Gate invalid or fallback evaluation headlines

**Why now:** all personas lose trust when a keyword fallback or an empty report
looks like a confident partner assessment. This covers feedback P0-1 and P0-3.

- **Files to touch:** `app/evaluator.py`, `app/main.py`, `app/static/debrief.js`,
  `app/static/debrief.html`, `app/static/debrief.css`,
  `tests/test_debrief_reliability.py`, `tests/test_debrief_ui.py`.
- **Endpoint / UI surface:** `POST /api/attempts/{id}/end` and
  `GET /api/attempts/{id}/evaluation`; the debrief executive header.
- **Implementation slice:** add an additive report reliability state
  (`complete`, `provisional`, or `incomplete`) plus a candidate-safe retry
  message. Mark caught evaluator failures with a persisted internal log reason;
  mark fallback and completeness-violation reports provisional/incomplete. The
  debrief replaces the score and MBB badge with a visible “Provisional
  evaluation” state whenever reliability is not `complete`.
- **Acceptance test:** a throwing evaluator and a syntactically valid but empty
  evaluator response both persist a readable report; the API includes the
  reliability state, the debrief shows the provisional banner, and neither
  response renders “Meets Bar” or a `0.0` headline.

### 2. [P0] Score fallback structuring from the actual framework turn

**Why now:** the current fallback grades the greeting, then excludes
structuring from the weighted result. This is a direct, deterministic P0-4 fix.

- **Files to touch:** `app/evaluator.py`, `tests/test_evaluator.py`,
  `tests/test_evaluator_v2.py`.
- **Endpoint / UI surface:** report returned by
  `GET /api/attempts/{id}/evaluation`; no new UI surface.
- **Implementation slice:** select the first framework-bearing candidate turn
  after the greeting (fall back to the strongest candidate turn), and use its
  message index and complete word-boundary excerpt for structuring evidence.
  Include structuring in weighted overall whenever it was assessed.
- **Acceptance test:** a transcript with “Hi Leo” followed by a tailored
  revenue/cost, price/volume tree cites the second turn, receives a non-floor
  structuring assessment, and does not list `structuring` in
  `excluded_dimensions`.

### 3. [P0] Make write contention survivable and regression-tested

**Why now:** an ordinary overlapping turn caused a temporary API-wide bare-500
outage (P0-2). The root cause is unconfirmed, so make the safe failure mode and
reproduction harness explicit before tuning storage further.

- **Files to touch:** `app/db.py`, `app/main.py`, `tests/test_attempt_service.py`
  (or a new focused `tests/test_database_contention.py`).
- **Endpoint / UI surface:** `POST /api/attempts/{id}/turn` and `/health`.
- **Implementation slice:** preserve the existing WAL/busy-timeout setup,
  translate exhausted SQLite lock errors into a structured retryable `503`
  response, and add a two-client contention test that holds one write while the
  other submits. Do not introduce a queue or database migration in this task.
- **Acceptance test:** under the controlled lock, the affected turn returns
  JSON with a retryable detail rather than a bare `500`; a second client can
  still read `/health` and `/api/cases`; normal concurrent saves remain `200`.

### 4. [P1] Show the candidate where they are in the case

**Why now:** phase and fact-progress are already in session state, making this
the highest persona-delight-per-effort learning-loop improvement (P1-10).

- **Files to touch:** `app/case_runtime.py`, `app/static/app.js`,
  `app/static/app.css`, `app/static/app.html`, `tests/test_case_progress.py`.
- **Endpoint / UI surface:** existing `GET /api/attempts/{id}` and turn response
  `attempt` object; the in-room side rail.
- **Implementation slice:** add candidate-safe `phase_index`, `phase_count`,
  and `facts_released`/`facts_total` to `InterviewSession.candidate_view()`;
  render “Phase 2 of 3 — Drill down” and “3 key facts uncovered” after each
  refresh. Do not expose hidden fact names or correctness hints.
- **Acceptance test:** an active attempt advances phase after a scripted turn;
  its response reports the correct ordinal/count, and the room DOM updates the
  progress copy without exposing undisclosed fact text.

### 5. [P1] Let early exits be abandoned, not scored performance

**Why now:** this is a small change with outsized expert trust value: a
readiness-only exit must not corrupt longitudinal trends (P1-6).

- **Files to touch:** `app/case_runtime.py`, `app/store.py`, `app/main.py`,
  `app/static/app.js`, `app/static/app.html`, `tests/test_case_progress.py`.
- **Endpoint / UI surface:** `POST /api/attempts/{id}/end`,
  `GET /api/me/practice-history`, `GET /api/me/profile`, and the end-practice
  confirmation.
- **Implementation slice:** accept an explicit `disposition: abandoned | scored`
  on end; default an attempt below a small substantive-turn threshold to
  `abandoned`. Save its transcript and show it in history, but exclude abandoned
  attempts from solved-case progress and all score averages.
- **Acceptance test:** ending after readiness is retained as `abandoned` but
  leaves profile averages and dimension trends unchanged; a normal multi-turn
  `scored` end still creates an evaluation and contributes to profile metrics.

### 6. [P1] Render the authored case insight, not the prompt question

**Why now:** the “what the case wanted to test” card is a high-value debrief
surface whose source data already exists in the case-essence contract (P1-5).

- **Files to touch:** `app/evaluator.py`, `app/static/debrief.js`,
  `tests/test_evaluator_v2.py`, `tests/test_debrief_ui.py`.
- **Endpoint / UI surface:** `GET /api/attempts/{id}/evaluation`; “What the
  case really wanted to test” card.
- **Implementation slice:** source `core_mechanism` and `pivotal_insight` from
  `CasePackage.essence`, retain the decision question only as context, and
  ensure the candidate-gap template is grammatical for a question-shaped
  objective.
- **Acceptance test:** evaluate a fixture whose decision question differs from
  its `case_essence`; the response/card contains the authored mechanism and
  pivotal insight, not a copied question or malformed “isolates Why…” sentence.

### 7. [P1] Make dimension evidence precise and transcript-linked

**Why now:** trustworthy evidence is the prerequisite for the evidence-linked
partner review wanted by intermediate and expert personas (P1-4).

- **Files to touch:** `app/evaluator.py`, `app/static/debrief.js`,
  `app/static/debrief.css`, `tests/test_evaluator.py`, `tests/test_debrief_ui.py`.
- **Endpoint / UI surface:** `dimension_scores[*].evidence` in
  `GET /api/attempts/{id}/evaluation`; evidence links in debrief dimension cards.
- **Implementation slice:** choose the candidate turn that matches the assessed
  behavior instead of the first digit/greeting; trim quotations at word
  boundaries; attach the existing message index as a `#transcript-turn-N`
  anchor and scroll/highlight that transcript turn when clicked.
- **Acceptance test:** a clarifying turn containing “1)” is never cited as
  quantitative proof when a later calculation exists; quotes end on a whole
  word; clicking a citation highlights the exact candidate transcript turn.

### 8. [P1] Produce one real, case-specific closing rewrite

**Why now:** this is the most compelling debrief teaching moment, and can be
tightly scoped to the closing card rather than reworking the entire evaluator
(P1-3).

- **Files to touch:** `app/evaluator.py`, `app/static/debrief.js`,
  `tests/test_evaluator.py`, `tests/test_debrief_ui.py`.
- **Endpoint / UI surface:** `golden_rewrites` in
  `GET /api/attempts/{id}/evaluation`; the closing Golden Rewrite card.
- **Implementation slice:** set `candidate_turn` to the final substantive
  candidate turn. Build the fallback partner closing from the case essence’s
  mechanism/pivotal insight plus only facts released in that attempt; put the
  exact missing decision, risk, or next step in `diagnostic_notes`.
- **Acceptance test:** on a fixture closing, the rewrite quotes that closing
  verbatim, contains the fixture’s case-specific mechanism, contains no
  unreleased fact, and differs across two different case fixtures.

### 9. [P2 — stretch] Make difficulty a visible, shareable catalogue choice

**Why now:** this is a tight expert-delight improvement that uses already
published case metadata and addresses P2-14 without building recommendations.

- **Files to touch:** `app/main.py`, `app/static/cases.js` (or the current
  catalogue controller), `app/static/cases.html`, `tests/test_case_catalogue_versioning.py`.
- **Endpoint / UI surface:** `GET /api/cases?difficulty=advanced` and the case
  catalogue filter chips/URL.
- **Implementation slice:** validate the optional difficulty query against
  `foundation|intermediate|advanced`, filter the existing catalogue response,
  and synchronize the selected chip and visible difficulty tag to the URL.
- **Acceptance test:** the advanced query returns only advanced cases, an
  invalid difficulty returns `422`, and loading a copied advanced URL leaves
  the Advanced chip selected with matching cards displayed.

### 10. [P2 — stretch] Export an owned transcript as Markdown

**Why now:** a power-user can keep or compare their own work immediately, with
no new persistence schema and no leakage risk. Keep this deliberately export-
only, not a replay editor.

- **Files to touch:** `app/main.py`, `app/static/debrief.js`,
  `app/static/debrief.html`, `tests/test_debrief_reliability.py`,
  `tests/test_debrief_ui.py`.
- **Endpoint / UI surface:** new `GET /api/attempts/{id}/transcript.md` and an
  “Export transcript” control on the debrief page.
- **Implementation slice:** authorize through the existing owned-attempt check,
  stream a Markdown attachment with title, mode, candidate/interviewer turns,
  and no hidden facts, evaluator prompt, or another user’s data.
- **Acceptance test:** the owner receives a downloadable Markdown transcript in
  recorded order; another signed-in user gets `404`/`403`; the file excludes
  undisclosed case-fact content.

## Proposed implementation waves

### Wave 1: three parallel P0 tasks

1. **Worker A:** Item 1 — evaluation validity gate and provisional debrief.
2. **Worker B:** Item 2 — framework-turn selection for fallback structuring.
3. **Worker C:** Item 3 — SQLite contention regression and structured failure.

Merge these before accepting any headline-score or debrief polish work. They
remove the false-confidence and availability blockers that make every later
learning feature suspect.

### Wave 2: three parallel candidate-learning tasks

1. **Worker A:** Item 4 — in-room phase and fact progress.
2. **Worker B:** Item 5 — abandoned-versus-scored attempt disposition.
3. **Worker C:** Item 6 — authored case-essence card.

### Wave 3: polish and tightly-scoped stretch work

1. **Worker A:** Item 7 — correct, clickable dimension evidence.
2. **Worker B:** Item 8 — transcript-specific closing rewrite.
3. **Worker C:** Item 9 — visible/shareable difficulty filters.
4. **Worker D (if capacity remains):** Item 10 — owned transcript Markdown
   export.

Items 9 and 10 are the two explicit stretches. Drop them before expanding any
item beyond its stated acceptance test.
