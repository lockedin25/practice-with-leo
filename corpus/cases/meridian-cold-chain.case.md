---
case_id: original-profitability-meridian-001
title: Meridian Cold Chain
package_type: case_world
status: draft
rights_status: original
source_id: internal-original
attribution: CaseCall original case
source_case_ids: []
category: profitability
industry: logistics
difficulty: foundation
supported_durations:
  - 30
simulation_modes:
  - coached
  - realistic
  - pressure
skills_tested:
  - clarification
  - tailored structure
  - unit economics
  - exhibit interpretation
  - synthesis
version: 1
---

# Meridian Cold Chain

## Candidate briefing

Your client is Meridian Cold Chain, an Indian temperature-controlled logistics operator. It moves packaged food and pharmaceutical products for manufacturers across the country. Revenue has grown steadily for two years, but the board is unhappy: EBITDA margin has fallen from about 18 percent to about 11 percent over the same period. The CEO has asked you to find out why, and to tell her what to do about it.

## World contract

```yaml
decision_question: "Why has Meridian's EBITDA margin fallen from 18 to 11 percent, and what should the CEO do in the next twelve months?"
success_metric: "EBITDA margin percentage"
time_horizon: "Two years of history, a twelve-month action plan"
deliverable: "Recommendation, supporting evidence, main risk, and a concrete next step"
```

## Knowledge ledger

### fact: objective-metric

```yaml
provenance: scenario
source_ref: null
entity: client
topic: objective
value: "Margin is EBITDA margin; the board wants a twelve-month plan"
units: null
period: current
release_policy: opening
stages:
  - opening
depends_on: []
consistent_with: []
author_rationale: "Removes an ambiguity that would otherwise waste the candidate's first question."
```

### fact: cost-side-not-revenue

```yaml
provenance: scenario
source_ref: null
entity: client
topic: scope
value: "Revenue grew about 20 percent; the gap is on cost per unit, not price"
units: percent
period: last_two_years
release_policy: on_targeted_question
stages:
  - clarification
  - structure
  - analysis
depends_on: []
consistent_with:
  - segment-mix
author_rationale: "Answers the first branch most candidates test and narrows the case without naming the driver."
```

### fact: segment-mix

```yaml
provenance: scenario
source_ref: null
entity: client
topic: segment_mix
value: "Food fell from 95 to 70 percent of volume; pharma grew from 5 to 30 percent"
units: percent
period: last_two_years
release_policy: on_targeted_question
stages:
  - clarification
  - structure
  - analysis
depends_on: []
consistent_with:
  - cost-side-not-revenue
author_rationale: "The pivotal scoping fact. Released on a segment question because that is the question that earns it."
```

### fact: no-one-offs

```yaml
provenance: scenario
source_ref: null
entity: client
topic: accounting
value: "No acquisitions, impairments or one-off charges"
units: null
period: last_two_years
release_policy: on_targeted_question
stages:
  - clarification
  - analysis
depends_on: []
consistent_with: []
author_rationale: "Closes a reasonable but low-value branch quickly so the case keeps moving."
```

### fact: geography-neutral

```yaml
provenance: scenario
source_ref: null
entity: client
topic: geography
value: "Pan-India; no single region explains the change"
units: null
period: current
release_policy: on_targeted_question
stages:
  - clarification
  - analysis
depends_on: []
consistent_with: []
author_rationale: "Another plausible branch that should be closed rather than explored."
```

### fact: competitor-benchmark

```yaml
provenance: scenario
source_ref: null
entity: market
topic: competitor_benchmark
value: "Food-only competitors held margins over the same period"
units: null
period: last_two_years
release_policy: on_hypothesis
stages:
  - clarification
  - analysis
depends_on: []
consistent_with:
  - segment-mix
author_rationale: "Confirms the problem is client-specific and points at the new segment without naming the mechanism."
```

### fact: segment-economics

```yaml
provenance: scenario
source_ref: null
entity: client
topic: unit_economics
value: "Per-kilogram revenue, cost and contribution by segment"
units: inr_per_kg
period: current
release_policy: on_hypothesis
stages:
  - analysis
  - exhibit_review
depends_on:
  - segment-mix
consistent_with:
  - cost-side-not-revenue
author_rationale: "The central exhibit. Gated on the candidate reaching for unit economics, which is the insight that matters."
table_columns:
  - Segment
  - Share of volume
  - Revenue per kg
  - Cost per kg
  - Contribution per kg
table_rows:
  - "Packaged food | 70% | 8.0 | 6.4 | 1.6"
  - "Pharmaceutical | 30% | 14.0 | 14.0 | 0.0"
expected_insight: "Pharma earns zero contribution per kilogram despite a much higher price, so growth in pharma volume dilutes the blended margin."
common_misread: "Reading the higher pharma price as evidence that pharma is the more attractive segment."
```

### fact: load-factor

```yaml
provenance: scenario
source_ref: null
entity: client
topic: asset_utilisation
value: "Pharma routes run at 55 percent load factor against 88 percent for food"
units: percent
period: current
release_policy: on_targeted_question
stages:
  - analysis
  - exhibit_review
  - synthesis
depends_on:
  - segment-economics
consistent_with: []
author_rationale: "The mechanism behind the cost gap. Depends on the exhibit so the candidate reads before asking why."
```

### fact: pharma-route-constraint

```yaml
provenance: scenario
source_ref: null
entity: operations
topic: route_constraint
value: "Pharma consignments are small, time-critical and need a tighter temperature band"
units: null
period: current
release_policy: on_hypothesis
stages:
  - analysis
depends_on:
  - load-factor
consistent_with: []
author_rationale: "Explains why the obvious fix does not work, which is what makes the recommendation non-trivial."
```

### fact: pricing-basis

```yaml
provenance: scenario
source_ref: null
entity: commercial
topic: pricing_basis
value: "Pharma contracts were priced off the food cost base"
units: null
period: last_two_years
release_policy: on_hypothesis
stages:
  - analysis
depends_on:
  - segment-economics
consistent_with: []
author_rationale: "The commercial half of the root cause, and the lever the twelve-month plan acts on."
```

### fact: contract-reopener

```yaml
provenance: scenario
source_ref: null
entity: commercial
topic: contract_terms
value: "Annual price revision permitted with 90 days notice"
units: null
period: current
release_policy: on_hypothesis
stages:
  - analysis
  - synthesis
depends_on: []
consistent_with: []
author_rationale: "Makes the recommendation actionable inside the twelve-month horizon the board asked for."
```

### fact: root-cause

```yaml
provenance: derived
source_ref: null
entity: client
topic: diagnosis
value: "Mix shift into a segment priced off the wrong cost base"
units: null
period: current
release_policy: never_candidate_visible
stages:
  - analysis
depends_on: []
consistent_with: []
author_rationale: "Evaluator-only. Present so the answer key has a ledger entry and can be consistency-checked."
```

## Derived calculations

### calculation: blended-margin-now

```yaml
label: "Blended contribution margin today"
inputs:
  - segment-economics
formula: "(0.70 * 1.6 + 0.30 * 0.0) / (0.70 * 8.0 + 0.30 * 14.0)"
expected_value: 11.4
unit: "percent"
tolerance: 1.0
release_policy: on_calculation_request
match:
  any:
    - "blended"
    - "weighted average"
    - "overall margin"
    - "total contribution"
    - "weighted margin"
    - "combined margin"
common_errors:
  - "Averages the two segment margin percentages instead of weighting by revenue"
  - "Weights by volume share but divides by unweighted revenue"
interviewer_recovery: "Walk me through the setup. What are you weighting, and by what?"
coached_correction: "Weight contribution per kilogram by volume share, then divide by revenue per kilogram weighted the same way: 1.12 divided by 9.8, so about 11 percent."
```

### calculation: pharma-cost-at-food-load

```yaml
label: "Pharma cost per kg if load factor matched food"
inputs:
  - load-factor
  - segment-economics
formula: "14.0 * (55 / 85)"
expected_value: 9.1
unit: "rupees per kg"
tolerance: 0.6
release_policy: on_calculation_request
match:
  any:
    - "if the load factor"
    - "if we filled"
    - "at 85"
    - "at 88"
    - "higher load"
    - "improve utilisation"
    - "improve utilization"
    - "fill the trucks"
common_errors:
  - "Scales revenue rather than cost"
  - "Treats the whole cost per kilogram as variable with load"
interviewer_recovery: "What part of that cost per kilogram moves when the vehicle is fuller, and what part does not?"
coached_correction: "Cost per kilogram is largely a trip cost spread over the kilograms carried, so scaling 14.0 by 55 over 85 gives roughly 9 rupees per kilogram."
```

## Case graph

### milestone: establish-objective

```yaml
required: true
goal: "Candidate states the client decision, the metric and the horizon"
entry_conditions: []
advance_when:
  - objective_restated
advance_when_description:
  - "Candidate restates the objective and the success metric in their own words"
relevant_fact_ids:
  - objective-metric
allowed_moves:
  - answer
  - invite
  - probe
  - nudge
next_milestones:
  - clarify-context
stage_hint: clarification
rubric_targets:
  - problem_definition
```

### milestone: clarify-context

```yaml
required: true
goal: "Candidate asks the questions that materially narrow the problem"
entry_conditions:
  - establish-objective
advance_when:
  - high_value_question_asked
  - scope_defined
advance_when_description:
  - "Candidate establishes whether the issue is revenue or cost"
  - "Candidate discovers the segment mix shift"
relevant_fact_ids:
  - cost-side-not-revenue
  - segment-mix
  - no-one-offs
  - geography-neutral
allowed_moves:
  - answer
  - probe
  - redirect
  - nudge
next_milestones:
  - candidate-structure
stage_hint: clarification
rubric_targets:
  - clarification
  - problem_definition
```

### milestone: candidate-structure

```yaml
required: true
goal: "Candidate proposes a tailored, prioritised approach"
entry_conditions:
  - clarify-context
advance_when:
  - structure_stated
  - branch_prioritised
advance_when_description:
  - "Candidate states a causal structure rather than a bucket list"
  - "Candidate names the branch they will test first and why"
relevant_fact_ids: []
allowed_moves:
  - invite
  - probe
  - challenge
  - nudge
  - redirect
next_milestones:
  - prioritised-deep-dive
stage_hint: structure
rubric_targets:
  - structure
  - business_judgement
```

### milestone: prioritised-deep-dive

```yaml
required: true
goal: "Candidate commits to a hypothesis and tests it against the economics"
entry_conditions:
  - candidate-structure
advance_when:
  - hypothesis_stated
advance_when_description:
  - "Candidate states a falsifiable hypothesis about the margin fall"
relevant_fact_ids:
  - competitor-benchmark
  - segment-economics
  - pricing-basis
allowed_moves:
  - answer
  - probe
  - challenge
  - nudge
  - redirect
next_milestones:
  - quant-or-qual-test
stage_hint: analysis
rubric_targets:
  - business_judgement
  - structure
```

### milestone: quant-or-qual-test

```yaml
required: true
goal: "Candidate reads the exhibit and quantifies or explains the mechanism"
entry_conditions:
  - prioritised-deep-dive
advance_when:
  - insight_stated
  - calculation_attempted
advance_when_description:
  - "Candidate reads the per-kilogram exhibit correctly"
  - "Candidate sets up a calculation or explains the cost mechanism"
relevant_fact_ids:
  - segment-economics
  - load-factor
  - pharma-route-constraint
allowed_moves:
  - answer
  - probe
  - challenge
  - nudge
  - assumption
next_milestones:
  - synthesis
stage_hint: analysis
rubric_targets:
  - data_interpretation
  - quantitative
```

### milestone: synthesis

```yaml
required: true
goal: "Candidate gives a decision-oriented recommendation"
entry_conditions:
  - quant-or-qual-test
advance_when:
  - recommendation_stated
advance_when_description:
  - "Candidate gives an answer, evidence, a risk and a next step"
relevant_fact_ids:
  - contract-reopener
allowed_moves:
  - challenge
  - close
  - probe
next_milestones: []
stage_hint: synthesis
rubric_targets:
  - synthesis
```

## Answer key

```yaml
diagnosis: "Blended margin fell because volume mix moved into a pharma book that was quoted off the packaged-food cost base and never re-costed for a 55 percent load factor, so it earns nothing per kilogram carried."
alternative_paths:
  - "Segment profitability first: ask for margin by segment before asking about mix, then work back to the mix shift"
  - "Asset utilisation first: notice fleet utilisation has fallen, then discover which segment causes it"
  - "Benchmark first: establish that food-only competitors held margin, then ask what is different about Meridian"
exemplar: "Blended margin fell because the volume mix moved into pharma, which earns zero contribution per kilogram against 1.6 rupees for food. Pharma was priced off the food cost base and never re-costed for a 55 percent load factor, and the consignments cannot be consolidated with food because of the tighter temperature band. Two of the four largest pharma contracts allow a price revision within six months, so the first move is to re-cost and reprice those, hold volume where the customer will not accept it, and only then attempt network changes to lift the load factor."
```

### recommendation: 1

```yaml
priority: 1
action: "Re-cost every pharma lane and reprice the two contracts that reopen within six months"
rationale: "The contracts were quoted off the wrong cost base and the reopener makes this achievable inside the twelve-month horizon"
risk: "A large pharma customer walks, which removes revenue faster than it removes cost"
```

### recommendation: 2

```yaml
priority: 2
action: "Lift pharma load factor by consolidating pharma-only routes and adding scheduled milk runs on the densest lanes"
rationale: "Cost per kilogram is a trip cost spread over kilograms carried, so load factor is the operational lever"
risk: "Time-critical consignments will not tolerate the extra stops, so service levels slip"
```

### recommendation: 3

```yaml
priority: 3
action: "Introduce a minimum-consignment charge and a temperature-band premium in all new pharma quotes"
rationale: "Prevents the same mispricing recurring as the pharma book grows"
risk: "Prices out smaller pharma customers and slows growth in the segment"
```
