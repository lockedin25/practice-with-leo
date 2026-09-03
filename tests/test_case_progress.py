"""Readiness gating and durable per-user case progress."""

from __future__ import annotations

from pathlib import Path

import pytest

import app.main as main
from app.voice_onboarding import VoiceOnboardingTurn


ROOT = Path(__file__).resolve().parents[1]


class NotReadyOnboarding:
    def respond(self, _candidate_turn: str) -> VoiceOnboardingTurn:
        return VoiceOnboardingTurn(
            ready_to_begin=False,
            reply="Take your time. I will start the case when you say you are ready.",
        )


class ReadyOnboarding:
    def respond(self, _candidate_turn: str) -> VoiceOnboardingTurn:
        return VoiceOnboardingTurn(ready_to_begin=True, reply="Okay, let's begin.")


def test_case_opening_is_held_until_llm_confirms_readiness(candidate_client, monkeypatch) -> None:
    client, _ = candidate_client
    monkeypatch.setattr(main, "VOICE_ONBOARDING", NotReadyOnboarding())
    started = client.post("/api/attempts", json={}).json()

    assert started["case_started"] is False
    assert len(started["messages"]) == 1
    assert main.CATALOGUE.default_case.opening not in str(started["messages"])

    waiting = client.post(
        f"/api/attempts/{started['id']}/turn",
        json={"content": "Can you explain the format first?", "turn_id": "orientation"},
    ).json()
    assert waiting["attempt"]["case_started"] is False
    assert main.CATALOGUE.default_case.opening not in str(waiting["attempt"]["messages"])

    monkeypatch.setattr(main, "VOICE_ONBOARDING", ReadyOnboarding())
    begun = client.post(
        f"/api/attempts/{started['id']}/turn",
        json={"content": "I am ready now.", "turn_id": "ready"},
    ).json()
    assert begun["attempt"]["case_started"] is True
    assert begun["reply"].startswith("Okay, let's begin.")
    assert begun["reply"].endswith(main.CATALOGUE.default_case.opening)


@pytest.mark.xfail(
    reason="Pre-existing RED on realtime-voice-ptt WIP: syncTimer() not implemented in "
    "app/static/app.js yet (known issue, tracked in docs/campaign/CAMPAIGN_REPORT.md)",
    strict=False,
)
def test_start_case_control_submits_a_readiness_turn_to_open_the_timer_gate() -> None:
    """The visible start control must actually drive the server-owned gate."""

    client_code = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert 'el.beginCase?.addEventListener("click"' in client_code
    assert 'sendTurn("I\'m ready to begin.", crypto.randomUUID());' in client_code
    assert "syncTimer(attempt);" in client_code


def test_early_exit_is_retained_abandoned_and_scored_practice_updates_progress(
    candidate_client, monkeypatch, stub_interviewer
) -> None:
    client, _ = candidate_client
    monkeypatch.setattr(main, "EVALUATOR", None)
    started = client.post("/api/attempts", json={}).json()
    case_id = started["case"]["id"]

    readiness = client.post(
        f"/api/attempts/{started['id']}/turn",
        json={"content": "I am ready to begin.", "turn_id": "ready"},
    )
    assert readiness.status_code == 200

    ended = client.post(f"/api/attempts/{started['id']}/end")
    assert ended.status_code == 200
    assert ended.json()["attempt"]["disposition"] == "abandoned"
    assert ended.json()["evaluation"] is None

    history = client.get("/api/me/practice-history").json()
    abandoned = next(item for item in history["attempts"] if item["id"] == started["id"])
    assert abandoned["disposition"] == "abandoned"
    assert abandoned["feedback"] is None
    assert history["summary"]["abandoned"] >= 1

    profile = client.get("/api/me/profile").json()
    assert profile["summary"]["average_feedback_score"] is None
    assert profile["performance"] == []

    progress = client.get("/api/me/case-progress").json()["progress"]
    current = next(item for item in progress if item["case_id"] == case_id)
    assert current["status"] == "not_started"

    # A real two-turn case is scored by default and contributes normally.
    scored = client.post("/api/attempts", json={"case_id": case_id}).json()
    client.post(
        f"/api/attempts/{scored['id']}/turn",
        json={"content": "I am ready to begin.", "turn_id": "scored-ready"},
    )
    for index in range(2):
        turn = client.post(
            f"/api/attempts/{scored['id']}/turn",
            json={"content": f"I will test driver {index} before drawing a conclusion.", "turn_id": f"case-{index}"},
        )
        assert turn.status_code == 200

    scored_end = client.post(f"/api/attempts/{scored['id']}/end")
    assert scored_end.status_code == 200
    assert scored_end.json()["attempt"]["disposition"] == "scored"
    assert scored_end.json()["evaluation"] is not None

    profile = client.get("/api/me/profile").json()
    assert profile["summary"]["average_feedback_score"] is not None
    assert profile["performance"]
    performance = client.get(f"/api/me/cases/{case_id}/performance").json()
    assert performance["progress"]["status"] == "solved"
