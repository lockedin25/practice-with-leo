# Question-Led Case Contribution Architecture

Status: proposed for approval on 2026-08-31. This supersedes the earlier phase-based plan. No application code has been changed.

## 1. Architectural decision

Case contribution and case practice are different products.

| Case practice | Case contribution |
|---|---|
| Simulates an interviewer | Extracts a remembered case accurately |
| Preserves uncertainty and lets the candidate explore | Drives directly toward missing information |
| Releases facts according to candidate actions | Asks for one defined piece of information at a time |
| Benefits from an organic, sometimes open-ended conversation | Benefits from short, sharp, completion-oriented questions |
| State is candidate progress through a case | State is evidence collected against a question catalogue |

They may share authentication, HTTP infrastructure, an LLM provider, transcript rendering, and the broad idea of a conversational agent. They must not share prompts, phase logic, disclosure rules, interview-director state, or question-selection behavior.

The current five-phase authoring loop will therefore be retired. Contribution will have a new question-led engine designed around one invariant:

> At any moment, Leo is trying to resolve exactly one active question from a ranked catalogue.

## 2. User-visible behavior

1. Leo asks for an overview once.
2. The answer is assessed and every supported fact is recorded.
3. Leo selects the highest-priority unresolved mandatory question.
4. Leo frames one context-aware question for that target.
5. The user answers.
6. Leo first decides whether that active question is completely answered.
7. If complete, Leo commits the answer, updates progress, and moves to the next unresolved question.
8. If incomplete, Leo keeps the same active question and asks a narrower clarification.
9. Once all mandatory questions are complete and progress reaches 70%, Leo exits the forced collection loop and enables submission.
10. The contributor may submit immediately or explicitly choose to improve fidelity through non-mandatory questions.

There is no minimum narration-turn count. Repetition happens only when a specific active question remains incomplete.

## 3. Ranked question catalogue

Questions, not phases, are the durable units of work. Each question definition contains:

- stable `question_id` and catalogue version;
- tier and rank;
- fields and facets it is trying to collect;
- mandatory or optional status;
- progress weight;
- dependencies and applicability rules;
- a deterministic completion rule;
- first-ask and retry guidance for the question-framing agent;
- whether `cannot recall` is allowed to resolve the question; and
- whether synthesis may fill the missing information later.

### Tier 0: Overview

| ID | Purpose | Weight | Completion rule |
|---|---|---:|---|
| `overview` | Let the contributor describe the case once in their own words | 0% directly | A coherent case recollection is present; any fields found receive their own weight |

The overview is a routing question, not a narration phase. It can populate any mandatory or optional criterion. If it already provides the full mandatory skeleton, submission can become available after this first answer.

### Tier 1: Mandatory case skeleton

| Rank | Question | Criteria | Weight | Complete when |
|---:|---|---|---:|---|
| M1 | Case setting | client and industry 15% + initial situation 10% | 25% | We know who the generic client is, what business they are in, and the problem presented |
| M2 | Decision objective | decision question | 20% | We know what the interviewer wanted decided, diagnosed, or explained |
| M3 | Core mechanism | underlying driver | 25% | We know the cause beneath the symptom and how it produced the observed outcome |

The mandatory skeleton totals exactly 70%. This makes the headline progress meaningful: reaching 70% means the minimum reconstructable case is present and submission is available.

### Tier 2: Optional fidelity

| Rank | Question | Criteria | Weight | Special rule |
|---:|---|---|---:|---|
| N1 | Turning-point insight | pivotal insight | 10% | May be synthesized after submission |
| N2 | Plausible wrong paths | two traps | 10% | One trap is partial; two resolves it |
| N3 | Numbers and magnitudes | quantities | 5% | “There were no numbers” is a valid resolution |
| N4 | What the case tested | tested skill or lesson | 5% | May be synthesized after submission |

Unweighted metadata such as time horizon, primary metric, information given upfront, information the candidate had to request, interviewer pushback, firm, round, geography, and month is extracted opportunistically from every answer. It does not delay submission.

### Selection rules

The next-question selector is deterministic:

1. If the active question is incomplete, keep it active.
2. Otherwise choose the lowest-ranked unresolved mandatory question.
3. If all mandatory questions are complete, enter `submission_ready` and select no question.
4. Only after the user chooses **Improve fidelity** does Leo select optional questions.
5. Within optional questions, use catalogue rank, skip already-resolved questions, and apply relevance rules such as asking about quantities only when the recollection suggests numbers were involved.

The LLM does not decide whether it would prefer to discuss a different topic.

## 4. New contribution domain model

The flat extracted-case object and model-owned phase will be replaced by a question ledger with evidence provenance.

```text
ContributionSessionState
├── schema_version
├── question_catalog_version
├── mode: collecting | submission_ready | improving | submitted
├── active_question_id
├── progress_score
├── question_states: question_id -> QuestionState
├── fact_ledger: FactRecord[]
├── case_draft: ContributionCaseDraft
├── transcript: ContributionTurn[]
└── draft_text

QuestionState
├── status: not_started | in_progress | complete | unavailable
├── attempts
├── completed_facets
├── missing_facets
├── working_answer
├── resolved_answer
└── source_turn_ids

FactRecord
├── field
├── normalized_value
├── evidence_quotes
├── source_turn_id
├── source_question_id
└── status: accepted | superseded
```

### Why this storage model

- Partial answers are not lost. They accumulate in `working_answer` while the active question remains open.
- A question is not marked complete merely because some text was extracted.
- Every stored fact points to the exact contributor turn and evidence that supports it.
- Corrections supersede earlier facts instead of silently overwriting them.
- Progress can be recomputed from resolved criteria rather than trusted as stored LLM opinion.
- The final case draft is a projection of accepted facts, not an untraceable rolling summary.

The existing `contribution_sessions` row and its atomic `state_json` column can remain as the persistence container. Its internal payload is replaced with this new versioned model. This keeps session lifecycle, one-live-session enforcement, pause, reset, and ownership separate from practice attempts without introducing unnecessary database infrastructure.

## 5. Agent architecture

Contribution uses two narrow LLM roles behind a deterministic orchestrator.

```text
                         USER RESPONSE
                              |
                              v
                   +---------------------+
                   |  Answer Assessor    |
                   | active question only|
                   +----------+----------+
                              |
                       structured result
                              |
                              v
                   +---------------------+
                   | Contribution Engine |
                   | evidence validation |
                   | completion rules    |
                   | storage + progress  |
                   | next-question rank  |
                   +----------+----------+
                              |
                    incomplete | complete
                    same target| next target / ready
                              v
                   +---------------------+
                   |  Question Framer    |
                   | context-aware words |
                   | fixed target/facets |
                   +----------+----------+
                              |
                              v
                     ONE SHARP QUESTION
```

### Answer Assessor

The assessor receives:

- the active question definition;
- its currently completed and missing facets;
- the accumulated working answer;
- relevant accepted case facts;
- recent attempts for this question; and
- only the latest user response as new evidence.

It returns structured data:

```text
question_id
verdict: complete | partial | not_answered | cannot_recall
facet_updates[]: facet_id, normalized_value, evidence_quotes
other_field_updates[]: field, normalized_value, evidence_quotes
missing_facets[]
contradictions[]
```

The assessor never chooses the next question and never writes directly to session state.

### Deterministic evidence and completion gate

Before storing any update, runtime code will:

1. Reject an assessment for any question other than `active_question_id`.
2. Reject unknown fields and facets.
3. Require every evidence quote to occur in the latest response after whitespace and case normalization.
4. Reject normalized values with no supporting latest-response quote.
5. Store supported facts about other questions opportunistically.
6. Evaluate the active question's completion rule from accumulated accepted facets.
7. Treat model `complete` as advice only; if a required facet is still absent, the question remains incomplete.
8. Detect explicit corrections and supersede the old fact with an auditable replacement.

### Question Framer

The framer receives a fixed question ID and objective from the engine, plus:

- accepted conversational context;
- only the missing facets;
- the last unsuccessful answer;
- the number and style of previous attempts; and
- first-ask or retry instructions from the catalogue.

It returns `question_id`, `target_facets`, and one question. Runtime rejects output that changes the question ID, targets already-complete facets, asks multiple questions, or closes the conversation.

If framing fails, a reviewed deterministic question template is used. An accepted answer can therefore never leave the session without a next question or a submit state.

The clean implementation uses one assessor call and, when another question is required, one framer call. The roles remain separate even if a later optimization uses a faster model for framing.

## 6. The incomplete-answer loop

```text
ACTIVE QUESTION Q
       |
       v
User responds
       |
       v
Assess against Q only
  | complete              | partial / unrelated
  v                       v
Resolve Q          Store supported partial facts
Update progress    Keep Q active
Select next        Increment Q attempts
  |                       |
  v                       v
Next Q / ready     Ask only for missing facet(s)
```

Retry behavior is driven by the actual gap:

- First ask: clear question covering the unresolved criterion.
- Partial answer: acknowledge the captured part and ask only for the missing facet.
- Unrelated answer: briefly redirect and repeat the same objective more concretely.
- Repeated difficulty: provide a contrast or example of the type of answer needed without suggesting case content.
- `Cannot recall` on a mandatory question: request the safest generic approximation because submission cannot proceed without it.
- `Cannot recall` on an optional question: mark it unavailable and move on.

There is no arbitrary retry count and no general narration loop. The loop ends only when the question is complete, optional information is explicitly unavailable, or the session reaches `submission_ready`.

## 7. Progress and submission

Progress is recomputed after every accepted response:

```text
resolved client/industry     15%
resolved situation           10%
resolved decision            20%
resolved mechanism           25%
resolved turning point       10%
resolved two traps           10%
resolved quantities           5%
resolved tested skill         5%
                              ----
                              100%
```

Rules:

- An unresolved field earns no full credit.
- A multi-part question may show `in progress`, while resolved underlying criteria contribute their own weight.
- The headline score and item statuses update in the same response that commits evidence.
- Submission requires all mandatory questions complete and a score of at least 70%.
- When this gate is reached, the engine sets `mode = submission_ready`, clears `active_question_id`, and does not force another question.
- The UI shows **Submit this case** and **Improve fidelity**.
- Choosing **Improve fidelity** sets `mode = improving` and starts the optional hierarchy.

Because the mandatory skeleton totals 70%, the UI does not need a confusing state where it displays 70% but submission remains blocked.

## 8. API and UI contract

Every turn response is one atomic projection of saved state:

```text
mode
active_question: {id, label, tier, attempt, missing_facets} | null
progress_score
can_submit
question_tracker[]
evidence_tracker[]
messages[]
next_message
```

The old five-stage strip will be replaced by a hierarchy tracker:

```text
Overview                    Complete

Must have                   70%
  Case setting              Complete / In progress / Missing
  Decision objective        Complete / In progress / Missing
  Core mechanism            Complete / In progress / Missing

Improve fidelity            30%
  Turning point             ...
  Wrong paths               ...
  Numbers                   ...
  What it tested            ...

Current focus: Core mechanism
Still needed: why that driver caused the reported outcome
```

The tracker, current-focus label, transcript question, score, and submit controls are rendered from the same server response. The browser does not infer stages or maintain a parallel progress state.

## 9. Code boundaries

The contribution implementation should be separated into a small domain package:

```text
app/contribution/
├── catalogue.py   # question definitions, ranking, weights, completion rules
├── models.py      # session, question state, fact ledger, draft, assessments
├── agent.py       # assessor and question-framer LLM adapters/prompts
└── engine.py      # deterministic turn orchestration and invariants
```

Integration boundaries:

- `app/main.py` calls the contribution engine and returns its projection.
- `app/store.py` persists the versioned contribution state atomically.
- `app/case_synthesis.py` receives a clean `ContributionCaseDraft` snapshot through an adapter; it does not read conversational state.
- `app/static/contribute.js` and `app/templates/contribute.html` render the new tracker and ready/improve actions.
- The old `app/case_author.py` phase engine is removed after legacy-session migration is covered.

Nothing in `app/interviewer.py`, practice attempt state, fact-release policy, evaluator flow, or practice-room prompt participates in contribution decisions.

## 10. Legacy-session migration

Existing unfinished contribution sessions will be upgraded on load:

1. Preserve transcript and unsent draft.
2. Map each existing extracted field into an accepted legacy fact record.
3. Recompute question statuses and progress from those facts.
4. Select the highest-priority unresolved mandatory question.
5. Discard the old phase and phase-turn count.
6. Persist the new schema on the next successful save.

Legacy facts are marked `source = legacy_contributor_state`; new facts require turn-level evidence quotes.

## 11. Failure modes and recovery

| Failure | Behavior |
|---|---|
| Assessor invents a fact | Evidence gate rejects it; active question remains unchanged |
| User answers another question | Supported facts are stored; active question stays locked until complete |
| User answers several questions at once | Store all supported facts; complete the active question; selector skips anything already resolved |
| User partially answers | Store partial facets, show `in progress`, ask only for missing facets |
| User corrects an earlier answer | Supersede the old fact and recompute affected question states and progress |
| Assessor call fails | Store nothing; preserve the user's text in the composer and allow retry |
| Framer call fails after a valid answer | Use deterministic fallback wording for the already-selected question |
| Model asks multiple questions | Reject and use the single-question fallback |
| Two mandatory facts conflict | Keep the affected question active and ask a direct reconciliation question |
| Old session has an impossible phase | Ignore phase and reconstruct state from accepted fields |

## 12. Test and evaluation plan

### Deterministic unit tests

- Question catalogue totals 100%; mandatory questions total 70%.
- Overview is always first and is never held for a fixed number of turns.
- Incomplete active question remains selected regardless of other extracted facts.
- Mandatory questions always outrank optional questions.
- All mandatory questions complete transitions immediately to `submission_ready`.
- Optional questions start only through **Improve fidelity**.
- Evidence quotes must occur in the latest response.
- Unsupported and unknown field updates are rejected.
- Partial facets accumulate without marking the question complete.
- Multiple fields from one response are stored and later questions are skipped.
- Corrections supersede facts and can reduce/recompute progress safely.
- `cannot_recall` differs for mandatory and optional questions.
- A framing failure produces a deterministic single-question fallback.
- Legacy state migrates without losing transcript, facts, draft, or readiness.

### API and persistence tests

- Starting a contribution returns `overview` as the active question.
- Each turn saves assessment, fact ledger, question status, progress, and next question atomically.
- Reload resumes the exact active question and missing facets.
- Pause/reset behavior remains intact with the new state.
- Submission is rejected below the mandatory 70% gate and accepted at the gate.
- The returned `active_question` always matches the final Leo message.
- A failed assessor does not persist the user turn or increment attempts.

### LLM evaluations

Create separate evaluation fixtures for the two prompts.

Assessor cases:

- direct complete answer;
- paraphrased complete answer;
- partial answer;
- unrelated but useful answer;
- several questions answered at once;
- explicit uncertainty;
- correction of an earlier fact;
- invented model field with no evidence;
- answer containing identifying information that must not be stored.

Framer cases:

- first mandatory ask;
- narrow retry for one missing facet;
- redirect after an unrelated answer;
- repeated difficulty without leading the contributor;
- one question only;
- no schema names, multi-part interrogations, closing thanks, or topic switching.

### End-to-end acceptance flows

1. Rich overview completes all mandatory criteria and immediately enables submission.
2. Thin overview enters M1, loops on its missing facet, then advances to M2.
3. An answer to M1 also contains M2; M1 remains active if incomplete, then M2 is skipped once M1 resolves.
4. M1, M2, and M3 resolution updates progress to 25%, 45%, and 70% respectively and exposes submit.
5. **Improve fidelity** continues to 80%, 90%, 95%, and 100% without making those questions compulsory.
6. Refreshing at every point preserves the current question, missing facets, partial evidence, and score.

## 13. Implementation sequence

1. Add the new question catalogue and domain-state tests.
2. Implement versioned models, evidence ledger, completion rules, progress calculation, and legacy adapter.
3. Implement the deterministic engine and its selection/transition tests.
4. Implement and evaluate the Answer Assessor.
5. Implement and evaluate the Question Framer plus deterministic fallbacks.
6. Integrate the engine with contribution endpoints and persistence.
7. Adapt synthesis to consume the canonical contribution draft.
8. Replace the phase UI with the hierarchy/current-focus tracker and submit/improve split.
9. Run contribution unit/API/eval tests, the full application suite, and manual browser QA across desktop and mobile.
10. Remove the old phase engine only after legacy migration and end-to-end tests pass.

Implementation should be sequential. Catalogue and state contracts determine the engine; the engine determines API and UI contracts. Parallelizing these files before those contracts settle would create disagreement at exactly the boundaries this design is meant to fix.

## 14. NOT in scope

- Reusing practice-room prompts, case-release logic, or interview phases.
- Voice contribution before the text question loop is proven.
- Automatic publication without human review.
- Embeddings, retrieval, or a general workflow framework.
- A second progress metric that can disagree with submission readiness.
- Model-selected topic changes outside the ranked catalogue.
- Optimizing back to one LLM call before assessor and framer quality is measured.

## 15. Approval gate

No application implementation should begin until this replacement architecture is approved or revised.
