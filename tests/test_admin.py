"""The admin console: who may open it, and whether its numbers are right."""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main
from conftest import sign_in


def _start(client, case_id: str | None = None) -> str:
    # A candidate may hold only one attempt per case, so a test that needs two
    # attempts for one person must spread them across two cases.
    payload = {} if case_id is None else {"case_id": case_id}
    started = client.post("/api/attempts", json=payload)
    assert started.status_code == 200
    return started.json()["id"]


# --- Access ----------------------------------------------------------------


def test_the_admin_api_is_closed_to_anonymous_visitors() -> None:
    client = TestClient(main.app)
    assert client.get("/api/admin/overview").status_code == 401


def test_the_admin_api_is_closed_to_ordinary_candidates(candidate_client) -> None:
    client, _ = candidate_client
    for path in ("/overview", "/users", "/attempts"):
        assert client.get(f"/api/admin{path}").status_code == 403


def test_the_admin_page_sends_candidates_back_to_the_practice_room(candidate_client) -> None:
    client, _ = candidate_client
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/practice"


def test_the_admin_page_sends_anonymous_visitors_to_sign_in() -> None:
    client = TestClient(main.app)
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert "/login" in response.headers["location"]


def test_an_administrator_is_recognised_from_the_environment(admin_client) -> None:
    client, user = admin_client
    assert user.is_admin is True
    assert client.get("/api/me").json()["user"]["is_admin"] is True
    assert client.get("/admin", follow_redirects=False).status_code == 200


def test_admin_status_follows_the_configured_allow_list(admin_client, monkeypatch) -> None:
    client, _ = admin_client
    monkeypatch.setenv("ADMIN_EMAILS", "someone.else@casecall.test")
    # Rights are derived per request, so revoking the allow-list entry takes
    # effect immediately rather than at the next sign-in.
    assert client.get("/api/admin/overview").status_code == 403


def test_no_one_is_an_administrator_when_the_allow_list_is_empty(monkeypatch) -> None:
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    client = TestClient(main.app)
    sign_in(client, "nobody@casecall.test")
    assert client.get("/api/admin/overview").status_code == 403


# --- Metrics ---------------------------------------------------------------


def test_the_overview_counts_attempts_and_completion(admin_client) -> None:
    admin, _ = admin_client

    candidate = TestClient(main.app)
    owner = sign_in(candidate, "metrics@casecall.test", name="Metrics Candidate")
    first = _start(candidate)
    _start(candidate, "clearcart-v1")
    assert candidate.post(f"/api/attempts/{first}/end", json={"disposition": "scored"}).status_code == 200

    totals = admin.get("/api/admin/overview").json()["totals"]
    assert totals["attempts"] >= 2
    assert totals["attempts_completed"] >= 1
    assert 0 < totals["completion_rate"] <= 1
    assert totals["users"] >= 2

    people = {person["email"]: person for person in admin.get("/api/admin/users").json()["users"]}
    assert people[owner.email]["attempts"] == 2
    assert people[owner.email]["attempts_completed"] == 1
    assert people[owner.email]["completion_rate"] == 0.5


def test_the_overview_reports_a_fourteen_day_window(admin_client) -> None:
    admin, _ = admin_client
    overview = admin.get("/api/admin/overview").json()
    assert len(overview["daily"]) == 14
    assert all(set(day) == {"date", "count"} for day in overview["daily"])


def test_attempts_can_be_filtered_to_one_candidate(admin_client) -> None:
    admin, _ = admin_client
    candidate = TestClient(main.app)
    owner = sign_in(candidate, "filter@casecall.test")
    _start(candidate)

    filtered = admin.get(f"/api/admin/attempts?user_id={owner.id}").json()["attempts"]
    assert filtered
    assert {attempt["user"]["id"] for attempt in filtered} == {owner.id}


# --- Transcripts -----------------------------------------------------------


def test_an_administrator_reads_the_transcript_with_its_owner(admin_client, stub_interviewer) -> None:
    admin, _ = admin_client
    candidate = TestClient(main.app)
    owner = sign_in(candidate, "transcript@casecall.test", name="Transcript Candidate")
    attempt_id = _start(candidate)
    assert candidate.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "I'm ready to begin.", "turn_id": "ready"},
    ).status_code == 200
    assert candidate.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "Has the customer mix changed?", "turn_id": "turn-1"},
    ).status_code == 200

    payload = admin.get(f"/api/admin/attempts/{attempt_id}").json()
    assert payload["attempt"]["user"]["email"] == owner.email
    roles = [message["role"] for message in payload["messages"]]
    assert roles == ["interviewer", "candidate", "interviewer", "candidate", "interviewer"]
    assert payload["facts"], "a released fact should be listed with its content"
    assert all(fact["content"] for fact in payload["facts"])
    assert payload["scorecard"]["dimensions"]


def test_a_transcript_never_carries_the_hidden_diagnosis(admin_client, stub_interviewer) -> None:
    admin, _ = admin_client
    candidate = TestClient(main.app)
    sign_in(candidate, "leak@casecall.test")
    attempt_id = _start(candidate)
    candidate.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "What is the segment mix?", "turn_id": "turn-1"},
    )

    body = str(admin.get(f"/api/admin/attempts/{attempt_id}").json()).lower()
    assert "priced off the food cost base" not in body


def test_an_unknown_transcript_is_a_clean_404(admin_client) -> None:
    admin, _ = admin_client
    assert admin.get("/api/admin/attempts/does-not-exist").status_code == 404


def test_an_administrator_may_read_a_candidates_attempt_through_the_interview_api(admin_client) -> None:
    admin, _ = admin_client
    candidate = TestClient(main.app)
    sign_in(candidate, "reviewed@casecall.test")
    attempt_id = _start(candidate)
    # Reviewing a candidate's own view is part of the admin remit.
    assert admin.get(f"/api/attempts/{attempt_id}").status_code == 200
