# Milestone 1 Assignment: Case Corpus Expansion & Essence Enrichment

## Mission
Enrich all 12 reservoir cases with full 5-file packages (`case_essence`, `issue-tree.yaml`, `facts.yaml` with hidden diagnosis & verified facts, `conversation-policy.yaml`, `validation.md`), create multi-school exemplar case library across IIM Ahmedabad, IIM Bangalore, IIM Calcutta, and ISB (~50-60 structured cases), and update case loader/models in `app/`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A forensic auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Rules & Guidelines
- Read `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/ORIGINAL_REQUEST.md`, `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/PROJECT.md`, and `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/explorer_survey_corpus/survey_report.md`.
- Working Directory: `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/worker_m1_corpus`
- Write ownership: `reservoir/`, `corpus/`, `app/models.py`, `app/case_loader.py`.
- Run pytest and case validation to verify all cases load cleanly without errors.
- Write your completion report in `handoff.md` and send a message when done.

## 2026-08-24T08:47:50Z
You are Worker M1 (Case Corpus Expansion & Essence Enrichment).
Your working directory is /Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/worker_m1_corpus.
Project root is /Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2.

Tasks:
1. Update case schema models in app/models.py and app/case_loader.py to support the structured `case_essence` schema (`core_mechanism`, `what_the_case_wanted_to_test`, `pivotal_insight`, `common_traps`, `takeaway_lesson`, `suggested_readings`).
2. Enrich all 12 reservoir cases (`reservoir/`) with full 5-file packages (`case.yaml`, `facts.yaml` with hidden diagnosis & verified facts, `issue-tree.yaml`, `conversation-policy.yaml`, `validation.md`) including complete `case_essence` and knowledge base linkages.
3. Curate and ingest the multi-school exemplar case library (~50-60 cases across IIM-A, IIM-B, IIM-C, ISB) under `corpus/` with structured essence metadata, verified facts, and issue trees.
4. Run validation and pytest to ensure all cases load and validate cleanly.

