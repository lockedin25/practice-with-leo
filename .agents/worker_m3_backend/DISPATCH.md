# Milestone 3 Assignment: Backend Database Persistence & Profile Linking

## Mission
Implement backend database persistence for rich `EvaluationReport` payloads in SQLite, ensure attempt completion automatically triggers evaluation and stores it, update user profile endpoints (`/api/profile`, `/api/attempts/{id}`) to include latest scores on the 1–5 scale, performance history, repeated development areas, and debrief links, and ensure `/api/attempts/{id}/evaluation` returns the full rich report payload.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Rules & Guidelines
- Read `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/ORIGINAL_REQUEST.md`, `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/PROJECT.md`, and `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/explorer_survey_evaluator_backend/survey_report.md`.
- Working Directory: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/worker_m3_backend`
- Write ownership: `app/store.py`, `app/main.py`, `app/attempt_service.py`.
- Ensure all tests in `tests/` pass with pytest.
- Write your completion report in `handoff.md` and send a message when done.
