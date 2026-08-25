"""Realtime speech transport: browser-held Scribe and TTS sockets.

The ``realtime`` voice mode replaces the ElevenLabs Agent product with the two
raw streaming endpoints, driven by a push-to-talk control in the browser. The
agent's ASR, turn detection, LLM callback and hosted prompt all disappear; Leo
keeps its own runtime and only borrows speech recognition and speech synthesis.

Only this module talks to ElevenLabs' token endpoint. The workspace API key
stays on the server: the browser receives single-use tokens that expire in
fifteen minutes and are consumed on use, which is the same trust boundary the
Agent conversation token already established in ``app.voice``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from app.voice import VoiceConfigurationError, VoiceProviderError


# ElevenLabs mints a distinct token type per streaming endpoint. Requesting the
# wrong one authenticates nowhere, so the names are pinned here rather than
# spelled out at each call site.
SCRIBE_TOKEN = "realtime_scribe"
TTS_TOKEN = "tts_websocket"

TOKEN_URL = "https://api.elevenlabs.io/v1/single-use-token/{token_type}"

STT_URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
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

    @classmethod
    def from_environment(cls) -> "RealtimeVoiceSettings":
        return cls(
            api_key=os.getenv("ELEVENLABS_API_KEY", "").strip(),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "").strip(),
            stt_model=os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2_realtime").strip()
            or "scribe_v2_realtime",
            tts_model=os.getenv("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5").strip()
            or "eleven_flash_v2_5",
            stt_audio_format=os.getenv("ELEVENLABS_STT_AUDIO_FORMAT", "pcm_16000").strip()
            or "pcm_16000",
            tts_output_format=os.getenv("ELEVENLABS_TTS_OUTPUT_FORMAT", "pcm_24000").strip()
            or "pcm_24000",
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


def speech_to_text_url(settings: RealtimeVoiceSettings, token: str, *, keyterms: list[str]) -> str:
    """Build the Scribe socket URL for one candidate utterance.

    ``commit_strategy=manual`` is what makes the spacebar authoritative: Scribe
    streams interim transcripts while the candidate speaks but only finalises a
    turn when the browser marks a chunk committed. Provider-side silence
    detection would end turns on its own and take that control away.
    """
    query = [
        f"model_id={settings.stt_model}",
        f"audio_format={settings.stt_audio_format}",
        "commit_strategy=manual",
        f"token={token}",
    ]
    # Case arithmetic dies on a misheard figure, so bias recognition toward the
    # numbers and proper nouns this specific case is going to use.
    for term in keyterms[:100]:
        query.append(f"keyterms={httpx.QueryParams({'k': term})['k']}")
    return f"{STT_URL}?{'&'.join(query)}"


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
