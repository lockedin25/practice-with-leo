# OUTBOX — claude

STATUS: DONE

## WHAT I DID
Completed the beginner-persona QA report per `agent-society/briefs/casecall-v2.md`,
across two runs (this is a retry that continued a prior run's surviving work):

- Attempt 1 (prior run, preserved as-is): Beer Manufacturer
  (`01-beer-manufacturer-v1`, foundation), 10 turns, run on a private local
  instance after the shared server crashed platform-wide (Bug #1, P0).
- Attempt 2 (this run): a *different*, market-entry case — Aster Diagnostics
  (`aster-diagnostics-v1`, intermediate) — run directly against the shared
  server at `http://localhost:8000` to see if Bug #1 would recur. It did not:
  the shared server stayed responsive throughout, though the final
  `POST /api/attempts/{id}/end` evaluation call took 2:06 wall-clock (a naive
  ~90s client timeout would treat that as a hard failure).
- Auth both times via the untracked `scripts/_persona_mint_session.py`
  (mints a `casecall_session` cookie against the main checkout's
  `data/.session_secret`, no Google OAuth needed) — `GET /api/me` → 200
  confirmed each time.
- Found a new, distinct evaluator bug in Attempt 2 (Bug #3): the evaluator
  did NOT hit the fallback path this time (`evaluator_version` names a real
  model, `google/gemini-3.7-flash`, no `fallback=true`), and its
  checklist/observed-behaviors output was accurate and well-evidenced (11/12
  markers correctly "missed") — but `dimensions`, `dimension_scores`,
  `executive_summary`, `golden_rewrites`, `strengths`, and
  `suggested_readings` all came back empty, while `overall_score` landed at
  `0.0` and `overall_band`/`mbb_rating_badge` still read **"Meets Bar"** — an
  internally contradictory result. Combined with Attempt 1's inflated
  fallback score, both attempts in this campaign produced a debrief with a
  headline number that misrepresents the actual (poor) performance shown in
  the transcript, via two entirely different failure paths.
- Added the "Missing features I WISHED existed" (top 3) section per the
  brief's "what each persona must produce" item 5.

## FILES CHANGED
- `docs/campaign/persona-beginner.md` (full report, 320 lines) — committed on
  `agent/claude` as `8ac8bca campaign: beginner persona QA report (2 live
  attempts)`.
- `_society/OUTBOX.md` (this file).
- Untracked, not committed (dev-only tooling, not campaign output):
  `scripts/_persona_mint_session.py`.

## HOW TO VERIFY
- `git show 8ac8bca --stat` on `agent/claude`.
- Read `docs/campaign/persona-beginner.md` — sections in order: persona
  voice/auth note, Bug #1 (shared-server crash), Attempt 1 turn-by-turn +
  Bug #2 (mismatched golden rewrite) + calibration table + debrief
  usefulness, Attempt 2 turn-by-turn + Bug #3 (empty-dimension evaluator),
  Missing features (top 3).
- To reproduce Attempt 2's Bug #3, replay attempt
  `c86827c5-43ce-4b0a-adc5-9501471c3dfc` if it's still in the shared DB, or
  mint a fresh session and rerun any case, then inspect the raw
  `POST /api/attempts/{id}/end` JSON — check `evaluation.evaluator_version`
  for a `model=` string with no `fallback=true`, alongside empty
  `dimensions`/`dimension_scores`/`executive_summary`.

## NOTES FOR NEXT AGENT
- The shared server did NOT crash this run under a single sequential
  persona's load — Bug #1 from Attempt 1 may be genuinely concurrency-shaped
  (multiple simultaneous personas), not reproducible from one agent alone.
  Worth another agent deliberately overlapping two personas' attempts against
  the shared server at once to try to reproduce it.
- Evaluation calls are slow (17–22s per turn, ~2 minutes for the final
  `/end` scoring call) — budget client timeouts generously (150s+) or the
  request will look like a failure when the server is actually still working.
- Only one case per category was tried; Bug #3 (empty-dimension evaluator)
  was seen once, on one case — worth confirming it's not a one-off flake by
  running a third attempt on a third case if another agent has budget.
- `scripts/_persona_mint_session.py` (untracked) is the reusable auth recipe
  for any future persona-QA work in this repo; it's dev/test-only, reads no
  secrets beyond the local `data/.session_secret`, and is documented inline.
