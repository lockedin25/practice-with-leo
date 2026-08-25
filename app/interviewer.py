"""Generic LangChain orchestration for an authored case world.

The director extracts intent and proposes actions through structured LLM output.
The voice model receives only runtime-approved factual context. No keyword router
or case-specific decision tree exists in application code.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.case_runtime import Fact, InterviewSession
from app.llm_budget import (
    COMPLETION_TOKENS,
    TRUNCATED_RETRY_TOKENS,
    message_text,
    was_truncated,
)


logger = logging.getLogger(__name__)


def _finalize_reply(reply: str) -> str:
    """Preserve AI-authored content while enforcing the product's punctuation rule."""
    return reply.strip().replace("—", ", ")


_AUDIO_TAG = re.compile(
    r"\[(?:warmly|confidently|patiently|empathetically|seriously|enthusiastically|excitedly|chuckles|laughing|sighs)\]\s*",
    flags=re.IGNORECASE,
)


def _without_audio_tags(reply: str) -> str:
    """Keep provider-only delivery cues out of Leo's canonical text transcript."""
    return _AUDIO_TAG.sub("", reply).strip()


class DirectorDecision(BaseModel):
    candidate_intent: str = Field(description="The candidate's intent in plain language.")
    move: str = Field(description="One of answer, probe, challenge, redirect, invite, or close.")
    next_phase: str = Field(description="The authored phase to hold or advance to.")
    fact_ids: list[str] = Field(default_factory=list, description="Eligible fact IDs to disclose this turn.")
    interviewer_brief: str = Field(description="A short non-solution instruction for the voice interviewer.")


class FactDeliveryAudit(BaseModel):
    """Private LLM verification that a displayed reply earned each side-panel fact."""

    reply_complete: bool = Field(
        description="True only if the reply is a finished, coherent answer to the candidate's latest turn."
    )
    communicated_fact_ids: list[str] = Field(
        default_factory=list,
        description="Only IDs whose material details are actually communicated in the reply."
    )


@dataclass(frozen=True)
class InterviewTurn:
    reply: str
    facts: list[Fact]
    spoken_reply: str | None = None


class InterviewerUnavailable(RuntimeError):
    """Raised when the configured LLM provider cannot complete a turn."""


class Interviewer(Protocol):
    def respond(self, session: InterviewSession, candidate_turn: str, *, spoken: bool = False) -> InterviewTurn: ...


class LangChainCaseInterviewer:
    def __init__(self) -> None:
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
        voice_model_settings = {
            **model_settings,
            "model": os.getenv("VOICE_OPENROUTER_MODEL", model_settings["model"]),
            # A voice retry makes silence feel broken. One retry handles a
            # transient provider failure without turning an answer into a long
            # wait; typed chat retains its more resilient setting above.
            "max_retries": 1,
        }
        # Keep the visible interviewer turn concise through prompting, not by
        # starving reasoning-capable providers of their total completion budget.
        # One generous cap covers every call, free text and structured output
        # alike; app/llm_budget.py records the measured reasoning burn that made
        # a smaller cap truncate a reply into a fragment.
        director_model = ChatOpenRouter(max_tokens=COMPLETION_TOKENS, **model_settings)
        voice_model = ChatOpenRouter(max_tokens=COMPLETION_TOKENS, **model_settings)
        voice_director_model = ChatOpenRouter(max_tokens=COMPLETION_TOKENS, **voice_model_settings)
        voice_delivery_model = ChatOpenRouter(max_tokens=COMPLETION_TOKENS, **voice_model_settings)
        audit_model = ChatOpenRouter(max_tokens=COMPLETION_TOKENS, **voice_model_settings)
        repair_model = ChatOpenRouter(max_tokens=COMPLETION_TOKENS, **voice_model_settings)

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
        self._voice_director = director_prompt | voice_director_model.with_structured_output(DirectorDecision)

        voice_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are Leo, a calm, incisive consulting case interviewer. You are direct, precise, "
                    "and respectful, never theatrical or overly encouraging. "
                    "Use only the approved facts in this prompt. Never reveal a solution, hidden context, "
                    "or a future fact. Write this exact turn afresh: do not use templates, canned phrasing, "
                    "or fixed dialogue. Treat approved facts as source material and paraphrase them naturally. "
                    "When approved factual context is supplied, communicate every material detail needed to answer the "
                    "candidate's exact question. Never begin an answer that you do not finish. "
                    "Use one or two short sentences, normally no more than 65 words. Never use an em dash. "
                    "For an early precision turn, answer only the exact question asked. Do not volunteer "
                    "adjacent facts, broad context, or a diagnosis. "
                    "Do not end every turn with a question. A concise declarative answer is the normal response when "
                    "a fact is approved. Ask at most one focused question only when the director move is probe and it "
                    "would help the candidate progress. When the candidate remains stuck after a prior probe, give the "
                    "approved answer directly instead of asking another question. If no fact is approved, follow the "
                    "director brief without inventing information. Occasionally, when the candidate has made a concrete "
                    "useful point or expressed uncertainty, open with a very short acknowledgement of that exact point. "
                    "Use this sparingly, roughly one turn in five when it is genuinely earned, never mechanically.",
                ),
                MessagesPlaceholder("history"),
                (
                    "human",
                    "Current phase: {current_phase}\n"
                    "Candidate turn number: {candidate_turn_number}\n"
                    "Turn pacing policy: {turn_pacing_policy}\n"
                    "Director move: {move}\n"
                    "Director brief: {interviewer_brief}\n"
                    "Delivery instruction: {delivery_instruction}\n"
                    "Approved factual context for this reply: {approved_facts}\n"
                    "Candidate's latest turn: {candidate_turn}",
                ),
            ]
        )
        # These writer chains keep the provider message instead of parsing
        # straight to text, so a budget-exhausted completion is recognisable
        # before it reaches the audit. Each has a larger-budget twin used
        # only to regenerate a truncated reply.
        self._voice = voice_prompt | voice_model
        self._voice_delivery = voice_prompt | voice_delivery_model
        self._voice_retry = voice_prompt | voice_model.bind(max_tokens=TRUNCATED_RETRY_TOKENS)
        self._voice_delivery_retry = voice_prompt | voice_delivery_model.bind(
            max_tokens=TRUNCATED_RETRY_TOKENS
        )

        audit_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You privately verify a case-interviewer reply before it is shown. Do not infer or reward facts "
                    "that are merely plausible. Mark reply_complete true only when the reply is a complete, coherent "
                    "answer, not a fragment. An empty string, a dangling opening, or an unfinished clause such as "
                    "'That is a' is incomplete. Return a fact ID only if the reply communicates that fact's material details "
                    "to the candidate, even when naturally paraphrased. IDs must come only from the supplied facts.",
                ),
                (
                    "human",
                    "Candidate turn: {candidate_turn}\nReply: {reply}\nApproved facts: {facts}",
                ),
            ]
        )
        repair_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are Leo. Rewrite the draft as one concise, complete consulting-interviewer answer. "
                    "Use only the approved facts. Answer the candidate's exact question, include every material "
                    "detail in the approved facts, and do not leave a clause unfinished. No em dash, no stage directions.",
                ),
                (
                    "human",
                    "Candidate turn: {candidate_turn}\nDraft: {reply}\nApproved facts: {facts}",
                ),
            ]
        )
        self._fact_audit = audit_prompt | audit_model.with_structured_output(FactDeliveryAudit)
        self._reply_repair = repair_prompt | repair_model
        self._reply_repair_retry = repair_prompt | repair_model.bind(
            max_tokens=TRUNCATED_RETRY_TOKENS
        )

    def _complete_text(self, chain: Any, retry: Any, inputs: dict[str, Any]) -> str:
        """Invoke a text chain, regenerating once if the token budget cut the reply.

        A provider that spends its whole completion budget on private reasoning
        returns a fragment the fact audit would reject anyway. Recognising that
        here costs one regeneration rather than the candidate's whole turn, and
        logs the cause instead of leaving it to look like a provider outage.
        """
        message = chain.invoke(inputs)
        if was_truncated(message):
            logger.warning(
                "Interviewer completion filled its %s token budget; regenerating with %s",
                COMPLETION_TOKENS,
                TRUNCATED_RETRY_TOKENS,
            )
            message = retry.invoke(inputs)
        return message_text(message)

    def respond(self, session: InterviewSession, candidate_turn: str, *, spoken: bool = False) -> InterviewTurn:
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
            decision = (self._voice_director if spoken else self._director).invoke(
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
            max_facts = 1 if is_early_precision_turn else 2
            # Truncate to the cap before validating. validate_fact_selection
            # slices in authored order, so an over-selection could otherwise
            # keep the director's third choice and drop its second, leaving the
            # reply narrating a fact the ledger never recorded.
            facts = session.case.validate_fact_selection(
                decision.fact_ids[:max_facts],
                session.stage,
                session.disclosed_ids,
                max_facts=max_facts,
            )
            next_phase = (
                session.stage
                if is_early_precision_turn
                else session.case.validate_phase_transition(session.stage, decision.next_phase)
            )
            approved_facts = "\n".join(f"- {fact.content}" for fact in facts) or "None"
            writer = self._voice_delivery if spoken else self._voice
            writer_retry = self._voice_delivery_retry if spoken else self._voice_retry
            writer_inputs = {
                "history": history,
                "current_phase": next_phase,
                "candidate_turn_number": session.candidate_turns,
                "turn_pacing_policy": turn_pacing_policy,
                "move": decision.move,
                "interviewer_brief": decision.interviewer_brief,
                "approved_facts": approved_facts,
                "candidate_turn": candidate_turn,
                "delivery_instruction": (
                    "This reply will be spoken aloud. Sound warm and confident for a welcome or clear direction, "
                    "patient and calm for process guidance or a calculation, and serious but never scolding when "
                    "precision matters. Show empathy only after expressed nerves or frustration. Use enthusiasm "
                    "only for a genuinely strong breakthrough. Never output bracketed audio tags, stage directions, "
                    "or words that describe delivery; they would be spoken aloud literally. Most factual answers "
                    "should be plain, concise, and neutral."
                    if spoken
                    else "This reply is displayed in typed chat. Do not use bracketed audio tags."
                ),
            }

            def write_reply() -> str:
                return _without_audio_tags(
                    _finalize_reply(self._complete_text(writer, writer_retry, writer_inputs))
                )

            reply = write_reply()
            fact_payload = json.dumps([{"id": fact.id, "content": fact.content} for fact in facts])
            selected_ids = {fact.id for fact in facts}
            audit = self._fact_audit.invoke(
                {"candidate_turn": candidate_turn, "reply": reply, "facts": fact_payload}
            )
            if not audit.reply_complete or set(audit.communicated_fact_ids) != selected_ids:
                if facts:
                    # The material facts are known, so repair the prose while
                    # keeping its factual surface tightly constrained.
                    reply = _without_audio_tags(
                        _finalize_reply(
                            self._complete_text(
                                self._reply_repair,
                                self._reply_repair_retry,
                                {
                                    "candidate_turn": candidate_turn,
                                    "reply": reply,
                                    "facts": fact_payload,
                                },
                            )
                        )
                    )
                else:
                    # There is no approved factual payload to repair from. Ask
                    # the same writer for one fresh, complete turn instead.
                    reply = write_reply()
                audit = self._fact_audit.invoke(
                    {"candidate_turn": candidate_turn, "reply": reply, "facts": fact_payload}
                )
            if not audit.reply_complete or set(audit.communicated_fact_ids) != selected_ids:
                raise RuntimeError("The interviewer reply was empty or incomplete")
            spoken_reply = reply
        except Exception as error:
            logger.exception(
                "OpenRouter interviewer turn failed (case=%s, spoken=%s, candidate_turn=%s)",
                session.case.id,
                spoken,
                session.candidate_turns,
            )
            # Remove the unserved candidate turn so a retry preserves a coherent transcript.
            session.messages.pop()
            session.candidate_turns -= 1
            raise InterviewerUnavailable("The interviewer provider did not complete this turn.") from error

        session.apply_director_decision(next_phase, facts)
        session.add_interviewer_turn(reply)
        return InterviewTurn(reply=reply, facts=facts, spoken_reply=spoken_reply if spoken else None)


def create_interviewer() -> Interviewer:
    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY is required to run the LLM interviewer")
    return LangChainCaseInterviewer()
