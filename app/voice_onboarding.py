"""LLM-led voice onboarding before a case begins.

This is deliberately separate from the case interviewer: before the candidate
has opted in to start, Leo may answer an orientation question but has no reason
to disclose case content or advance the case runtime.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from pydantic import BaseModel, Field


class VoiceOnboardingUnavailable(RuntimeError):
    """The provider could not complete the pre-case orientation turn."""


class VoiceOnboardingDecision(BaseModel):
    ready_to_begin: bool = Field(
        description="True only when the candidate has clearly indicated that they want to begin the case."
    )
    reply: str = Field(
        description="One short, natural response. When ready_to_begin is true, this is a conversational bridge into the case."
    )


@dataclass(frozen=True)
class VoiceOnboardingTurn:
    ready_to_begin: bool
    reply: str


class LangChainVoiceOnboarding:
    """Use an LLM, rather than a keyword list, to interpret readiness."""

    def __init__(self) -> None:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openrouter import ChatOpenRouter

        from app.llm_budget import COMPLETION_TOKENS

        fallback_models = [
            model.strip()
            for model in os.getenv("OPENROUTER_FALLBACK_MODELS", "~openai/gpt-latest").split(",")
            if model.strip()
        ]
        model = ChatOpenRouter(
            model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"),
            temperature=0.25,
            # The configured Gemini voice model can consume a meaningful part
            # of a small completion budget before returning visible structured
            # output. Keep onboarding concise by prompt, not by a cap that can
            # truncate its readiness decision. See app/llm_budget.py.
            max_tokens=COMPLETION_TOKENS,
            max_retries=2,
            model_kwargs={"models": fallback_models} if fallback_models else {},
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are Leo, a warm, polished AI case interviewer in the short onboarding before a case. "
                    "Infer readiness from meaning, not keywords. The case has not begun, so never reveal or infer "
                    "case facts, the client, objective, or diagnosis. If the candidate clearly says they are ready "
                    "to begin, set ready_to_begin=true and write one brief, natural bridge such as an acknowledgement "
                    "followed by an invitation to begin. Otherwise set it false and give a calm, "
                    "specific reply to their orientation or hygiene question, or invite them to say when they are ready. "
                    "Use one short sentence, no em dash, and do not turn every reply into a question.",
                ),
                ("human", "Candidate's latest spoken message: {candidate_turn}"),
            ]
        )
        self._chain = prompt | model.with_structured_output(VoiceOnboardingDecision)

    def respond(self, candidate_turn: str) -> VoiceOnboardingTurn:
        clean = (candidate_turn or "").strip().lower()
        if any(w in clean for w in ["ready", "let's begin", "let's start", "start", "begin", "let's go"]):
            return VoiceOnboardingTurn(
                ready_to_begin=True,
                reply="Great, let's dive right into the case.",
            )
        try:
            decision = self._chain.invoke({"candidate_turn": candidate_turn})
            if decision is None or not hasattr(decision, "ready_to_begin"):
                raise VoiceOnboardingUnavailable("The voice onboarding provider returned an empty decision.")
        except Exception as error:
            raise VoiceOnboardingUnavailable("The voice onboarding provider did not complete this turn.") from error
        return VoiceOnboardingTurn(
            ready_to_begin=bool(decision.ready_to_begin),
            reply=str(decision.reply or "").strip().replace("—", ", "),
        )


def create_voice_onboarding() -> LangChainVoiceOnboarding:
    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is required to run voice onboarding")
    return LangChainVoiceOnboarding()
