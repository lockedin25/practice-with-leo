# Handoff Report: Evaluator Engine & Backend Store Survey

**Agent**: Explorer 2 (`explorer_survey_evaluator_backend`)  
**Parent Agent**: Orchestrator (`parent`, id: `52543645-e2ea-4420-b0e0-9105575079aa`)  
**Date**: 2026-08-24  
**Handoff Type**: Hard (Survey Complete)

---

## 1. Observation

1. **Scoring Scale & Dimensions**:
   - `app/evaluator.py:41-42`:
     ```python
     DIMENSION_NAMES = ("structuring", "problem_solving", "communication", "quantitative")
     BAND_NAMES = ("Developing", "Solid", "Strong", "Exceptional")
     ```
   - `evaluation/prompts/writer_system.md:10`:
     ```markdown
     - Score each dimension 0 to 10 and assign one band per dimension from the
       rubric anchors supplied below.
     ```
   - `evaluation/rubric.yaml:14-74`: Lists 4 dimensions with weights: `structuring` (0.35), `problem_solving` (0.30), `communication` (0.20), `quantitative` (0.15).
   - `ORIGINAL_REQUEST.md:23-39`: Requires BCG-calibrated 1.0–5.0 scoring across 5 dimensions (`structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`) with a rich debrief payload.

2. **Evaluation Report Schema**:
   - `app/evaluator.py:75-83`:
     ```python
     class EvaluationReport(BaseModel):
         attempt_id: str
         dimensions: list[DimensionScore]
         checklist: list[ChecklistItem]
         headline_strengths: list[str] = Field(default_factory=list)
         priority_improvements: list[str] = Field(default_factory=list)
         next_drill: str = ""
         evaluator_version: str = ""
     ```
   - Missing fields required by R2: `executive_summary`, `what_the_case_wanted_to_test`, `golden_rewrites`, `strengths`, `areas_for_development`, `targeted_drill`, `suggested_readings`, `overall_score`, `overall_band`.

3. **Database Schema & Store**:
   - `app/store.py:465-472`: Table `evaluations`:
     ```sql
     CREATE TABLE IF NOT EXISTS evaluations (
         attempt_id TEXT NOT NULL,
         evaluator_version TEXT NOT NULL,
         report_json TEXT NOT NULL,
         created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
         PRIMARY KEY (attempt_id, evaluator_version)
     )
     ```
   - `app/store.py:160-177`: `list_user_practice` selects latest `evaluations` joined on `attempts`.
   - `app/store.py:202-224`: `mark_case_solved` stores `best_score` in `user_case_progress`.

4. **Attempt Completion Hook & APIs**:
   - `app/main.py:251-275`: `POST /api/attempts/{attempt_id}/end` sets `session.ended = True`, triggers `_evaluate_and_store(session)` and marks case solved with `_report_score(report)`.
   - `app/main.py:317-333`: `GET /api/attempts/{attempt_id}/evaluation` serves cached report or runs lazy evaluation.
   - `app/main.py:384-440`: `GET /api/me/profile` aggregates scores across assessed attempts.
   - `app/static/profile.js:76,104,110`: Profile UI already renders scores assuming a 1–5 scale (`score / 5`), while `debrief.html:74` and `debrief.js:140` display `/10`.

5. **Test Suite Baseline**:
   - Command `.venv/bin/pytest` executed 101 tests: **101 passed in 1.06s**.
   - `tests/test_evaluator.py` contains 20 tests verifying tools, leakage guards, citation validity, and degradation fallback.

---

## 2. Logic Chain

1. **Dimension & Scale Harmonization**:
   - Observations 1 and 4 show that `app/evaluator.py`, `rubric.yaml`, and `writer_system.md` operate on 4 dimensions and a 0–10 scale, whereas the product specification (`ORIGINAL_REQUEST.md`) and the profile frontend (`profile.js`) expect 5 dimensions on a 1.0–5.0 BCG scale.
   - Therefore, `DIMENSION_NAMES` must be updated to `("structuring", "problem_solving", "quantitative", "synthesis", "communication")`, `rubric.yaml` weights adjusted (e.g. 0.25, 0.25, 0.15, 0.20, 0.15), and prompt instructions updated to 1.0–5.0 scoring.

2. **Zero-Migration Rich Payload Persistence**:
   - Observation 3 shows that `evaluations` table stores `report_json TEXT NOT NULL`.
   - Extending `EvaluationReport` with Pydantic submodels (`WhatTheCaseWantedToTest`, `GoldenRewriteTurn`, `SuggestedReading`, etc.) will serialize directly into `report_json` upon `report.model_dump_json()`.
   - This ensures database persistence and versioning continue working seamlessly without requiring destructive SQLite table schema changes.

3. **Profile & Debrief API Alignment**:
   - Observation 4 shows `GET /api/me/profile` and `GET /api/attempts/{attempt_id}/evaluation` consume the serialized report.
   - By retaining backwards-compatible aliases (or mapping `headline_strengths` to `strengths`, `priority_improvements` to `areas_for_development`, `next_drill` to `targeted_drill`), existing API contracts and profile aggregations remain intact while delivering the new rich fields.

4. **Deterministic Validation & Safety Pipeline**:
   - Observation 5 shows `app/evaluator.py` relies on `citation_violations`, `completeness_violations`, `find_leakage`, and `_strip_em_dashes`.
   - When 5 dimensions and new fields are added, `completeness_violations`, `_report_texts`, and `_degrade_report` must be updated so that the safety invariants (no private case leakage, verbatim quote verification, no em-dashes) continue to hold.

---

## 3. Caveats

1. **Live LLM Provider Dependency in Production**: Tests use `FakeWriter` and `StubEvaluator`. Live execution in production requires `OPENROUTER_API_KEY` with OpenRouter models (Claude 3.5 Sonnet / GPT-4o).
2. **Case Essence Availability**: Full generation of `what_the_case_wanted_to_test` benefits from `case_essence` metadata in case packages (surveyed in parallel by Explorer 1). The evaluator should gracefully handle cases where `case_essence` is partially populated.

---

## 4. Conclusion

The evaluator engine and backend store architecture are well-structured, modular, and cleanly decoupled from the runtime. Upgrading to the 10x Debrief Engine requires:
1. Updating `app/evaluator.py` and `evaluation/rubric.yaml` to 5 BCG dimensions on the 1.0–5.0 scale.
2. Expanding `EvaluationReport` Pydantic models with `executive_summary`, `what_the_case_wanted_to_test`, `golden_rewrites`, `targeted_drill`, `suggested_readings`.
3. Updating writer prompts (`writer_system.md`) and planner prompts (`planner_system.md`).
4. Updating profile endpoints and test assertions in `tests/test_evaluator.py` and `tests/test_practice_history.py`.

All database storage in `app/store.py` natively supports the richer payload through existing JSON columns.

---

## 5. Verification Method

1. **Run Full Test Suite**:
   ```bash
   .venv/bin/pytest
   ```
2. **Run Evaluator & Store Tests**:
   ```bash
   .venv/bin/pytest tests/test_evaluator.py tests/test_store.py tests/test_practice_history.py -v
   ```
3. **Inspect Output Files**:
   - `survey_report.md` at `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/explorer_survey_evaluator_backend/survey_report.md`
   - `handoff.md` at `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/explorer_survey_evaluator_backend/handoff.md`
