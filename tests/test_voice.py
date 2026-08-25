import hashlib
import hmac
import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

import app.main as main
from app.interviewer import InterviewTurn
from app.store import ActiveVoiceSessionExists, VoiceSession
from app.voice import ProviderConversationToken
from app.voice_onboarding import VoiceOnboardingTurn
from conftest import sign_in


def _client() -> TestClient:
    client = TestClient(main.app)
    # A fresh candidate per test. One open attempt per user and case is
    # intended product behaviour, so a shared identity makes every attempt
    # after the first return 409 once a test has started one.
    sign_in(client, f"voice-candidate-{uuid4()}@casecall.test")
    return client


class VoiceStubInterviewer:
    def respond(self, session, candidate_turn, *, spoken=False):
        session.record_candidate_turn(candidate_turn)
        facts = session.case.validate_fact_selection(
            ["customers.segment-mix"], session.stage, session.disclosed_ids
        )
        session.apply_director_decision(session.stage, facts)
        session.add_interviewer_turn("The approved voice response.")
        return InterviewTurn(reply="The approved voice response.", facts=facts)


class ReadyOnboarding:
    def respond(self, candidate_turn):
        return VoiceOnboardingTurn(ready_to_begin=True, reply="Okay, let's begin.")


class DivergentVoiceStub:
    """Proves TTS always receives the exact reply persisted in chat."""

    def respond(self, session, candidate_turn, *, spoken=False):
        session.record_candidate_turn(candidate_turn)
        session.add_interviewer_turn("Canonical chat reply.")
        return InterviewTurn(
            reply="Canonical chat reply.", facts=[], spoken_reply="Different speech must never be used."
        )


def _enable_voice(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_leo_test")
    monkeypatch.setenv("ELEVENLABS_CUSTOM_LLM_SECRET", "adapter-secret")


def _enable_native_voice(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_VOICE_MODE", "native")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_leo_test")
    monkeypatch.setenv("ELEVENLABS_CASE_TOOL_SECRET", "case-tool-secret")
    monkeypatch.delenv("ELEVENLABS_CUSTOM_LLM_SECRET", raising=False)


def test_voice_session_route_is_hidden_until_feature_is_enabled(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_ENABLED", "false")
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]

    response = client.post(f"/api/attempts/{attempt_id}/voice-sessions")

    assert response.status_code == 404
    assert client.get("/api/voice/status").json() == {"enabled": False, "ready": False}


def test_voice_status_needs_the_adapter_secret_before_the_browser_can_start(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_AGENT_ID", "agent_leo_test")
    monkeypatch.delenv("ELEVENLABS_CUSTOM_LLM_SECRET", raising=False)

    assert _client().get("/api/voice/status").json() == {"enabled": True, "ready": False}


def test_voice_session_issues_only_a_browser_safe_conversation_token(monkeypatch) -> None:
    _enable_voice(monkeypatch)
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    captured: dict[str, str] = {}

    def issue_token(_, settings, *, participant_name):
        captured["participant_name"] = participant_name
        assert settings.agent_id == "agent_leo_test"
        return ProviderConversationToken(token="temporary-browser-token", conversation_id="conv_123")

    monkeypatch.setattr(main.VOICE_PROVIDER, "issue_token", issue_token.__get__(main.VOICE_PROVIDER))

    response = client.post(f"/api/attempts/{attempt_id}/voice-sessions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["voice_session_id"] == captured["participant_name"]
    assert payload["conversation_token"] == "temporary-browser-token"
    assert payload["transport"] == "webrtc"
    assert payload["voice_intro"].startswith("Hi, I'm Leo.")
    assert payload["case_opening"].startswith("Your client is Meridian Cold Chain")
    assert "conv_123" not in str(payload)
    stored = main.STORE.get_voice_session(payload["voice_session_id"])
    assert stored is not None
    assert stored.attempt_id == attempt_id
    assert stored.provider_conversation_id == "conv_123"
    attempt = client.get(f"/api/attempts/{attempt_id}").json()
    assert attempt["messages"] == [
        {
            "role": "interviewer",
            "content": "Hi, I'm Leo. I'll be your case interviewer today, and we're working through a profitability case. "
            "Think aloud, keep your reasoning structured, and ask for the information you need. "
            "When you're ready, just say so and we'll get started.",
        }
    ]


def test_native_voice_session_sends_only_selected_context_and_fact_index(monkeypatch) -> None:
    _enable_native_voice(monkeypatch)
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]

    def issue_token(_, settings, *, participant_name):
        assert settings.uses_native_agent is True
        return ProviderConversationToken(token="native-browser-token", conversation_id="conv_native")

    monkeypatch.setattr(main.VOICE_PROVIDER, "issue_token", issue_token.__get__(main.VOICE_PROVIDER))
    payload = client.post(f"/api/attempts/{attempt_id}/voice-sessions").json()

    assert payload["voice_mode"] == "native"
    variables = payload["dynamic_variables"]
    assert variables["voice_session_id"] == payload["voice_session_id"]
    assert variables["case_title"] == "Meridian Cold Chain"
    assert "customers.segment-mix" in variables["case_fact_index"]
    assert "Revenue grew" not in variables["case_fact_index"]
    assert "case_opening" in variables


def test_native_agent_transcript_is_saved_exactly_once_and_starts_case(monkeypatch) -> None:
    _enable_native_voice(monkeypatch)
    client = _client()
    started = client.post("/api/attempts", json={}).json()

    def issue_token(_, settings, *, participant_name):
        return ProviderConversationToken(token="native-browser-token", conversation_id="conv_native_transcript")

    monkeypatch.setattr(main.VOICE_PROVIDER, "issue_token", issue_token.__get__(main.VOICE_PROVIDER))
    voice = client.post(f"/api/attempts/{started['id']}/voice-sessions").json()
    intro = started["messages"][0]["content"]
    opening = main.CATALOGUE.default_case.opening

    for payload in (
        {"role": "interviewer", "content": intro, "event_id": "intro"},
        {"role": "candidate", "content": "I'm ready.", "event_id": "ready"},
        {"role": "interviewer", "content": opening, "event_id": "opening"},
        {"role": "interviewer", "content": opening, "event_id": "opening"},
    ):
        response = client.post(f"/api/voice-sessions/{voice['voice_session_id']}/transcript", json=payload)
        assert response.status_code == 200

    attempt = client.get(f"/api/attempts/{started['id']}").json()
    assert attempt["messages"] == [
        {"role": "interviewer", "content": intro},
        {"role": "candidate", "content": "I'm ready."},
        {"role": "interviewer", "content": opening},
    ]
    assert main.STORE.get_voice_session(voice["voice_session_id"]).case_started is True


def test_native_case_fact_tool_validates_and_releases_only_requested_fact(monkeypatch) -> None:
    _enable_native_voice(monkeypatch)
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    main.STORE.create_voice_session(
        VoiceSession(
            id="voice-native-facts",
            attempt_id=attempt_id,
            provider="elevenlabs",
            agent_id="agent_leo_test",
            provider_conversation_id="conv_native_facts",
            status="connected",
            case_started=True,
        )
    )
    request = {
        "voice_session_id": "voice-native-facts",
        "fact_ids": ["customers.segment-mix", "not-a-real-fact"],
        "proposed_phase": "clarification",
    }

    rejected = client.post("/api/elevenlabs/case-facts", json=request)
    accepted = client.post(
        "/api/elevenlabs/case-facts",
        json=request,
        headers={"Authorization": "Bearer case-tool-secret"},
    )
    raw_secret = client.post(
        "/api/elevenlabs/case-facts",
        json={**request, "fact_ids": []},
        headers={"Authorization": "case-tool-secret"},
    )

    assert rejected.status_code == 401
    assert accepted.status_code == 200
    assert raw_secret.status_code == 200
    assert accepted.json()["facts"] == [
        {
            "id": "customers.segment-mix",
            "content": (
                "Packaged food represented about 95 percent of volume two years ago and about 70 percent today. "
                "Pharmaceutical volume grew from about 5 percent to about 30 percent."
            ),
        }
    ]
    attempt = client.get(f"/api/attempts/{attempt_id}").json()
    assert attempt["facts"] == accepted.json()["facts"]


def test_attempt_cannot_have_two_live_voice_sessions() -> None:
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    main.STORE.create_voice_session(
        VoiceSession(
            id="voice-live-1",
            attempt_id=attempt_id,
            provider="elevenlabs",
            agent_id="agent_leo_test",
            provider_conversation_id="conv_live_1",
            status="issued",
        )
    )

    with pytest.raises(ActiveVoiceSessionExists):
        main.STORE.create_voice_session(
            VoiceSession(
                id="voice-live-2",
                attempt_id=attempt_id,
                provider="elevenlabs",
                agent_id="agent_leo_test",
                provider_conversation_id="conv_live_2",
                status="connected",
            )
        )


def test_custom_llm_adapter_uses_the_same_idempotent_turn_service(monkeypatch) -> None:
    _enable_voice(monkeypatch)
    monkeypatch.setattr(main, "INTERVIEWER", VoiceStubInterviewer())
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    voice_session = VoiceSession(
        id="voice-session-1",
        attempt_id=attempt_id,
        provider="elevenlabs",
        agent_id="agent_leo_test",
        provider_conversation_id="conv_voice_1",
        status="issued",
        case_started=True,
    )
    main.STORE.create_voice_session(voice_session)
    body = {
        "model": "leo",
        "user_id": voice_session.id,
        "messages": [{"role": "user", "content": "What has changed in the mix?"}],
    }
    headers = {"Authorization": "Bearer adapter-secret"}

    first = client.post("/v1/chat/completions", json=body, headers=headers)
    second = client.post("/v1/chat/completions", json=body, headers=headers)

    assert first.status_code == 200
    assert first.headers["content-type"].startswith("text/event-stream")
    assert "The approved voice response." in first.text
    assert first.text.rstrip().endswith("data: [DONE]")
    assert second.status_code == 200
    attempt = client.get(f"/api/attempts/{attempt_id}").json()
    assert [message["role"] for message in attempt["messages"]] == [
        "interviewer",
        "candidate",
        "interviewer",
    ]
    assert attempt["messages"][1]["content"] == "What has changed in the mix?"


def test_custom_llm_adapter_accepts_the_dynamic_voice_session_binding(monkeypatch) -> None:
    _enable_voice(monkeypatch)
    monkeypatch.setattr(main, "INTERVIEWER", VoiceStubInterviewer())
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    voice_session = VoiceSession(
        id="9bb95903-45f1-4dc1-ab9d-00b9db5f2621",
        attempt_id=attempt_id,
        provider="elevenlabs",
        agent_id="agent_leo_test",
        provider_conversation_id="conv_voice_dynamic",
        status="issued",
        case_started=True,
    )
    main.STORE.create_voice_session(voice_session)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "leo",
            "messages": [
                {"role": "system", "content": f"Runtime binding: VOICE_SESSION_ID={voice_session.id}"},
                {"role": "user", "content": "What has changed in the mix?"},
            ],
        },
        headers={"Authorization": "Bearer adapter-secret"},
    )

    assert response.status_code == 200
    assert "The approved voice response." in response.text


def test_custom_llm_adapter_accepts_the_signed_extra_body_binding(monkeypatch) -> None:
    _enable_voice(monkeypatch)
    monkeypatch.setattr(main, "INTERVIEWER", VoiceStubInterviewer())
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    voice_session = VoiceSession(
        id="3e96f6bc-99ab-498e-bce2-2c45f18366ac",
        attempt_id=attempt_id,
        provider="elevenlabs",
        agent_id="agent_leo_test",
        provider_conversation_id="conv_voice_extra_body",
        status="issued",
        case_started=True,
    )
    main.STORE.create_voice_session(voice_session)
    settings = main.VoiceSettings.from_environment()

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "leo",
            "messages": [{"role": "user", "content": "What has changed in the mix?"}],
            "elevenlabs_extra_body": {
                "voice_session_id": voice_session.id,
                "voice_session_binding": main._voice_session_binding(voice_session.id, settings),
            },
        },
        headers={"Authorization": "Bearer adapter-secret"},
    )

    assert response.status_code == 200
    assert "The approved voice response." in response.text

    rejected = client.post(
        "/v1/chat/completions",
        json={
            "model": "leo",
            "messages": [{"role": "user", "content": "Try again."}],
            "elevenlabs_extra_body": {
                "voice_session_id": voice_session.id,
                "voice_session_binding": "not-a-valid-binding",
            },
        },
        headers={"Authorization": "Bearer adapter-secret"},
    )
    assert rejected.status_code == 401


def test_custom_llm_speaks_the_exact_canonical_chat_reply(monkeypatch) -> None:
    _enable_voice(monkeypatch)
    monkeypatch.setattr(main, "INTERVIEWER", DivergentVoiceStub())
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    voice_session = VoiceSession(
        id="6822b404-0ce8-4e79-a5e6-6039ff8866aa",
        attempt_id=attempt_id,
        provider="elevenlabs",
        agent_id="agent_leo_test",
        provider_conversation_id="conv_voice_exact_text",
        status="issued",
        case_started=True,
    )
    main.STORE.create_voice_session(voice_session)

    response = client.post(
        "/v1/chat/completions",
        json={"model": "leo", "user_id": voice_session.id, "messages": [{"role": "user", "content": "Continue."}]},
        headers={"Authorization": "Bearer adapter-secret"},
    )

    assert "Canonical chat reply." in response.text
    assert "Different speech must never be used." not in response.text


def test_bound_voice_session_receives_the_welcome_before_any_candidate_turn(monkeypatch) -> None:
    _enable_voice(monkeypatch)
    client = _client()
    started = client.post("/api/attempts", json={}).json()
    voice_session = VoiceSession(
        id="9c866425-2a17-4278-8df2-ed3cc406aa91",
        attempt_id=started["id"],
        provider="elevenlabs",
        agent_id="agent_leo_test",
        provider_conversation_id="conv_voice_opening",
        status="issued",
    )
    main.STORE.create_voice_session(voice_session)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "leo",
            "messages": [{"role": "system", "content": f"VOICE_SESSION_ID={voice_session.id}"}],
        },
        headers={"Authorization": "Bearer adapter-secret"},
    )

    assert response.status_code == 200
    assert "Hi, I'm Leo." in response.text
    attempt = client.get(f"/api/attempts/{started['id']}").json()
    assert attempt["messages"] == started["messages"]


def test_voice_readiness_is_saved_to_chat_before_leo_starts_the_case(monkeypatch) -> None:
    _enable_voice(monkeypatch)
    monkeypatch.setattr(main, "VOICE_ONBOARDING", ReadyOnboarding())
    def issue_token(_, settings, *, participant_name):
        return ProviderConversationToken(token="temporary-browser-token", conversation_id="conv_voice_ready")

    monkeypatch.setattr(main.VOICE_PROVIDER, "issue_token", issue_token.__get__(main.VOICE_PROVIDER))
    client = _client()
    started = client.post("/api/attempts", json={}).json()
    voice_session = client.post(f"/api/attempts/{started['id']}/voice-sessions").json()

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "leo",
            "user_id": voice_session["voice_session_id"],
            "messages": [{"role": "user", "content": "I'm ready to begin."}],
        },
        headers={"Authorization": "Bearer adapter-secret"},
    )

    assert response.status_code == 200
    assert main.CATALOGUE.default_case.opening in response.text
    attempt = client.get(f"/api/attempts/{started['id']}").json()
    assert attempt["messages"][0]["content"].startswith("Hi, I'm Leo.")
    assert attempt["messages"][1] == {"role": "candidate", "content": "I'm ready to begin."}
    assert attempt["messages"][2]["role"] == "interviewer"
    assert attempt["messages"][2]["content"].endswith(main.CATALOGUE.default_case.opening)
    assert main.STORE.get_voice_session(voice_session["voice_session_id"]).case_started is True


def test_custom_llm_final_asr_reconciles_the_candidate_message_in_chat(monkeypatch) -> None:
    """The browser's final ASR event supersedes a provisional Custom LLM turn."""

    _enable_voice(monkeypatch)
    monkeypatch.setattr(main, "VOICE_ONBOARDING", ReadyOnboarding())
    client = _client()
    started = client.post("/api/attempts", json={}).json()
    voice_session = VoiceSession(
        id="voice-final-asr",
        attempt_id=started["id"],
        provider="elevenlabs",
        agent_id="agent_leo_test",
        provider_conversation_id="conv_final_asr",
        status="issued",
    )
    main.STORE.create_voice_session(voice_session)
    headers = {"Authorization": "Bearer adapter-secret"}

    provisional = client.post(
        "/v1/chat/completions",
        json={
            "model": "leo",
            "user_id": voice_session.id,
            "messages": [{"role": "user", "content": "I'm ready."}],
        },
        headers=headers,
    )
    assert provisional.status_code == 200

    reconciled = client.post(
        f"/api/voice-sessions/{voice_session.id}/final-candidate-transcript",
        json={"role": "candidate", "content": "I'm ready. Let's get started.", "event_id": "final-ready"},
    )

    assert reconciled.status_code == 200
    assert reconciled.json()["attempt"]["messages"][1] == {
        "role": "candidate",
        "content": "I'm ready. Let's get started.",
    }


def test_custom_llm_adapter_rejects_unknown_or_unauthenticated_callbacks(monkeypatch) -> None:
    _enable_voice(monkeypatch)
    client = _client()
    body = {"model": "leo", "user_id": "unknown", "messages": [{"role": "user", "content": "Hello"}]}

    assert client.post("/v1/chat/completions", json=body).status_code == 401
    assert client.post(
        "/v1/chat/completions", json=body, headers={"Authorization": "Bearer adapter-secret"}
    ).status_code == 404


def test_custom_llm_connection_check_is_safe_and_does_not_create_a_turn(monkeypatch) -> None:
    _enable_voice(monkeypatch)
    client = _client()
    response = client.post(
        "/v1/chat/completions",
        json={"model": "leo", "messages": [{"role": "user", "content": "Connection check"}]},
        headers={"Authorization": "Bearer adapter-secret"},
    )

    assert response.status_code == 200
    assert "Leo's voice connection is ready." in response.text


def test_post_call_webhook_requires_hmac_and_never_stores_the_provider_transcript(monkeypatch) -> None:
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", "webhook-secret")
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    main.STORE.create_voice_session(
        VoiceSession(
            id="voice-session-webhook",
            attempt_id=attempt_id,
            provider="elevenlabs",
            agent_id="agent_leo_test",
            provider_conversation_id="conv_webhook",
            status="ended",
        )
    )
    raw_body = json.dumps(
        {
            "type": "post_call_transcription",
            "data": {"conversation_id": "conv_webhook", "transcript": [{"message": "provider copy"}]},
        },
        separators=(",", ":"),
    ).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        b"webhook-secret", f"{timestamp}.".encode() + raw_body, hashlib.sha256
    ).hexdigest()

    rejected = client.post("/api/webhooks/elevenlabs/post-call", content=raw_body)
    accepted = client.post(
        "/api/webhooks/elevenlabs/post-call",
        content=raw_body,
        headers={"ElevenLabs-Signature": f"t={timestamp},v0={signature}", "Content-Type": "application/json"},
    )

    assert rejected.status_code == 401
    assert accepted.status_code == 200
    assert main.STORE.get_voice_session("voice-session-webhook").status == "reconciled"
