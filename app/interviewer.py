"""Generic LangChain orchestration for an authored case world.

The director extracts intent and proposes actions through structured LLM output.
The voice model receives only runtime-approved factual context. No keyword router
or case-specific decision tree exists in application code.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from app.case_runtime import Fact, InterviewSession


logger = logging.getLogger(__name__)


def _finalize_reply(reply: str) -> str:
    """Preserve AI-authored content while enforcing the product's punctuation rule."""
    return reply.strip().replace("—", ", ")


class DirectorDecision(BaseModel):
    candidate_intent: str = Field(description="The candidate's intent in plain language.")
    move: str = Field(description="One of answer, probe, challenge, redirect, invite, or close.")
    next_phase: str = Field(description="The authored phase to hold or advance to.")
    fact_ids: list[str] = Field(default_factory=list, description="Eligible fact IDs to disclose this turn.")
    interviewer_brief: str = Field(description="A short non-solution instruction for the voice interviewer.")


@dataclass(frozen=True)
class InterviewTurn:
    reply: str
    facts: list[Fact]


class InterviewerUnavailable(RuntimeError):
    """Raised when the configured LLM provider cannot complete a turn."""


class Interviewer(Protocol):
    def respond(self, session: InterviewSession, candidate_turn: str) -> InterviewTurn: ...


class LangChainCaseInterviewer:
    def __init__(self) -> None:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_openrouter import ChatOpenRouter

        fallback_models = [
            model.strip()
            for model in os.getenv("OPENROUTER_FALLBACK_MODELS", "~openai/gpt-latest").split(",")
            if model.strip()
        ]
        model_settings = {
            "model": os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"),
            "temperature": 0.2,
            "max_retries": 2,
            "model_kwargs": {"models": fallback_models} if fallback_models else {},
        }
        director_model = ChatOpenRouter(max_tokens=450, **model_settings)
        voice_model = ChatOpenRouter(max_tokens=180, **model_settings)

        director_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are the private director of a consulting-case simulation. "
                    "Infer the candidate's intent from the transcript, choose only the relevant "
                    "fact IDs from the supplied eligible facts, and choose the next authored phase. "
                    "Do not state a diagnosis, invent a fact, or select an ID not present in the facts. "
                    "Default to an answer, challenge, or concise redirection rather than a question. "
                    "Use probe only when one focused question would genuinely advance a promising line of reasoning. "
                    "If the candidate has already been unable to advance after a prior probe, select the narrowest "
                    "eligible fact that helps them and use answer or redirect. Do not repeat probes for the same impasse. "
                    "Write a brief that guides the voice interviewer without revealing unreleased evidence.",
                ),
                MessagesPlaceholder("history"),
                (
                    "human",
                    "Case objective: {objective}\n"
                    "Current phase: {current_phase}\n"
                    "Current phase goal: {phase_goal}\n"
                    "Candidate turn number: {candidate_turn_number}\n"
                    "Turn pacing policy: {turn_pacing_policy}\n"
                    "Authored phases, in order: {phase_ids}\n"
                    "Eligible facts: {eligible_facts}\n"
                    "Candidate's latest turn: {candidate_turn}",
                ),
            ]
        )
        self._director = director_prompt | director_model.with_structured_output(DirectorDecision)

        voice_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are Leo, a calm, incisive consulting case interviewer. You are direct, precise, "
                    "and respectful, never theatrical or overly encouraging. "
                    "Use only the approved facts in this prompt. Never reveal a solution, hidden context, "
                    "or a future fact. Write this exact turn afresh: do not use templates, canned phrasing, "
                    "or fixed dialogue. Treat approved facts as source material and paraphrase them naturally. "
                    "Use one or two short sentences, normally no more than 65 words. Never use an em dash. "
                    "For an early precision turn, answer only the exact question asked. Do not volunteer "
                    "adjacent facts, broad context, or a diagnosis. "
                    "Do not end every turn with a question. A concise declarative answer is the normal response when "
                    "a fact is approved. Ask at most one focused question only when the director move is probe and it "
                    "would help the candidate progress. When the candidate remains stuck after a prior probe, give the "
                    "approved answer directly instead of asking another question. If no fact is approved, follow the "
                    "director brief without inventing information.",
                ),
                MessagesPlaceholder("history"),
                (
                    "human",
                    "Current phase: {current_phase}\n"
                    "Candidate turn number: {candidate_turn_number}\n"
                    "Turn pacing policy: {turn_pacing_policy}\n"
                    "Director move: {move}\n"
                    "Director brief: {interviewer_brief}\n"
                    "Approved factual context for this reply: {approved_facts}\n"
                    "Candidate's latest turn: {candidate_turn}",
                ),
            ]
        )
        self._voice = voice_prompt | voice_model | StrOutputParser()

    def respond(self, session: InterviewSession, candidate_turn: str) -> InterviewTurn:
        from langchain_core.messages import AIMessage, HumanMessage

        session.record_candidate_turn(candidate_turn)
        history = [
            HumanMessage(content=message["content"])
            if message["role"] == "candidate"
            else AIMessage(content=message["content"])
            for message in session.messages[-7:-1]
        ]
        current_phase = session.case.phase(session.stage)
        is_early_precision_turn = session.candidate_turns <= 2
        turn_pacing_policy = (
            "EARLY PRECISION: This is one of the first two candidate turns. Select at most one atomic "
            "fact that directly answers the candidate's exact question. Hold the current phase. Do not "
            "volunteer adjacent information, context, or an inferred diagnosis."
            if is_early_precision_turn
            else "NORMAL PACING: Answer the candidate's relevant question with the narrowest useful fact. "
            "If the candidate remains stuck after a prior probe or cannot advance, provide one additional "
            "narrow fact that unblocks them rather than repeating a question."
        )
        try:
            decision = self._director.invoke(
                {
                    "history": history,
                    "objective": session.case.objective,
                    "current_phase": current_phase.id,
                    "phase_goal": current_phase.interviewer_goal,
                    "candidate_turn_number": session.candidate_turns,
                    "turn_pacing_policy": turn_pacing_policy,
                    "phase_ids": json.dumps([phase.id for phase in session.case.phases]),
                    "eligible_facts": json.dumps(
                        session.case.eligible_facts_for_director(session.stage, session.disclosed_ids)
                    ),
                    "candidate_turn": candidate_turn,
                }
            )
            facts = session.case.validate_fact_selection(
                decision.fact_ids,
                session.stage,
                session.disclosed_ids,
                max_facts=1 if is_early_precision_turn else 2,
            )
            next_phase = (
                session.stage
                if is_early_precision_turn
                else session.case.validate_phase_transition(session.stage, decision.next_phase)
            )
            approved_facts = "\n".join(f"- {fact.content}" for fact in facts) or "None"
            reply = self._voice.invoke(
                {
                    "history": history,
                    "current_phase": next_phase,
                    "candidate_turn_number": session.candidate_turns,
                    "turn_pacing_policy": turn_pacing_policy,
                    "move": decision.move,
                    "interviewer_brief": decision.interviewer_brief,
                    "approved_facts": approved_facts,
                    "candidate_turn": candidate_turn,
                }
            )
            reply = _finalize_reply(reply)
        except Exception as error:
            logger.exception("OpenRouter interviewer turn failed")
            # Remove the unserved candidate turn so a retry preserves a coherent transcript.
            session.messages.pop()
            session.candidate_turns -= 1
            raise InterviewerUnavailable("The interviewer provider did not complete this turn.") from error

        session.apply_director_decision(next_phase, facts)
        session.add_interviewer_turn(reply)
        return InterviewTurn(reply=reply, facts=facts)


def create_interviewer() -> Interviewer:
    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is required to run the LLM interviewer")
    return LangChainCaseInterviewer()
