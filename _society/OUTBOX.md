STATUS: DONE

WHAT I DID
- Read the CaseCall v2 brief, PROJECT.md, docs/codebase-guide.md, auth/E2E tests, and repository context.
- Ran two authenticated API campaign attempts in pressure mode: TerraBuild Materials and Forge Components, 10 candidate turns each, with expert-quality hypothesis-led, quantitative, and synthesis answers.
- Exercised turn retry/idempotency, active-attempt re-open, early end, catalogue retrieval/filter probe, debrief delivery, profile trends, practice history, and per-case performance.
- Documented calibration, bugs, friction, debrief usefulness, and requested features in the expert persona report.

FILES CHANGED
- docs/campaign/persona-expert.md
- _society/OUTBOX.md

HOW TO VERIFY
- Read docs/campaign/persona-expert.md for exact attempt IDs, endpoints, scores, and findings.
- The campaign trace was created only in /private/tmp/casecall-expert-api-trace.json and is intentionally not committed.
- `.venv/bin/pytest tests/ -x -q` cannot collect without OPENROUTER_API_KEY. With `OPENROUTER_API_KEY=campaign-stub`, it reaches 94 passed then fails tests/test_case_progress.py because app/static/app.js lacks the expected literal `syncTimer(attempt);`.

NOTES FOR NEXT AGENT
- P0: fallback scoring reports the two expert attempts as 3.47 and 3.57, not the expected 4-5 range. The report includes a dimension-level calibration table and evidence.
- P1: ending an attempt after only readiness creates a 2.45 scored result and lowers profile trends; add an abandoned/exclude-from-trends path.
- P1: no OPENROUTER_API_KEY prevents app boot, so local dogfooding has no degraded interviewer mode.
- The requested localhost server could not run here: localhost:8000 was down and binding the worktree server to 127.0.0.1:8002 was denied by the environment. Testing therefore used FastAPI TestClient with the test-suite signed-cookie auth path and a deterministic interviewer double; evaluation used the real fallback evaluator.
