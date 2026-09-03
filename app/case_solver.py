"""Play a contributed case headlessly and see whether it can actually be solved.

The deterministic gate in :mod:`app.case_validator` proves a package is
internally consistent. Consistency is not solvability. A synthesis pass will
happily produce a set of mutually consistent facts from which the stated
diagnosis does not follow, or follows only if you already knew it, and no
structural check can tell the difference.

So the case is played. An LLM candidate runs the real
:class:`~app.case_runtime.InterviewSession` against the real interviewer, sees
only what the runtime released, and is then asked what the underlying problem
was. A separate judge compares that answer to the authored ``core_mechanism``.

Two deliberate choices:

**The Coach persona.** This measures whether the case is solvable *at all*, not
whether it is hard. Running the probe against a withholding interviewer would
conflate "this case is broken" with "this case is difficult", and the first is
the only one that should block publication.

**Turns taken is reported, not judged.** A case solved in three turns with no
probing is too easy, which is worth telling the admin, but easiness is a
judgement call and not the gate's to make.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.case_runtime import CaseWorld, InterviewSession
from app.interviewer import Interviewer, InterviewerUnavailable


logger = logging.getLogger(__name__)

# Enough turns for a real line of inquiry, few enough that a pathological case
# cannot burn an unbounded number of provider calls during review.
MAX_PROBE_TURNS = 14


class SolverUnavailable(RuntimeError):
    """The probe could not run, which is not the same as the case failing."""


class ProbeTurn(BaseModel):
    """One move by the simulated candidate."""

    reasoning: str = Field(description="Why this question, in one short sentence.")
    message: str = Field(description="What the candidate says to the interviewer.")
    ready_to_diagnose: bool = Field(
        default=False,
        description="True only when the released evidence is enough to name the underlying problem.",
    )


class ProbeDiagnosis(BaseModel):
    """The simulated candidate's final answer."""

    diagnosis: str = Field(description="The underlying problem, stated plainly.")
    supporting_evidence: list[str] = Field(default_factory=list)


class SolveVerdict(BaseModel):
    """The judge's comparison of that answer to the authored mechanism."""

    reached_mechanism: bool = Field(
        description="True only if the diagnosis names the same underlying mechanism as the authored one."
    )
    justification: str = Field(description="One or two sentences explaining the call.")
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Anything the candidate would have needed but was never able to obtain.",
    )


@dataclass(frozen=True)
class SolveReport:
    """What the admin sees alongside the deterministic findings."""

    solvable: bool
    turns_taken: int
    facts_released: int
    facts_total: int
    diagnosis: str
    justification: str
    missing_evidence: tuple[str, ...]
    transcript: tuple[dict[str, str], ...]

    @property
    def too_easy(self) -> bool:
        """Solved almost immediately, which usually means the case gives itself away."""
        return self.solvable and self.turns_taken <= 3

    def as_dict(self) -> dict[str, Any]:
        return {
            "solvable": self.solvable,
            "too_easy": self.too_easy,
            "turns_taken": self.turns_taken,
            "facts_released": self.facts_released,
            "facts_total": self.facts_total,
            "diagnosis": self.diagnosis,
            "justification": self.justification,
            "missing_evidence": list(self.missing_evidence),
            "transcript": [dict(turn) for turn in self.transcript],
        }


class LangChainCaseSolver:
    """A simulated candidate plus a judge, over the real interview runtime."""

    def __init__(self) -> None:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openrouter import ChatOpenRouter

        from app.llm_budget import COMPLETION_TOKENS

        settings = {
            "model": os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"),
            "temperature": 0.3,
            "max_retries": 2,
        }
        candidate_model = ChatOpenRouter(max_tokens=COMPLETION_TOKENS, **settings)
        judge_model = ChatOpenRouter(max_tokens=COMPLETION_TOKENS, **settings)

        candidate_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a strong consulting candidate solving a case interview. Ask one focused, "
                    "specific question per turn that names the quantity, segment or driver you want and "
                    "implies why it matters. Build on what the interviewer has already told you. Do not "
                    "invent facts, and do not assume anything you have not been told. Set "
                    "ready_to_diagnose true only when the evidence you have actually been given is enough "
                    "to name the underlying problem, not when you merely have a guess.",
                ),
                (
                    "human",
                    "Case brief: {opening}\n"
                    "Decision to answer: {objective}\n"
                    "Transcript so far:\n{transcript}\n"
                    "Evidence released to you so far:\n{released}\n"
                    "Turn number: {turn_number} of {max_turns}",
                ),
            ]
        )
        diagnosis_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "State the underlying problem in this case, based only on the evidence you were "
                    "actually given. Do not speculate beyond it. If the evidence does not support a "
                    "diagnosis, say so plainly rather than guessing.",
                ),
                ("human", "Transcript:\n{transcript}\n\nEvidence released:\n{released}"),
            ]
        )
        judge_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You judge whether a candidate reached the same underlying mechanism the case author "
                    "intended. Judge the substance, not the wording: different vocabulary for the same "
                    "causal mechanism counts as reaching it. A diagnosis that names only a symptom, or "
                    "a different mechanism entirely, does not. Be strict, because the purpose of this "
                    "check is to stop an unsolvable case being published.",
                ),
                (
                    "human",
                    "Authored core mechanism: {mechanism}\n"
                    "Authored pivotal insight: {insight}\n"
                    "Candidate's diagnosis: {diagnosis}\n"
                    "Candidate's cited evidence: {evidence}",
                ),
            ]
        )
        self._candidate = candidate_prompt | candidate_model.with_structured_output(ProbeTurn)
        self._diagnose = diagnosis_prompt | candidate_model.with_structured_output(ProbeDiagnosis)
        self._judge = judge_prompt | judge_model.with_structured_output(SolveVerdict)

    def solve(
        self,
        world: CaseWorld,
        interviewer: Interviewer,
        *,
        mechanism: str,
        insight: str = "",
        max_turns: int = MAX_PROBE_TURNS,
    ) -> SolveReport:
        """Play the case to a diagnosis and judge it against the authored mechanism."""
        # The Coach, deliberately. This asks whether the case is solvable at all,
        # not whether it is hard, and a withholding persona would conflate the two.
        session = InterviewSession(id=f"probe-{uuid4()}", case=world, mode="coached")
        session.case_started = True

        transcript: list[dict[str, str]] = []
        turns = 0
        try:
            for turn in range(1, max_turns + 1):
                move = self._candidate.invoke(
                    {
                        "opening": world.opening,
                        "objective": world.objective,
                        "transcript": _render(transcript) or "Nothing yet.",
                        "released": _render_facts(session, world) or "Nothing yet.",
                        "turn_number": turn,
                        "max_turns": max_turns,
                    }
                )
                transcript.append({"role": "candidate", "content": move.message})
                turns = turn
                if move.ready_to_diagnose:
                    break
                reply = interviewer.respond(session, move.message)
                transcript.append({"role": "interviewer", "content": reply.reply})

            answer = self._diagnose.invoke(
                {
                    "transcript": _render(transcript),
                    "released": _render_facts(session, world) or "Nothing was released.",
                }
            )
            verdict = self._judge.invoke(
                {
                    "mechanism": mechanism,
                    "insight": insight or "Not stated.",
                    "diagnosis": answer.diagnosis,
                    "evidence": json.dumps(answer.supporting_evidence),
                }
            )
        except InterviewerUnavailable as error:
            raise SolverUnavailable("The interviewer could not complete the probe") from error
        except Exception as error:  # pragma: no cover - provider-shaped failures
            logger.exception("Solve-it-cold probe failed for case %s", world.id)
            raise SolverUnavailable("The solvability probe could not run") from error

        return SolveReport(
            solvable=verdict.reached_mechanism,
            turns_taken=turns,
            facts_released=len(session.disclosed_ids),
            facts_total=len(world.facts),
            diagnosis=answer.diagnosis,
            justification=verdict.justification,
            missing_evidence=tuple(verdict.missing_evidence),
            transcript=tuple(transcript),
        )


def _render(transcript: list[dict[str, str]]) -> str:
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in transcript)


def _render_facts(session: InterviewSession, world: CaseWorld) -> str:
    return "\n".join(
        f"- {fact.content}" for fact in world.facts if fact.id in session.disclosed_ids
    )


def create_case_solver() -> LangChainCaseSolver | None:
    """None when no provider key exists, so review degrades rather than breaks.

    A missing probe is reported to the admin as "not run", which is honest. Making
    it fatal would mean no case could be reviewed on an instance without a key.
    """
    if not os.getenv("OPENROUTER_API_KEY"):
        return None
    return LangChainCaseSolver()
