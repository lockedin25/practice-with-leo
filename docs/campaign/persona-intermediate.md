# Persona QA: INTERMEDIATE candidate — Nikhil Verma

- **Persona**: consulting-club member, ~15 cases in. Decent but generic structure,
  misses second-order effects, quant setup right / execution wobbles, synthesis is a
  summary instead of an answer. Wants honest scoring.
- **Date**: Sep 3, 2026, ~03:05-03:25 UTC. Server: shared dev instance on
  `http://localhost:8000` (owner-started, main checkout). Text/API flows only.
- **Attempts** (both `mode: realistic`, `duration_minutes: 30`, 30-min format):
  | # | Case | Attempt ID | Turns | Facts released | Result |
  |---|------|-----------|-------|----------------|--------|
  | 1 | `02-diagnostic-center-v1` (profitability, IIM-A) | `cb7f5062-4ef3-4412-b4be-0bb798b6b189` | 9 | 2/7 | overall 3.54, "Meets Bar" |
  | 2 | `02-saas-cross-sell-v1` (growth_strategy, ISB) | `b32eb2b3-cbce-403c-9771-65c7ace33b75` | 10 | 3/7 | overall 3.61, "Meets Bar" |

---

## 1. Bugs and errors (exact endpoint / trace)

### BUG-1 (P0): No supported dev/test login path — auth blocks every non-browser client
- `GET /auth/google/start` → 303 to Google (no Google credentials available to an
  agent). There is no dev/test login route, no seed-user login form, and
  `POST /auth/logout` is the only non-OAuth auth endpoint besides `GET /api/auth/config`.
- The only working path was to forge the cookie the app itself would issue:
  1. Read `data/.session_secret` (HMAC key) from the main checkout.
  2. Hand-INSERT a user row into the dev SQLite DB (`data/casecall.db`, `users`
     table) with a synthetic `google_sub` — the same `upsert_from_google` shape.
  3. Sign `{"uid": <user.id>}` with the app's own `Signer` (30-day TTL) and send it
     as cookie `casecall_session`.
- This works (session verified via `GET /api/me` → 200), but it is undocumented,
  requires direct DB writes to the shared dev database, and is exactly the kind of
  thing a QA persona should never have to do. Tests get `conftest.sign_in()`; live
  server users get nothing. **A dev/test auth path (seeded persona account + a
  documented way to mint a session, or an admin-impersonation endpoint) is missing.**
- Endpoints exercised with the forged cookie all behaved correctly (401 without
  cookie on `/api/attempts`, ownership respected), so this is a tooling gap, not a
  security hole in candidate flows.

### BUG-2 (P0): Every debrief on the live server is silently produced by the deterministic fallback evaluator
- `POST /api/attempts/{id}/end` returned in **0.2s / 0.07s** with
  `evaluation.evaluator_version = "evaluator-v3|rubric=rubric-v2|fallback=true"` on
  both attempts. The LLM evaluator (`LangChainCaseEvaluator`) never ran — either
  unconfigured or failing instantly — and the code path in
  `app/main.py::_evaluate_and_store` (catch-all `except Exception` →
  `FallbackCaseEvaluator`) swallows the reason.
- Nothing in the product tells the candidate. `GET /attempts/{id}/debrief` returns a
  13.9KB JS shell with **zero** occurrences of "fallback"/"deterministic" and does
  not display `evaluator_version`. The debrief presents keyword-driven scores with
  full BCG-calibrated confidence. A candidate cannot know the intelligence tier of
  the feedback they received.
- Consequence: all calibration defects below are *systemic*, not one-off.

### BUG-3 (P0): Structuring is scored on the candidate's FIRST turn, which is always a greeting
- Trace: `app/evaluator.py` `generate_fallback_evaluation()` —
  `opening_idx, opening_text = cand_turns[0]` (evaluator.py:~1021), then all
  structuring keyword checks (`restate_words`, `mece_words`, industry tailoring) run
  against `opening_text` only.
- My first turn was `"Hi Leo, I am ready to begin."` → structuring = **2.5 floor,
  empty evidence, empty observations**, boilerplate improvement
  "Confirm the client's quantified objective..." on **both** attempts — while my
  actual structure turn (t-003 attempt 1: revenue/cost, volume/price, fixed/variable)
  was never examined. Had that turn been the first candidate turn, the same keyword
  logic would have yielded ~4.3.
- Every real candidate greets/clarifies before structuring, so **everyone who
  structures after turn 1 gets the 2.5 floor**, and structuring is then excluded
  from the weighted overall (`excluded_dimensions: ["structuring"]`), further
  inflating the average. Highest-severity calibration bug found.

### BUG-4 (P1): Quantitative score is a flat 3.5 for any math-looking turn; arithmetic is never checked
- Trace: evaluator.py quantitative block — `quant_score = 2.5`; if any candidate
  turn matches `\d+` plus one keyword (`%`, "margin", "cost"...) → flat `3.5`,
  observation literally `"Handled quantitative calculations and data synthesis cleanly."`
- Attempt 1 t-007 I conflated a 12.6%-of-revenue commission drag with a 400bps EBITDA
  decline and only half-caught it; attempt 2 t-007 I asserted a 30% expansion uplift
  per multi-module client with no source, corrected the adoption assumption mid-flight.
  Both scored **3.5 "Meets Bar"** with "cleanly". A candidate whose arithmetic is
  wrong and one who is right get the identical number. The dimension is decorative
  in fallback mode.

### BUG-5 (P1): Evidence citations point at the wrong turns and are truncated mid-word
- Attempt 1: `quantitative` evidence cites `message_index 3` quoting
  `"Thanks. Before I structure, a few clarifying questions: 1) I"` — my clarifying
  questions cited as quant evidence (it is the first turn containing a digit).
- Attempt 1: `problem_solving` evidence cites my structure turn but the quote is cut
  mid-word: `"Since EBITDA margin is revenue minus cost over revenue, I wo"`.
- `communication` evidence on both attempts cites my greeting
  (`"Hi Leo, I am ready to begin."` / `"Hey Leo, ready when you are."`) as the proof
  of a 4.2. Quotes truncated at 60/50 chars (`quote[:min(60, len(text))]`).

### BUG-6 (P1): "What the case really wanted to test" card shows the decision question, not the authored insight
- Attempt 1 report: `what_the_case_wanted_to_test.core_mechanism = "Why has
  diagnostic center profitability fallen despite growing patient volume, and how can
  margins be restored?"` — that is the `objective_function.decision_question`.
  The authored `case_essence.core_mechanism` ("Channel mix shift toward
  physician-referred B2C patients with escalating referral commissions...") never
  appears.
- Knock-on: `candidate_vs_optimal_gap` renders the sentence
  `"The optimal MBB path isolates Why has diagnostic center profitability fallen... via ex-ante hypothesis testing"` — grammatically broken template fill.
- `pivotal_insight` = "Isolating root-cause unit economics" (generic), not the case's
  real pivotal insight (commissions 20%→38%).
- Golden Rewrites: opening rewrite treats my *greeting* as my opening
  (candidate_turn = "Hi Leo, I am ready to begin."), and the partner rewrite pastes
  the question into "our objective is to explain *Why has...*?" The closing partner
  rewrite is case-agnostic filler ("immediately execute a focused turnaround
  strategy to achieve the target objective").

### BUG-7 (P2): Interviewer teaches the answer during a "realistic" mode case
- Attempt 2, after my final synthesis (t-010), Leo volunteered:
  "One refinement worth adding... unifying the three modules should mean consolidating
  them into a single modular platform with unified single sign-on and shared data
  analytics... With that addition, your analysis is complete and well-structured."
- That is coaching (and glazing) inside `mode: realistic`, after the case is already
  functionally over. It contaminates the transcript the evaluator later reads
  (the released `recommendation.unified_platform` fact rides on my turn).

### BUG-8 (P2): Cross-attempt boilerplate
- Both attempts, different cases and different gaps: identical `next_drill`
  ("Construct a 3-level MECE tree for an unfamiliar business model in under 120
  seconds."), identical 12 `observed_behaviors`, identical structuring improvement
  text, identical strengths phrasing. The report is templated; a candidate doing
  daily practice sees the same debrief every time.

---

## 2. Friction and confusion moments (turn-numbered, both attempts)

| Moment | Attempt / turn | What happened | Why it stung |
|---|---|---|---|
| Cold-start auth wall | before A1 t-001 | No way to sign in outside a browser+Google account; had to forge a session (BUG-1). A real candidate in a test environment hits this immediately. | High |
| Pre-case turn is consumed silently | A1 t-001, A2 t-001 | `POST /turn` with "Hi Leo, I am ready to begin." returned in 0.02s and the reply bundles the greeting + full case opening. No phase indicator, no "onboarding complete" signal — as a candidate you only know the case started because the brief text appears. | Medium |
| Leo asks a question, answers nothing, releases no data | A1 t-005, A2 t-005 | After a correct hypothesis, Leo twice responded with a *counter-question* ("what factors do you believe could be driving...") instead of data. Fine once; twice it felt like stalling, and I did not know whether to push or answer. Turn latency made me resubmit-check (no ack that the turn was processing). | Medium |
| Turn latency 12-24s with no ack | all turns | `POST /turn` 12.6-23.8s (LLM writer). In the room UI I would have no idea whether my turn was accepted (idempotency exists via `turn_id` but nothing tells the candidate). | Medium |
| Interview ends but the attempt does not | A1 after t-009 | Leo said "That concludes our case interview" — but the attempt was still open; I had to know to `POST /end` myself. In the UI the equivalent is presumably the End Practice button, but the *interviewer* ending and the *attempt* ending are different events with no bridge. | Medium |
| 409 on re-attempting a solved case | between attempts | `POST /api/attempts` on a completed case returns 409 "You have already completed this case. Reset the test before attempting it again." — reasonable, but the reset is a separate unlinked call (`POST /api/cases/{id}/reset`) you must know about. | Low |
| Zero feedback during the case | all | No scorecard, no nudge intensity signal, no "you are in drill_down phase" — the phase machine (`clarification → drill_down → synthesis`) is invisible to the candidate until the debrief. As an intermediate I had no idea whether my quant was landing. | High (this is the core learning-loop gap) |
| Fact release timing feels arbitrary | A2 t-008→t-009 | I asked "do the modules share a unified data layer and SSO?" — Leo did NOT release `platform.integration`; one turn later, asking for the turnaround plan, the recommendation fact arrived attached to Leo's *own* suggestion instead. Felt like the fact release rules tripped over the persona budget. | Medium |

Positive friction notes (worth keeping): Leo's mid-case follow-ups were genuinely
good interviewer behavior — A1 t-003 ("what is your hypothesis..."), A2 t-005
("what other factors besides sales incentives...") forced second-order thinking that
the debrief then failed to reward. The interviewer is ahead of the evaluator.

---

## 3. Evaluator CALIBRATION (honest self-score vs Leo)

Band expectation for this persona: **2.5-3.5 on exercised dimensions.**
Scores below are per-dimension, 1-5.

### Attempt 1 — Diagnostic Center (profitability)

| Dimension | My honest self-score | Leo (fallback) | Delta | Verdict |
|---|---|---|---|---|
| structuring | 2.5 (decent but generic profitability tree, untailored at L1) | 2.5 | 0.0 | Accurate — **but by bug, not by judgment** (scored my greeting) |
| problem_solving | 2.5-3.0 (hypothesis-led, found 2/7 facts, never tested reagent gross margins) | 3.2 | +0.4 | Slightly generous |
| quantitative | 2.0-2.5 (setup right; conflated contribution drag with EBITDA; cushioning hand-wave) | 3.5 | **+1.2** | **Miscalibrated** — flat keyword score, says "cleanly" |
| synthesis | 2.0 (summary + list; no risks, no mitigations, no 100-day) | 3.5 | **+1.4** | **Miscalibrated** — "Answer-First" triggered by the word "recommend" |
| communication | 3.0 (clear, signposted; average, not Top 1%) | 4.2 "Top 1% MBB" | **+1.2** | **Glazing** — deterministic 3.2+0.6+0.4 for anyone who says "to summarize" |
| **Overall** | **~2.5-2.8** | **3.54** | **+0.8** | Report card flatters by ~a full band |

### Attempt 2 — SaaS NRR (growth_strategy)

| Dimension | My honest self-score | Leo (fallback) | Delta | Verdict |
|---|---|---|---|---|
| structuring | 3.0 (NRR decomposition was genuinely case-tailored) | 2.5 | -0.5 | **Under-scored** — again scored my greeting, not the structure turn |
| problem_solving | 3.0 (3/7 facts, good hypothesis chain) | 3.4 | +0.4 | Slightly generous, roughly fair |
| quantitative | 2.5 (right formula, unstated adoption assumption, self-corrected mid-air) | 3.5 | **+1.0** | **Miscalibrated** — same flat 3.5 |
| synthesis | 2.5 (answer-first-ish, sized the prize, but no risks/100-day) | 3.5 | **+1.0** | Generous |
| communication | 3.0 | 4.2 "Top 1% MBB" | **+1.2** | **Glazing** — identical score both attempts |
| **Overall** | **~2.9** | **3.61** | **+0.7** | Report card flatters |

### Calibration conclusions (for the roadmap)
1. **Inflation is systematic (+0.7 to +1.4 per dimension, +0.8 overall).** The
   deterministic engine cannot see quality, only keywords; its ceilings and floors
   compress everyone into 2.5-4.2. An intermediate with real quant errors gets the
   same quantitative score as an expert. The brief's target band (2.5-3.5) is only
   met by accident, on average.
2. **The "Top 1% MBB" communication badge is achievable by any candidate who says
   "to summarize" once and keeps turns under 120 words.** For a persona whose core
   ask is *honest scoring*, this single badge destroys trust in the whole debrief.
3. **Where it under-scores, it is for the wrong reason** (structuring on turn 1).
   Fixing BUG-3 would have moved my structuring from 2.5 to ~4.0-4.3 — overshooting
   in the other direction for identical content quality. The keyword model has no
   middle.
4. **Did Leo's feedback tell me HOW to improve, not just what I scored?**
   - *During the case: yes, partially.* Leo's counter-questions (A1 t-003, A2 t-005)
     modeled exactly the second-order probing I was missing; that is real coaching
     and the strongest part of the product.
   - *In the debrief: mostly WHAT, rarely HOW.* Concrete exceptions that did teach:
     quantitative ("Always follow arithmetic calculations with a commercial 'so
     what?'") and synthesis (risks+mitigations, 100-day roadmap) — both name the
     missing behavior. But none of them used *my* words or showed the rewrite; the
     Golden Rewrites card was supposed to do that and instead rewrote my greeting
     with case-agnostic filler (BUG-6). Structuring feedback was pure boilerplate
     triggered by BUG-3. Net: 2 of 5 dimensions gave actionable HOW; 3 gave WHAT
     (or noise). The debrief would make me slightly better, but I would not pay for
   it in its current fallback form — I would not trust the scores, and the rewrites
   are not rewrites of *my* words.
   - Missing entirely: any feedback on my two quant *errors* (the contribution-vs-
     EBITDA conflation; the unstated adoption assumption). A mock interviewer that
     misses your actual arithmetic mistakes is not doing the job this persona needs.

---

## 4. Debrief report usefulness (would this make me better?)

- **Structure of the report: 8/10.** All 7 cards exist and render
  (`GET /attempts/{id}/debrief` → 200; full schema incl. `observed_behaviors` (12),
  `golden_rewrites` (2), `suggested_readings` with real KB paths, `targeted_drill`,
  `mbb_rating_badge`). Nothing was missing or broken; profile aggregation
  (`GET /api/me/profile`, `GET /api/me/practice-history`) worked and correctly
  aggregated both attempts (avg 3.54→3.61, dev-area occurrence counting).
- **Content usefulness: 3/10** (in fallback mode). Scores are keyword-driven
  (BUGs 3-4), evidence quotes are wrong/truncated (BUG-5), the "what the case
  wanted" card shows a question instead of the authored insight (BUG-6), and the
  drill is identical across cases (BUG-8). The two genuinely useful artifacts were:
  the improvements list under synthesis/quantitative, and the KB reading links.
- **The interviewer >> the evaluator.** Leo-in-the-room asked better questions than
  Leo-with-the-red-pen answered. Whatever the LLM evaluator costs, it is the
  difference between a debrief I trust and one I skim.

---

## 5. Top-3 wished-for features (concrete)

1. **Live micro-feedback during the case ("in-room scorecard").**
   Endpoint exists conceptually (`GET /api/attempts/{id}` returns live state) — add a
   per-turn, private signal: current phase, facts-uncovered counter (e.g. "3/7 key
   facts"), and one nudge like "you asserted a 30% expansion uplift — state the
   source or flag it as an assumption." As an intermediate I *felt* my quant wobble;
   I wanted the platform to catch it in the moment, not 20 minutes later. The
   `release_credits`/persona-budget machinery already tracks state per turn — this
   is a surfacing problem, not a modeling one.

2. **Arithmetic checking on quant turns (unit/equation validation).**
   I stated formula-grade math in plain text ("0.7 × 18% = 12.6% of revenue... ≈
   400bps EBITDA decline"). The evaluator should extract candidate equations/claims,
   verify them against `facts.yaml` figures (case packages already carry verified
   numbers), and report "your 12.6% drag on revenue is correct, but reconciling it
   to the 400bps EBITDA move requires the fixed-cost absorption you never
   requested." This single feature converts the quantitative dimension from
   decorative (flat 3.5) to the thing an intermediate actually practices for.

3. **Real Golden Rewrites: my words vs the partner's words for THIS transcript.**
   The card's intent is the best idea in the debrief. Make the closing rewrite quote
   my actual closing turn, then show a case-specific partner rewrite using the
   case's authored `case_essence` (mechanism, pivotal insight, traps) and *my*
   released facts, with the diagnostic note pointing at the exact sentence where I
   went summary-mode ("To summarize: ..." → "The client should X because Y, in 3
   moves..."). Fallback or not, this can be assembled deterministically from the
   authored essence + template slots filled with case numbers — it does not need
   the LLM to be 10x better than the current filler.

*(Honorable mentions: a "post-case Leo teach-back" — a 60-second Leo-narrated
version of the debrief in his interviewer voice; a per-case drill that varies with
the case and my actual gaps; surfacing `fallback=true` on the debrief page.)*

---

## Verification trail (for repro)
- Persona user: `opencode-intermediate@casecall.test` (uid `a164649a1338-...`),
  session via forged `casecall_session` cookie (see BUG-1).
- Raw turn-by-turn log (endpoint, payload, reply, latency): retained at
  `/var/folders/.../opencode/persona_log.jsonl` during the run; key excerpts and all
  scores reproduced above from `GET /api/attempts/{id}/evaluation`.
- All flows mirror `tests/test_e2e_workflow.py` scenarios 1/3/4 (start → turns → end
  → evaluation → debrief → profile/history).
