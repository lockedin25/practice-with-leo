"""User-scoped persistence for cases, transcripts, and feedback."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
from conftest import sign_in


ROOT = Path(__file__).resolve().parents[1]


def _report(attempt_id: str) -> dict[str, object]:
    return {
        "attempt_id": attempt_id,
        "evaluator_version": "practice-history-v1",
        "dimensions": [
            {"name": "structuring", "score": 4.0},
            {"name": "problem_solving", "score": 3.0},
            {"name": "communication", "score": 5.0},
            {"name": "quantitative", "score": 4.0},
        ],
        "checklist": [],
        "headline_strengths": ["Clear structure"],
        "priority_improvements": ["State the hypothesis first"],
        "next_drill": "Practise hypothesis-led clarification.",
    }


def test_practice_history_is_user_scoped_and_contains_feedback(candidate_client) -> None:
    client, user = candidate_client
    started = client.post("/api/attempts", json={}).json()
    attempt_id = started["id"]
    main.EVALUATIONS.save(json.dumps(_report(attempt_id)), attempt_id, "practice-history-v1")

    other = TestClient(main.app)
    sign_in(other, "other-history@casecall.test")
    other.post("/api/attempts", json={"case_id": "harvest-table-v1"})

    history = client.get("/api/me/practice-history")

    assert history.status_code == 200
    body = history.json()
    record = next(item for item in body["attempts"] if item["id"] == attempt_id)
    assert record["case"]["id"] == started["case"]["id"]
    assert record["feedback"]["overall_score"] == 4.0
    assert body["summary"]["feedback_available"] >= 1
    assert main.STORE.get_user_practice(user.id, attempt_id) is not None
    assert all(item["id"] != attempt_id for item in other.get("/api/me/practice-history").json()["attempts"])


def test_practice_history_detail_returns_owned_transcript_and_hides_other_users(candidate_client) -> None:
    client, _ = candidate_client
    started = client.post("/api/attempts", json={}).json()
    attempt_id = started["id"]

    detail = client.get(f"/api/me/practice-history/{attempt_id}")

    assert detail.status_code == 200
    assert detail.json()["transcript"] == started["messages"]

    intruder = TestClient(main.app)
    sign_in(intruder, "history-intruder@casecall.test")
    assert intruder.get(f"/api/me/practice-history/{attempt_id}").status_code == 404


def test_profile_derives_personal_progress_and_development_areas(candidate_client) -> None:
    client, _ = candidate_client
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    report = _report(attempt_id)
    report["priority_improvements"] = ["State the hypothesis first"]
    report["headline_strengths"] = ["Clear structure"]
    main.EVALUATIONS.save(json.dumps(report), attempt_id, "practice-profile-v1")

    response = client.get("/api/me/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["attempts"] >= 1
    assert body["summary"]["average_feedback_score"] == 4.0
    assert body["performance"][0]["name"] == "problem_solving"
    assert body["development_areas"][0]["text"] == "State the hypothesis first"
    assert any(item["id"] == attempt_id for item in body["recent_attempts"])


def test_profile_page_requires_authentication() -> None:
    client = TestClient(main.app)
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] in ("/login?next=/profile", "/login?next=%2Fprofile")


def test_profile_recent_attempts_contain_debrief_url_and_source(candidate_client) -> None:
    client, _ = candidate_client
    started = client.post("/api/attempts", json={"case_id": "01-beer-manufacturer-v1"}).json()
    attempt_id = started["id"]

    response = client.get("/api/me/profile")
    assert response.status_code == 200
    body = response.json()
    attempt = next(item for item in body["recent_attempts"] if item["id"] == attempt_id)
    assert attempt["debrief_url"] == f"/attempts/{attempt_id}/debrief"
    assert attempt["case"]["source"] == "curated"
    assert attempt["case"]["title"] == "Beer Manufacturer"


def test_profile_page_includes_next_step_and_history_filter_controls(candidate_client) -> None:
    """The served profile page presents one next action and manageable history controls."""
    client, _ = candidate_client
    response = client.get("/profile")

    assert response.status_code == 200
    assert 'id="next-step-title"' in response.text
    assert 'id="history-filters"' in response.text
    assert 'data-history-filter="in_progress"' in response.text
    assert 'id="history-more"' in response.text
    assert 'id="strength-more"' in response.text
    assert 'id="development-more"' in response.text

    profile_js = (ROOT / "app" / "static" / "profile.js").read_text(encoding="utf-8")
    assert "renderNextStep" in profile_js
    assert "renderHistoryView" in profile_js
    assert "renderThemeList" in profile_js
    assert "skill-card" in profile_js
    assert 'historyFilter: "all"' in profile_js
