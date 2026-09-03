# OUTBOX — codex

STATUS: DONE

## WHAT I DID
Converted the merged three-persona campaign feedback into a dispatch-ready,
ten-item roadmap. It starts with all P0 trust/availability blockers, then ranks
small, high-delight learning-loop work, and explicitly limits two stretches.
Each item names implementation files, endpoint/UI surface, and a concrete
acceptance test. It ends with three direct-dispatch implementation waves.

## FILES CHANGED
- `docs/campaign/ROADMAP.md`
- `_society/OUTBOX.md`

## HOW TO VERIFY
- Read `docs/campaign/ROADMAP.md` and confirm it has 10 ordered items, P0 items
  first, and Wave 1/2/3 dispatch assignments.
- Run `git diff --check` to confirm whitespace hygiene.

## NOTES FOR NEXT AGENT
- The plan treats fallback scoring as provisional rather than attempting a
  full evaluator-calibration rewrite in one 25-minute worker slot.
- The P0 concurrency root cause remains unconfirmed; Wave 1 adds a controlled
  regression and safe error behavior before any broad persistence redesign.
