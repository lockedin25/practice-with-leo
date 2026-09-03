# Expert persona campaign: Leo v2

## Verdict

**Not ready for an expert candidate.** The attempt lifecycle, replay protection,
attempt restoration, early completion, debrief delivery, and history endpoints all
worked. The scoring did not: two strong, pressure-mode, advanced-case performances
landed at 3.47 and 3.57 out of 5, both labelled `Meets Bar`. The evaluator does not
reliably distinguish this candidate from a competent mid-level candidate.

## Test setup and limits

- Date: 2026-09-03, expert persona, `pressure` interviewer mode.
- Shared `http://localhost:8000` was down. Starting the requested worktree server
  at `127.0.0.1:8002` failed with `Errno 1: operation not permitted` in this
  environment.
- There is no development sign-in route. The live app correctly requires Google
  OAuth. I used the test-suite path in `tests/conftest.py`: create the local
  Google-shaped account and attach its signed session cookie. That exercised the
  real authenticated FastAPI routes and persistence against an isolated SQLite DB.
- The app cannot boot without `OPENROUTER_API_KEY` (`RuntimeError` from
  `create_interviewer()` during import), so the two HTTP sessions used the same
  deterministic interview double as the E2E tests and the real fallback evaluator.
  This means the lifecycle and evaluation evidence below is valid, but it is not
  a claim that the production LLM interviewer was live-tested. That missing
  no-key local mode is itself a finding.

## Two hard-case attempts

| Attempt | Case | Candidate turns | Expert behaviors exercised | Leo result |
|---|---:|---:|---|---|
| `4cba8237-3d3e-428b-8dc1-c3b54d465a2c` | TerraBuild Materials, advanced sustainability strategy | 10 | Decision criterion and return threshold, MECE value tree, emissions economics, order-of-magnitude payback, staged capex gates, downside cases, decisive recommendation | 3.47, `Meets Bar` |
| `d8c0b5f0-8406-4688-b14e-a99ea8f5b009` | Forge Components, advanced M&A | 10 | Risk-adjusted deal thesis, synergy tree, procurement math, enterprise-value sanity check, probability-weighted synergies, diligence plan, valuation ceiling and 100-day plan | 3.57, `Meets Bar` |

Both starts, all turns, explicit ends, evaluation fetches, and debrief shells
returned 200. Each attempt was re-opened while active through
`GET /api/attempts/{attempt_id}` and retained its transcript and state.

### Representative expert turns

TerraBuild turn 4: “A 100 million capex project needs roughly 15 to 20 million
annual incremental cash flow to clear a five to seven year payback.”

TerraBuild close: “Launch the no-regret operational programme now and approve a
staged targeted conversion conditional on signed customer offtake and a capex
gate.”

Forge turn 4: “If base EBITDA is 30 million and the buyer pays 9 times, enterprise
value is 270 million before debt; every 10 million of credible synergy at 8 times
adds around 80 million of value.”

Forge close: “Proceed to exclusive diligence, not signing, with a valuation ceiling
set by standalone value plus procurement and overhead synergies only.”

## Calibration: expert self-assessment versus Leo

Target for this persona is 4-5 on the exercised dimensions. The self-scores are
deliberately not 5s: no candidate receives all case facts, and the interviewer did
not force a final numerical model.

| Dimension | TerraBuild self | Leo | Forge self | Leo | Calibration read |
|---|---:|---:|---:|---:|---|
| Structuring | 4.5 | 3.1 | 4.6 | 3.1 | **Fail.** Explicit tailored trees and decision rules are treated as generic “Meets Bar.” |
| Problem solving | 4.5 | 3.8 | 4.6 | 3.8 | Under-scored, though Leo recognizes hypothesis-led inquiry. |
| Quantitative | 4.3 | 3.5 | 4.5 | 3.5 | **Fail.** Both runs include transparent arithmetic and order-of-magnitude checks. |
| Synthesis | 4.5 | 3.4 | 4.7 | 3.9 | **Fail.** Answer-first recommendations, risks, gates, and next steps were present. |
| Communication | 4.5 | 3.6 | 4.6 | 3.6 | **Fail.** The score does not reward concise signposting and controlled answer-first delivery. |
| Overall | 4.46 | 3.47 | 4.60 | 3.57 | **High-severity calibration gap:** -0.99 and -1.03 points. |

The strongest signal that Leo cannot distinguish expert from intermediate is the
near-identical scoring fingerprint across unrelated advanced cases: structuring
3.1, problem solving 3.8, quantitative 3.5, communication 3.6 in both. It also
issued stock development advice that conflicts with the transcript. For example,
both closes contain a clear hypothesis and implementation gates, but the report
still asks for an “ex-ante commercial hypothesis”; Forge closes with a concrete
first-100-day plan yet receives generic implementation guidance.

## API and power-user edge cases

| Check | Endpoint / trace | Result |
|---|---|---|
| Public catalogue | `GET /api/cases` | 200, 69 cases, 15 marked advanced. |
| Retry a submitted turn | `POST /api/attempts/4cba.../turn` with the same `turn_id` on turn 4; repeated on `d8c0...` turn 6 | 200; identical reply and unchanged message count both times. Pass. |
| Re-open an active attempt | `GET /api/attempts/4cba...`, `GET /api/attempts/d8c0...` | 200; same ID and `ended: false`. Pass. |
| End early | Start `25-genai-bank-v1`, complete readiness only, then `POST /api/attempts/9503.../end` | 200 and a debrief is generated. See profile-pollution finding below. |
| Debrief payload and UI route | `GET /api/attempts/{id}/evaluation`; `GET /attempts/{id}/debrief` | 200 for both completed hard cases. |
| Profile and trends | `GET /api/me/practice-history`, `GET /api/me/profile`, `GET /api/me/cases/terrabuild-materials-v1/performance` | 200; three attempts, history and per-case progress persisted. |
| Catalogue filtering | `GET /api/cases?difficulty=advanced` | 200 but returns all 69 cases, not the 15 advanced ones. The UI may intentionally filter client-side, but this blocks a shareable/filterable power-user URL or API client. |

## Findings

### P0: fallback evaluator compresses expert work into mid-level scores

- Evidence: `GET /api/attempts/4cba8237-3d3e-428b-8dc1-c3b54d465a2c/evaluation`
  returns `overall_score: 3.47`; `GET /api/attempts/d8c0b5f0-8406-4688-b14e-a99ea8f5b009/evaluation`
  returns `3.57`. Both report
  `evaluator_version: evaluator-v3|rubric=rubric-v2|fallback=true`.
- User impact: an MBB-ready user gets a “Meets Bar” result and generic drills
  after work that should trigger a 4-5 range, so the product is neither credible
  nor useful for performance differentiation.
- Required behavior: score against quoted transcript evidence and the case’s
  decision logic; permit 4s and 5s when a candidate supplies a tailored
  hypothesis, correct transparent math, hypothesis updates, and an answer-first
  close with risks and next actions.

### P1: ending early permanently contaminates trends

- Evidence: `POST /api/attempts/9503d142-8118-4a7f-bb92-004c87060e4f/end`
  after readiness alone returns 200 and stores a 2.45 `Developing` evaluation.
  `GET /api/me/profile` then reports all three attempts in the aggregate,
  `average_feedback_score: 3.16`, and structuring average 2.9.
- User impact: a connectivity abort, accidental click, or deliberately abandoned
  case is indistinguishable from poor performance and corrupts a serious
  candidate’s trendline.
- Needed: an explicit `abandoned` state or an end confirmation that offers
  “save as practice, exclude from scoring”; profile defaults should exclude
  attempts below a minimum substantive-turn threshold.

### P1: a no-key local server cannot start, although evaluation has a fallback

- Reproduction: `.venv/bin/uvicorn app.main:app --port 8002` from the worktree
  fails before serving `/health` with `RuntimeError: OPENROUTER_API_KEY is
  required to run the LLM interviewer` at application import.
- User impact: a contributor cannot dogfood text practice locally without a paid
  provider key. This blocked the requested live localhost campaign and forces
  tests to inject an interviewer.
- Needed: a clearly labelled local deterministic interviewer or an app factory
  that starts in degraded mode and returns a useful, honest 503 only for live
  turns if no test double is selected.

### P2: catalogue filters cannot be represented in the API or URL

- Evidence: `GET /api/cases?difficulty=advanced` is 200 but has 69 cases; local
  filtering finds only 15 advanced cases.
- User impact: an expert who wants advanced M&A or pricing cases cannot bookmark,
  share, or query that choice. If the browser filter is intentional, it still
  needs URL query synchronization.

## Friction and confusion log

| Moment | Friction |
|---|---|
| Before turn 1 | No usable `localhost` server: shared server was down, sandbox rejected the requested local bind, and no-key boot fails before health check. |
| Turn 0 | Auth has no developer route. The test cookie path is safe and well-tested, but it is undocumented for local dogfooding. |
| Turns 1-9, both cases | The deterministic test interviewer released evidence but could not challenge, redirect, or raise the bar. This is a test-mode limitation, but it means an expert cannot validate pressure-mode interviewer quality without provider access. |
| Debrief | The JSON has all five dimensions and evidence, but the feedback is template-shaped rather than diagnostic. It does not identify which hypothesis, calculation, or decision gate was strong or weak. |
| End early | The product treats a one-turn exit as scored performance without warning that it will depress the trendline. |

## Debrief usefulness for an already-good candidate

**2/10.** The report is polished enough to confirm that an attempt completed and
it notices broad behaviors such as objective restatement and answer-first closing.
It would not make a strong candidate better: no claim is tied to the exact line
where the logic broke, no alternative analysis is worked through with the case
facts, and the “next drill” is the same generic MECE exercise after two very
different cases. The lack of calibration makes the headline score actively
misleading.

## Top three wished-for features

1. **Evidence-linked partner review.** Every dimension needs 2-3 quoted moments,
   a verdict on the underlying business logic, and one precise rewrite or missing
   test. Let me click from the score to my line, the relevant fact, and a stronger
   MBB move.
2. **True expert pressure mode.** Detect when a candidate is driving well, stop
   spoon-feeding, introduce a contradictory fact or time pressure, ask for the
   exact calculation, and grade the defended trade-off. It should adapt upward,
   not use the same disclosure cadence for everyone.
3. **Signal-clean longitudinal practice.** Allow abandon versus score, let users
   tag a targeted skill, compare current and prior attempts by dimension and
   evidence, and surface one deliberately hard follow-up case based on the weak
   pattern. Stretch: replay a decision fork and score the revised two-turn answer
   side by side.

## Verification record

All documented routes returned 200 except the intentionally unavailable local
server process, which failed before binding due to missing provider configuration
and environment socket restrictions. Exact HTTP traces, candidate turns, replies,
and payloads were captured during the run in the local campaign trace; no runtime
database or secret was added to the repository.

Repository verification is currently blocked by a pre-existing test expectation:
with a placeholder `OPENROUTER_API_KEY` so collection can begin,
`.venv/bin/pytest tests/ -x -q` reaches **94 passed** then fails
`tests/test_case_progress.py::test_start_case_control_submits_a_readiness_turn_to_open_the_timer_gate` because
`app/static/app.js` no longer contains the asserted literal `syncTimer(attempt);`.
Without the placeholder, collection itself fails at `app/main.py` import because
the interviewer requires `OPENROUTER_API_KEY`. No production code was changed by
this campaign worker.
