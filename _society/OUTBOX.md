# OUTBOX — opencode (I3)

STATUS: DONE

## WHAT I DID
Executed roadmap item 3 "[P0] Make write contention survivable and regression-tested" (docs/campaign/ROADMAP.md on main) exactly within its stated scope:

- Preserved the existing WAL / busy-timeout setup untouched (app/db.py pragmas and BUSY_TIMEOUT_MS unchanged).
- app/db.py: added `DatabaseBusy(RuntimeError)` and `is_busy_error(error)` — the SQLite busy-error predicate that distinguishes an exhausted busy timeout ("database is locked", statement never ran, safe to resend) from every other OperationalError (stays a 500).
- app/main.py `POST /api/attempts/{id}/turn`: translates exhausted lock errors into `db.DatabaseBusy`, rendered by a registered app-level exception handler as a structured retryable `503`: `{"detail": "<human message>", "error": "database_busy", "retryable": true}` plus a `Retry-After: 1` header. `detail` stays a plain string deliberately — app.js `request()` puts `body.detail` straight into a toast, so a dict detail would degrade to "[object Object]" in the candidate's UI. Non-busy OperationalErrors still surface as bare 500s (not mislabelled retryable). No queue, no DB migration.
- New tests/test_database_contention.py (roadmap's "or a new focused test file" option): holds a real SQLite write lock via `BEGIN IMMEDIATE` + no-op write on a raw connection. Five tests: (1) contended turn returns 503 with retryable detail, `database_busy` error code and Retry-After header — not a bare 500; (2) while the write lock is held a second unauthenticated client still reads `/health` 200 and `/api/cases` 200 (WAL reader isolation, proven under a 50ms busy timeout); (3) the same turn succeeds on retry after the lock clears (blocked save wrote nothing); (4) two clients submitting turns concurrently both get 200 (ordinary overlap stays the busy timeout's job); (5) only "database is locked" is translated — "no such table" is not.

## FILES CHANGED
- app/db.py (+22: DatabaseBusy, is_busy_error; WAL/busy-timeout setup untouched)
- app/main.py (+29/-1: sqlite3 + JSONResponse imports, translation in submit_turn, `_database_busy` exception handler)
- tests/test_database_contention.py (new, 5 tests)
- Worktree setup note: worktree had no `.env`; created a local gitignored one with a placeholder OPENROUTER_API_KEY so `app.main` imports (tests stub the interviewer/evaluator, so no live calls). Not committed.

## HOW TO VERIFY
- `.venv/bin/pytest tests/ -x -q` → 429 passed, 1 xfailed (pre-existing syncTimer xfail); baseline before my change was 424 passed, 1 xfailed.
- `.venv/bin/pytest tests/test_database_contention.py -q` → 5 passed in <1s (lock holder + shrunk 50ms busy timeout keeps it fast; production 5s timeout untouched).
- Manual check of the endpoint surface: under a held `BEGIN IMMEDIATE` write lock, `POST /api/attempts/{id}/turn` returns `503` with `{"detail": "...", "error": "database_busy", "retryable": true}`; `/health` and `/api/cases` stay 200 throughout.

## NOTES FOR NEXT AGENT
- Scope kept to the roadmap's declared surface (turn endpoint + /health). Other write endpoints (/api/attempts POST, /end, contributions, voice) still 500 under an exhausted lock; if the P0-2 outage pattern reappears there, the fix is mechanical: catch `sqlite3.OperationalError`, use `db.is_busy_error`, raise `db.DatabaseBusy` — the app-level handler already renders the structured 503 for any endpoint.
- `db.DatabaseBusy` is a RuntimeError subclass; in `submit_turn` it is raised from the new `except sqlite3.OperationalError` clause, so the sibling `except (RuntimeError, ...)` clause cannot swallow it (siblings never re-catch; verified by the tests).
- The busy-timeout value is read at connect time from the module global, so tests monkeypatch `app.db.BUSY_TIMEOUT_MS`; no per-connection state to clean up.
- The bare-500 reproduction harness from feedback P0-2 (two overlapping personas on one server) is now deterministic in tests via the raw-lock holder, so nobody needs the shared dev server to reproduce contention. Root cause of the original outage remains unconfirmed — this task deliberately ships the safe failure mode + harness instead of a storage change.
- Merge note for foreman: branch agent/opencode was fast-forwarded to realtime-voice-ptt (0a5fe9d) before work began, so this merge should be conflict-free. Only commit here is d6397fc (plus this outbox commit).
