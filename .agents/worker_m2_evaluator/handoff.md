# Handoff Report — Milestone 2: BCG-Calibrated 1–5 Evaluator Agent Engine

**Agent**: Worker M2 (`worker_m2_evaluator`)  
**Date**: 2026-08-24  
**Project**: MBB Case Prep V2 (Leo)  
**Scope**: Evaluator Pydantic models, BCG 1.0–5.0 scoring scale across 5 dimensions, rich `EvaluationReport` schema, updated rubrics & prompts, deterministic heuristic fallback evaluation engine, and unit/integration test validation.

---

## 1. Observation

1. **Previous Evaluator Constraints**:
   - `app/evaluator.py` previously defined 4 dimensions on a 0–10 scale (`structuring`, `problem_solving`, `communication`, `quantitative`) with minimal payload fields (`dimensions`, `checklist`, `headline_strengths`, `priority_improvements`, `next_drill`).
   - `evaluation/rubric.yaml` and `evaluation/prompts/` were calibrated for 0–10 scoring without coverage for the 5th core consulting dimension (`synthesis`) or rich 10x debrief cards.
   - When LLM provider access was missing, evaluations had to rely on empty placeholders with score 0 rather than computing genuine heuristic assessments from candidate turns and case essence.

2. **Executed Code & Artifact Modifications**:
   - **`app/evaluator.py`**:
     - `DIMENSION_NAMES`: Updated to `("structuring", "problem_solving", "quantitative", "synthesis", "communication")` with weights `{"structuring": 0.25, "problem_solving": 0.25, "quantitative": 0.15, "synthesis": 0.20, "communication": 0.15}`.
     - `BAND_NAMES`: `("Below Bar", "Meets Bar", "Top 1% MBB")`.
     - `MBB_RATING_BADGES`: `("Distinction", "Strong Pass", "Meets Bar", "Developing", "Needs Substantial Practice")`.
     - `compute_mbb_rating_badge(score)` and `compute_overall_band(score)` helper functions.
     - Rich schemas: `WhatTheCaseWantedToTest`, `GoldenRewriteTurn`, `StrengthItem`, `DevelopmentAreaItem`, `TargetedDrillPayload`, `SuggestedReading`, `ChecklistItem` / `ObservedBehaviorItem`.
     - `EvaluationReport`: Fully typed model supporting `overall_score`, `mbb_rating_badge`, `overall_band`, `executive_summary`, `what_the_case_wanted_to_test`, `dimensions`, `dimension_scores`, `checklist`, `observed_behaviors`, `golden_rewrites`, `strengths`, `headline_strengths`, `areas_for_development`, `priority_improvements`, `targeted_drill`, `next_drill`, `drill_detail`, `suggested_readings` with bidirectional field sync validators.
     - `generate_fallback_evaluation` & `FallbackCaseEvaluator`: Genuine heuristic grading analyzing candidate transcript turns (opening objective restatement, MECE splits, hypothesis presence, quantitative calculation & 'so what' interpretation, 4-part Pyramid synthesis, signposting), fact discovery ratio, and case essence matching.
     - `create_evaluator(reservoir_root, allow_fallback=False)`: Supports fallback initialization when API key is unconfigured.
     - `_strip_em_dashes` and `_degrade_report`: Sanitizes all newly added rich fields and redacts private case content.
   - **`evaluation/rubric.yaml`**:
     - Upgraded to schema version `rubric-v2` specifying the 5 BCG dimensions, weights summing to 1.0, violation classes, and behavioral anchors for `Below Bar` (1.0–2.4), `Meets Bar` (2.5–3.7), and `Top 1% MBB` (3.8–5.0).
   - **`evaluation/checklist.yaml`**:
     - Upgraded to schema version `checklist-v2` with behavioral markers covering all 5 consulting stages and dimensions.
   - **`evaluation/prompts/planner_system.md` & `writer_system.md`**:
     - Updated with explicit BCG 1.0–5.0 grading rules, 5-dimension weights, Golden Rewrite harvesting (Opening & Closing), and rich report specifications.
   - **`tests/test_evaluator.py` & `tests/test_e2e_workflow.py`**:
     - Upgraded existing unit tests and added new test suites validating 5 dimensions, 1.0–5.0 bounds, bidirectional model synchronization, badge calculation, and fallback execution.

3. **Test Results**:
   - Ran `.venv/bin/pytest`: **167 tests passed, 0 failures** in 2.14s.

---

## 2. Logic Chain

1. **Dimension & Scoring Scale Calibration**:
   - Consulting case evaluation across McKinsey, BCG, and Bain requires assessing 5 distinct craft dimensions: structuring (25%), problem solving (25%), quantitative numeracy (15%), executive synthesis (20%), and communication (15%).
   - Calibrating scoring to the 1.0–5.0 interval aligns with `knowledge_base/evaluation_engine/detection_rubrics.yaml` and allows crisp mapping to MBB rating badges (*Distinction*, *Strong Pass*, *Meets Bar*, *Developing*, *Needs Substantial Practice*).

2. **10x Debrief Rich Payload Architecture**:
   - Candidates require actionable feedback beyond numerical scores:
     - `what_the_case_wanted_to_test` connects the attempt to the case's economic mechanism and pivotal insight.
     - `golden_rewrites` provide side-by-side comparative exemplars for opening and closing turns.
     - `strengths` and `areas_for_development` provide verbatim-cited wins and prioritized corrective guidance.
     - `targeted_drill` and `suggested_readings` give immediate 2-minute practice exercises and deep links to knowledge base modules.

3. **Resilient Fallback Heuristic Execution**:
   - In offline, local testing, or unconfigured LLM environments, the evaluator must maintain genuine heuristic intelligence rather than failing or returning empty mock data.
   - `generate_fallback_evaluation` inspects actual transcript tokens, checks for objective restatement, MECE formula keywords, hypothesis phrasing, arithmetic and 'so what' implications, 4-part synthesis structure, and compares against `case_essence` loaded from the reservoir case package.

4. **Backward Compatibility & Safety**:
   - Model validators ensure legacy API consumers reading `dimensions` (list), `headline_strengths`, `priority_improvements`, `next_drill`, and `checklist` continue to function seamlessly alongside new rich consumers reading `dimension_scores` (dict), `strengths`, `areas_for_development`, `targeted_drill`, and `observed_behaviors`.
   - Leakage guards and em-dash sanitizers inspect all text fields across the entire rich payload.

---

## 3. Caveats

- **OpenRouter API Key in Offline Test Mode**: Unit and E2E test suites run deterministically using `StubEvaluator`, `FakeWriter`, and `FallbackCaseEvaluator` without contacting external LLM network providers.
- **Quantitative Dimension Scaffolding**: If a candidate attempt does not involve numerical arithmetic, the quantitative dimension is graded with `confidence: "low"` and weight is redistributed proportionally during deterministic overall calculation.

---

## 4. Conclusion

Milestone 2 is complete and verified:
- `app/evaluator.py` implements the BCG 1.0–5.0 scoring scale across the 5 defined consulting dimensions.
- Rich `EvaluationReport` schemas and models are fully functional with complete data synchronization.
- Prompts, rubrics, and checklists are updated with BCG criteria and few-shot guidance.
- Deterministic fallback evaluation produces authentic, high-value debrief reports when LLM services are offline.
- 100% of test suites pass (167 / 167 tests).

---

## 5. Verification Method

To independently verify this milestone:

```bash
# 1. Run all unit and integration tests
.venv/bin/pytest

# 2. Run evaluator-specific test suite with verbose output
.venv/bin/pytest -v tests/test_evaluator.py tests/test_evaluator_v2.py

# 3. Test fallback evaluation directly in Python
.venv/bin/python -c "
from app.evaluator import FallbackCaseEvaluator, EvaluationReport
from app.case_runtime import CaseCatalogue, InterviewSession
from pathlib import Path

ROOT = Path('.').resolve()
cat = CaseCatalogue.from_reservoir(ROOT)
session = InterviewSession(id='verify-test', case=cat.get('meridian-cold-chain-v1'), mode='realistic')
session.add_interviewer_turn(session.case.opening)
session.record_candidate_turn('Let me restate the objective: understand why EBITDA fell from 18 to 11 percent.')
session.record_candidate_turn('I will structure revenue into price and volume, and explore pharma segment mix.')
session.ended = True

evaluator = FallbackCaseEvaluator(ROOT / 'reservoir')
report = evaluator.evaluate(session)
assert report.overall_score >= 1.0 and report.overall_score <= 5.0
assert len(report.dimensions) == 5
assert len(report.golden_rewrites) >= 2
assert report.what_the_case_wanted_to_test is not None
print('Verification Succeeded: Overall Score =', report.overall_score, '| Badge =', report.mbb_rating_badge)
"
```
