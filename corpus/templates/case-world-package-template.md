---
# Parsed only by the private content compiler. Candidate clients receive only the
# opening brief and individual facts released during the attempt.
case_id: example-original-profitability-001
title: Example original profitability case
package_type: case_world
status: draft
rights_status: original
source_case_ids: []
category: profitability
industry: consumer_goods
difficulty: foundation
target_duration_minutes: 30
simulation_modes:
  - coached
  - realistic
  - pressure
version: 1
---

# {{title}}

## Candidate briefing

Write the short opening statement the interviewer says before any questions. It
states the client, decision, and initial scope only. It must not reveal the
diagnosis, target branch, or answer-key language.

## World contract

| Field | Value |
|---|---|
| Client decision | What must the client decide or diagnose? |
| Objective | Which outcome matters? |
| Time horizon | What period or deadline constrains the decision? |
| Candidate deliverable | Recommendation, evidence, risk, and next step |
| Source route | Link to the source transcript, if applicable |
| Core diagnosis | Private one-line answer-key statement |

## Knowledge ledger

> Each fact is atomic. Do not mix source facts, computed implications, and
> original scenario details in one entry. `value` can be qualitative. `depends_on`
> lists fact IDs that must already be disclosed or true.

### fact: client-objective

```yaml
id: client-objective
provenance: source # source | derived | scenario | interviewer_assumption
source_ref: internal-original # use source_case_id + PDF pages for licensed material
entity: client
topic: objective
value: "Replace with approved fact"
units: null
period: current
release_policy: opening # opening | on_targeted_question | on_hypothesis | on_calculation_request | interviewer_probe | never_candidate_visible
release_triggers:
  - objective
  - success_metric
depends_on: []
consistent_with: []
candidate_wording: "Natural concise response the interviewer may say."
author_rationale: "Why this fact matters to the candidate's next decision."
```

### fact: optional-scenario-detail

```yaml
id: optional-scenario-detail
provenance: scenario
source_ref: null
entity: market
topic: competitor_benchmark
value: "Original, plausible scenario detail"
units: percent
period: current
release_policy: on_hypothesis
release_triggers:
  - candidate compares client with competitors
depends_on:
  - client-objective
consistent_with:
  - market-size
candidate_wording: "Approved spoken response, without falsely attributing it to a source."
author_rationale: "Answers a likely natural question and supports the intended test."
```

## Derived calculations

> Keep calculations private until the candidate has tried the setup. A derived
> result is not a new source fact.

### calculation: example-unit-economics

```yaml
id: example-unit-economics
inputs:
  - annual_volume
  - price_per_unit
  - variable_cost_per_unit
formula: "annual_volume * (price_per_unit - variable_cost_per_unit)"
result: "Private expected result"
tolerance: "State rounding rule"
release_policy: on_calculation_request
common_errors:
  - "Forgets to subtract variable cost"
interviewer_recovery: "Ask the candidate to state the equation before correcting it."
```

## Case graph

> Nodes are capabilities or learning milestones, never a forced sequence of
> questions. `advance_when` defines what sufficient evidence looks like.

### milestone: establish-objective

```yaml
id: establish-objective
required: true
goal: "Candidate understands the client decision and success metric."
entry_conditions: []
advance_when:
  - "Candidate accurately restates the problem and scope."
relevant_fact_ids:
  - client-objective
allowed_interviewer_moves:
  - answer
  - invite
  - probe
recovery_prompt: "What would you want to clarify before you structure the problem?"
next_milestones:
  - clarify-context
  - candidate-structure
```

### milestone: candidate-structure

```yaml
id: candidate-structure
required: true
goal: "Candidate produces a tailored and prioritised approach."
entry_conditions:
  - establish-objective
advance_when:
  - "Candidate states a causal issue tree, equation, or analytical plan."
  - "Candidate explains which branch they will test first and why."
relevant_fact_ids: []
allowed_interviewer_moves:
  - invite
  - probe
  - nudge
  - redirect
recovery_prompt: "Which driver would be most likely to change the client's decision?"
next_milestones:
  - prioritised-deep-dive
```

### milestone: prioritised-deep-dive

```yaml
id: prioritised-deep-dive
required: true
goal: "Candidate investigates the key driver and updates their hypothesis."
entry_conditions:
  - candidate-structure
advance_when:
  - "Candidate interprets relevant facts, an exhibit, or a calculation."
  - "Candidate links the insight to the client decision."
relevant_fact_ids:
  - optional-scenario-detail
allowed_interviewer_moves:
  - answer
  - probe
  - challenge
  - nudge
  - redirect
recovery_prompt: "Where would you look for the largest gap before exploring the rest?"
next_milestones:
  - synthesis
```

### milestone: synthesis

```yaml
id: synthesis
required: true
goal: "Candidate gives a decision-oriented recommendation."
entry_conditions:
  - prioritised-deep-dive
advance_when:
  - "Candidate gives an answer, supporting evidence, risk, and next step."
relevant_fact_ids: []
allowed_interviewer_moves:
  - challenge
  - close
recovery_prompt: "Please give your recommendation first, then the evidence, risk, and next step."
next_milestones: []
```

## Retrieval map

| Candidate intent | Matching facts or action | Constraint |
|---|---|---|
| Objective or scope clarification | `client-objective` | Concise answer; do not reveal the diagnosis. |
| Relevant comparison or data request | Approved fact ID(s) | Release only when dependencies are met. |
| Calculation request | Calculation ID | Candidate states setup before help. |
| Missing but reasonable question | Scenario fact ID or bounded assumption | Must be pre-authored and provenance-labelled. |
| Premature/unproductive branch | `redirect` | Preserve candidate agency and explain the priority. |
| Stalled on core driver | `nudge` | Use the nudge ladder, least revealing first. |

## Interviewer policy

### Style

- Respond naturally and briefly, as a professional interviewer would.
- Let the candidate lead the structure. Do not demand a memorised framework.
- Ask for reasoning after each meaningful data release.
- Keep a live record of disclosed facts and candidate claims.

### Nudge ladder

1. Ask the candidate to prioritise or state their hypothesis.
2. Point to the relevant analytical level, not the answer.
3. Ask a focused diagnostic question.
4. In `coached` mode only, disclose the missed direction and resume the case.

### Prohibited behaviour

- Do not reveal a future fact, answer key, source approach sheet, or exact source
  dialogue simply because the candidate asks broadly.
- Do not invent a fact at runtime. Use only a ledger fact or a clearly bounded
  interviewer assumption.
- Do not punish a different but valid route to the diagnosis.

## Evaluation map

| Competency | Strong evidence | Weak evidence | Capture |
|---|---|---|---|
| Clarification | Asks questions that materially change the approach | Repeats opening facts or requests low-value detail | Turn IDs and released facts |
| Structure | Tailored, causal, prioritised plan | Generic bucket list without priority | Candidate structure summary |
| Analysis | Correct setup, insight, and hypothesis update | Unexplained calculation or data recital | Calculation/exhibit turn |
| Judgement | Weighs trade-offs and risks | Presents one answer as certain | Challenge response |
| Synthesis | Recommendation, evidence, risk, next step | Repeats analysis without a decision | Final response |

## Consistency checks

- [ ] Every source fact has a page/source reference.
- [ ] Every scenario fact has an author rationale and no false source attribution.
- [ ] Every derived calculation names its inputs and formula.
- [ ] No fact is released before its dependencies are met.
- [ ] At least two valid analytical routes can reach every required milestone.
- [ ] A strong, alternate-valid, and stuck-recovery conversation have been simulated.
- [ ] Candidate-visible wording contains no answer-key language.
