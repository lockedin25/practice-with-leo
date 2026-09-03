# CaseCall "Leo" v2 — Day-Shift Persona Campaign Report

**Date:** Thu 03 Sep 2026 · **Branch:** `realtime-voice-ptt` · **Final suite:** 441 passed, 1 xfailed (pre-existing WIP gate test)
**Method:** three AI personas (beginner / intermediate / expert) each ran real practice attempts against Leo, filed QA reports; findings were consolidated, prioritized into a roadmap, and the top blockers were fixed and merged the same morning.

## What the personas found (verdict on Leo)

Three independent reports live in `docs/campaign/`:

- **`persona-beginner.md`** (2nd-year MBA, zero case experience, 2 live attempts): Leo's scoring can be wildly over-generous — a shaky beginner run was rated **3.48 "Meets Bar"** with Communication **4.2 "Top 1% MBB"**. Root cause: the LLM evaluator silently fell back to a keyword scorer (`fallback=true`), which is never disclosed to the candidate.
- **`persona-intermediate.md`** (Nikhil Verma, 2 live attempts): no supported dev/test auth path (every non-browser client must forge a session); quantitative scoring rewards "math-looking" turns without checking arithmetic; debrief evidence citations point at the wrong turns.
- **`persona-expert.md`** (partner-level, live attempt): evaluator calibration was accurate in-band for strong structure, but Golden Rewrites were generic template text not tied to the candidate's actual words, and ordinary concurrent load triggered a platform-wide 500 outage.

Consolidated: `docs/campaign/FEEDBACK.md` — 4 P0 blockers, 10 P1 majors, plus P2 wishlist.
Prioritized plan: `docs/campaign/ROADMAP.md` — 10 scoped items in 3 waves.

## Fixes shipped today (merged to `realtime-voice-ptt`, suite green after each merge)

| # | Fix | Type |
|---|-----|------|
| 1 | **Reliability gate for evaluations** — fallback/empty reports are marked `provisional`/`incomplete`; the debrief shows a "Provisional evaluation" banner instead of a fake score/badge | P0 |
| 2 | **Structuring scored from the real framework turn** — the fallback no longer grades the greeting; structuring rejoins the weighted overall | P0 |
| 3 | **SQLite write contention made survivable** — lock exhaustion now returns a retryable 503 JSON instead of a bare 500; two-client contention regression test added | P0 |
| 4 | **Abandoned vs scored endings** — readiness-only exits no longer poison profile trends/score averages | P1 |
| 5 | **Authored case-insight card** — "what the case really wanted to test" now renders the case's authored mechanism/insight, not the prompt question; grammatical gap templates | P1 |

Plus the campaign infrastructure itself: three persona QA reports, the consolidated feedback bag, and the 10-item roadmap.

## Known issues / deferred

- **Roadmap item 4 (in-room phase & fact progress rail)** — failed twice (worker turn-budget), deferred; partial work sits uncommitted in `.worktrees/claude`.
- **Wave 3 items 7-10** (clickable evidence, transcript-specific Golden Rewrite, difficulty filters, transcript export) — not started; roadmap is ready for a follow-up session.
- Shared dev server fd-leak under sustained load (restarted during the campaign); worth a leak-hunt task.
- `pytest` hits macOS's 256 fd soft limit (EMFILE in tmpdir) — run with `ulimit -n 2048`.
- Minor: evaluator_version/fallback metadata still not surfaced in the UI beyond the new banner; stray worker dev servers on :6520/:6530 left running.

## Society run log

- 08:26 personas dispatched · 09:06 P2+P3 merged · 09:55 P1 merged (retry 2) · 10:14 P4 feedback bag merged · 10:25 P5 roadmap merged · 10:50 Wave 1 (I1+I2+I3) merged · 11:13 I5 merged · 11:23 I6 merged · 11:28 foreman test-interaction fix → 441 green.
- Task ledger: 10 tasks done, 1 (I4) failed after 2 retries and deferred. Full history: `society.py report` in `~/Desktop/Projects/agent-society`.
