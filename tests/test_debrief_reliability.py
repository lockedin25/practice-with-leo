"""Regression coverage for durable, owner-visible post-case debriefs."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

import app.main as main
from app.case_runtime import InterviewSession
from app.evaluator import EvaluationReport, find_case_package
from conftest import sign_in


class ExplodingEvaluator:
    """Simulates an upstream model or prompt failure during grading."""

    def evaluate(self, _session):
        raise RuntimeError("upstream evaluator unavailable")

    def overall(self, _report):
        raise AssertionError("Fallback reports must calculate their own overall score")


class EmptyEvaluator:
    """Returns a typed response that contains none of the required evidence."""

    def evaluate(self, session):
        return EvaluationReport(attempt_id=session.id)


def test_live_evaluator_is_pointed_at_the_case_reservoir() -> None:
    """Regression for the production path bug that prevented every report."""
    assert getattr(main.EVALUATOR, "_reservoir_root", main.RESERVOIR_DIR) == main.RESERVOIR_DIR
    assert find_case_package(main.ROOT, "harvest-table-v1").name == "harvest-table"


def test_end_persists_an_elaborate_fallback_report_when_llm_grading_fails(monkeypatch, stub_interviewer) -> None:
    monkeypatch.setattr(main, "EVALUATOR", ExplodingEvaluator())
    main.app.state.evaluator = main.EVALUATOR
    client = TestClient(main.app)
    user = sign_in(client, "fallback-debrief@casecall.test")

    started = client.post("/api/attempts", json={}).json()
    attempt_id = started["id"]
    turn = client.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "I will split the margin issue into revenue, route cost, and storage cost.", "turn_id": "t1"},
    )
    assert turn.status_code == 200

    ended = client.post(f"/api/attempts/{attempt_id}/end", json={"disposition": "scored"})
    assert ended.status_code == 200
    assert "fallback=true" in ended.json()["evaluation"]["evaluator_version"]

    stored = main.EVALUATIONS.latest(attempt_id)
    assert stored is not None
    report = stored["report"]
    assert report["attempt_id"] == attempt_id
    assert report["reliability"] == "provisional"
    assert report["internal_log_reason"] == "primary_evaluator_failure"
    assert report["retry_message"]
    assert len(report["dimensions"]) == 5
    assert len(report["golden_rewrites"]) >= 2
    assert len(report["strengths"]) >= 2
    assert len(report["areas_for_development"]) >= 2
    assert report["targeted_drill"]

    debrief = client.get(f"/api/attempts/{attempt_id}/evaluation")
    assert debrief.status_code == 200
    assert debrief.json()["report"]["attempt_id"] == attempt_id
    assert debrief.json()["report"]["reliability"] == "provisional"
    assert "internal_log_reason" not in debrief.json()["report"]
    assert debrief.json()["overall"]["overall"] is not None
    assert main.STORE.get(attempt_id, main.CATALOGUE).ended is True
    assert user.id == stored["user_id"]


def test_empty_evaluator_response_persists_a_readable_incomplete_report(monkeypatch, stub_interviewer) -> None:
    """A syntactically valid but empty response cannot earn a headline score."""
    monkeypatch.setattr(main, "EVALUATOR", EmptyEvaluator())
    main.app.state.evaluator = main.EVALUATOR
    client = TestClient(main.app)
    sign_in(client, "empty-debrief@casecall.test")

    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    turn = client.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "I will test revenue, costs, and the most material driver first.", "turn_id": "t1"},
    )
    assert turn.status_code == 200

    ended = client.post(f"/api/attempts/{attempt_id}/end", json={"disposition": "scored"})
    assert ended.status_code == 200
    report = ended.json()["evaluation"]
    assert report["reliability"] == "incomplete"
    stored = main.EVALUATIONS.latest(attempt_id)
    assert stored is not None
    assert stored["report"]["internal_log_reason"] == "evaluator_response_incomplete"
    assert "internal_log_reason" not in report
    assert report["retry_message"]
    assert len(report["dimensions"]) == 5
    assert report["executive_summary"]

    fetched = client.get(f"/api/attempts/{attempt_id}/evaluation")
    assert fetched.status_code == 200
    assert fetched.json()["report"]["reliability"] == "incomplete"


def test_opening_an_old_completed_attempt_repairs_a_missing_debrief(monkeypatch) -> None:
    monkeypatch.setattr(main, "EVALUATOR", None)
    main.app.state.evaluator = None
    client = TestClient(main.app)
    user = sign_in(client, "repair-debrief@casecall.test")

    session = InterviewSession(id="old-ended-attempt", case=main.CATALOGUE.default_case, mode="realistic")
    session.add_interviewer_turn("The client has a margin problem.")
    session.record_candidate_turn("I would first confirm the objective and segment revenue and costs.")
    session.ended = True
    main.STORE.save(session, user_id=user.id)

    response = client.get(f"/api/attempts/{session.id}/evaluation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["report"]["attempt_id"] == session.id
    assert len(payload["report"]["dimensions"]) == 5
    assert main.EVALUATIONS.latest(session.id) is not None


def test_legacy_completed_attempt_without_a_schema_marker_can_be_debriefed(monkeypatch) -> None:
    monkeypatch.setattr(main, "EVALUATOR", None)
    client = TestClient(main.app)
    user = sign_in(client, "legacy-debrief@casecall.test")
    legacy_id = "legacy-ended-attempt"
    legacy_payload = {
        "mode": "realistic",
        "stage": "synthesis",
        "disclosed_ids": [],
        "messages": [
            {"role": "interviewer", "content": "The client needs a recommendation."},
            {"role": "candidate", "content": "I would clarify the objective, structure the drivers, and quantify the impact."},
        ],
        "candidate_turns": 1,
        "ended": True,
        "turn_results": {},
    }
    with main.STORE._connect() as connection:
        connection.execute(
            "INSERT INTO attempts (id, case_id, session_json, user_id) VALUES (?, ?, ?, ?)",
            (legacy_id, main.CATALOGUE.default_case.id, json.dumps(legacy_payload), user.id),
        )
    main.ACCOUNTS.claim_attempt(legacy_id, user.id)

    response = client.get(f"/api/attempts/{legacy_id}/evaluation")
    assert response.status_code == 200
    assert response.json()["report"]["attempt_id"] == legacy_id
    assert len(response.json()["report"]["dimensions"]) == 5
