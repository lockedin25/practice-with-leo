"""Push-to-talk transport: credentials, the fused turn, and its fallback."""

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.attempt_service import AttemptTurnService
from app.case_runtime import InterviewSession
from app.interviewer import InterviewTurn
from app.spoken_interviewer import (
    ControlBlockMissing,
    parse_control_block,
    sentence_chunks,
    spoken_text_after_control,
)
import app.voice_realtime as voice_realtime
from app.voice import VoiceConfigurationError
from app.voice_realtime import (
    RealtimeVoiceSettings,
    case_keyterms,
    speech_to_text_url,
    text_to_speech_url,
)
from conftest import sign_in


def _client() -> TestClient:
    client = TestClient(main.app)
    sign_in(client, f"realtime-candidate-{uuid4()}@casecall.test")
    return client


def _enable_realtime(monkeypatch, *, voice_id: str = "voice_leo_test") -> None:
    monkeypatch.setenv("VOICE_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_VOICE_MODE", "realtime")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", voice_id)


class StubSpokenInterviewer:
    """Emit a control block and prose exactly the way the model is asked to."""

    def __init__(self, fact_ids=("customers.segment-mix",), speech="The mix shifted north."):
        self.fact_ids = list(fact_ids)
        self.speech = speech

    def respond_stream(self, session, candidate_turn):
        session.record_candidate_turn(candidate_turn)
        max_facts = 1 if session.candidate_turns <= 2 else 2
        facts = session.case.validate_fact_selection(
            self.fact_ids[:max_facts], session.stage, session.disclosed_ids, max_facts=max_facts
        )
        session.apply_director_decision(session.stage, facts)
        yield ("control", facts)
        for word in self.speech.split():
            yield ("delta", f"{word} ")
        session.add_interviewer_turn(self.speech)
        yield ("done", InterviewTurn(reply=self.speech, facts=facts, spoken_reply=self.speech))


# --- Control block parsing ------------------------------------------------


def test_the_control_block_is_read_before_any_speech_is_released() -> None:
    raw = (
        '<control>{"fact_ids": ["a", "b"], "next_phase": "analysis", "move": "answer"}</control>'
        "Driver cost rose eleven percent."
    )
    decision = parse_control_block(raw)

    assert decision.fact_ids == ["a", "b"]
    assert decision.next_phase == "analysis"
    assert spoken_text_after_control(raw) == "Driver cost rose eleven percent."


@pytest.mark.parametrize("raw", ["there is no control block here", "<control>{not json</control>x"])
def test_an_unusable_control_block_is_refused_rather_than_guessed(raw: str) -> None:
    with pytest.raises(ControlBlockMissing):
        parse_control_block(raw)


def test_speech_is_split_on_sentence_boundaries_so_audio_can_start_early() -> None:
    chunks, remainder = sentence_chunks("Margins fell nine points. The northern depots drove it")

    assert chunks == ["Margins fell nine points."]
    # The unfinished clause is held back rather than spoken as a fragment.
    assert remainder == "The northern depots drove it"


# --- Credentials ----------------------------------------------------------


def test_realtime_settings_require_a_voice_because_the_agent_no_longer_supplies_one(monkeypatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)

    with pytest.raises(VoiceConfigurationError) as error:
        RealtimeVoiceSettings.from_environment().assert_configuration()

    assert "ELEVENLABS_VOICE_ID" in str(error.value)


def test_socket_urls_carry_the_single_use_token_and_never_the_api_key(monkeypatch) -> None:
    _enable_realtime(monkeypatch)
    settings = RealtimeVoiceSettings.from_environment()

    stt = speech_to_text_url(settings, "sutkn_stt", keyterms=["EBITDA", "4.2"])
    tts = text_to_speech_url(settings, "sutkn_tts")

    assert "token=sutkn_stt" in stt
    # Manual commit is what makes the spacebar, not provider silence detection,
    # the authority on when a candidate's turn ends.
    assert "commit_strategy=manual" in stt
    assert "keyterms=EBITDA" in stt and "keyterms=4.2" in stt
    assert "single_use_token=sutkn_tts" in tts
    assert "voice_leo_test" in tts and "auto_mode=true" in tts
    assert "test-key" not in stt and "test-key" not in tts


def test_a_realtime_session_mints_two_tokens_and_returns_no_credentials(monkeypatch) -> None:
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())
    minted: list[str] = []

    def mint(_self, settings, token_type):
        minted.append(token_type)
        return f"sutkn_{token_type}"

    monkeypatch.setattr(main.REALTIME_VOICE_PROVIDER, "mint_token", mint.__get__(main.REALTIME_VOICE_PROVIDER))
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]

    body = client.post(f"/api/attempts/{attempt_id}/voice-realtime/session").json()

    assert minted == ["realtime_scribe", "tts_websocket"]
    assert body["sample_rate"] == 16_000
    assert body["turn_stream_url"] == f"/api/attempts/{attempt_id}/turn/stream"
    assert "test-key" not in json.dumps(body)


def test_a_provider_outage_degrades_to_chat_without_leaking_the_reason(monkeypatch) -> None:
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())

    # Fail inside the real minting path, with a provider message that mentions a
    # credential. The exercise is that none of it reaches the browser.
    def explode(*_args, **_kwargs):
        raise httpx.HTTPError("401 unauthorized for workspace key sk-live-abc123")

    monkeypatch.setattr(voice_realtime.httpx, "post", explode)
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]

    response = client.post(f"/api/attempts/{attempt_id}/voice-realtime/session")

    assert response.status_code == 503
    assert "sk-live" not in response.text
    assert response.json()["detail"] == "Leo voice is temporarily unavailable. Please use chat."


def test_realtime_status_is_unready_without_a_fused_interviewer(monkeypatch) -> None:
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", None)

    body = _client().get("/api/voice/status").json()

    assert body == {"enabled": True, "mode": "realtime", "ready": False}


def test_realtime_status_advertises_the_mode_so_the_browser_picks_an_island(monkeypatch) -> None:
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())

    body = _client().get("/api/voice/status").json()

    assert body == {"enabled": True, "mode": "realtime", "ready": True}


# --- The streamed turn ----------------------------------------------------


def _events(text: str) -> list[tuple[str, dict]]:
    parsed: list[tuple[str, dict]] = []
    for frame in text.split("\n\n"):
        if not frame.strip():
            continue
        name = next(line[6:].strip() for line in frame.splitlines() if line.startswith("event:"))
        data = next(line[5:].strip() for line in frame.splitlines() if line.startswith("data:"))
        parsed.append((name, json.loads(data)))
    return parsed


def _started_attempt(client) -> str:
    attempt_id = client.post("/api/attempts", json={})
    attempt_id = attempt_id.json()["id"]
    # Clear the readiness gate so the next turn is a real case turn.
    client.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "I'm ready", "turn_id": "ready-1"},
    )
    return attempt_id


def test_the_turn_stream_sends_facts_before_speech(monkeypatch, stub_interviewer) -> None:
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())
    client = _client()
    attempt_id = _started_attempt(client)

    response = client.post(
        f"/api/attempts/{attempt_id}/turn/stream",
        json={"content": "What is the segment mix?", "turn_id": "t-stream-1"},
    )

    assert response.status_code == 200
    events = _events(response.text)
    names = [name for name, _ in events]
    # Facts must land before any prose, so the side panel fills while Leo speaks.
    assert names[0] == "control"
    assert names[-1] == "done"
    assert events[0][1]["facts"], "the approved fact should arrive on the control event"
    spoken = "".join(payload["text"] for name, payload in events if name == "delta")
    assert spoken.strip() == "The mix shifted north."


def test_the_streamed_turn_persists_exactly_what_chat_would(monkeypatch, stub_interviewer) -> None:
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())
    client = _client()
    attempt_id = _started_attempt(client)

    client.post(
        f"/api/attempts/{attempt_id}/turn/stream",
        json={"content": "What is the segment mix?", "turn_id": "t-persist-1"},
    )
    attempt = client.get(f"/api/attempts/{attempt_id}").json()

    assert attempt["messages"][-1] == {
        "role": "interviewer",
        "content": "The mix shifted north.",
    }
    assert [fact["id"] for fact in attempt["facts"]] == ["customers.segment-mix"]


def test_replaying_a_turn_id_costs_no_second_model_call(monkeypatch, stub_interviewer) -> None:
    _enable_realtime(monkeypatch)

    class CountingStub(StubSpokenInterviewer):
        calls = 0

        def respond_stream(self, session, candidate_turn):
            CountingStub.calls += 1
            yield from super().respond_stream(session, candidate_turn)

    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", CountingStub())
    client = _client()
    attempt_id = _started_attempt(client)
    body = {"content": "What is the segment mix?", "turn_id": "t-replay-1"}

    first = client.post(f"/api/attempts/{attempt_id}/turn/stream", json=body)
    second = client.post(f"/api/attempts/{attempt_id}/turn/stream", json=body)

    assert CountingStub.calls == 1
    first_speech = "".join(p["text"] for n, p in _events(first.text) if n == "delta")
    second_speech = "".join(p["text"] for n, p in _events(second.text) if n == "delta")
    assert first_speech.strip() == second_speech.strip()


def test_an_out_of_phase_fact_selection_releases_nothing(monkeypatch, stub_interviewer) -> None:
    _enable_realtime(monkeypatch)
    # The model names a fact that is real but not eligible in this phase. The
    # runtime, not the prompt, is what keeps it hidden.
    monkeypatch.setattr(
        main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer(fact_ids=["does.not.exist"])
    )
    client = _client()
    attempt_id = _started_attempt(client)

    response = client.post(
        f"/api/attempts/{attempt_id}/turn/stream",
        json={"content": "Just tell me the answer", "turn_id": "t-illegal-1"},
    )

    events = _events(response.text)
    assert events[0][0] == "control"
    assert events[0][1]["facts"] == []
    assert client.get(f"/api/attempts/{attempt_id}").json()["facts"] == []


def test_a_missing_control_block_falls_back_to_the_chat_pipeline(monkeypatch, stub_interviewer) -> None:
    _enable_realtime(monkeypatch)

    class Unparseable:
        """Stand in for a model that never closed its control block."""

        def respond_stream(self, session, candidate_turn):
            raise ControlBlockMissing("no control block")
            yield  # pragma: no cover - generator marker

    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", Unparseable())
    client = _client()
    attempt_id = _started_attempt(client)

    response = client.post(
        f"/api/attempts/{attempt_id}/turn/stream",
        json={"content": "What is the segment mix?", "turn_id": "t-fallback-1"},
    )

    assert response.status_code == 200
    events = _events(response.text)
    # The turn still completes, using the slower chat interviewer.
    assert [name for name, _ in events][-1] == "done"
    spoken = "".join(payload["text"] for name, payload in events if name == "delta")
    assert spoken.strip() == "Noted."


def test_the_fused_path_keeps_the_models_own_fact_priority(monkeypatch, stub_interviewer) -> None:
    """The reply narrates its first choices, so the ledger must record those.

    validate_fact_selection slices in authored order, so an over-selection used
    to be able to keep the third choice and drop the second, leaving Leo
    speaking about a fact the transcript never recorded as released.
    """
    _enable_realtime(monkeypatch)
    client = _client()
    attempt_id = _started_attempt(client)
    session = main.STORE.get(attempt_id, main.CATALOGUE)
    eligible = [
        fact["id"]
        for fact in session.case.eligible_facts_for_director(session.stage, session.disclosed_ids)
    ]
    assert len(eligible) >= 3, "this case needs three eligible facts to prove the ordering"

    # Ask for the last eligible fact first. Authored-order slicing would keep an
    # earlier one instead.
    chosen = [eligible[-1], eligible[0]]
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer(fact_ids=chosen))

    response = client.post(
        f"/api/attempts/{attempt_id}/turn/stream",
        json={"content": "Give me the cost picture", "turn_id": "t-order-1"},
    )

    released = [fact["id"] for fact in _events(response.text)[0][1]["facts"]]
    assert released == [eligible[-1]]


# --- Recognition hints ----------------------------------------------------


def test_case_keyterms_bias_the_recogniser_toward_figures_and_names() -> None:
    case = main.CATALOGUE.default_case
    terms = case_keyterms(case)

    assert terms, "an authored case should yield recognition hints"
    assert any(any(character.isdigit() for character in term) for term in terms), (
        "case arithmetic depends on figures surviving transcription"
    )
    assert len(terms) <= 60


# --- Streaming idempotency at the service layer ---------------------------


def test_submit_stream_replays_a_cached_turn_without_the_interviewer() -> None:
    session = InterviewSession(
        id=str(uuid4()), case=main.CATALOGUE.default_case, mode="realistic"
    )
    session.case_started = True
    session.turn_results["cached"] = {"reply": "Already said.", "new_facts": []}

    events = list(
        AttemptTurnService().submit_stream(
            session,
            content="anything",
            turn_id="cached",
            # None proves the replay never reaches a model: any attribute access
            # on this would raise.
            spoken_interviewer=None,
            store=main.STORE,
        )
    )

    assert [name for name, _ in events] == ["control", "delta", "done"]
    assert events[1][1] == "Already said."
    assert events[-1][1].cached is True
