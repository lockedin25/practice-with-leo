# Milestone 2 Assignment: BCG-Calibrated 1–5 Evaluator Agent Engine

## Mission
Upgrade the evaluation engine, rubric, prompts, and Pydantic models to a BCG-calibrated 1.0–5.0 scoring scale across 5 core consulting dimensions (`structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`), generating rich report payloads.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Rules & Guidelines
- Read `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/ORIGINAL_REQUEST.md`, `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/PROJECT.md`, and `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/explorer_survey_evaluator_backend/survey_report.md`.
- Working Directory: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/worker_m2_evaluator`
- Write ownership: `app/evaluator.py`, `evaluation/`.
- Ensure `EvaluationReport` matches the interface contract in `PROJECT.md` and includes all required fields: `overall_score` (1.0-5.0), `mbb_rating_badge`, `executive_summary`, `what_the_case_wanted_to_test`, `dimension_scores`, `golden_rewrites` (Opening and Closing), `strengths`, `areas_for_development`, `targeted_drill`, `suggested_readings`, `observed_behaviors`.
- Implement robust deterministic fallback evaluation when LLM is unavailable.
- Run pytest to verify all evaluator tests pass.
- Write your completion report in `handoff.md` and send a message when done.
