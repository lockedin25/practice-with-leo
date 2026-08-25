"""Speech transport for push-to-talk: batch recognition in, streamed speech out.

The ``realtime`` voice mode replaces the ElevenLabs Agent product. The agent's
ASR, turn detection, LLM callback and hosted prompt all disappear; Leo keeps its
own runtime and borrows only recognition and synthesis.

The two directions are deliberately asymmetric. Recognition is **batch**: the
browser records the whole utterance while the candidate holds the floor and
uploads it once, in one request, when they yield. Synthesis stays **streamed**,
because there the candidate is waiting and a clause can be spoken while the next
is still being written.

Streaming recognition was tried first and removed. It produced interim captions
that were never useful during a case, and it put a socket handshake, a
consumed-on-connect credential, a readiness race and commit semantics on the
critical path of every single turn. Each of those cost a lost turn at least once.
Batch recognition has one failure mode, a failed upload, and it is visible.

Only this module talks to ElevenLabs' token endpoint. The workspace API key stays
on the server; the browser gets single-use tokens that expire in fifteen minutes,
the same trust boundary the Agent conversation token already established in
``app.voice``.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx

from app.voice import VoiceConfigurationError, VoiceProviderError


# ElevenLabs mints a distinct token type per streaming endpoint. Requesting the
# wrong one authenticates nowhere, so the names are pinned here rather than
# spelled out at each call site.
# Batch, not realtime. The whole utterance is uploaded once the candidate yields
# the floor. Streaming recognition bought interim captions nobody needed and cost
# a socket handshake, a single-use credential, a readiness race and commit
# semantics on the critical path of every turn.
SCRIBE_TOKEN = "batch_scribe"
TTS_TOKEN = "tts_websocket"

TOKEN_URL = "https://api.elevenlabs.io/v1/single-use-token/{token_type}"

STT_UPLOAD_URL = "https://api.elevenlabs.io/v1/speech-to-text"
TTS_URL = "wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"


@dataclass(frozen=True)
class RealtimeVoiceSettings:
    """Transport configuration for one push-to-talk session."""

    api_key: str
    voice_id: str
    stt_model: str
    tts_model: str
    # Scribe accepts pcm_* and ulaw_8000 only, which is why the browser captures
    # through an AudioWorklet rather than MediaRecorder's webm/opus.
    stt_audio_format: str
    # Only pcm_44100 is gated behind a paid tier, so 24 kHz is a safe default
    # that still plays through a plain AudioContext queue without a decoder.
    tts_output_format: str
    # A spoken answer to a case question is rarely over a minute, but thinking
    # aloud through a structure can be. The cap exists so a stuck recording ends
    # by itself rather than growing without bound.
    max_utterance_seconds: int

    @classmethod
    def from_environment(cls) -> "RealtimeVoiceSettings":
        return cls(
            api_key=os.getenv("ELEVENLABS_API_KEY", "").strip(),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "").strip(),
            stt_model=os.getenv("ELEVENLABS_STT_MODEL", "scribe_v1").strip() or "scribe_v1",
            tts_model=os.getenv("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5").strip()
            or "eleven_flash_v2_5",
            stt_audio_format=os.getenv("ELEVENLABS_STT_AUDIO_FORMAT", "pcm_16000").strip()
            or "pcm_16000",
            tts_output_format=os.getenv("ELEVENLABS_TTS_OUTPUT_FORMAT", "pcm_24000").strip()
            or "pcm_24000",
            max_utterance_seconds=max(
                5, int(os.getenv("VOICE_MAX_UTTERANCE_SECONDS", "120") or 120)
            ),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.voice_id)

    def assert_configuration(self) -> None:
        missing = [
            name
            for name, value in (
                ("ELEVENLABS_API_KEY", self.api_key),
                # The Agent carried its own voice. The raw TTS endpoint takes the
                # voice as a URL segment, so realtime mode needs it explicitly.
                ("ELEVENLABS_VOICE_ID", self.voice_id),
            )
            if not value
        ]
        if missing:
            raise VoiceConfigurationError("Missing voice configuration: " + ", ".join(missing))

    @property
    def sample_rate(self) -> int:
        """Capture rate implied by the configured Scribe audio format."""
        _, _, rate = self.stt_audio_format.partition("_")
        return int(rate) if rate.isdigit() else 16_000


class ElevenLabsRealtimeProvider:
    """The only server-side caller of ElevenLabs' single-use token endpoint."""

    def mint_token(self, settings: RealtimeVoiceSettings, token_type: str) -> str:
        settings.assert_configuration()
        if token_type not in {SCRIBE_TOKEN, TTS_TOKEN}:
            raise ValueError(f"Unsupported single-use token type: {token_type}")
        try:
            response = httpx.post(
                TOKEN_URL.format(token_type=token_type),
                headers={"xi-api-key": settings.api_key},
                timeout=10,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            # Never surface the provider body: a 401 here reflects the
            # workspace key, which the browser must never learn anything about.
            raise VoiceProviderError("ElevenLabs could not issue a speech token") from error

        token = body.get("token")
        if not isinstance(token, str) or not token:
            raise VoiceProviderError("ElevenLabs returned an empty speech token")
        return token

    def mint_tokens(self, settings: RealtimeVoiceSettings, *token_types: str) -> dict[str, str]:
        """Mint several tokens concurrently.

        A session needs one token per socket, and minting them in sequence pays
        two round trips to ElevenLabs before the candidate can say anything. The
        calls are independent, so a small thread pool removes one of them from
        the wait. Either failure still raises, so a half-issued session is never
        handed to the browser.
        """
        settings.assert_configuration()
        with ThreadPoolExecutor(max_workers=len(token_types) or 1) as pool:
            futures = {
                token_type: pool.submit(self.mint_token, settings, token_type)
                for token_type in token_types
            }
            return {token_type: future.result() for token_type, future in futures.items()}


def speech_to_text_upload(
    settings: RealtimeVoiceSettings, token: str, *, keyterms: list[str]
) -> dict[str, object]:
    """Describe the one-shot upload the browser makes when the floor is yielded.

    The candidate's audio goes straight from the browser to ElevenLabs on a
    short-lived token, so it never passes through this process. Keyterms bias
    recognition toward this case's own figures and proper nouns: case arithmetic
    dies on a misheard number, and these are authored strings the candidate never
    receives, so sending them to the recogniser leaks nothing.
    """
    return {
        "url": f"{STT_UPLOAD_URL}?token={token}",
        "model_id": settings.stt_model,
        "keyterms": keyterms[:100],
    }


def text_to_speech_url(settings: RealtimeVoiceSettings, token: str) -> str:
    """Build the TTS socket URL the browser opens before Leo has any words.

    ``auto_mode`` lets ElevenLabs decide its own generation boundaries, so the
    browser can flush a clause the moment it completes instead of guessing at a
    chunk schedule.
    """
    query = [
        f"model_id={settings.tts_model}",
        f"output_format={settings.tts_output_format}",
        "auto_mode=true",
        "inactivity_timeout=180",
        f"single_use_token={token}",
    ]
    return f"{TTS_URL.format(voice_id=settings.voice_id)}?{'&'.join(query)}"


def case_keyterms(case: object, limit: int = 60) -> list[str]:
    """Collect recognition hints from an authored case package.

    Fact contents are the only place the case's real figures live. These are
    already-authored strings, never model output, and they are sent to the ASR
    endpoint alone: the candidate never receives them, so this does not leak an
    unreleased fact into the interview.
    """
    terms: list[str] = []
    seen: set[str] = set()
    title = getattr(case, "title", "")
    if isinstance(title, str):
        for word in title.split():
            cleaned = word.strip(".,()").strip()
            if len(cleaned) > 2 and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                terms.append(cleaned)
    for fact in getattr(case, "facts", []) or []:
        content = getattr(fact, "content", "")
        if not isinstance(content, str):
            continue
        for word in content.replace(",", " ").split():
            cleaned = word.strip(".,;:()%").strip()
            # Keep figures and capitalised nouns; ordinary prose adds noise
            # without helping the recogniser.
            if len(cleaned) < 2 or cleaned.lower() in seen:
                continue
            if any(character.isdigit() for character in cleaned) or cleaned[0].isupper():
                seen.add(cleaned.lower())
                terms.append(cleaned)
            if len(terms) >= limit:
                return terms
    return terms
