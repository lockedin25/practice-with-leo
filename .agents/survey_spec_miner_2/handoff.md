# Handoff Report: Evaluator Models, Schemas & API Endpoints

**Agent:** `survey_spec_miner_2`  
**Working Directory:** `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/survey_spec_miner_2`  
**Report Document:** `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/survey_spec_miner_2/survey_report.md`  
**Target Milestone:** Debrief Web Interface Upgrade Specification Discovery  

---

## 1. Observation

Direct code inspection of backend files revealed the following authoritative definitions and behaviors:

1. **Pydantic Schemas (`app/evaluator.py`, lines 87–274):**
   - `Citation` (lines 87–90): `message_index: int`, `quote: str`.
   - `DimensionScore` (lines 92–100): `name: str`, `score: float` (1.0–5.0 scale), `band: str` (`"Below Bar"`, `"Meets Bar"`, `"Top 1% MBB"`), `evidence: list[Citation]`, `observations: list[str]`, `improvements: list[str]`, `confidence: Literal["high", "medium", "low"]`, `notes: str`.
   - `WhatTheCaseWantedToTest` (lines 103–109): `core_mechanism: str`, `commercial_concept: str`, `pivotal_insight: str`, `candidate_performance_summary: str`, `candidate_vs_optimal_gap: str`.
   - `GoldenRewriteTurn` (lines 114–139): `stage: Literal["opening", "closing", "synthesis"]`, `phase: Literal["opening", "closing", "synthesis"]`, `candidate_turn: str`, `candidate_message_index: int | None`, `mbb_partner_turn: str`, `golden_mbb_turn: str`, `diagnostic_notes: list[str]`, `consulting_craft_delta: list[str]`.
   - `StrengthItem` (lines 144–148): `claim: str`, `verbatim_quote: str`, `impact: str`.
   - `DevelopmentAreaItem` (lines 150–154): `gap: str`, `priority: Literal["high", "medium", "low"]`, `corrective_guidance: str`.
   - `TargetedDrillPayload` (lines 156–161): `title: str`, `duration_seconds: int` (default 120), `prompt: str`, `focus_area: str`.
   - `SuggestedReading` (lines 163–175): `title: str`, `path: str`, `why_relevant: str`, `relevance_reason: str`.
   - `ChecklistItem` (lines 181–201): `id: str`, `marker_id: str`, `title: str`, `description: str`, `status: Literal["demonstrated", "missed", "partial", "not_applicable"]`, `evidence: list[Citation]`, `note: str`.
   - `EvaluationReport` (lines 206–274): root container with fields for `attempt_id`, `evaluator_version`, `overall_score`, `mbb_rating_badge`, `overall_band`, `executive_summary`, `what_the_case_wanted_to_test`, `dimensions`, `dimension_scores`, `checklist`, `observed_behaviors`, `golden_rewrites`, `strengths`, `headline_strengths`, `areas_for_development`, `priority_improvements`, `targeted_drill`, `next_drill`, `drill_detail`, `suggested_readings`.

2. **Rating Badge & Band Functions (`app/evaluator.py`, lines 62–82):**
   - `compute_mbb_rating_badge(score)`: $\ge 4.5 \rightarrow \text{"Distinction"}$, $\ge 3.8 \rightarrow \text{"Strong Pass"}$, $\ge 2.8 \rightarrow \text{"Meets Bar"}$, $\ge 2.0 \rightarrow \text{"Developing"}$, $< 2.0 \rightarrow \text{"Needs Substantial Practice"}$.
   - `compute_overall_band(score)`: $\ge 3.8 \rightarrow \text{"Top 1% MBB"}$, $\ge 2.5 \rightarrow \text{"Meets Bar"}$, $< 2.5 \rightarrow \text{"Below Bar"}$.

3. **API Endpoints (`app/main.py`, lines 219–235, 351–373):**
   - `GET /api/attempts/{attempt_id}`: returns `candidate_view()` dictionary (`id`, `case`, `mode`, `stage`, `messages`, `facts`, `case_started`, `ended`) plus `debrief_url`, `evaluation_url`, and when evaluated, `score`, `mbb_rating_badge`, and `evaluation`.
   - `GET /api/attempts/{attempt_id}/evaluation`: returns `{ "evaluator_version": str, "created_at": str, "user_id": str, "debrief_url": str, "overall": { "overall": float, "assessed_dimensions": list, "excluded_dimensions": list }, "report": { ...EvaluationReport fields... } }`.

4. **Persistence Layer (`app/store.py`, lines 451–589):**
   - `EvaluationStore` stores `report_json` under primary key `(attempt_id, evaluator_version)` in SQLite table `evaluations`.

5. **Test Suite Status (`uv run pytest`):**
   - 175 tests collected, 175 passing in 3.40 seconds across all test modules.

---

## 2. Logic Chain

1. **Scale Mapping:** The backend evaluator and rubric (`rubric.yaml`) strictly calibrate on a 1.0–5.0 scale. The current frontend (`debrief.html`, `debrief.js`) has a hardcoded `/10` scale in header and dimension score meters. Updating this requires aligning frontend meters to `aria-valuemax="5"` and percentage calculation to `(score / 5) * 100%`.
2. **Dimension Coverage:** `rubric.yaml` and `app/evaluator.py:DIMENSION_NAMES` define exactly 5 dimensions: `structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`. Frontend `DIMENSION_LABELS` in `debrief.js` currently omits `synthesis` (only has 4 dimensions). All 5 must be present in the map.
3. **Masterclass Sections Contract:** The backend already populates all 7 masterclass sections:
   - Executive header (`overall_score`, `mbb_rating_badge`, `executive_summary`)
   - "What the Case Wanted to Test" (`what_the_case_wanted_to_test`)
   - 5 Dimension cards (`dimensions`)
   - Golden MBB Rewrites (`golden_rewrites`)
   - Headline Strengths (`strengths` / `headline_strengths`)
   - Areas for Development (`areas_for_development` / `priority_improvements`)
   - Action Plan (`drill_detail` / `targeted_drill`, `suggested_readings`)
   - Observed Behaviors Checklist (`checklist` / `observed_behaviors`)
4. **Data Redundancy and Syncing:** `EvaluationReport` uses Pydantic validators (`_sync_report_data`, `_sync_fields`, `_sync_ids`, `_sync_relevance`) to ensure both list and dict representations (`dimensions` and `dimension_scores`), as well as alias fields (`stage`/`phase`, `mbb_partner_turn`/`golden_mbb_turn`, `diagnostic_notes`/`consulting_craft_delta`, `why_relevant`/`relevance_reason`, `targeted_drill`/`next_drill`) are reliably populated.
5. **Resilience & Degraded States:** If an attempt contains no quantitative calculation or no candidate turns, fields remain non-null or return structured defaults (score 1.0 floor, low confidence, empty lists). The frontend must check for presence before rendering to prevent TypeError exceptions.

---

## 3. Caveats

- **Frontend Implementation Scope:** This specification investigation focuses strictly on backend models, endpoints, persistence, and contract definitions. No frontend implementation was performed by this agent (maintaining read-only miner boundary).
- **LLM Provider Availability:** While LLM writer and planner models use OpenRouter (`anthropic/claude-sonnet-4.6`), tests and offline environments use `FallbackCaseEvaluator`, which guarantees deterministic evaluation following the identical Pydantic schema contract.

---

## 4. Conclusion

The backend evaluator models, persistence, and API endpoints are 100% ready and proven by 175 passing tests. All required schemas (`EvaluationReport`, `WhatTheCaseWantedToTest`, `DimensionScore`, `GoldenRewriteTurn`, `StrengthItem`, `DevelopmentAreaItem`, `TargetedDrillPayload`, `SuggestedReading`, `ChecklistItem`) and the exact payload schemas for `GET /api/attempts/{id}/evaluation` and `GET /api/attempts/{id}` have been completely extracted, documented, and cross-referenced in `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/survey_spec_miner_2/survey_report.md`.

---

## 5. Verification Method

To verify these discoveries independently:
1. **Run test suite:**
   ```bash
   uv run pytest tests/test_evaluator.py tests/test_evaluator_v2.py tests/test_debrief_ui.py
   ```
2. **Inspect schema definitions:**
   - Review `app/evaluator.py` lines 87–274.
   - Review `app/main.py` lines 351–373.
   - Review `evaluation/rubric.yaml` and `evaluation/checklist.yaml`.
3. **Inspect survey report:**
   - Open `/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/.agents/survey_spec_miner_2/survey_report.md`.
