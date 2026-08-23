from fastapi.testclient import TestClient

import app.main as main
from conftest import sign_in
from app.interviewer import InterviewTurn, _finalize_reply


class StubInterviewer:
    """A scripted test double; production routing is exclusively LLM-directed."""

    def respond(self, session, candidate_turn):
        session.record_candidate_turn(candidate_turn)
        facts = session.case.validate_fact_selection(
            ["customers.segment-mix"], session.stage, session.disclosed_ids
        )
        session.apply_director_decision(session.stage, facts)
        session.add_interviewer_turn("The relevant case context has been released.")
        return InterviewTurn(reply="The relevant case context has been released.", facts=facts)


main.INTERVIEWER = StubInterviewer()
client = TestClient(main.app)
# The interview API now requires a signed-in candidate. Google is not involved
# here: conftest.sign_in creates the account and attaches its session cookie.
CANDIDATE = sign_in(client, "candidate@casecall.test")


def test_landing_page_is_public_and_does_not_start_an_attempt() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Practise with" in response.text
    assert "Leo" in response.text
    assert "id=\"case-grid\"" in response.text


def test_candidate_never_receives_hidden_diagnosis() -> None:
    started = client.post("/api/attempts", json={})
    assert started.status_code == 200
    payload = started.json()
    assert "priced off the food cost base" not in str(payload).lower()

    attempt_id = payload["id"]
    response = client.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "Has the customer or product mix changed?", "turn_id": "mix-question"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "95 percent" in str(data["new_facts"]).lower()
    assert "priced off the food cost base" not in str(data).lower()


def test_cannot_start_an_unsupported_case_duration() -> None:
    response = client.post("/api/attempts", json={"duration_minutes": 45})
    assert response.status_code == 422


def test_public_catalogue_lists_the_twelve_case_library() -> None:
    response = client.get("/api/cases")

    assert response.status_code == 200
    assert len(response.json()["cases"]) == 12
    assert {case["id"] for case in response.json()["cases"]} >= {
        "meridian-cold-chain-v1", "harvest-table-v1", "terrabuild-materials-v1"
    }


def test_candidate_can_start_a_selected_case() -> None:
    response = client.post("/api/attempts", json={"case_id": "harvest-table-v1"})

    assert response.status_code == 200
    assert response.json()["case"]["title"] == "Harvest Table"


def test_case_opening_is_a_brief_not_a_forced_question() -> None:
    response = client.post("/api/attempts", json={})

    assert response.status_code == 200
    opening = response.json()["messages"][0]["content"].strip()
    assert not opening.endswith("?")


def test_duplicate_turn_id_is_processed_once() -> None:
    started = client.post("/api/attempts", json={}).json()
    payload = {"content": "What is the business model?", "turn_id": "same-turn"}

    first = client.post(f"/api/attempts/{started['id']}/turn", json=payload)
    second = client.post(f"/api/attempts/{started['id']}/turn", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["attempt"]["messages"]) == 3


def test_interviewer_reply_never_contains_an_em_dash() -> None:
    assert _finalize_reply("The relevant point is clear—move to the next branch.") == (
        "The relevant point is clear, move to the next branch."
    )
