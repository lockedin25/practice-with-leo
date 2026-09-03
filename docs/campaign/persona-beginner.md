# Persona QA Report — BEGINNER (2nd-year MBA, zero case experience)

Persona voice: anxious, rambly ("um", "uh", "sorry"), dumps a generic framework
before hearing the prompt, doesn't drive the conversation, asks the
interviewer for hints/answers outright, shaky mental math, wants to wrap up
early when uncomfortable.

Auth path used (dev/test, no Google OAuth): `scripts/_persona_mint_session.py`
run with `DATABASE_PATH=<main-checkout>/data/casecall.db` so it reuses the
server's real `.session_secret` and inserts a row via `AccountStore.upsert_from_google`,
then `issue_session()` mints the `casecall_session` cookie. `GET /api/me` → 200
confirmed this works against the shared server. This is undocumented outside
`tests/conftest.py::sign_in` — a first-time agent without that file would be
stuck. **Finding (P1, DX):** there is no documented "how to drive Leo
programmatically without Google OAuth" path for the persona-QA use case this
campaign requires; `scripts/_persona_mint_session.py` had to be reverse-engineered
from `app/accounts.py`.

## Bug #1 (P0 — Reliability/Concurrency): shared dev server went down for all users

- **Endpoint:** `POST /api/attempts/{attempt_id}/turn` on the shared server
  (`http://localhost:8000`), attempt `1989c426-028e-4572-bef7-75d5c8dfa379`,
  case `01-beer-manufacturer-v1`, turn `t-007`.
- **Trace:** the turn request (candidate doing shaky mental math: "3 plants ×
  3 machines = 9 machines, 30,000 × 3 = 90,000 bottles, 90,000/9 = 10,000/machine,
  sorry what were we solving for again?") hung and the client-side call timed
  out after 120s. Immediately after, **every** `/api/*` endpoint on the shared
  server started returning a bare `Internal Server Error` (HTTP 500, no JSON
  body) — including unrelated, previously-working calls: `GET /api/cases`
  (no auth needed), `GET /api/me`, `GET /api/attempts/{id}`. This was not
  transient: it was still broken 30+ seconds later. Static pages (`GET /`)
  kept serving 200, so only the API layer (almost certainly the DB layer) was
  wedged.
- **Root cause (best guess, not confirmed via server logs — none were
  reachable from this worktree):** the shared server was being hit
  concurrently by multiple agents/personas in this campaign at once. I could
  **not** reproduce the crash by replaying the identical turn content against
  my own private instance (see below) — it returned normally in 17–22s. That
  points to a **concurrency/locking bug** (e.g. SQLite write contention across
  simultaneous sessions) rather than something inherent to beginner-style
  input, and it is more concerning: it means one slow/awkward request from any
  single candidate can take down the platform for every other concurrent user.
- **Mitigation used:** per the brief's fallback instruction, I stopped hitting
  the shared server and started my own instance from this worktree
  (`.venv/bin/uvicorn app.main:app --port 8002`, fresh local
  `data/casecall.db`) and reran both attempts there end-to-end successfully.
  I did not touch the shared server process or its DB (main checkout is
  owned by the foreman).
- **Severity:** P0. This is worse than a single-case bug — it's a
  platform-wide outage triggered by ordinary concurrent load, with no visible
  recovery path and no error surfaced to the candidate (the UI would just
  hang or show a generic failure).

## Attempt 1 — Profitability case: "Beer Manufacturer" (`01-beer-manufacturer-v1`, foundation)

Run on private instance (port 8002), `mode: realistic`, 10 candidate turns.

Turn-by-turn (candidate persona in beginner voice; ⚠ = friction/finding):

1. Opens with an untailored framework dump ("classic profit = revenue − cost")
   before even hearing the prompt. ⚠ Leo does not push back on the
   premature/generic framework at all — just proceeds to give the case
   prompt. A real MBB interviewer would flag "let's hear the prompt first."
2. Guesses processing cost = "labor and raw materials," asks for raw material
   cost directly. Leo correctly redirects ("raw materials are distinct from
   processing costs").
3. Candidate explicitly asks for a definitional hint ("is processing cost
   like conversion cost...?"). ⚠ **Finding:** Leo just confirms and hands over
   the full definition ("That is correct... encompassing labor, utilities,
   maintenance, and plant overhead") instead of making the candidate work for
   it or reflecting the ask back. For a persona whose whole failure mode is
   "asks the interviewer for help," this makes it too easy to fish for answers
   turn by turn without penalty.
4. Candidate proposes a labor/energy/maintenance/overhead cut, asks to "look
   at labor first." Leo ignores the direct ask and redirects to
   footprint-level structuring — reasonable interviewer discipline, but also
   means Leo never actually answers a candidate's direct question in this
   run; every question gets redirected into another question.
5. Candidate reacts to the 45%-gap fact with an unstructured, non-hypothesis
   data request. Leo (correctly, per real MBB style) refuses to hand over the
   breakdown and demands a hypothesis first.
6. Candidate states a specific hypothesis (labor/automation gap) — this is
   actually the single most "senior" moment in the whole transcript.
7. **(turn 7, timestamped ~T+6 min of the transcript)** Shaky math turn: candidate
   miscounts machines/bottles out loud, self-corrects, then asks "sorry, what
   were we solving for again?" — a hallmark beginner panic moment. Leo
   answers matter-of-factly and keeps going; does not flag the loss of
   thread as an issue anywhere in the eventual debrief.
8. Candidate misreads "10,000 bottles/machine" as obviously low utilization
   without benchmark data — an unjustified leap. Leo correctly challenges it
   ("does not necessarily mean low utilization").
9. Candidate, uncomfortable, tries to wrap early ("I think that is my answer,
   can we wrap up? I am running low on time") without being asked. Leo does
   not acknowledge the bail-out attempt; it just prompts for a formal
   synthesis anyway, which happens to save the interview structurally, but a
   candidate genuinely trying to escape a hard case shouldn't be so easily
   funneled back in with no comment on the behavior itself.
10. Final recommendation delivered — generic, not quantified, no
    risks/mitigations, no 100-day plan (matches the beginner persona brief:
    "gets lost mid-case," weak synthesis).

### Bug #2 (P1 — Debrief content quality): generic, case-mismatched "golden rewrite"

The debrief's `golden_rewrites[1].golden_mbb_turn` (closing stage) reads:
*"Second, optimize variable operating cost per unit across high-volume
routes. Third, implement dynamic pricing indexed to input costs. Key
implementation risks include client pushback during **contract
renegotiations** (mitigated via value-tiered SLAs)."*

This is boilerplate from a **pricing/logistics-contract case template**, not
the beer-plant conversion-cost case actually run. There are no "routes,"
"dynamic pricing," or "contract renegotiations" anywhere in this case. The
`candidate_turn` and `mbb_partner_turn` fields for both golden-rewrite entries
are also byte-for-byte identical to `golden_mbb_turn` — the "compare your
answer to the ideal" mechanic isn't actually diffing anything, it's just
inserting the same generic template three times. This directly undermines the
core promised value of the debrief (a genuinely case-tailored ideal answer to
learn from).

### CALIBRATION — self-score vs Leo's dimension scores

Self-assessment (honest, in-persona): this was a shaky, unfocused run. I
rambled, dumped an untailored framework, needed a definitional hint fished
out of the interviewer, botched my own arithmetic mid-turn, made an
unsupported leap on utilization, and tried to bail before synthesis. This is
a **1.5–2/5** performance by any real MBB rubric — closer to "not
interview-ready" than "meets bar."

| Dimension | My self-score | Leo's score | Leo's band | Gap |
|---|---|---|---|---|
| Structuring | 1.5 | 3.3 | Meets Bar | **+1.8** |
| Problem solving | 1.5 | 3.2 | Meets Bar | **+1.7** |
| Quantitative | 1.0 (miscounted live, needed a redo) | 3.5 | Meets Bar | **+2.5** |
| Synthesis | 1.5 (generic, no risks, no 100-day plan, tried to bail) | 3.5 | Meets Bar | **+2.0** |
| Communication | 1.5 (filler words, lost the thread, asked "what were we solving for again") | **4.2** | **Top 1% MBB** | **+2.7** |
| **Overall** | **~1.5** | **3.48 ("Meets Bar")** | | **+1.98** |

**This is the single highest-severity finding in this report.** The brief's
target band for beginner is 1.5–2.5; Leo landed at 3.48 and rated
communication "Top 1% MBB" for a transcript full of "um," "uh," "sorry," and a
mid-case loss of thread. Root cause visible in the raw payload:
`"evaluator_version":"evaluator-v3|rubric=rubric-v2|fallback=true"` —
**`fallback=true` means the real (presumably LLM-based) evaluator did not run,
and Leo silently graded this attempt with a deterministic fallback scorer**
that appears to reward turn count / structural completion (did you reach
synthesis? did you say a number? did you use transition words?) rather than
actual reasoning quality. The candidate is never told the evaluation was a
fallback — the UI-facing `evaluator_version` string is buried in the API
response, not surfaced anywhere a candidate would see it. A candidate would
walk away believing they are Top-1%-MBB-caliber on communication.

### Debrief usefulness

Structurally the debrief is rich (executive summary, per-dimension evidence
quotes + observations + improvements, a checklist of named markers
demonstrated/missed, golden rewrites, a targeted drill, suggested readings).
If the scores and golden rewrites were trustworthy this would be a genuinely
strong learning artifact — better than most human-run mock feedback. As
observed in this run, though, it is **not currently useful for a beginner**:
the score is badly inflated (see calibration above) so it wouldn't tell this
candidate they need serious help, and the one worked example meant to show
"what good looks like" (`golden_rewrites`) is generic template text that
doesn't match the case, so there's nothing case-specific to actually learn
from. The `checklist`/`observed_behaviors` marker list (e.g. "restate
objective first: missed," "4-part closing: missed") is the most honestly
useful part of the debrief — it correctly flags real gaps even while the
headline score doesn't reflect them.

## Attempt 2 — Market-entry case: "Aster Diagnostics" (`aster-diagnostics-v1`, intermediate)

Auth reused the exact recipe from Attempt 1 (`scripts/_persona_mint_session.py`
against the main checkout's `data/casecall.db`/`.session_secret`, minted for a
fresh persona user `persona-beginner-attempt2@example.com`). `GET /api/me` →
200 confirmed. Run **against the shared server** at `http://localhost:8000`
this time (not a private instance) — chosen deliberately to see whether Bug
#1's platform-wide 500 crash would recur under today's load. `mode: realistic`,
10 candidate turns, case picked via `GET /api/cases` filtered to
`market_entry`/`growth_strategy` titles (avoided re-running Beer Manufacturer
per the brief).

**No repeat of Bug #1's global crash** — the shared server stayed responsive
throughout (`GET /api/me` and `GET /api/cases` kept returning 200 after every
turn, including after a request that itself timed out client-side). One new,
related reliability observation: turns individually took 15–20s each (matches
Attempt 1), and the final `POST /api/attempts/{id}/end` (evaluation) call took
**2:06** wall-clock — long enough that a naive client timeout (my first
attempt used a 90s cap) would treat it as a hard failure and the candidate
would see nothing at all. That's consistent with Bug #1's theory that the
platform is fragile under normal latency, not just literal concurrency.

Turn-by-turn (candidate persona in beginner voice; ⚠ = friction/finding):

1. Same premature framework-dump opener as Attempt 1 ("classic 3C framework
   ... before we dive in"). **Contrast with Attempt 1:** this time Leo
   explicitly declined and redirected — *"You are welcome to use whichever
   framework fits best once you hear the prompt... let me know whenever you
   want to begin"* — instead of just proceeding to give the prompt. ⚠
   **Finding:** the same beginner failure mode (framework-dump before
   hearing the prompt) got two different interviewer responses across the
   two cases run in this campaign — Attempt 1's Leo let it slide, Attempt
   2's Leo pushed back correctly. Inconsistent interviewer discipline across
   cases, not just across personas.
2. Candidate asks for the prompt. Leo delivers it cleanly.
3. Candidate restates the prompt back in a still-generic, untailored list
   ("market size, competition, our capabilities, costs, maybe regulatory
   stuff"). ⚠ Leo accepts this at face value ("Those areas cover the
   relevant dimensions") rather than pushing for a tailored, MECE structure
   — same gap as Attempt 1 turn 1, just one turn later in the flow.
4. Candidate asks a real clarifying question (current tier-1 share, existing
   tier-2 footprint). Leo answers directly (no footprint) and immediately
   demands a hypothesis — good interviewer discipline, matches Attempt 1's
   better moments.
5. Candidate skips stating a hypothesis and asks directly for population and
   per-capita spend data to size the market from scratch. ⚠ **Finding
   (inconsistent with Attempt 1):** here Leo just hands over the aggregate
   figure directly (*"approximately 1,200 crore rupees annually... growing
   at roughly 12 percent... organised chains ~25 percent"*) with no pushback
   on the missing hypothesis. Attempt 1's Leo, faced with the equivalent
   no-hypothesis data grab, explicitly refused and demanded a hypothesis
   first. Same rule ("hypothesis before data"), enforced in one case and not
   the other.
6. Shaky-math turn: candidate tries to size a single city from scratch
   anyway (2M people × 10% × 2 tests/yr × ₹500), fumbles the
   crore/million conversion out loud, and second-guesses the result
   ("sorry, is that right, that seems really high, did I mess up the
   units?"). ⚠ Leo does not correct or even acknowledge the arithmetic
   confusion — it just says the from-scratch estimate is unnecessary since
   the aggregate number already exists. A real interviewer would clarify the
   unit slip (20 crore ≠ 200 million is actually consistent here, but the
   candidate never gets confirmation either way) — a missed teaching moment
   for exactly the persona this campaign is testing.
7. Candidate gives up on the math and just asks Leo to hand over "the actual
   addressable market size" outright — a clean fish-for-the-answer moment.
   ⚠ Leo complies (restates the same 1,200 crore figure) with no comment on
   the candidate abandoning their own calculation.
8. Candidate states a hypothesis (operational barriers — real estate,
   phlebotomists — over demand). Leo correctly refuses to validate it and
   redirects to comparing operating models first — good discipline,
   consistent with Attempt 1 turn 5's refusal pattern.
9. Candidate proposes a hub-and-spoke model and tries to bail early ("I
   think that's basically my answer, can we wrap up? I'm a bit lost on the
   numbers side"). ⚠ Same pattern as Attempt 1 turn 9: Leo doesn't
   acknowledge the bail-out attempt at all, just prompts for a formal
   synthesis anyway.
10. Final recommendation: hub-and-spoke model, one named risk (sample
    logistics) with no mitigation, no quantified market-capture numbers, no
    100-day plan — matches the beginner brief ("gets lost mid-case," weak
    synthesis), same shape as Attempt 1's ending.

### Bug #3 (P0 — Evaluation pipeline): real (non-fallback) evaluator returned an empty score with a contradictory "Meets Bar" badge

Per the retry instructions: **this run's evaluator does NOT show
`fallback=true`.** `evaluation.evaluator_version` reads
`"evaluator-v3|rubric=rubric-v2|checklist=checklist-v2|model=google/gemini-3.7-flash"`
— an actual model is named, unlike Attempt 1's
`...|fallback=true`. That makes this a **different and arguably worse**
bug than Attempt 1's inflated fallback score:

- `evaluation.checklist` / `evaluation.observed_behaviors` (12 named
  markers) came back **rich, accurate, and well-evidenced** — 11 of 12
  correctly marked `"missed"` with specific quotes and notes (e.g.
  *"Candidate did not state an explicit equation, mixed up Crores and
  Millions, and did not conduct a sanity check"*; *"Candidate abruptly
  requested to wrap up early rather than cleanly signposting
  transitions"*). This is the most honest, well-calibrated qualitative
  feedback seen in either attempt of this campaign — it matches this
  transcript's real quality far better than Attempt 1's fallback checklist
  did.
- But `evaluation.dimensions: []`, `evaluation.dimension_scores: {}`,
  `evaluation.executive_summary: ""`, `evaluation.golden_rewrites: []`,
  `evaluation.strengths: []`, `evaluation.headline_strengths: []`,
  `evaluation.suggested_readings: []`, and `evaluation.overall.overall:
  null` are **all empty** — the entire numeric-scoring and narrative-writeup
  half of the evaluator produced nothing.
- Despite that, `evaluation.overall_score` is `0.0` and
  `evaluation.overall_band` / `evaluation.mbb_rating_badge` are both
  **`"Meets Bar"`** — an internally contradictory result (a 0.0 score
  should not badge as "Meets Bar" under any rubric; it reads like a
  default/uninitialized value that never got overwritten because the
  scoring step that should have set it silently produced nothing).
- Net effect for a candidate: they'd see a headline "Meets Bar" badge (or
  whatever the UI renders for a `0.0`/`"Meets Bar"` combination) while the
  one part of the debrief that's actually correct — the checklist — is
  screaming "11 of 12 markers missed." This is the same underlying failure
  mode as Attempt 1's Bug (a badge that doesn't reflect real performance),
  reached by an entirely different broken path (partial real-evaluator
  failure vs. a full fallback), which suggests the debrief's headline
  score/badge is unreliable **regardless of whether the fallback path is
  triggered** — the bug is broader than "the fallback scorer is bad."

## Missing features I WISHED existed (top 3, concrete)

1. **No visible signal when the evaluation is degraded, partial, or the
   fallback path fired.** `evaluator_version` carries exactly this
   information (`fallback=true` in Attempt 1; an empty
   dimensions/executive-summary payload in Attempt 2) but it's a raw string
   buried in the API response, never surfaced in the UI and never checked
   before rendering the headline badge. Concrete ask: if `fallback=true` OR
   any of `dimensions`/`dimension_scores`/`executive_summary` come back
   empty, render a visible "provisional / evaluation incomplete — retry
   recommended" banner on the debrief instead of a confident-looking
   "Meets Bar" badge with a `0.0` score.
2. **No phase/progress indicator for the candidate during the case.** The
   attempt object tracks `stage` (`clarification` → `drill_down` →
   `synthesis`) server-side, but nothing in what I saw exposes "you are in
   phase 2 of 3" as a readable progress marker. For exactly the persona this
   campaign is testing — someone anxious and prone to wanting to bail mid-case
   — not knowing how much case is left materially drives the "can we wrap
   up, I'm lost" behavior seen in both attempts' turn 9. Concrete ask: a
   simple "Phase 2/3 — Drill Down" indicator alongside the chat.
3. **No way to retry/regenerate a single broken evaluation.** I found one
   evaluate-related route, `POST /admin/attempts/{attempt_id}/evaluate` in
   `app/admin.py`, which by its module location looks admin-only, not
   candidate-facing. Given that 2 of 2 attempts in this campaign produced a
   debrief with a wrong headline number (Attempt 1: inflated fallback score;
   Attempt 2: empty-dimensions score badged "Meets Bar"), a candidate has no
   self-serve way to say "this debrief looks wrong, re-score it" without
   replaying the entire 10+-turn case from scratch. Concrete ask: expose a
   candidate-facing "regenerate evaluation" action on a completed attempt.

