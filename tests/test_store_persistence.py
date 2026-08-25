"""E2E Test Suite: Store Persistence, Attempt Lifecycle Auto-Evaluation & Profile Integration.

Validates:
- SQLite persistence of rich evaluation reports under EvaluationStore.
- User case progress tracking (in_progress, solved, best_score, attempts_count, reset).
- Practice history tracking and versioned evaluation history.
- Profile aggregation metrics on the BCG 1-5 scale (dimension averages, top repeated gaps and strengths).
- API endpoints: /api/attempts/{id}/evaluation, /api/me/profile, /api/me/practice-history, /api/me/case-progress.
- Security and isolation: Cross-user attempt ownership and access control.
- Boundary conditions: unended attempts, non-existent records, idempotency.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.accounts import AccountStore, User
from app.case_runtime import CaseCatalogue, InterviewSession
from app.store import EvaluationStore, SessionStore
from conftest import sign_in


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = CaseCatalogue.from_reservoir(ROOT)


@pytest.fixture
def isolated_db(tmp_path):
    db_path = tmp_path / "persistence_test.db"
    store = SessionStore(db_path)
    eval_store = EvaluationStore(db_path)
    accounts = AccountStore(db_path)
    return db_path, store, eval_store, accounts


# =============================================================================
# TIER 1: Persistence & Storage Coverage Tests (≥5 tests)
# =============================================================================

def test_t1_evaluation_store_saves_and_retrieves_latest(isolated_db) -> None:
    """Verify EvaluationStore persists full evaluation report JSON and retrieves latest."""
    _, _, eval_store, _ = isolated_db
    attempt_id = "attempt-pers-001"
    report_data = {
        "attempt_id": attempt_id,
        "overall_score": 4.5,
        "mbb_rating_badge": "Strong Pass",
        "executive_summary": "Solid structured communication and rigorous problem solving.",
        "dimensions": [
            {"name": "structuring", "score": 4.5, "band": "Strong"},
            {"name": "problem_solving", "score": 4.5, "band": "Strong"},
            {"name": "quantitative", "score": 4.0, "band": "Strong"},
            {"name": "synthesis", "score": 4.5, "band": "Strong"},
            {"name": "communication", "score": 5.0, "band": "Exceptional"},
        ],
        "priority_improvements": ["State backhaul assumptions"],
        "headline_strengths": ["MECE tree"],
    }
    eval_store.save(json.dumps(report_data), attempt_id, "evaluator-v2-bcg")
    
    latest = eval_store.latest(attempt_id)
    assert latest is not None
    assert latest["evaluator_version"] == "evaluator-v2-bcg"
    assert latest["report"]["overall_score"] == 4.5
    assert latest["report"]["mbb_rating_badge"] == "Strong Pass"


def test_t1_evaluation_store_maintains_versioned_history(isolated_db) -> None:
    """Verify EvaluationStore preserves multiple evaluations under different versions."""
    _, _, eval_store, _ = isolated_db
    attempt_id = "attempt-pers-002"
    
    # Save version 1
    eval_store.save(json.dumps({"attempt_id": attempt_id, "score": 3.0}), attempt_id, "eval-v1")
    # Save version 2
    eval_store.save(json.dumps({"attempt_id": attempt_id, "score": 4.2}), attempt_id, "eval-v2")
    
    history = eval_store.history(attempt_id)
    assert len(history) == 2
    versions = [h["evaluator_version"] for h in history]
    assert "eval-v2" in versions
    assert "eval-v1" in versions


def test_t1_session_store_case_progress_lifecycle(isolated_db) -> None:
    """Verify SessionStore correctly tracks in_progress, solved, and best_score."""
    _, store, _, _ = isolated_db
    user_id = "usr-test-progress"
    case_id = "meridian-cold-chain-v1"
    
    # 1. Start case
    store.record_case_started(user_id, case_id, "attempt-1")
    prog = store.get_user_case_progress(user_id, case_id)
    assert prog is not None
    assert prog["status"] == "in_progress"
    assert prog["attempts_count"] == 1
    
    # 2. Mark solved with score 3.8
    store.mark_case_solved(user_id, case_id, "attempt-1", score=3.8)
    prog = store.get_user_case_progress(user_id, case_id)
    assert prog["status"] == "solved"
    assert prog["best_score"] == 3.8
    assert prog["last_completed_at"] is not None
    
    # 3. Solve again with higher score 4.5
    store.mark_case_solved(user_id, case_id, "attempt-2", score=4.5)
    prog = store.get_user_case_progress(user_id, case_id)
    assert prog["best_score"] == 4.5
    assert prog["attempts_count"] == 1  # solved preserves best


def test_t1_session_store_reset_case_progress(isolated_db) -> None:
    """Verify reset_case_progress resets status to not_started without deleting attempt history."""
    _, store, _, _ = isolated_db
    user_id = "usr-reset-test"
    case_id = "meridian-cold-chain-v1"
    
    store.record_case_started(user_id, case_id, "att-reset-1")
    store.mark_case_solved(user_id, case_id, "att-reset-1", score=4.0)
    
    reset_ok = store.reset_case_progress(user_id, case_id)
    assert reset_ok is True
    
    prog = store.get_user_case_progress(user_id, case_id)
    assert prog["status"] == "not_started"
    assert prog["latest_attempt_id"] is None
    assert prog["reset_at"] is not None


def test_t1_list_user_practice_joins_latest_evaluation(isolated_db) -> None:
    """Verify list_user_practice returns attempt along with latest feedback."""
    _, store, eval_store, _ = isolated_db
    user_id = "usr-practice-list"
    session = InterviewSession(id="att-joined-1", case=CATALOGUE.get("meridian-cold-chain-v1"), mode="realistic")
    session.ended = True
    store.save(session, user_id=user_id)
    
    eval_store.save(json.dumps({"dimensions": [{"name": "structuring", "score": 4.5}]}), session.id, "v2")
    
    practice = store.list_user_practice(user_id)
    assert len(practice) == 1
    assert practice[0]["id"] == session.id
    assert practice[0]["feedback"] is not None
    assert practice[0]["feedback"]["evaluator_version"] == "v2"


# =============================================================================
# TIER 2: Boundary, Negative & Authorization Tests (≥5 tests)
# =============================================================================

def test_t2_unended_attempt_evaluation_rejected(candidate_client) -> None:
    """Boundary test: /api/attempts/{id}/evaluation returns 409 if attempt is still in progress."""
    client, _ = candidate_client
    started = client.post("/api/attempts", json={}).json()
    attempt_id = started["id"]
    
    resp = client.get(f"/api/attempts/{attempt_id}/evaluation")
    assert resp.status_code == 409
    assert "not ended" in resp.json()["detail"].lower()


def test_t2_nonexistent_attempt_returns_404(candidate_client) -> None:
    """Boundary test: /api/attempts/{id} returns 404 for non-existent attempt."""
    client, _ = candidate_client
    resp = client.get("/api/attempts/non-existent-uuid-12345")
    assert resp.status_code == 404


def test_t2_cross_user_evaluation_access_forbidden(candidate_client) -> None:
    """Boundary test: Candidate A cannot access Candidate B's attempt evaluation."""
    client_a, _ = candidate_client
    client_b = TestClient(main.app)
    sign_in(client_b, "candidate-b@casecall.test")
    
    # User A starts and ends an attempt
    att_a = client_a.post("/api/attempts", json={}).json()
    attempt_id = att_a["id"]
    
    # User B tries to access User A's attempt
    resp_b = client_b.get(f"/api/attempts/{attempt_id}")
    assert resp_b.status_code == 404  # 404 avoids leaking attempt existence


def test_t2_practice_history_detail_not_found(candidate_client) -> None:
    """Boundary test: /api/me/practice-history/{id} returns 404 for invalid attempt ID."""
    client, _ = candidate_client
    resp = client.get("/api/me/practice-history/unknown-attempt-id")
    assert resp.status_code == 404


def test_t2_reset_nonexistent_case_progress_returns_404(candidate_client) -> None:
    """Boundary test: Resetting unpracticed case returns 404."""
    client, _ = candidate_client
    resp = client.post("/api/cases/meridian-cold-chain-v1/reset")
    assert resp.status_code == 404


# =============================================================================
# TIER 3: Cross-Feature Integration Tests (API + DB + Profile)
# =============================================================================

def test_t3_profile_aggregates_dimensions_and_repeated_development_areas(candidate_client) -> None:
    """Cross-feature test: /api/me/profile aggregates scores across attempts on 1-5 scale."""
    client, user = candidate_client
    
    # Create 2 completed attempts with rich evaluations in DB
    session1 = InterviewSession(id="prof-att-1", case=CATALOGUE.get("meridian-cold-chain-v1"), mode="realistic")
    session1.ended = True
    main.STORE.save(session1, user_id=user.id)
    
    rep1 = {
        "dimensions": [
            {"name": "structuring", "score": 4.0},
            {"name": "problem_solving", "score": 3.0},
            {"name": "quantitative", "score": 4.0},
            {"name": "synthesis", "score": 5.0},
            {"name": "communication", "score": 4.0},
        ],
        "priority_improvements": ["State backhaul assumptions", "MECE formula precision"],
        "headline_strengths": ["Crisp synthesis"],
    }
    main.EVALUATIONS.save(json.dumps(rep1), session1.id, "v2")
    
    session2 = InterviewSession(id="prof-att-2", case=CATALOGUE.get("meridian-cold-chain-v1"), mode="realistic")
    session2.ended = True
    main.STORE.save(session2, user_id=user.id)
    
    rep2 = {
        "dimensions": [
            {"name": "structuring", "score": 4.4},
            {"name": "problem_solving", "score": 4.0},
            {"name": "quantitative", "score": 4.0},
            {"name": "synthesis", "score": 4.6},
            {"name": "communication", "score": 4.6},
        ],
        "priority_improvements": ["State backhaul assumptions", "Signposting transitions"],
        "headline_strengths": ["Crisp synthesis", "Tailored structuring"],
    }
    main.EVALUATIONS.save(json.dumps(rep2), session2.id, "v2")
    
    # Fetch profile
    prof_resp = client.get("/api/me/profile")
    assert prof_resp.status_code == 200
    data = prof_resp.json()
    
    # Verify summary
    assert data["summary"]["completed"] >= 2
    assert data["summary"]["feedback_available"] >= 2
    assert data["summary"]["average_feedback_score"] is not None
    
    # Verify repeated development areas has "State backhaul assumptions" with 2 occurrences
    dev_areas = {d["text"]: d["occurrences"] for d in data["development_areas"]}
    assert dev_areas.get("State backhaul assumptions") == 2
    
    # Verify performance dimension averages
    struct_perf = next((p for p in data["performance"] if p["name"] == "structuring"), None)
    assert struct_perf is not None
    assert struct_perf["average_score"] == 4.2  # (4.0 + 4.4) / 2


# =============================================================================
# TIER 4: Real-World Workload Scenarios
# =============================================================================

def test_t4_real_world_attempt_auto_trigger_and_persistence_workflow(candidate_client, monkeypatch) -> None:
    """Scenario 4: Complete attempt ending triggers evaluation, persists report, and updates progress."""
    client, user = candidate_client
    
    # Script stub evaluator
    class BCGStubEvaluator:
        def evaluate(self, session):
            from app.evaluator import DimensionScore, EvaluationReport, ChecklistItem, Citation
            return EvaluationReport(
                attempt_id=session.id,
                dimensions=[
                    DimensionScore(name="structuring", score=4.5, band="Strong", observations=["Clean tree."]),
                    DimensionScore(name="problem_solving", score=4.0, band="Strong", observations=["Hypothesis led."]),
                    DimensionScore(name="communication", score=4.5, band="Strong", observations=["Top-down."]),
                    DimensionScore(name="quantitative", score=4.0, band="Strong", observations=["Accurate math."]),
                ],
                checklist=[ChecklistItem(id="cl-1", title="Restate goal", status="demonstrated", evidence=[Citation(message_index=0, quote="goal")])],
                headline_strengths=["Strong opening."],
                priority_improvements=["Quantify backhaul."],
                next_drill="2-minute route math drill.",
                evaluator_version="stub-bcg-v2",
            )
        def overall(self, report):
            return {"overall": 4.25, "assessed_dimensions": ["structuring", "problem_solving", "communication", "quantitative"]}
    
    monkeypatch.setattr(main, "EVALUATOR", BCGStubEvaluator())
    main.app.state.evaluator = BCGStubEvaluator()
    
    # 1. Start attempt
    start_resp = client.post("/api/attempts", json={"case_id": "meridian-cold-chain-v1", "mode": "realistic"})
    assert start_resp.status_code == 200
    attempt_id = start_resp.json()["id"]
    
    # 2. End attempt
    end_resp = client.post(f"/api/attempts/{attempt_id}/end")
    assert end_resp.status_code == 200
    end_data = end_resp.json()
    assert end_data["attempt"]["ended"] is True
    assert end_data["evaluation"] is not None
    
    # 3. Verify persistence
    eval_resp = client.get(f"/api/attempts/{attempt_id}/evaluation")
    assert eval_resp.status_code == 200
    assert eval_resp.json()["report"]["attempt_id"] == attempt_id
    
    # 4. Verify case progress solved
    prog_resp = client.get("/api/me/case-progress")
    assert prog_resp.status_code == 200
    prog_list = prog_resp.json()["progress"]
    meridian_prog = next((p for p in prog_list if p["case_id"] == "meridian-cold-chain-v1"), None)
    assert meridian_prog is not None
    assert meridian_prog["status"] == "solved"


def test_t1_evaluation_store_user_id_linking_and_queries(isolated_db) -> None:
    """Verify evaluations are linked to user_id and can be queried by user."""
    _, store, eval_store, _ = isolated_db
    user_a = "usr-linked-a"
    user_b = "usr-linked-b"
    case = CATALOGUE.get("meridian-cold-chain-v1")

    # Attempt 1 for User A
    session1 = InterviewSession(id="att-link-1", case=case, mode="realistic")
    session1.ended = True
    store.save(session1, user_id=user_a)
    eval_store.save(json.dumps({"overall_score": 4.2}), session1.id, "v1", user_id=user_a)

    # Attempt 2 for User A (inferred user_id from attempts table)
    session2 = InterviewSession(id="att-link-2", case=case, mode="realistic")
    session2.ended = True
    store.save(session2, user_id=user_a)
    eval_store.save(json.dumps({"overall_score": 4.6}), session2.id, "v1")  # user_id is None -> auto inferred

    # Attempt 3 for User B
    session3 = InterviewSession(id="att-link-3", case=case, mode="realistic")
    session3.ended = True
    store.save(session3, user_id=user_b)
    eval_store.save(json.dumps({"overall_score": 3.5}), session3.id, "v1", user_id=user_b)

    # Query by user
    user_a_evals = eval_store.list_by_user(user_a)
    assert len(user_a_evals) == 2
    assert all(e["user_id"] == user_a for e in user_a_evals)
    attempt_ids = {e["attempt_id"] for e in user_a_evals}
    assert attempt_ids == {"att-link-1", "att-link-2"}

    user_b_evals = eval_store.list_by_user(user_b)
    assert len(user_b_evals) == 1
    assert user_b_evals[0]["attempt_id"] == "att-link-3"

    # Test get specific version
    record = eval_store.get("att-link-1", "v1")
    assert record is not None
    assert record["user_id"] == user_a
    assert record["report"]["overall_score"] == 4.2


def test_t3_api_profile_and_attempt_linking(candidate_client) -> None:
    """Verify /api/profile and /api/attempts/{id} return scores, badges, and debrief links."""
    client, user = candidate_client

    session = InterviewSession(id="att-profile-test-1", case=CATALOGUE.get("meridian-cold-chain-v1"), mode="realistic")
    session.ended = True
    main.STORE.save(session, user_id=user.id)

    rep = {
        "attempt_id": session.id,
        "overall_score": 4.75,
        "mbb_rating_badge": "Distinction",
        "executive_summary": "Exceptional top-down synthesis and rigorous math.",
        "dimensions": [
            {"name": "structuring", "score": 5.0, "band": "Top 1% MBB"},
            {"name": "problem_solving", "score": 4.5, "band": "Top 1% MBB"},
            {"name": "quantitative", "score": 4.5, "band": "Top 1% MBB"},
            {"name": "synthesis", "score": 5.0, "band": "Top 1% MBB"},
            {"name": "communication", "score": 4.75, "band": "Top 1% MBB"},
        ],
        "areas_for_development": [{"gap": "Clarify capital constraints earlier", "priority": "medium"}],
        "strengths": [{"claim": "Flawless MECE tree", "verbatim_quote": "Let's decompose..."}],
    }
    main.EVALUATIONS.save(json.dumps(rep), session.id, "v2", user_id=user.id)

    # Test GET /api/profile
    prof_resp = client.get("/api/profile")
    assert prof_resp.status_code == 200
    pdata = prof_resp.json()
    assert pdata["summary"]["completed"] >= 1
    assert pdata["summary"]["average_feedback_score"] == 4.75
    assert len(pdata["performance"]) == 5
    assert len(pdata["development_areas"]) >= 1
    assert pdata["development_areas"][0]["text"] == "Clarify capital constraints earlier"
    assert len(pdata["strengths"]) >= 1
    assert pdata["strengths"][0]["text"] == "Flawless MECE tree"
    assert "performance_history" in pdata
    assert pdata["performance_history"][0]["debrief_url"] == f"/attempts/{session.id}/debrief"

    # Test GET /api/attempts/{id}
    att_resp = client.get(f"/api/attempts/{session.id}")
    assert att_resp.status_code == 200
    att_data = att_resp.json()
    assert att_data["debrief_url"] == f"/attempts/{session.id}/debrief"
    assert att_data["evaluation_url"] == f"/api/attempts/{session.id}/evaluation"
    assert att_data["score"] == 4.75
    assert att_data["mbb_rating_badge"] == "Distinction"


def test_t4_attempt_lifecycle_service(isolated_db) -> None:
    """Verify AttemptLifecycleService coordinates end, evaluate, persist, and progress update."""
    from app.attempt_service import AttemptLifecycleService
    from app.evaluator import DimensionScore, EvaluationReport

    _, store, eval_store, _ = isolated_db
    service = AttemptLifecycleService()
    user_id = "usr-lifecycle-1"
    session = InterviewSession(id="att-life-1", case=CATALOGUE.get("meridian-cold-chain-v1"), mode="realistic")
    store.save(session, user_id=user_id)

    class MockEvaluator:
        version = "mock-eval-v1"
        def evaluate(self, s):
            return EvaluationReport(
                attempt_id=s.id,
                overall_score=4.4,
                mbb_rating_badge="Strong Pass",
                dimensions=[
                    DimensionScore(name="structuring", score=4.5, band="Strong"),
                    DimensionScore(name="problem_solving", score=4.5, band="Strong"),
                    DimensionScore(name="quantitative", score=4.0, band="Strong"),
                    DimensionScore(name="synthesis", score=4.5, band="Strong"),
                    DimensionScore(name="communication", score=4.5, band="Strong"),
                ],
                evaluator_version=self.version,
            )
        def overall(self, r):
            return {"overall": 4.4}

    result = service.complete_attempt(
        session,
        store=store,
        evaluations=eval_store,
        evaluator=MockEvaluator(),
        user_id=user_id,
    )

    assert session.ended is True
    assert result["attempt"]["ended"] is True
    assert result["evaluation"] is not None
    assert result["debrief_url"] == f"/attempts/{session.id}/debrief"

    # Check evaluation stored
    saved = eval_store.latest(session.id)
    assert saved is not None
    assert saved["report"]["overall_score"] == 4.4

    # Check user progress updated
    prog = store.get_user_case_progress(user_id, session.case.id)
    assert prog is not None
    assert prog["status"] == "solved"
    assert prog["best_score"] == 4.4

