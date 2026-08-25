"""One streaming LLM call per spoken turn.

Typed chat runs the four-stage pipeline in ``app.interviewer``: a director
chooses facts, a writer turns the brief into prose, an audit checks the result,
and a repair pass rewrites it. That is three to five sequential round trips, and
``_sse_reply`` could not emit a single byte until the last of them returned, so
speech began only after the entire reply existed.

A spoken turn cannot afford that. Here the director and the writer become one
streaming call: the model emits a machine-readable control block first, then
speaks. The control block closes within the first few tokens, which lets the
runtime release facts immediately, and every token after it is speakable text
that flows straight through to the browser and on to speech synthesis. Audio for
the first sentence is generated while the second is still being written.

Safety is unchanged and still lives in code, not in the prompt. The model only
ever sees ``eligible_facts_for_director``, already filtered by phase and by
dependency, and ``validate_fact_selection`` re-filters whatever comes back. The
audit that leaves the critical path was checking reply *quality*, never
disclosure: a thin answer is a thin answer, not a leaked fact.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Iterator

from app.case_runtime import Fact, InterviewSession
from app.interviewer import (
    InterviewTurn,
    InterviewerUnavailable,
    _finalize_reply,
    _without_audio_tags,
)


logger = logging.getLogger(__name__)


CONTROL_OPEN = "<control>"
CONTROL_CLOSE = "</control>"

# If the model has produced this much text without closing its control block it
# is not going to. Abandoning here costs one wasted prefix rather than a turn
# spoken from an unvalidated fact selection.
CONTROL_DEADLINE_CHARS = 400

# A spoken turn is one or two short sentences. The chat budget is sized for a
# reasoning model's private preamble, which is pure silence on this path.
SPOKEN_COMPLETION_TOKENS = int(os.getenv("VOICE_COMPLETION_TOKENS", "700"))

DEFAULT_SPOKEN_MODEL = "anthropic/claude-sonnet-4.6"


SYSTEM_PROMPT = """You are Leo, a calm, incisive consulting case interviewer speaking aloud to a \
candidate. You are direct, precise and respectful, never theatrical or overly encouraging.

Every reply has exactly two parts, in this order.

First, one line of control data and nothing else:
<control>{"fact_ids": [...], "next_phase": "...", "move": "..."}</control>
  fact_ids   Zero or more IDs, chosen only from the eligible facts given below, listing the facts
             you are about to communicate. Order them by importance: only the first few are
             released, so put the fact your answer leans on first. Never invent an ID.
  next_phase One of the authored phase IDs. Hold the current phase or advance exactly one.
  move       One of answer, probe, challenge, redirect, invite, close.

Then, immediately after the closing tag, the words you actually speak. Nothing else follows them.

Rules for the spoken part:
- Use only the facts you listed. Never reveal a solution, a hidden diagnosis, or a future fact.
- Communicate every material detail of the facts you listed, paraphrased naturally.
- One or two short sentences, normally under 65 words. Never use an em dash.
- Write this turn afresh. No templates, no canned phrasing, no stage directions, no bracketed
  audio tags: anything you write is spoken aloud literally.
- Do not end every turn with a question. A concise declarative answer is the normal response when
  a fact is available. Ask at most one focused question, and only when the move is probe.
- If the candidate is stuck after an earlier probe, give the answer directly rather than asking again.
- Occasionally, about one turn in five and only when genuinely earned, open with a very short
  acknowledgement of the candidate's exact point.
- Never begin an answer you do not finish."""


@dataclass(frozen=True)
class ControlDecision:
    fact_ids: list[str]
    next_phase: str
    move: str


class ControlBlockMissing(RuntimeError):
    """The model never emitted a parseable control block."""


def parse_control_block(text: str) -> ControlDecision:
    """Read the control preamble, tolerating whitespace and stray fencing."""
    start = text.find(CONTROL_OPEN)
    end = text.find(CONTROL_CLOSE)
    if start == -1 or end == -1 or end < start:
        raise ControlBlockMissing("No control block in the spoken completion")
    payload = text[start + len(CONTROL_OPEN) : end].strip()
    payload = payload.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ControlBlockMissing("Malformed control block in the spoken completion") from error
    if not isinstance(parsed, dict):
        raise ControlBlockMissing("Control block was not an object")
    raw_ids = parsed.get("fact_ids") or []
    fact_ids = [str(value) for value in raw_ids if isinstance(value, (str, int))]
    return ControlDecision(
        fact_ids=fact_ids,
        next_phase=str(parsed.get("next_phase") or ""),
        move=str(parsed.get("move") or "answer"),
    )


def spoken_text_after_control(text: str) -> str:
    """Everything the candidate is meant to hear."""
    _, separator, tail = text.partition(CONTROL_CLOSE)
    return (tail if separator else text).strip()


_SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def sentence_chunks(text: str, *, minimum: int = 60) -> tuple[list[str], str]:
    """Split streamed prose into speakable chunks plus an unfinished remainder.

    Speech synthesis wants whole clauses, not tokens. Flushing on a sentence
    boundary keeps prosody intact; the length floor stops one long clause from
    holding back audio that could already be playing.
    """
    chunks: list[str] = []
    remainder = text
    while True:
        match = _SENTENCE_END.search(remainder)
        if match is None:
            break
        cut = match.end()
        chunk = remainder[:cut].strip()
        if not chunk:
            break
        chunks.append(chunk)
        remainder = remainder[cut:].lstrip()
    if not chunks and len(remainder) > minimum:
        comma = remainder.rfind(", ")
        if comma > minimum // 2:
            chunks.append(remainder[: comma + 1].strip())
            remainder = remainder[comma + 1 :].lstrip()
    return chunks, remainder


class SpokenInterviewer:
    """Fused decide-and-speak turn, streamed over OpenRouter.

    Deliberately the same provider typed chat already uses. The fused call and
    the clause-at-a-time hand-off to speech are what buy the latency back; the
    gateway hop is worth a fraction of that, and staying on one provider keeps
    one credential and the model-fallback behaviour the rest of the app relies
    on.
    """

    def __init__(self) -> None:
        from langchain_openrouter import ChatOpenRouter

        fallback_models = [
            model.strip()
            for model in os.getenv("OPENROUTER_FALLBACK_MODELS", "").split(",")
            if model.strip()
        ]
        self._model_name = (
            os.getenv("VOICE_OPENROUTER_MODEL", "").strip()
            or os.getenv("OPENROUTER_MODEL", "").strip()
            or DEFAULT_SPOKEN_MODEL
        )
        # Measured on anthropic/claude-sonnet-4.6 through OpenRouter: with
        # reasoning left on, a five-sentence reply arrives as ONE delta after
        # 4.65s, which makes clause-by-clause speech impossible. Excluding
        # reasoning gives 18 deltas with the first at 1.9s. This parameter is
        # therefore not a cost tweak, it is what makes streamed speech work.
        self._client = ChatOpenRouter(
            model=self._model_name,
            temperature=0.3,
            max_tokens=SPOKEN_COMPLETION_TOKENS,
            # A spoken retry turns an answer into a long silence.
            max_retries=1,
            reasoning={"exclude": True},
            model_kwargs={"models": fallback_models} if fallback_models else {},
        )

    # -- prompt assembly ---------------------------------------------------

    def _system_text(self, session: InterviewSession) -> str:
        """The half of the prompt that never changes inside one attempt.

        Kept first and byte-stable so a caching gateway can reuse it across the
        turns of one case. Everything volatile, the current phase and the
        eligible fact contents, goes in the turn message instead.
        """
        case = session.case
        phases = "\n".join(f"- {phase.id}: {phase.interviewer_goal}" for phase in case.phases)
        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"Case: {case.title}\n"
            f"Category: {case.category.replace('-', ' ')}\n"
            f"Objective: {case.objective}\n"
            f"Authored phases, in order:\n{phases}"
        )

    def _turn_message(
        self,
        session: InterviewSession,
        candidate_turn: str,
        *,
        eligible: list[dict[str, object]],
        pacing: str,
        max_facts: int,
    ) -> str:
        return (
            f"Current phase: {session.stage}\n"
            f"Candidate turn number: {session.candidate_turns}\n"
            f"Turn pacing policy: {pacing}\n"
            f"Release at most {max_facts} fact(s) this turn.\n"
            f"Eligible facts (choose only from these):\n{json.dumps(eligible, indent=None)}\n\n"
            f"Candidate's latest turn: {candidate_turn}"
        )

    def _history(self, session: InterviewSession) -> list[object]:
        from langchain_core.messages import AIMessage, HumanMessage

        return [
            HumanMessage(content=message["content"])
            if message["role"] == "candidate"
            else AIMessage(content=message["content"])
            for message in session.messages[-7:-1]
        ]

    # -- the streaming turn ------------------------------------------------

    def respond_stream(
        self, session: InterviewSession, candidate_turn: str
    ) -> Iterator[tuple[str, object]]:
        """Yield ('control', facts), then ('delta', text)..., then ('done', turn).

        The caller owns persistence. This generator mutates the session only
        after the control block has been validated, so an abandoned stream
        cannot leave a fact marked as disclosed.
        """
        session.record_candidate_turn(candidate_turn)
        is_early = session.candidate_turns <= 2
        max_facts = 1 if is_early else 2
        pacing = (
            "EARLY PRECISION: one of the first two candidate turns. Answer only the exact question "
            "asked with at most one atomic fact. Hold the current phase. Volunteer nothing."
            if is_early
            else "NORMAL PACING: answer with the narrowest useful fact. If the candidate is stuck "
            "after a prior probe, give one additional narrow fact rather than asking again."
        )
        eligible = session.case.eligible_facts_for_director(session.stage, session.disclosed_ids)

        from langchain_core.messages import HumanMessage, SystemMessage

        accumulated = ""
        spoken = ""
        control: ControlDecision | None = None
        facts: list[Fact] = []
        try:
            stream = self._client.stream(
                [
                    SystemMessage(content=self._system_text(session)),
                    *self._history(session),
                    HumanMessage(
                        content=self._turn_message(
                            session,
                            candidate_turn,
                            eligible=eligible,
                            pacing=pacing,
                            max_facts=max_facts,
                        )
                    ),
                ]
            )
            for chunk in stream:
                delta = chunk.content if isinstance(chunk.content, str) else ""
                if not delta:
                    continue
                accumulated += delta
                if control is None:
                    if CONTROL_CLOSE not in accumulated:
                        if len(accumulated) > CONTROL_DEADLINE_CHARS:
                            raise ControlBlockMissing(
                                "Control block never closed within its deadline"
                            )
                        continue
                    control = parse_control_block(accumulated)
                    # The runtime, not the model, decides what is released.
                    # Truncating to the cap first keeps the model's own priority
                    # order, so the facts it narrates are the facts the ledger
                    # records.
                    facts = session.case.validate_fact_selection(
                        control.fact_ids[:max_facts],
                        session.stage,
                        session.disclosed_ids,
                        max_facts=max_facts,
                    )
                    next_phase = (
                        session.stage
                        if is_early
                        else session.case.validate_phase_transition(
                            session.stage, control.next_phase
                        )
                    )
                    session.apply_director_decision(next_phase, facts)
                    yield ("control", facts)
                    tail = spoken_text_after_control(accumulated)
                    if tail:
                        spoken = tail
                        yield ("delta", tail)
                    continue
                spoken += delta
                yield ("delta", delta)

            if control is None:
                raise ControlBlockMissing("The spoken completion contained no control block")
            logger.info(
                "Spoken turn: model=%s facts=%s",
                self._model_name,
                [fact.id for fact in facts],
            )
        except ControlBlockMissing:
            self._rewind(session)
            raise
        except Exception as error:
            logger.exception(
                "Spoken interviewer turn failed (case=%s, turn=%s)",
                session.case.id,
                session.candidate_turns,
            )
            self._rewind(session)
            raise InterviewerUnavailable("The spoken interviewer did not complete this turn.") from error

        reply = _without_audio_tags(_finalize_reply(spoken))
        if not reply:
            self._rewind(session)
            raise ControlBlockMissing("The spoken completion had a control block but no speech")
        session.add_interviewer_turn(reply)
        yield ("done", InterviewTurn(reply=reply, facts=facts, spoken_reply=reply))

    @staticmethod
    def _rewind(session: InterviewSession) -> None:
        """Undo the unserved candidate turn so a retry keeps the transcript coherent."""
        if session.messages and session.messages[-1]["role"] == "candidate":
            session.messages.pop()
            session.candidate_turns -= 1


def create_spoken_interviewer() -> SpokenInterviewer | None:
    """Build the fused spoken path, or None when it is not configured.

    A missing key disables low-latency voice rather than the product: callers
    fall back to the existing chat pipeline, which is the same way voice already
    degrades elsewhere.
    """
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.info("Spoken interviewer disabled: OPENROUTER_API_KEY is not set")
        return None
    try:
        return SpokenInterviewer()
    except Exception as error:  # pragma: no cover - import or client construction
        logger.warning("Spoken interviewer disabled: %s", error)
        return None
