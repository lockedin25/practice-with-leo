# OUTBOX — codex

STATUS: DONE

## WHAT I DID
- Implemented the P1 abandoned-versus-scored end disposition. Readiness is not
  substantive evidence; attempts with fewer than two substantive case turns
  default to `abandoned` unless the caller explicitly requests `scored`.
- Persisted disposition and substantive-turn count with backward-compatible
  session loading. Abandoned attempts retain their transcripts and appear in
  practice history, but do not create feedback, solve a case, increment case
  completion, or enter profile score and dimension aggregates.
- Updated the end confirmation to say “Save without scoring” for an early
  attempt and redirect it to the profile rather than a debrief.
- Added roadmap acceptance coverage for readiness-only abandonment and a normal
  scored multi-turn case. Updated existing evaluator-specific tests to request
  `scored` explicitly, preserving their purpose under the new default.

## FILES CHANGED
- `app/case_runtime.py`
- `app/store.py`
- `app/main.py`
- `app/static/app.js`
- `tests/test_case_progress.py`
- `tests/test_admin.py`
- `tests/test_debrief_reliability.py`
- `tests/test_e2e_workflow.py`
- `tests/test_evaluator.py`
- `tests/test_store_persistence.py`

## HOW TO VERIFY
- `OPENROUTER_API_KEY=test .venv/bin/pytest tests/ -x -q`
- Result: `426 passed, 1 xfailed`.

## NOTES FOR NEXT AGENT
- The roadmap names `app/static/app.html`, but this checkout has no such file;
  the practice room is rendered from `app/templates/practice.html`. The actual
  end confirmation behavior lives in `app/static/app.js` and needed no markup
  change.
- The placeholder key is only needed because provider construction occurs at
  import time; tests replace all live providers before requests.
