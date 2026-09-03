# OUTBOX — opencode

STATUS: DONE

## WHAT I DID
Executed ROADMAP item 6 ("[P1] Render the authored case insight, not the prompt
question") in docs/campaign/ROADMAP.md, on top of a fast-forward sync with the
integration branch (realtime-voice-ptt @ 9214226), so items 1-3 (evaluator
reliability gate, framework-turn structuring, contention 503) are all in the
base I built on.

The P1-5 bug had two live paths and both are now closed:

1. Fallback evaluator (app/evaluator.py, generate_fallback_evaluation): when the
   case essence could not be loaded it substituted `session.case.objective`
   (the decision question) for `core_mechanism` and a generic constant for
   `pivotal_insight` — exactly the "copied question + generic insight" failure
   the intermediate persona reported (BUG-6). It now sources both fields only
   from the authored `case_essence` and leaves them empty when the package has
   none (the debrief card then hides those slots instead of fabricating filler).
2. The candidate-gap template `The optimal MBB path isolates {core_mechanism}
   via ...` spliced question-shaped text into a sentence ("...isolates Why has
   ... via ex-ante hypothesis testing"). Replaced with `optimal_path_gap()`,
   which renders three grammatical shapes: mechanism statement (existing
   template, trailing period trimmed), question-shaped (renders as
   `The optimal MBB path answers the case question (...) by isolating ...`),
   and empty mechanism (self-contained hypothesis-first line). Also guards the
   fallback partner-closing rewrite so an empty mechanism omits the clause
   instead of printing "address the core economic mechanism of .".
3. LLM writer path: added `apply_authored_essence()` called deterministically
   in `LangChainCaseEvaluator.evaluate()` after boundary enforcement. Whatever
   the writer put in the card, the authored essence's core_mechanism and
   pivotal_insight win (and the card is created from essence if the writer
   omitted it). With no essence on disk it is a no-op, so evaluator-authored
   content for essence-less contributed cases survives. The decision question
   now appears only as context (objective/opening surfaces), never as the
   mechanism.
4. debrief.js: the "What this case was testing" card now collapses individual
   empty masterclass slots (micro-label + blank line) via `fillInsightSlot()`,
   so a partially-filled card renders only authored content.

FILES CHANGED
- app/evaluator.py (essence-only sourcing, `is_question_shaped` /
  `optimal_path_gap` / `apply_authored_essence` helpers, LLM-path override)
- app/static/debrief.js (`fillInsightSlot`, empty-slot collapse)
- tests/test_evaluator_v2.py (5 new tests: fallback acceptance vs authored
  essence, question-shaped gap grammar, gap template unit shapes,
  is_question_shaped unit coverage, LLM writer override reproducing BUG-6,
  plus card-creation and no-essence no-op cases)
- tests/test_debrief_ui.py (2 new tests: JS slot-collapse contract, and the
  roadmap acceptance test driving POST /turn, POST /end and GET
  /api/attempts/{id}/evaluation end to end asserting the authored mechanism
  and pivotal insight, never the decision question)

Committed incrementally on agent/opencode: 933c188 (implementation),
431bf6a (evaluator acceptance tests), a5f1121 (debrief surface tests).

HOW TO VERIFY
- `.venv/bin/pytest tests/ -x -q` → 441 passed, 1 xfailed (verified green
  before the final commit; the three items above were also run file-by-file).
- Roadmap acceptance, item by item: read
  tests/test_evaluator_v2.py::test_case_insight_card_carries_the_authored_essence_not_the_prompt_question
  and tests/test_debrief_ui.py::test_t5_case_insight_card_serves_the_authored_essence —
  both use meridian-cold-chain-v1, whose decision question ("Why has EBITDA
  margin fallen, and what should the CEO do?") differs from its authored
  essence, and assert the card carries the essence verbatim (normalized) with
  no "isolates Why" splice.
- Manual: `git show 933c188` for the whole implementation diff.

NOTES FOR NEXT AGENT
- Item 7 (transcript-linked evidence) and item 8 (closing rewrite) are the
  natural follow-ons; item 8 will rework the same fallback partner-closing
  block I touched — my change there is only the empty-mechanism guard, feel
  free to supersede it.
- The writer prompt (evaluation/prompts/writer_system.md) still asks the writer
  to author the card fields; the deterministic override makes that safe, but if
  you want the writer to stop wasting tokens paraphrasing the essence, add a
  line there pointing at case_essence (out of item 6's declared file list, so
  I left it).
- `is_question_shaped` matches trailing "?" or a leading interrogative word
  (why/how/what/should/which/where/when/who/will/can/could/is/are/do/does/did).
  A mechanism sentence starting with e.g. "Did the client..." is treated as a
  question by design.
- The integration branch moved during the night: I merged realtime-voice-ptt
  into agent/opencode (fast-forward, no rebase) before starting, so this branch
  should merge cleanly after items 4/5 land.
- Untracked and intentionally not committed: .venv, _society/INBOX.md.
