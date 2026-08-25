## 2026-08-24T09:27:35Z
You are survey_spec_miner_2.
Your working directory is /Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/survey_spec_miner_2.
Read /Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/ORIGINAL_REQUEST.md first.

Your mission:
Investigate the backend evaluator models, schemas, and endpoints:
- `app/evaluator.py`
- `app/main.py`
- `app/models.py`
- `app/database.py`
- and any case corpus or evaluation data structures.

Extract:
1. Exact Pydantic schema for `EvaluationReport`, `WhatTheCaseWantedToTest`, `DimensionScore`, `GoldenRewrite`, `StrengthItem`, `DevelopmentAreaItem`, `TargetedDrillPayload`, `ChecklistItem`, and top-level response payload for `GET /api/attempts/{id}/evaluation`.
2. All field names, types, optionality/nullability/defaults, and possible values (e.g. bands, priorities, phases).
3. Payload format of `GET /api/attempts/{id}`.
4. Edge cases where fields may be null, empty list, score 0, or omitted.

Write your specification analysis to `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/survey_spec_miner_2/survey_report.md` and write a handoff report to `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/survey_spec_miner_2/handoff.md`.
Send a message when finished with the report paths and key takeaways.
