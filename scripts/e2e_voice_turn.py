"""Drive one complete spoken turn without a microphone, and time every stage.

Speech synthesis stands in for the candidate: a question is rendered to PCM,
streamed to Scribe exactly as the AudioWorklet would, committed the way the
spacebar commits, then the transcript goes through the real fused turn and Leo's
reply is synthesised back. That exercises every hop the browser uses except the
microphone itself.

The headline number is time from commit to first audio byte, because that is the
silence a candidate actually experiences after they stop speaking.

    uv run python scripts/e2e_voice_turn.py
    uv run python scripts/e2e_voice_turn.py --say "Can you give me the cost breakdown"
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import httpx  # noqa: E402
import websockets  # noqa: E402

import app.main as main  # noqa: E402
from app.case_runtime import InterviewSession  # noqa: E402
from app.spoken_interviewer import SpokenInterviewer, sentence_chunks  # noqa: E402
from app.voice_realtime import (  # noqa: E402
    SCRIBE_TOKEN,
    TTS_TOKEN,
    ElevenLabsRealtimeProvider,
    RealtimeVoiceSettings,
    case_keyterms,
    speech_to_text_url,
    text_to_speech_url,
)

DEFAULT_SAY = "What has happened to the cost per route recently?"
# Scribe's capture rate. The candidate voice is rendered at this rate so no
# resampling sits between the two services and confuses the comparison.
CAPTURE_RATE = 16_000
# 50ms of audio per message, matching the AudioWorklet's block size.
BLOCK_SAMPLES = CAPTURE_RATE // 20


def render_candidate_voice(settings: RealtimeVoiceSettings, text: str) -> bytes:
    """Speak the candidate's question to raw PCM, as a microphone would deliver it."""
    response = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{settings.voice_id}",
        headers={"xi-api-key": settings.api_key},
        params={"output_format": f"pcm_{CAPTURE_RATE}"},
        json={"text": text, "model_id": settings.tts_model},
        timeout=60,
    )
    response.raise_for_status()
    return response.content


async def transcribe(settings: RealtimeVoiceSettings, token: str, pcm: bytes, keyterms: list[str]):
    """Stream the audio in real time, then commit the way the spacebar does."""
    url = speech_to_text_url(settings, token, keyterms=keyterms)
    committed: list[str] = []
    partials = 0
    async with websockets.connect(url, max_size=None) as socket:
        blocks = [
            pcm[i : i + BLOCK_SAMPLES * 2] for i in range(0, len(pcm), BLOCK_SAMPLES * 2)
        ]
        for block in blocks:
            await socket.send(
                json.dumps(
                    {
                        "message_type": "input_audio_chunk",
                        "audio_base_64": base64.b64encode(block).decode(),
                        "sample_rate": CAPTURE_RATE,
                        "commit": False,
                    }
                )
            )
            # Pace the send to real time: buffering the whole utterance instantly
            # would hide the fact that transcription overlaps speaking.
            await asyncio.sleep(0.05)

        commit_at = time.time()
        await socket.send(
            json.dumps(
                {
                    "message_type": "input_audio_chunk",
                    "audio_base_64": "",
                    "sample_rate": CAPTURE_RATE,
                    "commit": True,
                }
            )
        )
        while True:
            try:
                raw = await asyncio.wait_for(socket.recv(), timeout=8)
            except (asyncio.TimeoutError, websockets.ConnectionClosed):
                break
            message = json.loads(raw)
            kind = message.get("message_type") or message.get("type")
            if kind == "partial_transcript":
                partials += 1
            elif kind in {"committed_transcript", "final_transcript"}:
                text = message.get("text") or message.get("transcript") or ""
                if text:
                    committed.append(text)
                    break
            elif isinstance(kind, str) and kind.endswith("_error"):
                raise RuntimeError(f"Scribe error: {message}")
    return " ".join(committed).strip(), time.time() - commit_at, partials


async def open_synthesis(settings: RealtimeVoiceSettings, token: str):
    """Open and initialise the synthesis socket before there is anything to say.

    The browser does this at space-down so the handshake overlaps the candidate
    still talking. Timing a socket opened at flush time would charge that
    handshake to the silence after the spacebar, where it does not belong.
    """
    socket = await websockets.connect(text_to_speech_url(settings, token), max_size=None)
    await socket.send(
        json.dumps(
            {"text": " ", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
        )
    )
    return socket


async def synthesise(socket, sentences: list[str]):
    """Push each finished clause into the warm socket and time the first byte."""
    sent_at = time.time()
    for sentence in sentences:
        await socket.send(json.dumps({"text": f"{sentence.strip()} "}))
    await socket.send(json.dumps({"text": " ", "flush": True}))

    first_audio = None
    total_bytes = 0
    while True:
        try:
            raw = await asyncio.wait_for(socket.recv(), timeout=20)
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            break
        message = json.loads(raw)
        if message.get("audio"):
            if first_audio is None:
                first_audio = time.time() - sent_at
            total_bytes += len(base64.b64decode(message["audio"]))
        if message.get("isFinal"):
            break
    await socket.close()
    return first_audio, total_bytes


async def run(say: str) -> int:
    settings = RealtimeVoiceSettings.from_environment()
    settings.assert_configuration()
    provider = ElevenLabsRealtimeProvider()

    case = main.CATALOGUE.default_case
    session = InterviewSession(id="e2e-probe", case=case, mode="realistic")
    session.case_started = True
    session.add_interviewer_turn("Welcome. Tell me how you would like to start.")

    print(f'\nCandidate says: "{say}"')
    print(f"Case: {case.title}   model: {SpokenInterviewer()._model_name}\n")

    tokens = provider.mint_tokens(settings, SCRIBE_TOKEN, TTS_TOKEN)
    # Warmed before a word is spoken, exactly as the browser does at space-down.
    tts_socket = await open_synthesis(settings, tokens[TTS_TOKEN])
    pcm = render_candidate_voice(settings, say)
    seconds = len(pcm) / 2 / CAPTURE_RATE
    print(f"rendered {seconds:.1f}s of candidate audio ({len(pcm):,} bytes PCM)")

    transcript, commit_to_transcript, partials = await transcribe(
        settings, tokens[SCRIBE_TOKEN], pcm, case_keyterms(case)
    )
    print(f'heard: "{transcript}"   ({partials} interim updates while speaking)')
    if not transcript:
        print("\nFAILED: nothing was transcribed")
        return 1

    interviewer = SpokenInterviewer()
    turn_start = time.time()
    control_at = first_sentence_at = None
    pending = ""
    spoken = ""
    first_sentences: list[str] = []
    facts: list[str] = []
    for event, payload in interviewer.respond_stream(session, transcript):
        now = time.time() - turn_start
        if event == "control":
            control_at = now
            facts = [fact.id for fact in payload]
        elif event == "delta":
            pending += payload
            spoken += payload
            chunks, pending = sentence_chunks(pending)
            if chunks and first_sentence_at is None:
                first_sentence_at = now
                first_sentences = chunks
    if pending.strip():
        first_sentences = first_sentences or [pending]
    llm_total = time.time() - turn_start

    first_audio, audio_bytes = await synthesise(tts_socket, first_sentences or [spoken])
    if first_audio is None:
        print("\nFAILED: synthesis returned no audio")
        return 1

    print(f'Leo replies: "{spoken.strip()}"')
    print(f"facts released: {facts}\n")

    commit_to_audio = commit_to_transcript + (first_sentence_at or llm_total) + first_audio
    print("Stage timings, from the moment the spacebar committed the turn")
    print("-" * 62)
    print(f"  commit -> final transcript      {commit_to_transcript:>6.2f}s")
    print(f"  control block (facts released)  {control_at or 0:>6.2f}s")
    print(f"  first speakable sentence        {first_sentence_at or llm_total:>6.2f}s")
    print(f"  first audio byte after flush    {first_audio:>6.2f}s")
    print("-" * 62)
    print(f"  SILENCE THE CANDIDATE HEARS     {commit_to_audio:>6.2f}s")
    print(f"  full reply generated            {llm_total:>6.2f}s")
    print(f"  audio returned                  {audio_bytes:,} bytes\n")
    print("Was 6-14s before this work: 3-5 sequential calls, then TTS on the whole reply.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--say", default=DEFAULT_SAY)
    raise SystemExit(asyncio.run(run(parser.parse_args().say)))
