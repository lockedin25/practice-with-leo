"""ElevenLabs transport primitives.

The provider is only a voice transport. ``custom`` mode keeps the existing
OpenAI-compatible adapter, while ``native`` mode uses an ElevenLabs-hosted LLM
with a narrow, authenticated fact-release tool back to this application.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx


class VoiceConfigurationError(RuntimeError):
    """Voice was enabled without the server credentials required to run it."""


class VoiceProviderError(RuntimeError):
    """ElevenLabs did not issue a usable private conversation token."""


@dataclass(frozen=True)
class VoiceSettings:
    enabled: bool
    mode: str
    api_key: str
    agent_id: str
    environment: str
    custom_llm_secret: str
    case_tool_secret: str
    webhook_secret: str

    @classmethod
    def from_environment(cls) -> "VoiceSettings":
        return cls(
            enabled=os.getenv("VOICE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
            mode=os.getenv("ELEVENLABS_VOICE_MODE", "custom").strip().lower() or "custom",
            api_key=os.getenv("ELEVENLABS_API_KEY", "").strip(),
            agent_id=os.getenv("ELEVENLABS_AGENT_ID", "").strip(),
            environment=os.getenv("ELEVENLABS_ENVIRONMENT", "development").strip() or "development",
            custom_llm_secret=os.getenv("ELEVENLABS_CUSTOM_LLM_SECRET", "").strip(),
            case_tool_secret=os.getenv("ELEVENLABS_CASE_TOOL_SECRET", "").strip(),
            webhook_secret=os.getenv("ELEVENLABS_WEBHOOK_SECRET", "").strip(),
        )

    @property
    def uses_native_agent(self) -> bool:
        return self.mode == "native"

    @property
    def uses_realtime_speech(self) -> bool:
        """Push-to-talk over the raw Scribe and TTS endpoints, with no Agent.

        Nothing calls back into this server in realtime mode, so it needs no
        agent, no Custom LLM secret, and no public HTTPS tunnel.
        """
        return self.mode == "realtime"

    @property
    def uses_agent(self) -> bool:
        return self.mode in {"custom", "native"}

    def assert_mode_configuration(self) -> None:
        if self.mode not in {"custom", "native", "realtime"}:
            raise VoiceConfigurationError(
                "ELEVENLABS_VOICE_MODE must be 'custom', 'native', or 'realtime'"
            )
        if self.uses_native_agent and not self.case_tool_secret:
            raise VoiceConfigurationError("Missing voice configuration: ELEVENLABS_CASE_TOOL_SECRET")

    def assert_token_configuration(self) -> None:
        self.assert_mode_configuration()
        required = [("ELEVENLABS_API_KEY", self.api_key)]
        if self.uses_agent:
            required.append(("ELEVENLABS_AGENT_ID", self.agent_id))
        missing = [name for name, value in required if not value]
        if missing:
            raise VoiceConfigurationError("Missing voice configuration: " + ", ".join(missing))


@dataclass(frozen=True)
class ProviderConversationToken:
    token: str
    conversation_id: str


class ElevenLabsProvider:
    """The only server-side caller of ElevenLabs' conversation-token API."""

    token_url = "https://api.elevenlabs.io/v1/convai/conversation/token"

    def issue_token(self, settings: VoiceSettings, *, participant_name: str) -> ProviderConversationToken:
        settings.assert_token_configuration()
        try:
            response = httpx.get(
                self.token_url,
                params={
                    "agent_id": settings.agent_id,
                    "environment": settings.environment,
                    "participant_name": participant_name,
                },
                headers={"xi-api-key": settings.api_key},
                timeout=15,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise VoiceProviderError("ElevenLabs could not issue a voice session") from error

        token = body.get("token")
        conversation_id = body.get("conversation_id")
        if not isinstance(token, str) or not token or not isinstance(conversation_id, str) or not conversation_id:
            raise VoiceProviderError("ElevenLabs returned an incomplete voice session")
        return ProviderConversationToken(token=token, conversation_id=conversation_id)


def latest_candidate_utterance(messages: list[object]) -> tuple[str, int]:
    """Extract the final provider user message without treating partial ASR as a turn."""
    candidates: list[str] = []
    for message in messages:
        if not isinstance(message, dict) or str(message.get("role", "")).lower() not in {"user", "candidate"}:
            continue
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            candidates.append(content.strip())
    if not candidates:
        raise ValueError("The voice request did not include a final candidate utterance")
    return candidates[-1], len(candidates)


_SESSION_BINDING = re.compile(r"VOICE_SESSION_ID=([0-9a-fA-F-]{36})")
_AUDIO_CUE = re.compile(
    r"\[(?:warmly|confidently|patiently|empathetically|seriously|enthusiastically|excitedly|chuckles|laughing|sighs)\]\s*",
    flags=re.IGNORECASE,
)


def clean_spoken_text(text: str) -> str:
    """Remove legacy audio-tag tokens before sending text to provider TTS.

    Custom LLM streaming treats these suggested UI tags as literal words, so
    they must never cross the speech boundary. Tone is controlled by Leo's
    natural-language delivery prompt instead.
    """
    return _AUDIO_CUE.sub("", text).strip()


def voice_session_id_from_request(messages: list[object], user_id: str | None) -> str | None:
    """Read Leo's opaque binding from a provider-generated system message.

    ElevenLabs does not currently mirror the WebRTC token's participant name in
    its Custom LLM ``user_id`` field. The agent system prompt instead contains
    a dynamic variable which the browser fills with this random session ID.
    This is not a case fact and is checked against the local session table
    before it can mutate an attempt.
    """
    if user_id:
        return user_id
    for message in messages:
        if not isinstance(message, dict) or str(message.get("role", "")).lower() != "system":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        if match := _SESSION_BINDING.search(content):
            return match.group(1)
    return None
