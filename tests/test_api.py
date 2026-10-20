from fastapi.testclient import TestClient

import app.main as main
from conftest import sign_in
from app.case_runtime import InterviewSession
from app.interviewer import (
    DirectorDecision,
    FactDeliveryAudit,
    InterviewTurn,
    LangChainCaseInterviewer,
    _finalize_reply,
)


class StubInterviewer:
    """A scripted test double; production routing is exclusively LLM-directed."""

    def respond(self, session, candidate_turn, *, spoken=False):
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
    assert "id=\"browse-all-cases\"" in response.text


def test_cases_page_is_public_and_serves_catalogue() -> None:
    response = client.get("/cases")

    assert response.status_code == 200
    assert "Case Library" in response.text
    assert "id=\"cases-grid\"" in response.text
    assert "id=\"case-search\"" in response.text
    assert 'class="cases-loading"' in response.text
    assert "grid-spinner" not in response.text
    assert "nav-cta" not in response.text


def test_candidate_never_receives_hidden_diagnosis() -> None:
    started = client.post("/api/attempts", json={})
    assert started.status_code == 200
    payload = started.json()
    assert "priced off the food cost base" not in str(payload).lower()

    attempt_id = payload["id"]
    assert client.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "I'm ready to begin.", "turn_id": "ready"},
    ).status_code == 200
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
    assert len(response.json()["cases"]) == 69
    assert {case["id"] for case in response.json()["cases"]} >= {
        "meridian-cold-chain-v1", "harvest-table-v1", "terrabuild-materials-v1"
    }


def test_candidate_can_start_a_selected_case() -> None:
    response = client.post("/api/attempts", json={"case_id": "harvest-table-v1"})

    assert response.status_code == 200
    assert response.json()["case"]["title"] == "Harvest Table"


def test_case_opening_is_a_brief_not_a_forced_question() -> None:
    response = client.post("/api/attempts", json={"case_id": "terrabuild-materials-v1"})

    assert response.status_code == 200
    opening = response.json()["messages"][0]["content"].strip()
    assert not opening.endswith("?")


def test_duplicate_turn_id_is_processed_once() -> None:
    started = client.post("/api/attempts", json={"case_id": "bluecurrent-water-v1"}).json()
    assert client.post(
        f"/api/attempts/{started['id']}/turn",
        json={"content": "I'm ready to begin.", "turn_id": "ready"},
    ).status_code == 200
    payload = {"content": "What is the business model?", "turn_id": "same-turn"}

    first = client.post(f"/api/attempts/{started['id']}/turn", json=payload)
    second = client.post(f"/api/attempts/{started['id']}/turn", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["attempt"]["messages"]) == 5


def test_interviewer_reply_never_contains_an_em_dash() -> None:
    assert _finalize_reply("The relevant point is clear—move to the next branch.") == (
        "The relevant point is clear, move to the next branch."
    )


def test_incomplete_reply_is_regenerated_before_it_can_be_persisted() -> None:
    """A model fragment must never become a visible or spoken Leo turn."""

    class SequenceChain:
        def __init__(self, values):
            self.values = list(values)
            self.calls = 0

        def invoke(self, _inputs):
            self.calls += 1
            return self.values.pop(0)

    interviewer = LangChainCaseInterviewer.__new__(LangChainCaseInterviewer)
    interviewer._director = SequenceChain(
        [
            DirectorDecision(
                candidate_intent="The candidate is reflecting on the case framing.",
                move="answer",
                next_phase="clarification",
                fact_ids=[],
                interviewer_brief="Confirm the reasoning and direct the next useful step.",
            )
        ]
    )
    interviewer._voice_director = interviewer._director
    writer = SequenceChain(["That is a", "That is a reasonable starting point. Separate revenue, cost, and margin before testing a driver."])
    interviewer._voice = writer
    interviewer._voice_delivery = writer
    interviewer._voice_retry = writer
    interviewer._voice_delivery_retry = writer
    interviewer._fact_audit = SequenceChain(
        [
            FactDeliveryAudit(reply_complete=False, communicated_fact_ids=[]),
            FactDeliveryAudit(reply_complete=True, communicated_fact_ids=[]),
        ]
    )
    interviewer._reply_repair = SequenceChain([])
    interviewer._reply_repair_retry = SequenceChain([])
    session = InterviewSession(id="fragment-guard", case=main.CATALOGUE.default_case, mode="realistic")

    result = interviewer.respond(session, "I think costs have increased.")

    assert result.reply == "That is a reasonable starting point. Separate revenue, cost, and margin before testing a driver."
    assert session.messages[-1] == {"role": "interviewer", "content": result.reply}
    assert writer.calls == 2
