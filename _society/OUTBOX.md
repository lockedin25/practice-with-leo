# OUTBOX — opencode

STATUS: DONE

## WHAT I DID
P4 feedback-bag synthesis task. Read the three merged persona reports
(docs/campaign/persona-beginner.md, persona-intermediate.md, persona-expert.md
in the main checkout, as merged by the foreman) plus my INBOX handoffs
(claude's beginner outbox, codex's expert outbox), and consolidated everything
into docs/campaign/FEEDBACK.md:

- 20 deduplicated, severity-ranked findings: 4 P0, 10 P1, 6 P2, each with
  source persona(s), evidence (endpoint/attempt/turn/quote), and fix direction.
- Evaluator calibration verdict with all numbers quoted: scores do NOT
  separate the personas — beginner 3.48 vs expert 3.47/3.57 vs intermediate
  3.54/3.61, all "Meets Bar"; "Top 1% MBB" communication badge went to the
  beginner (4.2) while the expert got 3.6; only mover was the abandoned
  1-turn attempt (2.45).
- Ranked top-13 UX friction list plus the positive-friction note.
- Raw unfiltered feature-wish list (all three personas, including honorable
  mentions) with cross-persona clusters.
- Appendix A: dedup map tracing each consolidated finding back to source
  report sections, plus explicitly-not-carried test-setup limitations.

Severity calls where personas disagreed: intermediate rated the missing
dev/test auth path P0, beginner P1 — I ranked it P1 (blocks agents/dogfooding,
not real candidates) with the disagreement noted inline.

## FILES CHANGED
- docs/campaign/FEEDBACK.md (new, committed)
- _society/OUTBOX.md (this handoff)

## HOW TO VERIFY
- `git show` on agent/opencode; read docs/campaign/FEEDBACK.md top to bottom.
- Spot-check three load-bearing numbers against the source reports:
  beginner overall 3.48 vs self ~1.5 (persona-beginner.md calibration table),
  expert 3.47/3.57 vs self 4.46/4.60 (persona-expert.md calibration table),
  structuring-on-greeting trace evaluator.py:~1021 (persona-intermediate.md BUG-3).

## NOTES FOR NEXT AGENT
- P5 (roadmap) should treat P0-1 (silent fallback evaluator + two-direction
  miscalibration), P0-3 (badge validation), and P1-10 (in-case feedback) as the
  spine — the feature-wish clusters in FEEDBACK.md section 4 map directly onto
  them.
- Bug P0-2 (concurrent-load outage) is still unreproduced; beginner suggested
  deliberately overlapping two personas' attempts against one server. Nobody
  has budget for that yet.
- scripts/_persona_mint_session.py (untracked, claude's) is the reusable auth
  recipe if any future agent needs a session; FEEDBACK.md P1-1 recommends
  making it (or an equivalent) a documented, committed dev tool.
