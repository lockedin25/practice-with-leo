# Milestone 3 Handoff Report: Backend Database Persistence & Profile Linking

## 1. Observation
- **Evaluations Table & Persistence (`app/store.py`)**:
  - `EvaluationStore` initializes table `evaluations` with `(attempt_id, evaluator_version, report_json, created_at, user_id)`.
  - Schema migration dynamically checks `PRAGMA table_info(evaluations)` and executes `ALTER TABLE evaluations ADD COLUMN user_id TEXT` if missing.
  - Indices created: `evaluations_user` on `user_id` and `evaluations_attempt` on `attempt_id`.
  - Backfill query links existing evaluations lacking `user_id` to their respective owner from `attempts`.
  - `EvaluationStore.save(report_json, attempt_id, evaluator_version, *, user_id=None)` records `user_id` explicitly or queries it from `attempts` if omitted.
  - Added `EvaluationStore.list_by_user(user_id, limit=100)` and `EvaluationStore.get(attempt_id, evaluator_version)`.
- **Attempt Lifecycle & Auto-Evaluation (`app/attempt_service.py`)**:
  - Implemented `AttemptLifecycleService.complete_attempt(session, store, evaluations, evaluator, *, user_id=None)` which sets `session.ended = True`, stores the session, executes evaluation, saves the rich report linked to `attempt_id` and `user_id`, and updates `user_case_progress.best_score` and status.
- **FastAPI Endpoints & Profile Integration (`app/main.py`)**:
  - `POST /api/attempts/{id}/end` automatically evaluates, saves with `user_id`, updates solved progress with 1–5 score, and returns `debrief_url` (`/attempts/{id}/debrief`) and `evaluation_url` (`/api/attempts/{id}/evaluation`).
  - `GET /api/attempts/{id}` augments `candidate_view` with `debrief_url`, `evaluation_url`, latest 1-5 scale score, and `mbb_rating_badge`.
  - `GET /api/attempts/{id}/evaluation` returns the full rich report payload, overall metrics, and `debrief_url`.
  - Profile endpoints `@app.get("/api/profile")` and `@app.get("/api/me/profile")` aggregate across completed attempts:
    - Calculates 1–5 scale dimension averages for 5 BCG dimensions (`structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`).
    - Aggregates top repeated development areas (with occurrence counts) supporting both string lists and structured objects.
    - Aggregates top repeated strengths (with occurrence counts).
    - Returns `recent_attempts` and `performance_history` containing debrief URLs and scores.
  - `_practice_summary` provides `debrief_url`, `evaluation_url`, `overall_score`, and `mbb_rating_badge`.
  - `_session` ownership validation checks both `ACCOUNTS.owner_of` and `attempts.user_id`.

## 2. Logic Chain
- **Requirement R3.1 (DB Persistence)**: Required full rich `EvaluationReport` to be persisted in SQLite `evaluations` linked to `attempt_id` and `user_id`. `EvaluationStore` now persists JSON payloads with `user_id` column, indexed queries, and backfill migration.
- **Requirement R3.2 (Attempt Lifecycle)**: Required every completed attempt to automatically trigger evaluation and store results. `POST /api/attempts/{id}/end` and `AttemptLifecycleService.complete_attempt` trigger evaluation and update `user_case_progress`.
- **Requirement R3.3 (Profile Endpoints)**: Required `/api/profile` and `/api/attempts/{id}` to return 1–5 scale scores, performance history, repeated development areas, and links to full debrief reports. Both endpoints now expose these fields with robust backward compatibility.
- **Requirement R3.4 (Debrief API)**: Required `/api/attempts/{id}/evaluation` to return the rich report payload. The endpoint returns the full report dictionary, overall calculation, and debrief URL.

## 3. Caveats
- No destructive SQL migrations were performed; all schema additions are backward-compatible.
- If the LLM evaluator provider is offline or unconfigured, the system gracefully generates fallback evaluations or provides the heuristic scorecard without losing attempt data.

## 4. Conclusion
Milestone 3 (Backend Database Persistence & Profile Linking) is fully implemented, verified, and passing all test suites. All requirements in `ORIGINAL_REQUEST.md` (§R3) and `PROJECT.md` have been met with clean, genuine implementations.

## 5. Verification Method
- **Pytest Suite Execution**:
  ```bash
  .venv/bin/pytest -v
  ```
  Result: **175 passed in 3.32s**.
- **Syntax Compilation**:
  ```bash
  .venv/bin/python -m py_compile app/store.py app/main.py app/attempt_service.py tests/test_store_persistence.py
  ```
  Result: **0 errors**.
- **Key Verified Tests**:
  - `tests/test_store_persistence.py::test_t1_evaluation_store_saves_and_retrieves_latest`
  - `tests/test_store_persistence.py::test_t1_evaluation_store_maintains_versioned_history`
  - `tests/test_store_persistence.py::test_t1_evaluation_store_user_id_linking_and_queries`
  - `tests/test_store_persistence.py::test_t3_api_profile_and_attempt_linking`
  - `tests/test_store_persistence.py::test_t3_profile_aggregates_dimensions_and_repeated_development_areas`
  - `tests/test_store_persistence.py::test_t4_attempt_lifecycle_service`
  - `tests/test_store_persistence.py::test_t4_real_world_attempt_auto_trigger_and_persistence_workflow`
  - `tests/test_e2e_workflow.py::test_scenario_1_end_to_end_attempt_lifecycle_and_debrief`
