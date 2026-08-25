"""E2E Test Suite: 10x Debrief Web Interface Structure, 7 Masterclass Cards & Theme Integration.

Validates:
- debrief.html structure and all 7 masterclass cards/sections.
- debrief.css layout, responsive styling, score bars, and badge colors.
- debrief.js rendering pipeline, error states, and XSS safety (textContent).
- tokens.css design system tokens and light/dark theme switcher in theme.js.
- API payload compatibility between /api/attempts/{id}/evaluation and frontend renderer.
- Accessibility markers (ARIA roles, meters, semantic landmarks).
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

import app.main as main
from conftest import sign_in


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"
TEMPLATE_PATH = ROOT / "app" / "templates" / "debrief.html"
CSS_PATH = STATIC_DIR / "debrief.css"
JS_PATH = STATIC_DIR / "debrief.js"
TOKENS_PATH = STATIC_DIR / "tokens.css"
THEME_JS_PATH = STATIC_DIR / "theme.js"


# =============================================================================
# TIER 1: HTML & Static File Structure Coverage Tests (≥5 tests)
# =============================================================================

def test_t1_all_debrief_assets_exist() -> None:
    """Verify the served template and its frontend assets exist and are non-empty."""
    assert TEMPLATE_PATH.is_file(), "debrief template missing"
    assert CSS_PATH.is_file(), "debrief.css missing"
    assert JS_PATH.is_file(), "debrief.js missing"
    assert TOKENS_PATH.is_file(), "tokens.css missing"
    assert THEME_JS_PATH.is_file(), "theme.js missing"
    assert TEMPLATE_PATH.stat().st_size > 1000
    assert CSS_PATH.stat().st_size > 1000
    assert JS_PATH.stat().st_size > 1000


def test_t1_debrief_html_executive_header_card() -> None:
    """Verify Executive Header card elements (#case-title, #overall-score, .overall-card)."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="case-title"' in content
    assert 'id="report-subtitle"' in content
    assert 'class="overall-card"' in content
    assert 'id="overall-score"' in content
    assert 'id="overall-note"' in content


def test_t1_debrief_template_has_a_clear_return_to_practice_room() -> None:
    """The review surface has an explicit, always-visible exit to live practice."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'class="debrief-return"' in content
    assert 'class="debrief-return-link" href="/practice"' in content
    assert "Back to practice room" in content


def test_t1_debrief_html_takeaways_and_strengths_cards() -> None:
    """Verify Strengths, Priority Improvements, and Next Drill containers."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="strength-list"' in content
    assert 'id="priority-list"' in content
    assert 'id="drill-text"' in content
    assert 'takeaway-card' in content


def test_t1_debrief_html_dimension_grid_and_checklist_cards() -> None:
    """Verify Dimension Breakdown grid and Observed Behaviors checklist."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="dimension-grid"' in content
    assert 'id="checklist"' in content
    assert 'class="checklist-legend"' in content
    assert 'id="evidence-template"' in content


def test_t1_debrief_uses_the_shared_site_header() -> None:
    """Debrief supplies page content while base.html owns global navigation."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert '{% extends "base.html" %}' in content
    assert '<header class="navbar">' not in content
    assert 'id="transcript-link"' not in content
    assert 'Back to practice room' in content


# =============================================================================
# TIER 2: Boundary, Negative & Accessibility Tests (≥5 tests)
# =============================================================================

def test_t2_debrief_accessibility_semantic_landmarks_and_aria() -> None:
    """Boundary test: Ensure semantic HTML landmarks and ARIA attributes are present."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "<main" in content and "</main>" in content
    assert "<header" in content and "</header>" in content
    assert "<footer" in content and "</footer>" in content
    assert 'aria-label="Case debrief"' in content or 'aria-label="Leo Home"' in content
    assert 'aria-live="polite"' in content  # toast alerts live region


def test_t2_evidence_template_structure() -> None:
    """Boundary test: Evidence template contains figure, blockquote, and figcaption."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    template_match = re.search(r'<template id="evidence-template">(.*?)</template>', content, re.DOTALL)
    assert template_match is not None
    tmpl = template_match.group(1)
    assert '<figure class="evidence">' in tmpl
    assert '<blockquote class="evidence-quote">' in tmpl
    assert '<figcaption class="evidence-ref">' in tmpl


def test_t2_debrief_js_handles_error_state_elements() -> None:
    """Boundary test: debrief.js handles loading, retry, 404, 409, and 503 states."""
    js_content = JS_PATH.read_text(encoding="utf-8")
    assert "showState" in js_content
    assert "409" in js_content  # attempt in progress
    assert "404" in js_content  # not found
    assert "503" in js_content  # evaluator busy / retry
    assert "stateRetry" in js_content


def test_t2_debrief_js_xss_protection_uses_textcontent() -> None:
    """Boundary test: debrief.js avoids dangerous innerHTML for user/model strings."""
    js_content = JS_PATH.read_text(encoding="utf-8")
    # node helper must use textContent
    assert "element.textContent = text" in js_content or "textContent" in js_content
    # Check that model texts are set via textContent
    assert "el.caseTitle.textContent" in js_content
    assert "el.overallScore.textContent" in js_content


def test_t2_tokens_css_defines_color_and_theme_variables() -> None:
    """Boundary test: tokens.css defines light/dark design tokens and brand colors."""
    tokens = TOKENS_PATH.read_text(encoding="utf-8")
    assert "--brand-primary:" in tokens or "--brand-" in tokens
    assert "--bg-" in tokens or "--surface-" in tokens
    assert "--line-" in tokens or "--border-" in tokens


# =============================================================================
# TIER 3: Cross-Feature Integration Tests (HTML + JS + API Contract)
# =============================================================================

def test_t3_debrief_page_route_serves_html(candidate_client) -> None:
    """Cross-feature test: /attempts/{id}/debrief serves debrief.html for authenticated users."""
    client, _ = candidate_client
    started = client.post("/api/attempts", json={}).json()
    attempt_id = started["id"]
    
    resp = client.get(f"/attempts/{attempt_id}/debrief")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Debrief · Leo MBB Prep" in resp.text


def test_t3_debrief_js_api_contract_matches_evaluation_endpoints() -> None:
    """Cross-feature test: Verify endpoint URLs referenced in debrief.js match backend router."""
    js_content = JS_PATH.read_text(encoding="utf-8")
    assert "/api/attempts/" in js_content
    assert "/evaluation" in js_content
    assert "/auth/logout" in js_content


def test_t3_debrief_css_contains_meter_and_band_styles() -> None:
    """Cross-feature test: CSS contains classes for score meters, checklists, and cards."""
    css_content = CSS_PATH.read_text(encoding="utf-8")
    assert ".overall-card" in css_content
    assert ".score-track" in css_content or ".score-fill" in css_content
    assert ".checklist-item" in css_content or ".evidence" in css_content
    assert ".debrief" in css_content


# =============================================================================
# TIER 4: Real-World Workload Scenarios
# =============================================================================

def test_t4_real_world_debrief_page_delivery_scenario(candidate_client) -> None:
    """Scenario 3: Candidate finishes a case and accesses the full debrief UI."""
    client, _ = candidate_client
    
    # 1. Start case
    start_resp = client.post("/api/attempts", json={"case_id": "meridian-cold-chain-v1"})
    attempt_id = start_resp.json()["id"]
    
    # 2. Access debrief page before ending -> renders shell
    debrief_html_resp = client.get(f"/attempts/{attempt_id}/debrief")
    assert debrief_html_resp.status_code == 200
    assert 'id="debrief-report"' in debrief_html_resp.text
    
    # 3. Check theme switcher script is linked
    assert '<script src="/static/theme.js"></script>' in debrief_html_resp.text
    assert '<script src="/static/debrief.js"></script>' in debrief_html_resp.text
    assert 'id="checklist-status-filter"' in debrief_html_resp.text
    assert 'class="action-disclosure"' in debrief_html_resp.text


# =============================================================================
# TIER 5: 10x Masterclass Section Verification Tests
# =============================================================================

def test_t5_debrief_html_overall_score_uses_5_scale() -> None:
    """Verify overall score display shows /5 not /10."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "/5</span>" in content
    assert "/10</span>" not in content


def test_t5_debrief_html_executive_summary_card_exists() -> None:
    """Verify executive summary and MBB rating badge containers exist."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="executive-summary-card"' in content
    assert 'id="executive-summary-text"' in content
    assert 'id="mbb-badge"' in content


def test_t5_debrief_html_case_wanted_to_test_card_exists() -> None:
    """Verify 'What This Case Really Wanted to Test' masterclass card exists."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="case-wanted-card"' in content
    assert 'id="case-core-mechanism"' in content
    assert 'id="case-pivotal-insight"' in content
    assert 'id="case-candidate-performance"' in content
    assert 'id="case-optimal-gap"' in content


def test_t5_debrief_html_golden_rewrites_card_exists() -> None:
    """Verify Golden MBB Rewrites comparison section exists."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="golden-rewrites-card"' in content
    assert 'id="golden-rewrites-list"' in content


def test_t5_debrief_html_strengths_and_development_cards_exist() -> None:
    """Verify Strengths and Areas for Development sections exist."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="strengths-card"' in content
    assert 'id="strengths-list"' in content
    assert 'id="development-card"' in content
    assert 'id="development-list"' in content


def test_t5_debrief_html_action_plan_card_exists() -> None:
    """Verify Action Plan with drill and readings sections exist."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="action-plan-card"' in content
    assert 'id="drill-title"' in content
    assert 'id="drill-prompt"' in content
    assert 'id="readings-list"' in content


def test_t5_debrief_html_behaviour_filter_and_collapsibles_exist() -> None:
    """The served Jinja template defaults to missed markers and uses collapsibles."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="checklist-status-filter"' in content
    assert '<option value="missed" selected>' in content
    assert '<option value="demonstrated">' in content
    assert '<option value="not_applicable">' in content
    assert 'id="checklist-summary"' in content
    assert 'class="action-disclosure"' in content


def test_t5_debrief_js_filters_behaviour_statuses_and_renders_details() -> None:
    """The client filters markers by status and exposes detail only on demand."""
    js_content = JS_PATH.read_text(encoding="utf-8")
    assert 'checklistStatus: "missed"' in js_content
    assert 'checklistItems.filter((item) => item.status === status)' in js_content
    assert 'hasDetail ? "details" : "div"' in js_content
    assert "checklist-details${hasDetail" in js_content
    assert 'checklistFilter?.addEventListener("change"' in js_content


def test_t5_debrief_js_dimension_labels_has_all_five() -> None:
    """Verify JS DIMENSION_LABELS includes all 5 BCG dimensions."""
    js_content = JS_PATH.read_text(encoding="utf-8")
    for dim in ("structuring", "problem_solving", "quantitative", "synthesis", "communication"):
        assert dim in js_content, f"DIMENSION_LABELS missing: {dim}"


def test_t5_debrief_js_uses_5_scale_not_10() -> None:
    """Verify JS score bars use /5 scale, not /10."""
    js_content = JS_PATH.read_text(encoding="utf-8")
    assert '"/5"' in js_content or "'/5'" in js_content or '"/5")' in js_content
    assert '"aria-valuemax", "5"' in js_content


def test_t5_debrief_js_renders_new_masterclass_sections() -> None:
    """Verify JS has render functions for all new masterclass sections."""
    js_content = JS_PATH.read_text(encoding="utf-8")
    assert "renderExecutiveSummary" in js_content
    assert "renderCaseWantedToTest" in js_content
    assert "renderGoldenRewrites" in js_content
    assert "renderStrengths" in js_content
    assert "renderDevelopmentAreas" in js_content
    assert "renderActionPlan" in js_content


def test_t5_debrief_css_has_masterclass_section_styles() -> None:
    """Verify CSS includes styles for all new masterclass sections."""
    css_content = CSS_PATH.read_text(encoding="utf-8")
    assert ".executive-summary-card" in css_content
    assert ".mbb-badge" in css_content
    assert ".masterclass-card" in css_content
    assert ".golden-rewrites-card" in css_content
    assert ".rewrite-comparison" in css_content
    assert ".strengths-card" in css_content
    assert ".development-card" in css_content
    assert ".action-plan-card" in css_content
    assert ".priority-badge" in css_content
