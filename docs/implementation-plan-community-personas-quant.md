# Implementation plan: personas, mutable catalogue, and crowdsourced contribution

**Date:** 2026-08-27
**Scope:** Phases 0 to 3. Phases 4 and 5 (reactions, suggested edits, comments, both
leaderboards) are deferred by decision. The quantitative runtime becomes Phase 4.
**Status:** Phases 0 to 3 complete. Phase 4 (quantitative runtime) is next.

---

## 1. Decisions taken

Recorded here because several of them reverse what the first draft of this plan
proposed.

| Decision | Detail |
|---|---|
| Communication scoring | Narrowed to transcript-observable craft, not fix-scored and not dropped. Delivery (tone, pace, confidence, filler) is explicitly out of scope until voice scoring exists. |
| Quantitative content | Optional per case, permanently. A case with no quantitative surface is correct and normal, not a gap to backfill. |
| Catalogue | Becomes mutable. Minimal monotonic integer versioning, since suggested edits are deferred and admin edits are the only mutation path. |
| Review gate | Every contributed case is private until admin review. Admin is Shubham. No auto-publish path in this scope. |
| Persona release rates | Coach one fact per turn. Operator one per two to three turns. Skeptic one per five to six turns. Coach is a tightening of today's behaviour, not a loosening. |
| Institution names | Removed from user-visible surfaces only. `corpus/` directory names, the source rights register, and git history are left alone. |
| Case library filter | The School/Source filter becomes Curated vs Community. |
| Cost | Not a constraint. Contribution may be expensive as long as it is seamless. Keep a concurrency guard against runaway loops, drop the daily caps. |
| Contribution interface | Chat and voice, reusing the existing turn and voice-realtime architecture. Many more turns than a case. Open-ended at the start, long by design. |
| Quantitative grading | Consulting math, not arithmetic. Order of magnitude over precision, setup over execution. |

**Scope correction:** there are **69 playable cases**, not 12.
`CaseCatalogue.from_reservoir` also walks `corpus/exemplars/`
([`case_runtime.py:201`](../app/case_runtime.py)), which holds 57 packages across
four institution directories, on top of the 12 in `reservoir/`.

---

## 2. Phase 0: dimension assessability. Complete.

### What was wrong

Two related defects, and the first draft of this plan diagnosed them too broadly.

**The redistribution machinery already existed on one path.**
`weighted_overall` was already documented as "unassessed dimensions redistribute
weight", and [`main.py:366`](../app/main.py) uses it for the durable score. But it
decided assessability by *inferring* it from whether the writer had produced a
citation, and `completeness_violations` simultaneously flagged any dimension
without evidence. So the evaluator was actively pressured to manufacture a
citation for `quantitative`, at which point it carried its full 0.15 weight
against a candidate who was never asked to compute anything.

**The heuristic fallback path had no redistribution at all.** It applied a
hardcoded weight table and scored `quantitative` at a default 2.5 whenever no
arithmetic was detected.

**And the two paths disagreed with each other.** [`profile.js:445`](../app/static/profile.js)
displays `report.overall_score`, which the fallback computed with fixed weights,
while the stored practice score came from `weighted_overall`. One attempt could
legitimately show two different numbers in two places.

### What changed

- `DimensionScore` gains `assessed: bool` and `unassessed_reason: str`. Assessability
  is now declared, not inferred.
- `dimension_counts_toward_score()` requires both the explicit flag and evidence.
  The evidence condition is retained deliberately: `evaluator-v2` reports predate
  the flag and default it to True, so dropping the evidence check would have pulled
  previously excluded dimensions back into historical scores.
- `completeness_violations` no longer demands a citation for an unassessed
  dimension, and instead requires `unassessed_reason`. This removes the pressure
  that caused the original defect.
- The heuristic fallback marks `quantitative` unassessed when the attempt contains
  no quantitative work, and redistributes rather than charging a default 2.5.
- `stamp_overall()` writes the deterministic score, badge, band, `weights_used`,
  `assessed_dimensions` and `excluded_dimensions` onto the report. Both evaluators
  call it, so the profile and the stored score are now the same number.
- `EVALUATOR_VERSION` is `evaluator-v3`. Prior reports keep their stored version.
- `evaluation/rubric.yaml`: `quantitative` rewritten for consulting math (see §5.1);
  `communication` narrowed with an explicit `assessable_from_transcript` /
  `not_assessable_from_transcript` split.

Measured effect: a candidate scoring 4.0 on the four exercised dimensions used to
receive 3.775. They now receive 4.0.

Tests added in `tests/test_evaluator_v2.py` cover redistribution, the pinned
arithmetic of the old defect, legacy-report score stability, and the
`unassessed_reason` requirement. Suite: 240 passing.

> Pre-existing unrelated failure:
> `tests/test_case_progress.py::test_start_case_control_submits_a_readiness_turn_to_open_the_timer_gate`
> asserts `syncTimer(attempt);` exists in `app/static/app.js`. It is absent at HEAD
> and `app.js` is unmodified, so this predates this work.

### Communication, and where voice scoring slots in

The dimension now scores only what a transcript can evidence: top-down delivery,
signposting, information density, concision, answering the exact question asked,
and holding a position under pushback. The research basis for that last one is that
interviewers challenge correct answers about as often as incorrect ones, so both
instant capitulation and defensive restatement are scored as failures.

Delivery is named in the rubric as explicitly not assessable from a transcript.
When voice confidence and pacing scoring exists, it becomes a second assessable
signal using the same `assessed` flag, with no rescoring event for historical
attempts.

---

## 3. Phase 1: interviewer personas. Complete.

### 3.1 Research basis

- **McKinsey is interviewer-led.** Central case team, scripts, interviewer owns the
  process and releases targeted data tied to the question it just asked.
- **BCG is candidate-led.** Cases built by consultants from their own work; the
  interviewer knows the whole world and lets the candidate choose the path.
  High-level information upfront, everything else must be asked for.
- **Bain has moved from candidate-led toward interviewer-led.**
- **Pushback is an instrument, not a verdict.** Applied to correct answers about as
  often as incorrect ones, to see whether a position is defensible.
- **In candidate-led cases, dead ends are allowed to run.**

Design conclusion: **disclosure and demeanour are independent axes.** A brusque
interviewer who answers everything directly is as real as a warm one who tells you
nothing. Collapsing them into one difficulty slider produces caricature.

### 3.2 Presets

```
disclosure_regime:  generous | neutral | withholding
demeanour:          warm | neutral | clipped | superior
```

| Persona | Regime | Demeanour | Release rate |
|---|---|---|---|
| **The Coach** | generous | warm | 1 fact per turn |
| **The Operator** | neutral | neutral | 1 fact per 2 to 3 turns |
| **The Skeptic** | withholding | clipped | 1 fact per 5 to 6 turns |

`superior` is a demeanour available on any regime rather than a fourth preset.
Arrogance is not what makes a case hard; withholding information is.

Today's behaviour releases up to 2 facts per turn after the opening, so **Coach is
a tightening of the current product, not the current product renamed.**

### 3.3 Rate mechanism: budget plus precision bar

A per-turn cap cannot express "one fact per five turns", and a blunt cooldown makes
the Skeptic feel broken rather than hard. Stonewalling a precisely-targeted question
is not realistic behaviour; real hard interviewers refuse *vague* questions.

So two coupled mechanisms:

**Release budget.** Each candidate turn accrues `release_rate` credits (Coach 1.0,
Operator 0.4, Skeptic 0.18). Releasing one fact costs one credit. Credits accrue up
to a small cap so a patient candidate banks a little, but cannot bank ten turns of
silence into a data dump.

**Precision bar.** Persona-specific threshold on how targeted the question must be
before it can draw down budget. The director already classifies candidate intent, so
this is a graded judgement on the existing signal, not a new inference. A brilliant
question lands early even on the Skeptic. A loose one earns nothing even when
credits are available.

**Anti-stonewall floor.** Per persona, after N consecutive well-targeted questions
that earned nothing, release the narrowest eligible fact regardless of budget.
Coach's floor is 1, Operator's 3, Skeptic's 6. Without this the Skeptic reads as a
bug report.

### 3.4 Existing levers

Every dial is currently a hardcoded constant.

| Lever | Location |
|---|---|
| Facts per turn | `max_facts = 1 if is_early_precision_turn else 2` in [`interviewer.py`](../app/interviewer.py) `respond()` |
| Permitted reveal levels | `phase_policy[].reveal_levels` in `conversation-policy.yaml` |
| Stuck recovery | Director prompt: "select the narrowest eligible fact that helps them" |
| Move bias | `DirectorDecision.move` enum |
| Unproductive follow-ups | `RecoveryPolicy.maximum_unproductive_follow_ups` ([`models.py:150`](../app/models.py)) |
| Tone | Voice prompt system message |

### 3.5 Implementation

- New `app/personas.py` holding the three presets, both dials, release rate,
  precision bar, and floor.
- **Prompts take persona as an input variable, not new chains.** The templates are
  compiled once in `__init__`. Add `{persona_disclosure_policy}`,
  `{persona_pushback_policy}` and `{persona_demeanour}` placeholders and pass them at
  `invoke()`. The existing `turn_pacing_policy` proves the pattern.
- Reveal-level shifting stays in `case_runtime.py`, on the authoritative side, so the
  leak-prevention property holds regardless of persona.
- `InterviewSession.persona`, distinct from the existing `mode` (which already means
  `session_contract.mode: realistic`). Persistence is free, since `store.save()`
  serialises the session payload.
- Budget state (`release_credits`, `turns_since_release`, `consecutive_precise_misses`)
  lives on the session and is persisted with it.
- **Persona recorded on the attempt and the evaluation.** Required for any future
  cross-user comparison to mean anything.
- `StartAttemptRequest.persona`, defaulting to `operator`. `GET /api/personas`.
- Persona picker on the case start screen; persona shown in the room header and on
  the debrief.

- [x] `app/personas.py`
- [x] Persona placeholders in director and voice templates
- [x] Release budget, precision bar, anti-stonewall floor
- [x] Reveal-level widening in `case_runtime.py`
- [x] Persona resolved from the existing `mode`; budget persisted; label on the attempt
- [x] `mode` validated on `StartAttemptRequest`; `GET /api/personas`
- [x] Persona picker in the library; persona label in the room header and tags
- [x] Tests: cadence, precision bar, floor, refund, reload, API (34 tests)

### 3.6 Measured cadence

Facts disclosed over 30 candidate turns, driven through the shipped
`allowance_for` / `resolve_release` gate:

| Persona | Targeted questions | Partial | Vague |
|---|---|---|---|
| The Coach | 30 | 30 | 30 |
| The Operator | 12 | 12 | 0 |
| The Skeptic | 5 | 4 | 0 |

Two bugs were found by these tests and fixed rather than accommodated:

1. **Clamping credit accrual at 1.0 discarded the fractional remainder**, so a
   rate of 0.4 produced a fact every three turns instead of every two and a half.
   The cap now sits at 2.0 and `max_facts_per_turn` enforces the one-fact-per-turn
   guarantee instead.
2. **The anti-stonewall floor counted the wrong thing.** It advanced only on
   questions clearing the persona's own bar, which are exactly the turns the budget
   is deliberately withholding, so the counter reset on every disclosure and the
   floor never fired. It now advances on any question graded `partial` or better,
   which is the real stonewall: decent questions landing just under a demanding
   bar. Vague questions still never count, so the floor cannot be farmed.

---

## 4. Phase 2: mutable catalogue, provenance, institution removal. Complete.

### 4.1 Catalogue

Authored cases stay on the filesystem and stay in git, which is what
`corpus/README.md`'s rights discipline exists to protect. Contributed cases live in
SQLite on the mounted volume. The catalogue merges both.

```sql
CREATE TABLE cases (
    case_id        TEXT NOT NULL,
    version        INTEGER NOT NULL,
    source         TEXT NOT NULL CHECK(source IN ('authored','contributed')),
    status         TEXT NOT NULL CHECK(status IN
                     ('draft','submitted','validated','published','needs_changes','unpublished')),
    package_json   TEXT NOT NULL,
    contributor_id TEXT,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id, version),
    FOREIGN KEY (contributor_id) REFERENCES users(id)
);
CREATE INDEX cases_published ON cases(status, case_id, version DESC);
```

Versioning is kept minimal: a monotonic integer, latest published version wins when
unpinned, `attempts.case_version` pins a live attempt so an admin edit cannot shift
the world under a candidate mid-interview.

`CaseWorld` stays immutable. The catalogue becomes a registry with `register()` and
`reload()`. Startup validation is preserved, because nothing reaches `published`
without passing the Phase 3 gate.

The six direct reads of the `CATALOGUE` module global in `main.py` move to
`app.state.catalogue` through a dependency. Mechanical, but its own commit.

### 4.2 Provenance

```yaml
provenance:
  source_type: interview_recall   # interview_recall | authored
  firm: McKinsey                  # nullable
  round: 1                        # nullable
  geography: India
  interview_month: 2026-07        # month precision, never a full date
  contributor_id: usr_...
  attribution_mode: pseudonymous  # anonymous | pseudonymous | public
  embargo_until: 2026-10-01       # nullable
```

Month precision is deliberate: a full date plus a firm plus a round is close to
identifying. `embargo_until` lets a mid-process candidate contribute now and publish
after their process closes, which removes their main reason to withhold.

### 4.3 Institution removal, user-visible surfaces

Live footprint:

| Surface | Location |
|---|---|
| School/Source dropdown with named institutions and counts | [`cases.html:124`](../app/static/cases.html) |
| `SCHOOL_NAMES` map | [`cases.js:40`](../app/static/cases.js) |
| Search placeholder naming IIM-A and ISB | [`cases.html:106`](../app/static/cases.html) |
| Relevance boost on `school === "MBB Core"` | [`cases.js:183`](../app/static/cases.js) |
| History meta line | [`profile.js:388`](../app/static/profile.js) |
| `school` in the API projection | `catalogue_item()` in [`case_runtime.py:129`](../app/case_runtime.py) |
| `school` on the manifest | [`models.py:195`](../app/models.py) |
| `school:` values | 57 `case.yaml` files |

Replace with a neutral `source` axis: `curated` for the existing 69, `community` for
contributed. That is also exactly the shelf separation Phase 3 needs, so the filter
slot stays useful rather than being removed and later re-added.

Left untouched by decision: `corpus/exemplars/{iima,iimb,iimc,isb}/` directory names,
`corpus/iima-consult-prep-book-2025-26/`, the source rights register, and git history.

### 4.4 Quant schema, defined now

Defined in this phase so the Phase 3 extraction agent captures quant from its first
run rather than requiring contributors to be re-interviewed later.

Cases without quant remain valid indefinitely. Phase 0 already makes an unassessed
quantitative dimension a correct outcome rather than a penalty.

- [x] `cases` table, versioning, `attempts.case_version` with a backfill migration
- [x] Catalogue registry with `register()`, `unregister()` and version pinning
- [x] `provenance` and `source` on `CaseManifest`; `ProvenanceModel`
- [x] `case_stats` with `times_attempted` / `times_completed`, merged into `/api/cases`
- [x] `QuantStep` / `QuantPackage` schema; `formula`, `depends_on`, `numeric_value` on `FactItem`
- [x] `app/expressions.py`: AST-walking evaluator, no `eval`, plus consulting-math grading
- [x] Institution removal across every user-visible surface
- [x] `source` filter replaces the School filter
- [x] All 69 authored cases load unchanged
- [~] `CATALOGUE` global replaced by `app.state.catalogue` — **not done, deliberately.** See below.

### 4.5 Deviation: the global stayed

The plan called for replacing the `CATALOGUE` module global across 13 call sites
with an `app.state` dependency, on the reasoning that "the seam does not exist
yet". That reasoning stopped being true once the registry became mutable.
`CATALOGUE` and `app.state.catalogue` are now the same object, and `register()`
mutates it in place, so both views are already consistent. Rewriting 13 call sites
would have been churn with no behavioural change.

What the refactor would still buy is test isolation, and that was solved more
cheaply: `tests/conftest.py` already rebinds the stores onto a throwaway database,
and `CaseStore` now joins them.

### 4.6 A real bug the tests surfaced

The first version of `reload_contributed_cases()` was add-only. Tests that
published a case leaked it into every later assertion on library size, which
looked like test hygiene but was not: an add-only reload means an admin
**unpublishing a broken case would not remove it from the library** until the next
restart, so the withdrawal button would quietly do nothing. That is the lever that
exists for a case found to be unsafe.

It now reconciles: community cases no longer in the published set are withdrawn.
Authored cases are never touched by this path, so an empty `cases` table cannot
empty the library.

### 4.7 Verified

- 69 cases load; `{'curated'}` is the only source; every item carries `version`,
  `times_attempted` and `times_completed`.
- No institution string appears anywhere in the serialized catalogue or in the
  rendered library page. A regression test asserts this against the whole payload
  rather than one field, since a name could return through a title or summary.
- An attempt started on version 1 still resolves to version 1 after version 2 is
  published, while the library shows version 2.
- A malformed contributed package is skipped with a logged exception and the other
  69 cases still serve.

Suite: 332 passing.

---

## 5. Phase 3: contribution engine. Complete.

### 5.1 Consulting math, and what it means for the schema

Research finding that changes the design: interviewers grade four things, and
arithmetic precision is the weakest of them.

1. **Structure before execution.** Can the candidate derive the approach, inputs and
   formula before multiplying?
2. **Controlled accuracy.** A correct or near-correct answer under time pressure.
3. **Narration.** Can they talk through the approach as they go?
4. **Business interpretation.** Turning the number into an insight. A breakeven of
   180,000 units means nothing until you say whether it is achievable.

The load-bearing detail: a candidate who slips, catches it on a sanity check, and
corrects calmly scores **higher** than one who grinds out a flawless number
mechanically. And aggressive rounding to keep arithmetic tractable is correct
professional behaviour, not a shortcut.

So `expected_value` with a 5% tolerance was wrong. The schema:

```yaml
schema_version: quant-v1
quant_steps:
  - id: quant.pharma-contribution
    release_level: hypothesis_backed
    intent: Candidate computes contribution margin per kg on pharma routes.
    kind: unit_economics       # market_sizing | breakeven | profitability
                               # growth | unit_economics | exhibit_read
    inputs: [economics.pharma-rate, operations.pharma-utilisation]
    formula: "rate_per_kg - (cost_per_km / (load_factor * capacity_kg))"
    expected_value: 0
    unit: INR per kg
    accuracy_bands:
      correct_magnitude: 0.5x to 2x of expected
      close: 0.8x to 1.25x of expected
    graded_behaviours:
      - states_formula_before_computing
      - names_assumptions_explicitly
      - rounds_deliberately
      - sanity_checks_plausibility
      - states_commercial_so_what
    interviewer_behaviour: >-
      Ask the candidate to set it up. Confirm or correct the setup.
      Never supply the arithmetic.
```

Arithmetic is evaluated in code, never by the model, through one shared safe
evaluator serving the validation gate, the derived-fact consistency check, and the
Phase 4 grader.

### 5.2 Extraction

Authenticated users only. Chat and voice, reusing the existing turn, streaming, and
voice-realtime paths.

**Phased, and open-ended first.** The agent does not start with a form.

1. **Narration.** Broad prompts, minimal interruption. Let them talk about the case
   for as long as they want. This is the phase that recovers the texture a form
   destroys.
2. **Structure.** Fill the manifest and objective function from what was said, asking
   only about genuine gaps.
3. **Quantification.** Magnitudes, ratios, and which quantities were in play. Not
   exact figures, which nobody remembers.
4. **Teeth.** Traps, pivotal insight, and the pushback they received. Hard-gated.
5. **Playback.** Read the reconstructed case back and let them correct it.

Structured output per turn, mirroring `DirectorDecision`:

```python
class ExtractionTurn(BaseModel):
    next_question: str
    fields_filled: dict[str, Any]
    completeness: float
    blocking_gaps: list[str]
    phase: str
    ready_to_synthesize: bool
```

**Threshold gate.** Submission opens at a weighted evidence score of **0.70**, but
only when three non-negotiable anchors came from the contributor:
`client_and_industry`, `decision_question`, and `core_mechanism`. Those anchors
total 0.60, so at least one meaningful piece of texture must also be captured,
such as the situation, pivotal insight, traps, quantities, or what the case
tested. Missing pivotal insight, extra traps, exact numbers, and takeaway are
recoverable in the synthesis pass. Recalled versions are still preferred, so the
single highest-value follow-up remains some form of *"what did you say that the
interviewer pushed back on?"*

Since cost is not a constraint, the agent should be materially pushier than the case
interviewer: more turns, more follow-ups, more willingness to circle back.

### 5.3 Validation gate

`app/case_validator.py`, automatic on submission. Six checks:

1. **Schema.** Pydantic parse of the full `CasePackage`.
2. **Dependency DAG.** No cycles; every dependency ID exists.
3. **Reachability.** Every fact's `release_level` appears in some phase's
   `reveal_levels`. Catches an authored fact that can never be released, which is
   currently undetectable.
4. **Arithmetic closure.** Recompute derived facts and quant expected values from
   their formulas. Code, not model.
5. **Solve it cold.** Headless attempt through the existing runtime with an LLM
   candidate, checking it reaches `core_mechanism` from released facts alone. Doubles
   as a difficulty meter: solved in three turns with no probing means too easy.
6. **Safety.** PII scan and real-company-name check. Contributed cases are re-skinned
   by synthesis rather than published verbatim, which is the defensible position on
   recalled interview content and should be explicit policy.

### 5.4 Review

`draft → submitted → validated → needs_changes | published`.

Admin review is **mandatory and has no bypass in this scope.** Nothing reaches
`published` without explicit approval. The admin console at
[`app/admin.py`](../app/admin.py) and `admin.html` is the surface to extend: queue,
full package view, validation report, solve-it-cold transcript, approve or return
with notes.

Published contributed cases appear under `source: community`, visibly distinct from
curated.

### 5.5 Guards

Cost is not a constraint, so no daily caps. Still needed:

- One concurrent contribution session per user, against runaway loops.
- Hard turn ceiling with graceful save-as-draft, so a stuck session ends cleanly.
- Token budget per session wired through [`app/llm_budget.py`](../app/llm_budget.py),
  for observability rather than restriction.

- [x] `contribution_sessions` table with a one-live-session-per-user partial index
- [x] `app/case_author.py`: five-phase extraction, `ExtractionTurn`, accumulating merge
- [x] Hard gates on mechanism, insight, traps, decision question, enforced in code
- [x] `app/case_synthesis.py`: re-skinning synthesis producing a full package
- [x] `app/case_validator.py`: five deterministic checks
- [x] `app/case_solver.py`: headless solve-it-cold harness, run on demand
- [x] Admin review queue, publish / return / withdraw, blocking-error refusal
- [x] Community source shown in the library
- [x] Concurrency guard and turn ceiling
- [x] Contribution page, thread UI, progress track, explicit save/resume and atomic restart
- [ ] Voice path reusing voice-realtime — **deferred.** See below.

### 5.6 What is not done

**The voice path.** The plan called for chat and voice from the start. Chat
shipped; voice did not. The extraction loop is transport-agnostic by design
(`ExtractionState` in, `ExtractionState` out, no assumption about how the message
arrived), so wiring `voice-realtime` to it is additive rather than a rework. It
was left out because the chat path needed to be proven end to end first, and
because a forty-turn spoken conversation is a different reliability problem from
a forty-turn typed one.

### 5.6b Reported defect: a Submit button that refused itself

A contributor reached a Submit button, clicked it, and was told five schema
fields were missing that they had never been asked about. Three separate defects,
all the same shape: something trusted a claim instead of the fact.

**1. The button was never hidden at all.** `.btn { display: inline-flex }` in
`tokens.css` is a class selector, so it outranks the user agent's
`[hidden] { display: none }`. Every `hidden` attribute in the contribute page was
decorative, including on the composer. `[hidden] { display: none !important }` is
now defined globally, because this is a whole-app footgun and not specific to one
page. A test asserts the rule exists, since without it the fix is a one-line CSS
change nothing would notice being reverted.

**2. Readiness was read back from storage rather than derived.** The extraction
agent can set `ready_to_submit`, and the view returned it verbatim. It is now
computed as `stored AND no gaps`, so a disagreement between the flag and the gap
list always resolves to "not ready". This is what produced the "that is
everything" line while five fields were empty.

**3. Gaps were named by schema identifier.** A contributor cannot answer for
`core_mechanism`. Every human-facing gap now goes through `describe_missing`, and
the server owns the phrasing so the progress line and any refusal message cannot
drift apart.

**And the behaviour change underneath.** The agent used to be free to wander,
summarise, and declare itself finished with fields empty. The runtime now picks
one gap at a time in conversational order, names it in the prompt with a concrete
question to ask, and requires the answer be recorded. `field_attempts` counts asks
that captured nothing, and after two the instruction becomes more direct. Once
the synthesis threshold is reached, the contributor is also reminded that they
may stop and let Leo complete recoverable detail. That state is durable, so a
reload does not restart the escalation.

**4. Model prose could still contradict runtime state.** Hiding the Submit button
did not stop the agent from saying thank you and ending the conversation while
gaps remained. Every extraction reply now passes through
`enforce_conversation_state`: if the state is not ready and the proposed reply is
a closing statement or a vague "anything else?", the runtime replaces it with a
sharp question for the next required gap. Once the weighted threshold and anchors
are satisfied, a closing statement instead offers the explicit choice to submit
now or keep answering for higher fidelity. The former 60-turn API hard stop was
removed because it could leave a still-incomplete session with neither a question
nor a valid submission path.

**5. Leaving and restarting are explicit states.** Every active composer shows
**Save & resume later**, which persists both the extracted conversation and any
unsent textarea draft before leaving. Returning to `/contribute` restores both.
**Start again** requires confirmation, atomically marks the old session
`abandoned`, and creates one clean live replacement, preserving the one-live-
session database invariant.

**6. The gate is inspectable.** A collapsible **Completion criteria (temporary
tracker)** view sits inside the progress card and is fed by the same server-owned
ledger as the submit endpoint. It lists all eight weighted evidence fields, their
current captured/partial/missing status and contribution to the score. It marks
the three mandatory submission anchors separately from supporting evidence, and
also identifies the five fields required to call the recollection fully
reconstructed. This makes the distinction explicit: 70% plus anchors is ready to
submit; client, decision, mechanism, pivotal insight and two traps is complete.

### 5.7 Design decisions worth recording

**The runtime, not the prompt, decides when a contributor may submit.**
`advance_phase`, the contributor view, and the submit endpoint all use the same
weighted threshold plus anchor rule. The model cannot expose submission early,
but missing recoverable enrichment no longer blocks a contributor who has given
enough to build a credible case.

**Narration has a floor, not just a ceiling.** Three turns minimum before the
agent may move on. An agent optimising for progress will otherwise cut short the
one phase that produces the texture a form destroys.

**The merge accumulates.** A patch adding one trap must not discard the two
already captured, and a patch that omits a field means "nothing new this turn",
not "erase it". Both were live bugs in the first draft of the merge.

**Provenance is truncated, not rejected.** A contributor who gives `2026-07-14`
has the day dropped and the month kept, because a full date plus a firm plus a
round is close to identifying, and rejecting the value outright would lose the
recency signal the whole feature rests on.

**Arithmetic is decided in code.** `app/expressions.py` serves the validator and
will serve the Phase 4 grader. No model is ever asked whether a sum is correct.

**Re-skinning is enforced, not assumed.** The synthesis prompt asks for an
invented client and the safety check rejects a package that still names a real
organisation, so the defensible position on recalled interview content holds
mechanically rather than by good intentions.

Contribution suite: 63 passing. Full suite on 2026-08-31: 424 passing with one
unrelated existing practice-room timer assertion failing in
`tests/test_case_progress.py`.

---

## 6. Deferred

**Phase 4, quantitative runtime.** Exhibits with gated release, an exhibit tray,
`request_calculation`, `quant_state` on the session, the scratchpad
(`session_contract.scratchpad` is currently disabled everywhere), and grading the
quantitative dimension from `quant_state` instead of from prose. Until this lands,
quant steps collected by the extraction engine are stored but inert. That is
intentional, and it is why the schema comes first.

**Phase 5 and beyond, by decision.** Reactions and likes, suggested edits, comments,
the solver leaderboard, and the contributor leaderboard. Notes worth keeping for
when they return:

- Ranking on raw like count is rich-get-richer and buries fresh cases, which
  contradicts the recency thesis. Use like rate with a prior plus a guaranteed-exposure
  new shelf.
- A solver board must rank first-attempt scores, segment by persona, and pin the
  evaluator version, or it is gameable and unstable.
- A contributor board must rank on reach and quality, not published count.
- Comments are a spoiler surface and should be visible only post-completion.

---

## 7. Open risks

**Contribution supply is still unvalidated.** The engine assumes people will spend
thirty to forty minutes in an extraction interview. Testable by hand this week with
no code, and it determines whether Phase 3 is worth building.

**Bland is the failure mode, not broken.** The gate catches inconsistency; it cannot
catch a case with no teeth. The hard-gated traps and pivotal insight are the only
real defence and should not be relaxed to improve submission conversion.

**Admin review is a throughput ceiling.** With no auto-publish path, contribution
volume is bounded by Shubham's review time. Fine at low volume, and the deferred
reaction signal is what eventually lifts it.

**Persona tuning is empirical.** The release rates are a starting point. Whether the
Skeptic reads as hard or as broken can only be settled by running it.
