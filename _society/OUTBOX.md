STATUS: DONE

WHAT I DID
Implemented ROADMAP item 2 ("Score fallback structuring from the actual
framework turn"). The deterministic fallback evaluator previously graded
the `structuring` dimension against the literal first candidate turn. When
that turn was a bare greeting ("Hi Leo, good to be here"), no restatement
or MECE keyword matched, evidence stayed empty, and
`dimension_counts_toward_score` silently dropped `structuring` out of the
weighted overall.

Added `_select_structuring_turn()` in app/evaluator.py: scans all candidate
turns, returns the first one showing restatement or strong (>=2 word) MECE
signal, falling back to the turn with the highest signal strength, and
finally to the literal first turn if nothing matches at all. Also added
`_word_boundary_excerpt()` so evidence quotes never open/close mid-word
(previously a raw character-offset slice could cut a word in half).
`generate_fallback_evaluation` now grades structuring, MECE, and industry
tailoring against the selected turn instead of always the opening turn.

FILES CHANGED
- app/evaluator.py (+68 lines): `_select_structuring_turn`,
  `_word_boundary_excerpt`, and the structuring block in
  `generate_fallback_evaluation` rewired to use them.
- tests/test_evaluator.py (+27 lines): new test
  `test_fallback_structures_from_the_actual_framework_turn` — greeting
  turn followed by a real revenue/cost, price/volume framework turn;
  asserts score > 1.0, evidence cites message_index 3 (the framework
  turn, not the greeting), and `structuring` is absent from
  `excluded_dimensions`.

Commit: 04aada7 on agent/claude.

HOW TO VERIFY
.venv/bin/pytest tests/test_evaluator.py -q   # 27 passed
.venv/bin/pytest tests/ -q                    # 425 passed, 1 failed, 1 warning

Acceptance test from ROADMAP.md item 2 is met by
test_fallback_structures_from_the_actual_framework_turn (see above).

NOTES FOR NEXT AGENT
The full-suite run has ONE pre-existing failure unrelated to this task:
tests/test_case_progress.py::test_start_case_control_submits_a_readiness_turn_to_open_the_timer_gate
fails because app/static/app.js (committed at d39cc5a, before this
session) has no `syncTimer(attempt);` call — that's ROADMAP item 4
("Show the candidate where they are in the case"), not item 2. It was
already failing before I touched anything (confirmed both files were
already committed, not part of my diff). Did not touch it — out of scope
for item 2 and outside this run's budget. Whoever picks up item 4 should
start there.

tests/test_evaluator_v2.py was left untouched: it only exercises
mocked/fixture dimension data, never the real `generate_fallback_evaluation`
structuring path, so there was no gap to close there for this item.
