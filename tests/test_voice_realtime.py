"""Push-to-talk transport: credentials, the fused turn, and its fallback."""

from __future__ import annotations

import json
import threading
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
    speech_to_text_upload,
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
    assert decision.case_concluded is False
    assert spoken_text_after_control(raw) == "Driver cost rose eleven percent."


def test_the_control_block_can_formally_conclude_the_interview() -> None:
    raw = (
        '<control>{"fact_ids": [], "next_phase": "synthesis", "move": "close", '
        '"case_concluded": true}</control>That concludes the interview.'
    )

    decision = parse_control_block(raw)

    assert decision.case_concluded is True


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


def test_the_upload_carries_the_single_use_token_and_never_the_api_key(monkeypatch) -> None:
    _enable_realtime(monkeypatch)
    settings = RealtimeVoiceSettings.from_environment()

    stt = speech_to_text_upload(settings, "sutkn_stt", keyterms=["EBITDA", "4.2"])
    tts = text_to_speech_url(settings, "sutkn_tts")

    assert "token=sutkn_stt" in stt["url"]
    assert stt["model_id"] == settings.stt_model
    # Recognition is biased toward this case's own figures; a misheard number is
    # worse than a misheard word in a quantitative interview.
    assert stt["keyterms"] == ["EBITDA", "4.2"]
    assert "single_use_token=sutkn_tts" in tts
    assert "voice_leo_test" in tts and "auto_mode=true" in tts
    assert "test-key" not in stt["url"] and "test-key" not in tts


def test_the_session_route_describes_the_transport_without_issuing_anything(monkeypatch) -> None:
    """Session setup must not hand out a credential it cannot replace."""
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())

    def explode(_self, _settings, _token_type):
        raise AssertionError("the session route must not mint tokens")

    monkeypatch.setattr(type(main.REALTIME_VOICE_PROVIDER), "mint_token", explode)
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]

    body = client.post(f"/api/attempts/{attempt_id}/voice-realtime/session").json()

    assert body["sample_rate"] == 16_000
    assert body["sockets_url"] == f"/api/attempts/{attempt_id}/voice-realtime/sockets"
    assert body["turn_stream_url"] == f"/api/attempts/{attempt_id}/turn/stream"
    assert body["max_utterance_seconds"] >= 5
    # Nothing spendable, so nothing to go stale between utterances.
    assert "stt" not in body and "tts_url" not in body


def test_every_utterance_gets_a_freshly_minted_socket_pair(monkeypatch) -> None:
    """The regression: a single-use token is consumed by the socket that uses it.

    Reusing one pair for the whole case meant the second utterance opened a
    socket that closed instantly, and the candidate was told nothing was heard
    after speaking into it.
    """
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())
    issued = []

    def mint(_self, _settings, token_type):
        issued.append(token_type)
        return f"sutkn_{token_type}_{len(issued)}"

    monkeypatch.setattr(type(main.REALTIME_VOICE_PROVIDER), "mint_token", mint)
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]
    url = f"/api/attempts/{attempt_id}/voice-realtime/sockets"

    first = client.post(url).json()
    second = client.post(url).json()

    assert len(issued) == 4, "two utterances need two pairs, not one reused pair"
    assert first["stt"]["url"] != second["stt"]["url"]
    assert first["tts_url"] != second["tts_url"]
    assert "test-key" not in json.dumps([first, second])


def test_socket_urls_never_carry_the_workspace_key(monkeypatch) -> None:
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())
    monkeypatch.setattr(
        type(main.REALTIME_VOICE_PROVIDER),
        "mint_token",
        lambda _self, _settings, token_type: f"sutkn_{token_type}",
    )
    client = _client()
    attempt_id = client.post("/api/attempts", json={}).json()["id"]

    body = client.post(f"/api/attempts/{attempt_id}/voice-realtime/sockets").json()

    assert body["stt"]["url"].startswith("https://api.elevenlabs.io/v1/speech-to-text?token=")
    assert "auto_mode=true" in body["tts_url"]
    assert "test-key" not in json.dumps(body)


def test_the_two_tokens_are_minted_concurrently(monkeypatch) -> None:
    """Two sequential round trips would be paid before a word can be said."""
    _enable_realtime(monkeypatch)
    settings = RealtimeVoiceSettings.from_environment()
    barrier = threading.Barrier(2, timeout=5)

    def mint(_self, _settings, token_type):
        # Only passes if both calls are in flight at the same time.
        barrier.wait()
        return f"sutkn_{token_type}"

    provider = voice_realtime.ElevenLabsRealtimeProvider()
    monkeypatch.setattr(type(provider), "mint_token", mint)

    tokens = provider.mint_tokens(settings, "batch_scribe", "tts_websocket")

    assert tokens == {
        "batch_scribe": "sutkn_batch_scribe",
        "tts_websocket": "sutkn_tts_websocket",
    }


def test_a_half_issued_session_is_never_returned(monkeypatch) -> None:
    """One failed mint must fail the session, not hand over a usable half."""
    _enable_realtime(monkeypatch)
    settings = RealtimeVoiceSettings.from_environment()

    def mint(_self, _settings, token_type):
        if token_type == "tts_websocket":
            raise voice_realtime.VoiceProviderError("no tts permission")
        return "sutkn_ok"

    provider = voice_realtime.ElevenLabsRealtimeProvider()
    monkeypatch.setattr(type(provider), "mint_token", mint)

    with pytest.raises(voice_realtime.VoiceProviderError):
        provider.mint_tokens(settings, "batch_scribe", "tts_websocket")


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

    response = client.post(f"/api/attempts/{attempt_id}/voice-realtime/sockets")

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


# --- The post-hoc audit ---------------------------------------------------


def test_the_audit_runs_after_the_turn_and_never_blocks_it(monkeypatch, stub_interviewer) -> None:
    """Speech must not wait on a verdict about speech already delivered."""
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())
    seen: list[dict] = []
    done = threading.Event()

    class RecordingAuditor:
        def audit(self, *, candidate_turn, reply, facts):
            seen.append({"reply": reply, "facts": [f.id for f in facts]})
            done.set()
            return {"delivered": [f.id for f in facts], "complete": True, "undelivered": []}

    monkeypatch.setattr(main, "SPOKEN_AUDITOR", RecordingAuditor())
    client = _client()
    attempt_id = _started_attempt(client)

    response = client.post(
        f"/api/attempts/{attempt_id}/turn/stream",
        json={"content": "What is the segment mix?", "turn_id": "t-audit-1"},
    )

    # The turn completed on its own; the audit is a separate, later thread.
    assert [name for name, _ in _events(response.text)][-1] == "done"
    assert done.wait(timeout=5), "the audit thread should have run"
    assert seen[0]["reply"] == "The mix shifted north."
    assert seen[0]["facts"] == ["customers.segment-mix"]


def test_a_failing_audit_cannot_break_the_turn(monkeypatch, stub_interviewer) -> None:
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer())

    class ExplodingAuditor:
        def audit(self, **_kwargs):
            raise RuntimeError("provider down")

    monkeypatch.setattr(main, "SPOKEN_AUDITOR", ExplodingAuditor())
    client = _client()
    attempt_id = _started_attempt(client)

    response = client.post(
        f"/api/attempts/{attempt_id}/turn/stream",
        json={"content": "What is the segment mix?", "turn_id": "t-audit-2"},
    )

    assert response.status_code == 200
    spoken = "".join(p["text"] for n, p in _events(response.text) if n == "delta")
    assert spoken.strip() == "The mix shifted north."


def test_the_audit_is_skipped_when_no_fact_was_released(monkeypatch, stub_interviewer) -> None:
    """Nothing to under-deliver, so nothing to spend a call checking."""
    _enable_realtime(monkeypatch)
    monkeypatch.setattr(main, "SPOKEN_INTERVIEWER", StubSpokenInterviewer(fact_ids=[]))
    called = []

    class Auditor:
        def audit(self, **kwargs):
            called.append(kwargs)
            return {"delivered": [], "complete": True, "undelivered": []}

    monkeypatch.setattr(main, "SPOKEN_AUDITOR", Auditor())
    client = _client()
    attempt_id = _started_attempt(client)

    client.post(
        f"/api/attempts/{attempt_id}/turn/stream",
        json={"content": "Anything else?", "turn_id": "t-audit-3"},
    )

    assert called == []


# --- Recording invariants in the browser island ---------------------------
#
# There is no JavaScript test runner here, and these failure modes were all
# silent: the candidate saw "nothing was heard" and could not tell which stage
# dropped the turn. Source-level invariants are crude but real.


def _island_source() -> str:
    from pathlib import Path

    return (Path(__file__).resolve().parents[1] / "app/static/voice-realtime.js").read_text()


def test_recognition_is_batch_with_no_streaming_socket() -> None:
    """Streaming recognition put a handshake, a consumed credential, a readiness
    race and commit semantics on the critical path of every turn, and each of
    those lost a turn at least once."""
    source = _island_source()

    assert "function encodeWav(" in source
    assert "async function transcribe(blob, stt)" in source
    # None of the streaming machinery may come back.
    for gone in (
        "speech-to-text/realtime",
        "input_audio_chunk",
        "commit_strategy",
        "settleTranscript",
        "waitForTranscript",
        "session_started",
    ):
        assert gone not in source, f"streaming recognition leftover: {gone}"


def test_capture_begins_without_waiting_on_anything() -> None:
    source = _island_source()
    gate_opened = source.index("state.capturing = true;")
    recording_announced = source.index('setPhase("recording")')
    # The only await before capture is the microphone itself, which is already
    # open from session start in the normal case.
    prelude = source[source.index("async function startRecording()") : gate_opened]

    assert recording_announced > gate_opened
    assert "takeCredentials" not in prelude, (
        "a credential fetch before capture is what discarded the opening words"
    )
    assert "openSynthesisSocket" not in prelude


def test_the_microphone_is_held_open_across_turns() -> None:
    """Re-acquiring the device per turn restarted echo cancellation, noise
    suppression and auto gain, and their convergence ramp landed on the
    candidate's opening words."""
    source = _island_source()

    assert source.count("teardownMicrophone();") == 1, (
        "the microphone must be released only when voice mode ends"
    )
    assert "async function ensureMicrophone()" in source
    # Recording toggles a gate, never the device.
    assert "if (!state.capturing) return;" in source


def test_a_recording_is_capped_and_cannot_grow_without_bound() -> None:
    source = _island_source()

    assert "state.maxSamples" in source
    assert "max_utterance_seconds" in source
    # Reaching the cap yields the floor and keeps what was said.
    assert "stopRecording();" in source
