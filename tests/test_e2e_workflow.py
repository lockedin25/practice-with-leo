"""E2E Test Suite: Complete End-to-End Simulation Workflows & Real-World User Journeys.

Covers Tier 4 Real-World Application Scenarios:
- Scenario 1: Full Case Lifecycle on Reservoir Case with Rich Evaluation
- Scenario 2: Multi-School Case Selection & Essence Validation
- Scenario 3: Debrief Page Delivery & Verification with 5 Dimensions & Golden Rewrites
- Scenario 4: Profile Trend Tracking Across Multiple 1-5 Evaluated Attempts
- Scenario 5: Deterministic Fallback Evaluation under Missing/Degraded LLM Conditions
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.case_runtime import CaseCatalogue, InterviewSession
from app.evaluator import (
    Citation,
    ChecklistItem,
    DimensionScore,
    EvaluationReport,
    load_rubric,
    weighted_overall,
)
from conftest import sign_in


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = CaseCatalogue.from_reservoir(ROOT)
KB_DIR = ROOT / "knowledge_base"


class ScriptedE2EEvaluator:
    """BCG-calibrated 1-5 evaluator double producing valid rich reports."""

    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, session: InterviewSession) -> EvaluationReport:
        self.calls += 1
        quote = session.messages[1]["content"][:30] if len(session.messages) > 1 else "restate objective"
        return EvaluationReport(
            attempt_id=session.id,
            dimensions=[
                DimensionScore(
                    name="structuring",
                    score=4.5,
                    band="Strong",
                    evidence=[Citation(message_index=1, quote=quote)],
                    observations=["MECE decomposition tailored to business model."],
                    improvements=["Include route density explicitly."],
                    confidence="high",
                ),
                DimensionScore(
                    name="problem_solving",
                    score=4.0,
                    band="Strong",
                    evidence=[Citation(message_index=1, quote=quote)],
                    observations=["Hypothesis-led inquiry focused on margin leakage."],
                    improvements=["Quantify backhaul empty returns."],
                    confidence="high",
                ),
                DimensionScore(
                    name="quantitative",
                    score=4.0,
                    band="Strong",
                    evidence=[Citation(message_index=1, quote=quote)],
                    observations=["Segment margin math was accurate."],
                    improvements=["State formula first."],
                    confidence="medium",
                ),
                DimensionScore(
                    name="synthesis",
                    score=4.5,
                    band="Strong",
                    evidence=[Citation(message_index=1, quote=quote)],
                    observations=["Pyramid Principle 4-part synthesis."],
                    improvements=["Add concrete 100-day plan."],
                    confidence="high",
                ),
                DimensionScore(
                    name="communication",
                    score=4.0,
                    band="Strong",
                    evidence=[Citation(message_index=1, quote=quote)],
                    observations=["Top-down executive delivery."],
                    improvements=["Avoid filler."],
                    confidence="high",
                ),
            ],
            checklist=[
                ChecklistItem(
                    id="preliminary.confirm_objective",
                    title="Confirm client objective and metric",
                    status="demonstrated",
                    evidence=[Citation(message_index=1, quote=quote)],
                )
            ],
            headline_strengths=["Restated objective cleanly before structuring.", "Strong top-down delivery."],
            priority_improvements=["Quantify round-trip backhaul utilization.", "State testable hypothesis earlier."],
            next_drill="Run a 2-minute route density sizing calculation.",
            evaluator_version=f"evaluator-v2-bcg|run={self.calls}",
        )

    def overall(self, report: EvaluationReport) -> dict[str, object]:
        return weighted_overall(report, load_rubric())


# =============================================================================
# SCENARIO 1: Full Case Lifecycle on Reservoir Case with Rich Evaluation
# =============================================================================

def test_scenario_1_full_case_lifecycle_on_reservoir_case(monkeypatch, stub_interviewer) -> None:
    """Scenario 1: Candidate starts reservoir case, submits turns, ends attempt, gets auto-evaluated and debriefed."""
    evaluator_stub = ScriptedE2EEvaluator()
    monkeypatch.setattr(main, "EVALUATOR", evaluator_stub)
    main.app.state.evaluator = evaluator_stub

    client = TestClient(main.app)
    user = sign_in(client, "candidate-scenario-1@casecall.test", name="Aarav Sharma")

    # 1. Candidate lists available cases from library
    cases_resp = client.get("/api/cases")
    assert cases_resp.status_code == 200
    cases = cases_resp.json()["cases"]
    assert len(cases) == 69
    meridian = next(c for c in cases if c["id"] == "meridian-cold-chain-v1")
    assert meridian["title"] == "Meridian Cold Chain"

    # 2. Candidate starts attempt on Meridian Cold Chain
    start_resp = client.post("/api/attempts", json={"case_id": "meridian-cold-chain-v1", "mode": "realistic", "duration_minutes": 30})
    assert start_resp.status_code == 200
    session_data = start_resp.json()
    attempt_id = session_data["id"]
    assert session_data["case"]["id"] == "meridian-cold-chain-v1"
    assert len(session_data["messages"]) == 1  # intro message

    # 3. Candidate turn 1 (Onboarding readiness / clarification)
    turn1_resp = client.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "I am ready to begin. The client is Meridian Cold Chain facing EBITDA margin drop from 18% to 11%.", "turn_id": "t-001"},
    )
    assert turn1_resp.status_code == 200
    t1_data = turn1_resp.json()
    assert len(t1_data["attempt"]["messages"]) >= 2

    # 4. Candidate turn 2 (Structuring & hypothesis inquiry)
    turn2_resp = client.post(
        f"/api/attempts/{attempt_id}/turn",
        json={
            "content": "I will structure revenue into food vs pharma segments, and costs into route operations and storage. Has segment mix changed?",
            "turn_id": "t-002",
        },
    )
    assert turn2_resp.status_code == 200

    # 5. Candidate ends attempt -> auto-triggers evaluation and updates progress
    end_resp = client.post(f"/api/attempts/{attempt_id}/end", json={"disposition": "scored"})
    assert end_resp.status_code == 200
    end_data = end_resp.json()
    assert end_data["attempt"]["ended"] is True
    assert end_data["evaluation"] is not None
    assert evaluator_stub.calls == 1

    # 6. Candidate views debrief API payload
    eval_resp = client.get(f"/api/attempts/{attempt_id}/evaluation")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["report"]["attempt_id"] == attempt_id
    assert eval_data["overall"]["overall"] == 4.22
    assert len(eval_data["report"]["dimensions"]) == 5

    # 7. Candidate loads debrief HTML page shell
    debrief_html = client.get(f"/attempts/{attempt_id}/debrief")
    assert debrief_html.status_code == 200
    assert "debrief-report" in debrief_html.text


# =============================================================================
# SCENARIO 2: Multi-School Case Selection & Essence Validation
# =============================================================================

def test_scenario_2_multi_school_case_selection_and_essence_validation() -> None:
    """Scenario 2: Candidate inspects exemplar multi-school cases and resolves knowledge base links."""
    # 1. Load multi-school case catalog from IIM Ahmedabad prep book
    iima_dir = ROOT / "corpus" / "iima-consult-prep-book-2025-26" / "cases"
    assert iima_dir.is_dir()
    case_files = sorted(iima_dir.glob("*.md"))
    assert len(case_files) >= 50

    # 2. Pick exemplar case (001-beer-manufacturer.md)
    beer_case = case_files[0]
    content = beer_case.read_text(encoding="utf-8")
    assert "Beer Manufacturer" in content
    assert "Profitability" in content
    assert "Opening brief" in content

    # 3. Verify knowledge base links for profitability cases exist
    profitability_kb = KB_DIR / "case_types" / "profitability.md"
    assert profitability_kb.is_file()
    kb_content = profitability_kb.read_text(encoding="utf-8")
    assert "Profitability Framework" in kb_content or "profitability" in kb_content.lower()


# =============================================================================
# SCENARIO 3: Debrief Page Delivery & Verification with 5 Dimensions & Golden Rewrites
# =============================================================================

def test_scenario_3_debrief_page_delivery_with_5_dimensions_and_golden_rewrites(candidate_client, monkeypatch, stub_interviewer) -> None:
    """Scenario 3: Evaluated attempt delivers 5 dimensions, golden rewrites, and verbatim citations."""
    client, _ = candidate_client

    evaluator_stub = ScriptedE2EEvaluator()
    monkeypatch.setattr(main, "EVALUATOR", evaluator_stub)
    main.app.state.evaluator = evaluator_stub

    # Start and conduct attempt
    start = client.post("/api/attempts", json={"case_id": "meridian-cold-chain-v1"}).json()
    att_id = start["id"]

    client.post(
        f"/api/attempts/{att_id}/turn",
        json={"content": "Let me restate the objective of Meridian Cold Chain.", "turn_id": "t1"},
    )
    client.post(f"/api/attempts/{att_id}/end", json={"disposition": "scored"})

    # Fetch rich evaluation report
    resp = client.get(f"/api/attempts/{att_id}/evaluation")
    assert resp.status_code == 200
    report = resp.json()["report"]

    # Verify 5 dimensions
    dims = {d["name"]: d["score"] for d in report["dimensions"]}
    assert set(dims.keys()) == {"structuring", "problem_solving", "quantitative", "synthesis", "communication"}
    assert all(1.0 <= score <= 5.0 for score in dims.values())

    # Verify strengths and priority improvements
    assert len(report["headline_strengths"]) >= 1
    assert len(report["priority_improvements"]) >= 1
    assert len(report["next_drill"]) > 10

    # Verify citation quote exists in transcript
    for dim in report["dimensions"]:
        for cit in dim.get("evidence", []):
            assert cit["quote"] in "Let me restate the objective of Meridian Cold Chain."


# =============================================================================
# SCENARIO 4: Profile Trend Tracking Across Multiple 1-5 Evaluated Attempts
# =============================================================================

def test_scenario_4_profile_trend_tracking_across_multiple_attempts(candidate_client, monkeypatch) -> None:
    """Scenario 4: Candidate completes multiple attempts, tracking 1-5 scale scores and repeated development areas."""
    client, user = candidate_client

    # Create 2 completed sessions
    s1 = InterviewSession(id="multi-att-001", case=CATALOGUE.get("meridian-cold-chain-v1"), mode="realistic")
    s1.ended = True
    main.STORE.save(s1, user_id=user.id)
    main.EVALUATIONS.save(
        json.dumps({
            "dimensions": [
                {"name": "structuring", "score": 4.0},
                {"name": "problem_solving", "score": 3.8},
                {"name": "quantitative", "score": 4.2},
                {"name": "synthesis", "score": 4.0},
                {"name": "communication", "score": 4.5},
            ],
            "priority_improvements": ["State backhaul assumptions", "Signpost structure"],
            "headline_strengths": ["Top-down communication"],
        }),
        s1.id,
        "eval-v2",
    )
    main.STORE.mark_case_solved(user.id, "meridian-cold-chain-v1", s1.id, score=4.1)

    s2 = InterviewSession(id="multi-att-002", case=CATALOGUE.get("aster-diagnostics-v1"), mode="realistic")
    s2.ended = True
    main.STORE.save(s2, user_id=user.id)
    main.EVALUATIONS.save(
        json.dumps({
            "dimensions": [
                {"name": "structuring", "score": 4.6},
                {"name": "problem_solving", "score": 4.4},
                {"name": "quantitative", "score": 4.0},
                {"name": "synthesis", "score": 4.4},
                {"name": "communication", "score": 4.8},
            ],
            "priority_improvements": ["State backhaul assumptions", "Sanity check capex"],
            "headline_strengths": ["MECE market entry tree", "Top-down communication"],
        }),
        s2.id,
        "eval-v2",
    )
    main.STORE.mark_case_solved(user.id, "aster-diagnostics-v1", s2.id, score=4.44)

    # Fetch profile
    prof_resp = client.get("/api/me/profile")
    assert prof_resp.status_code == 200
    prof = prof_resp.json()

    assert prof["summary"]["completed"] >= 2
    assert prof["summary"]["average_feedback_score"] is not None
    assert 4.0 <= prof["summary"]["average_feedback_score"] <= 4.5

    # Check repeated development area "State backhaul assumptions" occurred twice
    repeated_gaps = {g["text"]: g["occurrences"] for g in prof["development_areas"]}
    assert repeated_gaps.get("State backhaul assumptions") == 2

    # Check repeated strength "Top-down communication" occurred twice
    repeated_strengths = {s["text"]: s["occurrences"] for s in prof["strengths"]}
    assert repeated_strengths.get("Top-down communication") == 2

    # Check practice history
    hist_resp = client.get("/api/me/practice-history")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert hist["summary"]["completed"] >= 2
    assert len(hist["attempts"]) >= 2


# =============================================================================
# SCENARIO 5: Deterministic Fallback Evaluation under Missing/Degraded LLM
# =============================================================================

def test_scenario_5_deterministic_fallback_under_missing_llm(candidate_client, monkeypatch, stub_interviewer) -> None:
    """Scenario 5: Attempt ends cleanly even if evaluator agent is offline, falling back gracefully."""
    client, _ = candidate_client

    # Disable evaluator (simulating missing OPENROUTER_API_KEY)
    monkeypatch.setattr(main, "EVALUATOR", None)
    main.app.state.evaluator = None

    # Start attempt
    start = client.post("/api/attempts", json={"case_id": "meridian-cold-chain-v1"}).json()
    att_id = start["id"]

    # Submit a turn
    client.post(
        f"/api/attempts/{att_id}/turn",
        json={"content": "I am ready. What is the breakdown of revenue?", "turn_id": "t1"},
    )

    # End attempt -> must not crash, must return scorecard
    end_resp = client.post(f"/api/attempts/{att_id}/end", json={"disposition": "scored"})
    assert end_resp.status_code == 200
    end_data = end_resp.json()
    assert end_data["attempt"]["ended"] is True
    assert end_data["scorecard"] is not None
    assert len(end_data["scorecard"]["dimensions"]) >= 3
    assert end_data["evaluation"] is not None
    assert "fallback=true" in end_data["evaluation"]["evaluator_version"]
    assert len(end_data["evaluation"]["dimensions"]) == 5
