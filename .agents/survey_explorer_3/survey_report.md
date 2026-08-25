# Comprehensive Test Suite & Infrastructure Survey Report

**Agent**: `survey_explorer_3`  
**Date**: 2026-08-24  
**Project**: MBB Case Prep V2 — 10x Masterclass Debrief Upgrade  
**Baseline Test Status**: **175 passed in 3.68s** (`uv run pytest`)

---

## 1. Test Suite Organization & Execution

### 1.1 Infrastructure & Configuration
- **Pytest Configuration (`pyproject.toml`)**:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  pythonpath = ["."]
  ```
- **Test Runner Command**:
  ```bash
  uv run pytest
  # Or targeting debrief UI specifically:
  uv run pytest tests/test_debrief_ui.py -v
  ```
- **Execution Speed**: 175 tests execute cleanly in **~3.68 seconds** on Python 3.14 / pytest 8.4.2 / pluggy 1.6.0.
- **Installed Plugins**: `langsmith-0.11.1`, `anyio-4.14.2`.

### 1.2 Test Fixtures & Isolation (`tests/conftest.py`)
- **Hermetic Database Isolation (`pytest_configure` / `pytest_unconfigure`)**:
  - `conftest.py` dynamically creates a temporary directory (`tempfile.mkdtemp(prefix="casecall-tests-")`) and points `app.main.DATABASE_PATH`, `main.ACCOUNTS`, `main.STORE`, and `main.EVALUATIONS` to a throwaway SQLite database (`casecall.db`).
  - Cleans up on test unconfigure, ensuring local developer data in `data/casecall.db` is never read or mutated.
- **Authentication Lifecycle (`sign_in`, `_authentication_stays_real`)**:
  - `sign_in(client, email, name)` creates a Google-equivalent user record in `AccountStore` and sets the session cookie `SESSION_COOKIE` on the test client.
  - `_authentication_stays_real` autouse fixture guards against leaking `require_user` dependency overrides across tests, ensuring genuine authentication code paths are exercised.
- **Pre-configured Test Clients**:
  - `candidate_client`: Yields `(TestClient(main.app), user)` with a signed-in candidate (`candidate-{uuid4()}@casecall.test`).
  - `admin_client`: Yields `(TestClient(main.app), user)` signed in as `director@casecall.test` with `ADMIN_EMAILS="director@casecall.test"`.
- **Interviewer Test Double (`stub_interviewer`)**:
  - Replaces LLM interviewer with a deterministic scripted interviewer that validates and releases known facts without making external provider calls.

---

## 2. Existing Debrief UI & Endpoint Test Coverage

Across the 16 test files (175 tests), debrief UI, evaluations, and associated endpoints are covered in several distinct modules:

| Test File | Total Tests | Debrief / Evaluation Focus Areas |
|---|---|---|
| `tests/test_debrief_ui.py` | 14 | Static asset existence, HTML element IDs, CSS meter styles, JS error states, XSS safety, authenticated route delivery, 4-tier E2E structure. |
| `tests/test_evaluator_v2.py` | 13 | BCG 1.0–5.0 scale, MBB rating badges, 5 core dimensions, What The Case Wanted To Test payload, Golden MBB Rewrites, Strengths/Development areas schemas, deterministic fallback. |
| `tests/test_evaluator.py` | 26 | Evaluator engine mechanics, citation verification against transcripts, anti-leakage redaction, completeness checks, admin re-evaluation versioning, debrief route auth redirect. |
| `tests/test_e2e_workflow.py` | 5 | Scenario 1 (Full lifecycle -> debrief), Scenario 3 (Debrief delivery with 5 dimensions & rewrites), Scenario 4 (Profile trend tracking), Scenario 5 (Offline fallback). |
| `tests/test_store_persistence.py` | 15 | EvaluationStore saving, versioned history retrieval, 404/409 error status codes, user-linked evaluation queries. |
| `tests/test_api.py` | 10 | `/api/attempts` lifecycle, duplicate turn suppression, model fragment regeneration. |

### Detailed Analysis of Existing `test_debrief_ui.py`
Currently contains 14 tests structured in 4 Tiers:
- **Tier 1 (5 tests)**:
  - `test_t1_all_debrief_static_assets_exist`: Confirms `debrief.html`, `debrief.css`, `debrief.js`, `tokens.css`, `theme.js` exist.
  - `test_t1_debrief_html_executive_header_card`: Checks `#case-title`, `#report-subtitle`, `.overall-card`, `#overall-score`, `#overall-note`.
  - `test_t1_debrief_html_takeaways_and_strengths_cards`: Checks `#strength-list`, `#priority-list`, `#drill-text`, `takeaway-card`.
  - `test_t1_debrief_html_dimension_grid_and_checklist_cards`: Checks `#dimension-grid`, `#checklist`, `.checklist-legend`, `#evidence-template`.
  - `test_t1_debrief_html_topbar_and_theme_switcher`: Checks `#theme-toggle`, `#sign-out`, `#transcript-link`, `href="/cases"`.
- **Tier 2 (5 tests)**:
  - `test_t2_debrief_accessibility_semantic_landmarks_and_aria`: Semantic landmarks (`<main>`, `<header>`, `<footer>`, `aria-live="polite"`).
  - `test_t2_evidence_template_structure`: Evidence template `<figure>`, `<blockquote>`, `<figcaption>`.
  - `test_t2_debrief_js_handles_error_state_elements`: Checks `showState`, 409, 404, 503, `stateRetry`.
  - `test_t2_debrief_js_xss_protection_uses_textcontent`: Checks `textContent` assignments in `debrief.js`.
  - `test_t2_tokens_css_defines_color_and_theme_variables`: Checks CSS custom property tokens.
- **Tier 3 (3 tests)**:
  - `test_t3_debrief_page_route_serves_html`: `GET /attempts/{id}/debrief` serves 200 HTML for candidate.
  - `test_t3_debrief_js_api_contract_matches_evaluation_endpoints`: Checks endpoint strings in `debrief.js`.
  - `test_t3_debrief_css_contains_meter_and_band_styles`: Checks classes `.overall-card`, `.score-track`, `.checklist-item`.
- **Tier 4 (1 test)**:
  - `test_t4_real_world_debrief_page_delivery_scenario`: Start attempt -> access `/attempts/{id}/debrief` -> verify HTML shell.

---

## 3. Gap Analysis: What Needs to be Tested for the 10x Masterclass Debrief

The current frontend (`debrief.html`, `debrief.js`, `debrief.css`) and existing `test_debrief_ui.py` reflect the older v1 design. The following gaps must be addressed in testing:

### Gap 1: Scoring Scale Calibrated to /5 (not /10)
- **Current frontend**: `overall-out-of` displays `/10`, dimension cards show `/10`, `fill.style.width` calculates `dimension.score * 10%`, `aria-valuemax` is `"10"`.
- **New Requirement**:
  - Overall score header must display `/5`.
  - Dimension cards must display `/5` with score formatted to 1 decimal place.
  - Dimension score bars must use `aria-valuemax="5"` and fill percentage `(score / 5.0) * 100%`.
  - `DIMENSION_LABELS` in `debrief.js` must contain all 5 dimensions:
    `structuring`, `problem_solving`, `quantitative`, `synthesis`, `communication`. (Currently missing `synthesis`!).

### Gap 2: Containers & Elements for All 7 Masterclass Sections
The upgraded debrief interface must render 7 structured sections in order:
1. **Executive Header**: Overall score out of 5.0, MBB Rating Badge (`#mbb-rating-badge`), executive summary (`#executive-summary` or `.executive-summary`).
2. **"What This Case Really Wanted to Test"**: Masterclass reveal card (`#what-case-tested-card` / `#what-the-case-wanted-to-test`) containing `core_mechanism`, `pivotal_insight` / `commercial_concept`, `candidate_performance_summary`, and `candidate_vs_optimal_gap`.
3. **5 Core Dimension Cards**: `#dimension-grid` containing cards for structuring, problem_solving, quantitative, synthesis, communication with 1-5 score bars, band badges, verbatim citations, observations, and improvements.
4. **Golden MBB Rewrites**: Side-by-side or comparison section (`#golden-rewrites-section` / `#golden-rewrites-list`) rendering `candidate_turn` vs `mbb_partner_turn` for opening and closing, along with `diagnostic_notes`.
5. **Headline Strengths**: Rich strength cards (`#strength-list` / `#strengths-section`) rendering `claim`, `verbatim_quote`, and `impact`.
6. **Areas for Development**: Rich development area cards (`#priority-list` / `#development-section`) rendering `gap`, priority badge (`high`/`medium`/`low`), and `corrective_guidance`.
7. **Action Plan**: Targeted drill (`#drill-card` / `#targeted-drill`) with `title`, `duration_seconds` (e.g. 120s / 2 min), `prompt`, `focus_area`, plus Suggested Readings (`#suggested-readings-list`) with paths and titles.
8. **Observed Behaviours Checklist**: Retained at the bottom (`#checklist`).

### Gap 3: JS Robustness & Graceful Partial Data Handling
- Backend reports may return missing/null fields (e.g., candidate did not complete closing rewrite, quantitative score is unassessed, suggested readings empty, what-the-case-tested omitted).
- Tests must verify `debrief.js` handles partial/missing payloads gracefully without JavaScript `TypeError` or DOM breakage.
- Strict XSS protection must be verified: all dynamic model strings must be inserted via `textContent` (or `node(..., text)`).

---

## 4. Recommended E2E Testing Track Architecture (Tiers 1–4)

We recommend upgrading `tests/test_debrief_ui.py` (and complementing with `test_evaluator_v2.py` / `test_e2e_workflow.py`) to the full **4-Tier Testing Architecture** (target: ≥20 dedicated debrief tests, taking overall suite from 175 to ~185+ tests).

```
================================================================================
TIER 1: Static Asset, HTML Structure & Section DOM Containers Coverage (6+ tests)
--------------------------------------------------------------------------------
├── test_t1_all_debrief_static_assets_exist
├── test_t1_debrief_html_contains_all_7_masterclass_section_containers
├── test_t1_debrief_html_calibrated_to_5_point_scale
├── test_t1_debrief_js_dimension_labels_contains_all_5_dimensions
├── test_t1_debrief_js_score_meter_and_percentage_calibrated_to_5
└── test_t1_debrief_html_topbar_and_navigation_actions

TIER 2: Boundary, Negative, Robustness, Accessibility & Theme (6+ tests)
--------------------------------------------------------------------------------
├── test_t2_debrief_accessibility_semantic_landmarks_and_aria_meters
├── test_t2_debrief_js_xss_protection_strict_textcontent_usage
├── test_t2_debrief_js_partial_data_and_null_field_resilience
├── test_t2_debrief_js_handles_http_error_states_404_409_503
├── test_t2_tokens_css_defines_mbb_band_and_priority_color_tokens
└── test_t2_evidence_and_golden_rewrite_template_structures

TIER 3: Cross-Feature Integration & Contract Synchronization (5+ tests)
--------------------------------------------------------------------------------
├── test_t3_debrief_page_route_serves_html_for_authenticated_candidate
├── test_t3_debrief_page_route_redirects_unauthenticated_candidate
├── test_t3_debrief_js_api_contract_matches_evaluation_report_schema
├── test_t3_debrief_css_styles_all_7_masterclass_card_components
└── test_t3_evaluation_api_payload_synchronization_with_debrief_views

TIER 4: Real-World Workload Scenarios & Fallback Workflows (4+ tests)
--------------------------------------------------------------------------------
├── test_t4_full_flow_attempt_to_10x_masterclass_debrief_page
├── test_t4_debrief_rendering_with_complete_rich_mbb_report
├── test_t4_debrief_rendering_with_partial_or_degraded_report
└── test_t4_offline_evaluator_fallback_report_delivery_scenario
================================================================================
```

### Detailed Tier Specifications

#### Tier 1: HTML Structure, DOM Containers & JS Constants
1. **`test_t1_all_debrief_static_assets_exist`**:
   - Asserts `debrief.html`, `debrief.css`, `debrief.js`, `tokens.css`, `theme.js` exist and have non-trivial size (`stat().st_size > 1000`).
2. **`test_t1_debrief_html_contains_all_7_masterclass_section_containers`**:
   - Asserts presence of DOM container IDs/classes in `debrief.html`:
     - Section 1: `#case-title`, `#overall-score`, `.overall-card`, `#mbb-rating-badge`, `#executive-summary`.
     - Section 2: `#what-case-tested-card` (or `#what-case-wanted-to-test`), `#core-mechanism`, `#pivotal-insight`, `#candidate-summary`, `#optimal-gap`.
     - Section 3: `#dimension-grid` (5 dimensions).
     - Section 4: `#golden-rewrites-section` / `#golden-rewrites-list`.
     - Section 5: `#strength-list` / `#strengths-section`.
     - Section 6: `#priority-list` / `#development-section`.
     - Section 7: `#drill-card` (or `#targeted-drill`), `#suggested-readings-list`.
     - Section 8: `#checklist` (Observed Behaviours).
3. **`test_t1_debrief_html_calibrated_to_5_point_scale`**:
   - Asserts `"/5"` is present in `.overall-out-of` and `"/10"` is completely absent from `debrief.html`.
4. **`test_t1_debrief_js_dimension_labels_contains_all_5_dimensions`**:
   - Parses/searches `DIMENSION_LABELS` in `debrief.js` and asserts presence of:
     - `structuring`
     - `problem_solving`
     - `quantitative`
     - `synthesis`
     - `communication`
5. **`test_t1_debrief_js_score_meter_and_percentage_calibrated_to_5`**:
   - Asserts `aria-valuemax` is set to `"5"` in `debrief.js`.
   - Asserts score bar width calculation divides by `5` (e.g. `(score / 5) * 100` or `score * 20%`), not `/ 10`.
   - Asserts `dimension-out-of` shows `"/5"`.

#### Tier 2: Boundary, Negative, Robustness, Accessibility & Security
1. **`test_t2_debrief_accessibility_semantic_landmarks_and_aria_meters`**:
   - Validates `<main class="debrief">`, `<header>`, `<footer>`, `role="meter"`, `aria-valuemin="1"` (or `"0"`), `aria-valuemax="5"`, `aria-valuenow`, `aria-live="polite"`.
2. **`test_t2_debrief_js_xss_protection_strict_textcontent_usage`**:
   - Checks that dynamic user/model data is strictly set via `textContent` or `node(tag, class, text)` helper.
   - Asserts no unsanitized `innerHTML = ...` containing payload strings.
3. **`test_t2_debrief_js_partial_data_and_null_field_resilience`**:
   - Inspects `debrief.js` for defensive rendering checks:
     - Safe access to `report.what_the_case_wanted_to_test` (e.g. `if (!whatTested) ...`).
     - Safe iteration over `report.golden_rewrites || []`.
     - Safe iteration over `report.strengths || report.headline_strengths || []`.
     - Safe iteration over `report.areas_for_development || report.priority_improvements || []`.
     - Safe handling of `report.targeted_drill` / `report.drill_detail`.
     - Safe handling of `report.suggested_readings || []`.
4. **`test_t2_debrief_js_handles_http_error_states_404_409_503`**:
   - Asserts `debrief.js` has distinct branches for HTTP 409 (attempt ongoing), 404 (not found), 503 (evaluator busy / retry), and generic errors.
5. **`test_t2_tokens_css_defines_mbb_band_and_priority_color_tokens`**:
   - Asserts `tokens.css` defines color variables for rating badges, score meters, priority tags, and light/dark theme variables.

#### Tier 3: Cross-Feature Integration & Contract Synchronization
1. **`test_t3_debrief_page_route_serves_html_for_authenticated_candidate`**:
   - Authenticated candidate calls `GET /attempts/{id}/debrief` -> 200 OK, `text/html`.
2. **`test_t3_debrief_page_route_redirects_unauthenticated_candidate`**:
   - Anonymous request to `GET /attempts/{id}/debrief` -> 303 Redirect to `/login?next=...`.
3. **`test_t3_debrief_js_api_contract_matches_evaluation_report_schema`**:
   - Validates that JS field references match the backend `EvaluationReport` Pydantic model (`executive_summary`, `what_the_case_wanted_to_test`, `core_mechanism`, `pivotal_insight`, `candidate_performance_summary`, `candidate_vs_optimal_gap`, `golden_rewrites`, `candidate_turn`, `mbb_partner_turn`, `diagnostic_notes`, `strengths`, `areas_for_development`, `targeted_drill`, `suggested_readings`).
4. **`test_t3_debrief_css_styles_all_7_masterclass_card_components`**:
   - Verifies CSS rules exist for:
     - Executive header & overall score badge (`.overall-card`, `.overall-value`, `.mbb-rating-badge`)
     - What case tested card (`.what-tested-card` / `.crux-card`)
     - Dimension breakdown (`.dimension-grid`, `.dimension-card`, `.score-track`, `.score-fill`)
     - Golden rewrites (`.golden-rewrite-card`, `.mbb-partner-turn`, `.candidate-turn`)
     - Strengths & Development areas (`.strength-item`, `.development-item`, `.priority-badge`)
     - Action plan & drill (`.drill-card`, `.reading-item`)
     - Checklist (`.checklist-card`, `.checklist-item`)

#### Tier 4: Real-World Workload Scenarios & User Journeys
1. **`test_t4_full_flow_attempt_to_10x_masterclass_debrief_page`**:
   - Start attempt on `meridian-cold-chain-v1` -> conduct turns -> end attempt -> verify evaluation API returns full rich report -> verify debrief page delivers all 7 section DOM anchors.
2. **`test_t4_debrief_rendering_with_complete_rich_mbb_report`**:
   - Verifies end-to-end API response containing all 7 sections with 5 dimensions, distinction badge, golden rewrites, and readings.
3. **`test_t4_debrief_rendering_with_partial_or_degraded_report`**:
   - Simulates attempt with sparse data (e.g. single turn, missing rewrites); verifies API returns valid schema and debrief page renders without errors.
4. **`test_t4_offline_evaluator_fallback_report_delivery_scenario`**:
   - Evaluator agent offline; attempt ends and triggers `FallbackCaseEvaluator` producing BCG 1.0–5.0 report; verifies API serves payload and debrief HTML contains all required containers.

---

## 5. Summary & Actionable Recommendations for Implementation & Testing

1. **Implement scale fix first**:
   - Update `app/static/debrief.html` from `/10` to `/5`.
   - Update `app/static/debrief.js` `DIMENSION_LABELS` to include `synthesis: "Synthesis"`.
   - Update `debrief.js` meter and percentage calculations to base-5 (`aria-valuemax="5"`, `(score / 5) * 100%`).
2. **Implement 7 masterclass section containers in `debrief.html` & renderer in `debrief.js`**:
   - Follow clean semantic HTML structure and CSS classes.
   - Use `textContent` exclusively for all dynamic data.
   - Add defensive null-coalescing for every optional field.
3. **Upgrade `tests/test_debrief_ui.py`**:
   - Expand from 14 tests to 20+ tests covering all 4 Tiers.
   - Ensure all 175 existing baseline tests + new tests pass (`uv run pytest`).
