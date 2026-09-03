# Campaign Feedback Bag — FEEDBACK.md

Consolidated findings from the three-persona QA campaign against Leo (CaseCall v2).
Written by worker `opencode` (P4). Every finding below is deduplicated across
personas, severity-ranked, and carries source, evidence, and a fix direction.

**Sources (merged persona reports):**

| Persona | Report | Runner | Attempts |
|---|---|---|---|
| Beginner (2nd-yr MBA, zero cases) | `persona-beginner.md` | claude | Beer Manufacturer (foundation), Aster Diagnostics (market entry) |
| Intermediate (~15 cases, club member) | `persona-intermediate.md` | opencode | Diagnostic Center (profitability), SaaS Cross-Sell (growth) |
| Expert (pressure mode, advanced cases) | `persona-expert.md` | codex | TerraBuild Materials, Forge Components (both advanced) |

**Method:** all findings from all three reports were extracted, merged where they
describe the same underlying defect, and ranked. Severity legend: **P0** = breaks
the core product promise or platform stability for real users; **P1** = major
defect a real user (or the QA/dogfood program) hits; **P2** = polish. Where
personas disagreed on severity (noted inline), product impact won. A dedup map
tying each consolidated finding back to the source reports is in Appendix A.

---

## 1. Evaluator calibration verdict

**Verdict: NO — the scores do not separate beginner / intermediate / expert. The three personas are statistically indistinguishable, and the expert scored lowest of the three real candidates.**

The numbers, quoted from the three reports:

| Persona | Brief's target band | Honest self-score | Leo's overall | Leo's band | Delta |
|---|---|---|---|---|---|
| Beginner, attempt 1 | 1.5–2.5 | ~1.5 | **3.48** | "Meets Bar" | **+1.98 (inflated)** |
| Beginner, attempt 2 | 1.5–2.5 | ~1.5–2 | 0.0 | **"Meets Bar"** (contradictory; empty evaluation) | n/a — headline broken |
| Intermediate, attempt 1 | 2.5–3.5 | ~2.5–2.8 | **3.54** | "Meets Bar" | +0.7/+0.8 (flattered) |
| Intermediate, attempt 2 | 2.5–3.5 | ~2.9 | **3.61** | "Meets Bar" | +0.7 (flattered) |
| Expert (pressure), TerraBuild | 4–5 | 4.46 | **3.47** | "Meets Bar" | **−0.99 (deflated)** |
| Expert (pressure), Forge | 4–5 | 4.60 | **3.57** | "Meets Bar" | **−1.03 (deflated)** |
| Expert, abandoned 1-turn attempt | n/a | n/a | 2.45 | "Developing" | only low score in campaign |

Three kill-shots, quoted from the sources:

1. **"Beginner (3.48) scored higher than expert (3.47)."** The weakest transcript
   and the strongest transcripts in the campaign got the same overall score, both
   "Meets Bar". Every scored attempt in the entire campaign landed in
   3.47–3.61 — a spread of 0.14 across a ~3-point real-skill range.
2. **Dimension compression.** The expert saw "near-identical scoring fingerprints
   across unrelated advanced cases: structuring 3.1, problem solving 3.8,
   quantitative 3.5, communication 3.6 in both." The intermediate diagnosed the
   keyword engine's band directly: "its ceilings and floors compress everyone
   into 2.5–4.2. An intermediate with real quant errors gets the same
   quantitative score as an expert."
3. **The "Top 1% MBB" communication badge went to the beginner, not the expert.**
   Beginner communication: 4.2 / "Top 1% MBB" for a transcript full of "um," "uh,"
   "sorry," and a mid-case "sorry, what were we solving for again?" (self 1.5).
   Intermediate got the identical 4.2 / "Top 1% MBB" on both attempts. The
   expert — concise, signposted, answer-first — got **3.6**. Per the
   intermediate: "The 'Top 1% MBB' communication badge is achievable by any
   candidate who says 'to summarize' once and keeps turns under 120 words."

**Why it happens (three independent mechanisms, all observed):**

- **The LLM evaluator mostly never runs.** 5 of 6 scored attempts returned
  `evaluator_version: "evaluator-v3|rubric=rubric-v2|fallback=true"`, some in
  0.07–0.2s. Intermediate traced the swallow point: the catch-all
  `except Exception → FallbackCaseEvaluator` in `app/main.py::_evaluate_and_store`
  discards the failure reason. Nothing tells the candidate (`GET /attempts/{id}/debrief`
  contains zero occurrences of "fallback"/"deterministic").
- **When the real evaluator DID run** (beginner attempt 2, `model=google/gemini-3.7-flash`,
  no `fallback=true`), the checklist half was excellent ("11 of 12 markers correctly
  missed") but the entire scoring half returned empty: `dimensions: []`,
  `dimension_scores: {}`, `executive_summary: ""`, `overall: null`,
  `overall_score: 0.0` — badged **"Meets Bar"** anyway.
- **The fallback keyword engine has specific systematic biases:** structuring
  scored on the first candidate turn (always a greeting) at a 2.5 floor;
  quantitative = flat 3.5 for any turn containing a digit plus a keyword;
  communication = deterministic 3.2+0.6+0.4 for saying "to summarize"; synthesis
  3.5 triggered by the word "recommend."

The only score in the campaign that moved: the abandoned 1-turn attempt (2.45,
"Developing") — which then permanently polluted the expert's profile trends.

**One calibration-related positive:** where the evaluator under-scores, it does so
for detectable mechanical reasons (structuring-on-greeting), and where the LLM
evaluator's checklist ran, its qualitative marker judgments were the best-calibrated
feedback of the entire campaign. The raw material for a correct evaluator exists;
the scoring and surfacing layers around it are what fail.

---

## 2. Consolidated findings

### P0 — Blockers

#### P0-1. The evaluator is silently degraded on nearly every attempt, and wrong in both directions
- **Source:** all three personas (beginner Bug #1-calibration + intermediate BUG-2 + expert P0).
- **Evidence:** 5/6 scored attempts ran `evaluator-v3|rubric=rubric-v2|fallback=true`
  (0.07–0.2s responses; `LangChainCaseEvaluator` never ran). Beginner: overall
  3.48 "Meets Bar" vs self ~1.5, communication 4.2 "Top 1% MBB." Expert: 3.47/3.57
  "Meets Bar" vs self 4.46/4.60, identical dimension fingerprint across two
  unrelated advanced cases. The catch-all `except Exception` in
  `app/main.py::_evaluate_and_store` hides why the real evaluator fails.
- **Fix direction:** surface evaluator failures instead of swallowing them (log +
  persist the exception); treat fallback scoring as provisional, not equivalent;
  make the real evaluator the only path that can emit a headline score. Score
  against quoted transcript evidence and the case's decision logic, and permit
  4s and 5s when a candidate supplies tailored hypothesis, correct transparent
  math, and an answer-first close with risks and next actions (expert's required
  behavior). Never let a keyword floor/ceiling compress the range.

#### P0-2. Platform-wide API outage triggered by ordinary concurrent load
- **Source:** beginner (Bug #1).
- **Evidence:** `POST /api/attempts/{attempt_id}/turn` on the shared server
  (attempt `1989c426-...`, case `01-beer-manufacturer-v1`, turn t-007) hung, timed
  out client-side after 120s, then **every** `/api/*` endpoint returned bare
  HTTP 500 for 30+ seconds (including unauthenticated `GET /api/cases`), while
  static pages kept serving 200. Best-guess root cause: SQLite write contention /
  locking across concurrent sessions. Not reproducible from a single persona
  running alone — a concurrency-shaped bug.
- **Fix direction:** investigate the DB layer for write-lock handling under
  concurrent sessions (WAL mode, busy timeout, single-writer queue); make the
  API return structured JSON errors with recovery guidance instead of a bare
  500; add a health endpoint check and an alert. Reproduce by overlapping two
  personas' turns against one server (beginner's suggested experiment; nobody
  has confirmed it yet).

#### P0-3. A partial/empty evaluation is badged "Meets Bar" with score 0.0
- **Source:** beginner (Bug #3).
- **Evidence:** attempt `c86827c5-43ce-4b0a-adc5-9501471c3dfc`, real evaluator
  (`model=google/gemini-3.7-flash`, no `fallback=true`): `checklist`/`observed_behaviors`
  rich and accurate (11/12 markers correctly "missed"), but `dimensions: []`,
  `dimension_scores: {}`, `executive_summary: ""`, `golden_rewrites: []`,
  `strengths: []`, `overall: null`, `overall_score: 0.0`, and
  `overall_band`/`mbb_rating_badge` = **"Meets Bar"**.
- **Fix direction:** validate evaluation completeness before computing/rendering
  any badge; if `fallback=true` OR `dimensions`/`dimension_scores`/`executive_summary`
  are empty, show a visible "provisional / evaluation incomplete — retry
  recommended" state instead of a confident badge. A 0.0 must never badge
  "Meets Bar." Add a candidate-facing regenerate-evaluation action (see P2-19).

#### P0-4. Fallback structuring score is computed on the candidate's first turn, which is always a greeting
- **Source:** intermediate (BUG-3, "highest-severity calibration bug found").
- **Evidence:** `app/evaluator.py` `generate_fallback_evaluation()` uses
  `cand_turns[0]` (evaluator.py:~1021) for all structuring keyword checks. First
  turn was `"Hi Leo, I am ready to begin."` → structuring 2.5 floor with empty
  evidence on both attempts, while the real structure turn (revenue/cost,
  volume/price, fixed/variable) was never examined and would have scored ~4.3.
  Structuring is then excluded from the weighted overall
  (`excluded_dimensions: ["structuring"]`), further inflating the average for
  every candidate who structures after turn 1 — i.e., everyone.
- **Fix direction:** never score structuring on the greeting turn; evaluate the
  best/longest/last framework-bearing turn, or let the (working) LLM evaluator
  select the turn. In fallback mode, at minimum scan all candidate turns for
  structuring keywords.

### P1 — Major

#### P1-1. No supported dev/test auth path; every non-browser client must forge a session
- **Source:** all three (intermediate BUG-1 rated P0; beginner rated P1 DX; expert "Turn 0" friction).
- **Evidence:** no dev login route; `GET /auth/google/start` → 303 to Google.
  Three agents independently reverse-engineered the same workaround: read
  `data/.session_secret`, hand-INSERT a user row (or use `tests/conftest.py::sign_in`),
  sign `{"uid": <id>}` and send as `casecall_session`. Intermediate had to write
  directly to the shared dev DB.
- **Fix direction:** document and ship a first-class dev/test auth path — a
  seeded persona account plus a documented session-minting script (beginner
  already built an untracked one: `scripts/_persona_mint_session.py`), or an
  admin-impersonation endpoint. Candidate-facing OAuth flows are fine; the gap
  is tooling.

#### P1-2. Quantitative score is a flat 3.5 for any math-looking turn; arithmetic is never checked
- **Source:** intermediate (BUG-4); corroborated by beginner (quant 3.5 "Meets Bar" on a turn with live miscounting) and expert (quant 3.5 despite transparent order-of-magnitude checks).
- **Evidence:** evaluator.py quantitative block: `quant_score = 2.5`; any turn
  matching `\d+` plus one keyword → flat 3.5 with observation "Handled
  quantitative calculations and data synthesis cleanly." Intermediate's real
  errors (conflating a 12.6%-of-revenue commission drag with a 400bps EBITDA
  decline; an unstated 30% adoption-uplift assumption) scored 3.5 "cleanly" —
  identical to an expert's correct math.
- **Fix direction:** extract candidate equations/claims and validate against the
  case's `facts.yaml` figures (packages already carry verified numbers); report
  specific corrections ("your 12.6% drag on revenue is correct, but reconciling
  to 400bps EBITDA requires the fixed-cost absorption you never requested").

#### P1-3. Golden Rewrites are generic template text, not rewrites of the candidate's words
- **Source:** beginner (Bug #2) + intermediate (BUG-6) — same defect, two runs, merged.
- **Evidence:** beginner's closing golden rewrite references "routes," "dynamic
  pricing," "contract renegotiations" — none of which exist in the beer-plant
  case; `candidate_turn`/`mbb_partner_turn` are byte-for-byte identical to
  `golden_mbb_turn`. Intermediate's opening rewrite "rewrote" their greeting
  (`"Hi Leo, I am ready to begin."`) and the closing partner rewrite is
  case-agnostic filler.
- **Fix direction:** assemble rewrites deterministically from the case's authored
  `case_essence` (mechanism, pivotal insight, traps) plus the candidate's actual
  closing turn and released facts (intermediate's suggestion: template slots
  filled with case numbers; does not need a better LLM). Quote the candidate's
  real closing sentence, point the diagnostic note at the exact sentence where
  they went summary-mode.

#### P1-4. Evidence citations point at the wrong turns and are truncated mid-word
- **Source:** intermediate (BUG-5).
- **Evidence:** `quantitative` evidence cites `message_index 3` quoting
  `"Thanks. Before I structure, a few clarifying questions: 1) I"` (the first
  turn containing a digit — a greeting/clarification cited as quant proof);
  `communication` cites the greeting as proof of 4.2; quotes truncated at
  60/50 chars (`quote[:min(60, len(text))]`).
- **Fix direction:** cite the turn that actually demonstrates the dimension;
  never truncate quotes mid-word; make evidence clickable back to the exact
  line in the transcript (overlaps expert wish #1).

#### P1-5. "What the case really wanted to test" shows the decision question, not the authored insight
- **Source:** intermediate (BUG-6).
- **Evidence:** `what_the_case_wanted_to_test.core_mechanism` = the
  `objective_function.decision_question` ("Why has diagnostic center profitability
  fallen...") instead of the authored `case_essence.core_mechanism` ("Channel mix
  shift toward physician-referred B2C patients with escalating referral
  commissions..."). Knock-ons: `candidate_vs_optimal_gap` renders a grammatically
  broken template fill ("...isolates Why has diagnostic center profitability
  fallen... via ex-ante hypothesis testing"); `pivotal_insight` generic instead
  of the case's real one (commissions 20%→38%).
- **Fix direction:** wire the card to `case_essence` fields, not the decision
  question; fix the template fill so it doesn't splice a question into a sentence.

#### P1-6. Ending an attempt early permanently contaminates profile trends
- **Source:** expert (P1).
- **Evidence:** `POST /api/attempts/9503d142-.../end` after readiness-only
  returns 200 and stores a 2.45 "Developing" evaluation; `GET /api/me/profile`
  aggregates all three attempts (`average_feedback_score: 3.16`, structuring 2.9).
  A connectivity abort or accidental click is indistinguishable from poor
  performance.
- **Fix direction:** explicit `abandoned` state, or an end-confirmation offering
  "save as practice, exclude from scoring"; exclude attempts below a minimum
  substantive-turn threshold from profile aggregates by default.

#### P1-7. The server cannot boot without `OPENROUTER_API_KEY`; no degraded local mode
- **Source:** expert (P1); also blocked beginner's and expert's localhost plans at various points.
- **Evidence:** `RuntimeError: OPENROUTER_API_KEY is required to run the LLM
  interviewer` at import, before `/health`. Contributors cannot dogfood locally
  without a paid key; tests must inject an interviewer double.
- **Fix direction:** a clearly-labelled local deterministic interviewer mode, or
  an app factory that starts degraded and returns an honest 503 for live turns
  when no provider key / test double is configured.

#### P1-8. Evaluation latency is wildly variable with no acknowledgement or progress signal
- **Source:** beginner + intermediate + expert (friction logs, all three).
- **Evidence:** `POST /turn` latency 12.6–23.8s (intermediate), 15–22s
  (beginner); final `POST /api/attempts/{id}/end` took 0.07s (fallback) vs
  **2:06** (real evaluator, beginner attempt 2). Beginner's first client used a
  90s timeout and would have treated a healthy server as failed. No
  processing ack on turns; a candidate cannot tell a slow turn from a hung one.
- **Fix direction:** immediate ack + processing indicator on turns; a progress
  state for the final evaluation ("scoring your case, ~1–2 min"); document/raise
  client timeouts (150s+); consider async scoring with a "debrief ready" signal.

#### P1-9. Interviewer discipline is inconsistent across cases
- **Source:** beginner (findings on both attempts).
- **Evidence:** the same premature framework-dump opener was waved through in
  Attempt 1 but correctly redirected in Attempt 2 ("You are welcome to use
  whichever framework fits best once you hear the prompt..."). The
  hypothesis-before-data rule was enforced in Attempt 1 (refused a no-hypothesis
  data grab) but not Attempt 2 (handed over the 1,200-crore aggregate directly).
- **Fix direction:** pin interviewer behaviors (framework-before-prompt pushback,
  hypothesis-before-data) in the interviewer prompt/policy and add regression
  tests per case family so discipline doesn't vary by case.

#### P1-10. Zero in-case feedback or progress signal — the core learning-loop gap
- **Source:** beginner + intermediate (intermediate rates it "High — the core learning-loop gap").
- **Evidence:** the phase machine (`clarification → drill_down → synthesis`)
  exists server-side (attempt `stage`) but is never surfaced; no facts-uncovered
  counter (intermediate tracked 2/7 and 3/7 manually), no nudge, no signal
  whether quant is landing. Intermediate: "As an intermediate I had no idea
  whether my quant was landing." Beginner ties missing progress directly to the
  bail-out behavior seen at turn 9 in both attempts.
- **Fix direction:** the state machinery already exists (`release_credits`,
  persona budget, `stage`) — this is a surfacing problem, not a modeling one.
  See feature wishes B1/B2.

### P2 — Nice to fix

#### P2-11. Cross-attempt boilerplate: the debrief is templated
- **Source:** intermediate (BUG-8) + expert (debrief usefulness 2/10).
- **Evidence:** two different cases, different gaps → identical `next_drill`
  ("Construct a 3-level MECE tree..."), identical 12 `observed_behaviors`,
  identical strengths/improvement text. Expert: the report asked for an
  "ex-ante commercial hypothesis" both times although both closes contained
  explicit hypotheses and implementation gates.
- **Fix direction:** vary drills from the case's authored essence and the
  candidate's actual missed markers; ground every claim in the transcript.

#### P2-12. Leo coaches and glazes inside `mode: realistic` after the case is over
- **Source:** intermediate (BUG-7).
- **Evidence:** after final synthesis (A2 t-010): "One refinement worth adding...
  With that addition, your analysis is complete and well-structured" — coaching
  that also contaminates the transcript the evaluator later reads.
- **Fix direction:** suppress post-case coaching in realistic mode, or move it
  to a clearly-marked post-interview debrief section.

#### P2-13. Bail-out attempts are ignored by the interviewer
- **Source:** beginner (both attempts, turn 9).
- **Evidence:** "I think that is my answer, can we wrap up? I am running low on
  time" — Leo never acknowledges the bail-out, just prompts for formal synthesis.
- **Fix direction:** have Leo name the behavior ("Candidates under pressure often
  try to wrap early — let's close properly instead"), which is itself the
  teachable moment.

#### P2-14. Catalogue filters not representable in API or URL
- **Source:** expert (P2).
- **Evidence:** `GET /api/cases?difficulty=advanced` → 200 with all 69 cases
  (only 15 are advanced).
- **Fix direction:** support server-side filters and sync the UI filter to URL
  query params so choices are shareable/bookmarkable.

#### P2-15. Re-attempting a solved case: 409 with an unlinked reset call
- **Source:** intermediate.
- **Evidence:** `POST /api/attempts` on a completed case → 409 "You have already
  completed this case. Reset the test before attempting it again." — reset is a
  separate call (`POST /api/cases/{id}/reset`) you must know about.
- **Fix direction:** include the reset action/endpoint in the 409 response body
  (and a UI affordance).

#### P2-16. Live interviewer misses the candidate's arithmetic confusion; no teaching moment
- **Source:** beginner (A2 turn 6).
- **Evidence:** candidate fumbles a crore/million conversion and asks "did I mess
  up the units?" — Leo neither confirms nor corrects, just says the estimate is
  unnecessary. (Related to P1-2 but this is the in-room half.)
- **Fix direction:** at minimum acknowledge/correct unit slips; a real
  interviewer would. Full arithmetic checking is P1-2.

---

## 3. Top UX friction list (ranked)

1. **The debrief headline can't be trusted** — scores from a silent fallback path, badges contradicting empty evaluations, no visibility into evaluation tier (all three). The single biggest trust-killer.
2. **Auth wall** — no dev/test login; three agents had to forge cookies (all three).
3. **Turn latency 12–24s with no ack** — is my turn accepted? (intermediate; beginner's 15–22s matches).
4. **No phase/progress indicator** — "Phase 2 of 3" is invisible; drives mid-case panic and bail-outs (beginner + intermediate).
5. **Zero in-case feedback** — no nudge, no facts counter, no signal quant is landing (intermediate, "core learning-loop gap").
6. **Evaluation latency variance, 0.2s to 2:06** — no progress UI; naive timeouts read a healthy server as failed (beginner + expert).
7. **Interviewer ends but the attempt doesn't** — "That concludes our case interview," then you must know to `POST /end` yourself (intermediate).
8. **Early end silently depresses your trendline** — no warning, no abandon state (expert).
9. **Leo counter-questions without releasing data, twice in a row** — feels like stalling; candidate doesn't know whether to push or answer (intermediate).
10. **Fact release timing feels arbitrary** — a direct question goes unanswered; one turn later the fact arrives attached to Leo's own suggestion (intermediate).
11. **Bail-out attempts ignored** (beginner).
12. **409 on re-attempt with an unlinked reset call** (intermediate).
13. **Filters not shareable/bookmarkable** (expert).

Positive friction worth keeping (intermediate): Leo's mid-case follow-ups
(A1 t-003, A2 t-005) were genuinely good interviewer behavior that forced
second-order thinking — "the interviewer is ahead of the evaluator."

---

## 4. Raw feature-wish list (unfiltered, all three personas)

**Beginner** (from "Missing features I WISHED existed"):
1. Visible signal when the evaluation is degraded, partial, or fallback-fired — a "provisional / evaluation incomplete — retry recommended" banner on the debrief instead of a confident "Meets Bar" badge.
2. Phase/progress indicator during the case ("Phase 2/3 — Drill Down") alongside the chat.
3. Candidate-facing "regenerate evaluation" action on a completed attempt, instead of replaying 10+ turns from scratch.

**Intermediate** (top 3 + honorable mentions):
1. Live micro-feedback during the case ("in-room scorecard"): current phase, facts-uncovered counter ("3/7 key facts"), one per-turn nudge ("you asserted a 30% expansion uplift — state the source or flag it as an assumption").
2. Arithmetic checking on quant turns: extract candidate equations/claims, verify against `facts.yaml` figures, report specific corrections.
3. Real Golden Rewrites: my words vs the partner's words for THIS transcript, assembled from authored `case_essence` + my released facts, with the diagnostic note pointing at the exact sentence where I went summary-mode.
- Honorable mentions: a 60-second "post-case Leo teach-back" (debrief narrated in Leo's interviewer voice); a per-case drill that varies with the case and my actual gaps; surfacing `fallback=true` on the debrief page.

**Expert** (top 3):
1. Evidence-linked partner review: 2–3 quoted moments per dimension, a verdict on the underlying business logic, one precise rewrite or missing test; click from the score to my line, the relevant fact, and a stronger MBB move.
2. True expert pressure mode: detect when the candidate is driving well, stop spoon-feeding, introduce a contradictory fact or time pressure, demand the exact calculation, grade the defended trade-off — adapt upward, not the same disclosure cadence for everyone.
3. Signal-clean longitudinal practice: abandon versus score; user-tagged skill focus; current-vs-prior attempt comparison by dimension and evidence; one deliberately hard follow-up case based on the weak pattern. Stretch: replay a decision fork and score the revised two-turn answer side by side.

**Cross-persona clusters** (for the roadmap): (a) evaluation transparency and
regeneration (beginner 1/3, intermediate HM3, expert 1); (b) in-case feedback
and progress (beginner 2, intermediate 1, expert 2/3); (c) transcript-specific
rewrites and drills (beginner, intermediate 3, expert 1 + P2-11); (d) honest
longitudinal scoring (expert 3, intermediate's "honest scoring" persona ask).

---

## Appendix A — Dedup map

| Consolidated | Source findings |
|---|---|
| P0-1 silent fallback + calibration | beginner Bug #1 (attempt-1 calibration), beginner A2 analysis, intermediate BUG-2, expert P0 |
| P0-2 platform outage | beginner Bug #1 (server crash) |
| P0-3 contradictory badge | beginner Bug #3 |
| P0-4 structuring on greeting | intermediate BUG-3 |
| P1-1 auth path | beginner auth note (P1 DX), intermediate BUG-1, expert friction "Turn 0" |
| P1-2 flat quant / no arithmetic check | intermediate BUG-4; beginner calibration (quant 3.5 vs 1.0); expert calibration (quant 3.5 vs 4.3–4.5) |
| P1-3 golden rewrites generic | beginner Bug #2, intermediate BUG-6 (rewrite half) |
| P1-4 evidence citations wrong/truncated | intermediate BUG-5 |
| P1-5 "what the case wanted" card | intermediate BUG-6 (core-mechanism half) |
| P1-6 early-end pollutes trends | expert P1; corroborated by intermediate's 2.45-style concern? no — expert only |
| P1-7 no-key boot | expert P1; beginner used a private instance only after outage (related) |
| P1-8 latency variance | beginner A2 (2:06), intermediate friction (12–24s), expert friction |
| P1-9 inconsistent discipline | beginner A1 t-1 vs A2 t-1; beginner A1 t-5 vs A2 t-5 |
| P1-10 no in-case feedback | intermediate friction table (High), beginner wish 2 (phase indicator) |
| P2-11 boilerplate | intermediate BUG-8, expert "same generic MECE exercise" + stock-advice-contradicts-transcript |
| P2-12 coaching in realistic mode | intermediate BUG-7 |
| P2-13 bail-outs ignored | beginner A1 t-9, A2 t-9 |
| P2-14 filters not shareable | expert P2 |
| P2-15 409/reset | intermediate friction (Low) |
| P2-16 live arithmetic teaching missed | beginner A2 t-6 (live half of P1-2) |

Not carried as product findings (test-setup limitations, noted for the
program): expert's sandbox blocked binding port 8002 and the deterministic
interviewer double couldn't exercise pressure-mode interviewer quality;
pre-existing test failure `tests/test_case_progress.py` (asserts literal
`syncTimer(attempt);` no longer in `app/static/app.js`) already xfailed on the
foreman branch (ebdb144).
