"""Turn an extracted memory into a runnable, re-skinned case package.

This is the step the contribution engine exists for. A contributor gives a fuzzy
account: the mechanism, roughly which quantities moved, what tripped them up.
That is not playable. A playable case is a fact ledger with release levels and
dependencies, an issue tree, a conversation policy, and numbers that close.

Three properties this pass must hold, in order of how badly they fail:

**Re-skin, always.** The output is a synthetic case inspired by a recalled
mechanism, never a transcript of a real one. That is the defensible position on
recalled interview content, and it is also what makes the safety check in
:mod:`app.case_validator` satisfiable rather than adversarial. The prompt asks for
a new client in a comparable industry.

**Numbers close, or the gate catches it.** The model proposes magnitudes and the
relationships between them; ``app.expressions`` decides whether the arithmetic
actually lands. Nothing here trusts a model's arithmetic, because multi-constraint
numeric closure is precisely where models are confidently wrong.

**The recalled teeth survive.** The mechanism always comes from the contributor.
Any pivotal insight or trap they remember carries over in substance. When those
recoverable details are absent, the model may complete them from the anchored
mechanism so imperfect recall does not block contribution; the package records
which fields were synthesized.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from pydantic import BaseModel, Field

from app.case_author import ExtractedCase


logger = logging.getLogger(__name__)


class SynthesisUnavailable(RuntimeError):
    """The provider could not produce a package."""


# Mirrors the shared conversation policy in reservoir/_shared-policy.yaml. Every
# contributed case gets the same phase structure, so the runtime's disclosure
# behaviour is identical whoever wrote the case.
DEFAULT_PHASE_POLICY: dict[str, Any] = {
    "clarification": {
        "interviewer_goal": "Confirm the client, decision, scope, and the candidate's first useful line of inquiry.",
        "reveal_levels": ["opening", "broad_context", "sharp_question"],
        "expected_candidate_behaviours": [
            "Ask clarifying questions that materially narrow the case.",
            "Restate the decision, metric, or time horizon.",
        ],
    },
    "drill_down": {
        "interviewer_goal": "Let the candidate test a prioritised hypothesis against case evidence.",
        "reveal_levels": ["broad_context", "sharp_question", "hypothesis_backed"],
        "expected_candidate_behaviours": [
            "Present a tailored issue tree or causal hypothesis.",
            "Prioritise a branch and explain why it matters.",
        ],
    },
    "synthesis": {
        "interviewer_goal": "Assess a recommendation with evidence, trade-offs, and an implementation next step.",
        "reveal_levels": ["hypothesis_backed", "synthesis_support"],
        "expected_candidate_behaviours": [
            "State a diagnosis rather than repeat facts.",
            "Make a prioritised recommendation.",
        ],
    },
}


class SynthesisedFact(BaseModel):
    id: str = Field(description="Dotted identifier, for example 'economics.unit-cost'.")
    domain: str = Field(description="Business domain, for example 'company' or 'economics'.")
    release_level: str = Field(
        description="One of opening, broad_context, sharp_question, hypothesis_backed, synthesis_support."
    )
    content: str = Field(description="The fact as the interviewer would state it.")
    candidate_purpose: str = Field(default="", description="Why this fact matters to the candidate.")
    question_examples: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    numeric_value: float | None = Field(
        default=None, description="The number this fact states, when it states one."
    )
    formula: str = Field(
        default="",
        description="For a derived fact only, the arithmetic producing numeric_value from other facts.",
    )
    depends_on: dict[str, str] = Field(
        default_factory=dict, description="Maps each formula variable to the fact ID supplying it."
    )


class SynthesisedCase(BaseModel):
    """The model's proposal, before any of it is trusted."""

    title: str = Field(description="A short invented client name and descriptor.")
    category: str = Field(description="profitability, growth_strategy, market_entry, pricing_strategy, operations, or mergers_and_acquisitions.")
    industry: str = Field(description="Industry slug, for example 'temperature_controlled_logistics'.")
    difficulty: str = Field(default="intermediate", description="foundation, intermediate, or advanced.")
    skills_tested: list[str] = Field(default_factory=list)
    opening_context: str = Field(description="Client background and situation, candidate-facing.")
    opening_objective: str = Field(description="The decision and time horizon, candidate-facing.")
    primary_metric: str = Field(default="")
    decision_question: str = Field(description="The question the candidate must answer.")
    time_horizon: str = Field(default="twelve months")
    core_mechanism: str = Field(description="The underlying driver, carried over from the contributor.")
    what_the_case_wanted_to_test: str = Field(default="")
    pivotal_insight: str = Field(description="Carried over from the contributor.")
    common_traps: list[str] = Field(default_factory=list, description="Carried over from the contributor.")
    takeaway_lesson: str = Field(default="")
    facts: list[SynthesisedFact] = Field(default_factory=list)
    hidden_diagnosis: str = Field(
        default="", description="The answer, stored interviewer-only and never released."
    )


def slugify(value: str, fallback: str = "contributed-case") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug[:48] or fallback


class LangChainCaseSynthesiser:
    def __init__(self) -> None:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openrouter import ChatOpenRouter

        from app.llm_budget import COMPLETION_TOKENS

        model = ChatOpenRouter(
            max_tokens=COMPLETION_TOKENS,
            model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"),
            temperature=0.3,
            max_retries=2,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You turn a candidate's recollection of a case interview into a runnable, "
                    "self-consistent case world.\n\n"
                    "RE-SKIN THE CASE. Invent a new client in a comparable industry with an invented "
                    "name. Never name a real company, firm, or person anywhere in the output. The "
                    "mechanism is what carries over, not the identity.\n\n"
                    "PRESERVE WHAT WAS RECALLED. The core mechanism came from the real interview and "
                    "must remain the causal spine. Carry over any pivotal insight, traps, quantities, "
                    "or pushback the contributor supplied in substance. Never contradict them.\n\n"
                    "COMPLETE RECOVERABLE GAPS. If the pivotal insight, traps, takeaway, exact numbers, "
                    "or other teaching details are absent, synthesize plausible versions that follow "
                    "from the contributor's client frame, decision, situation, and mechanism. Always "
                    "produce at least two distinct common traps and a non-empty takeaway lesson. This "
                    "is an invented practice case inspired by the recollection, not a claim that the "
                    "contributor remembered every generated detail.\n\n"
                    "MAKE THE NUMBERS CLOSE. Choose a set of quantities that are internally consistent "
                    "and that make the stated mechanism actually true. Respect the contributor's "
                    "directions and rough ratios; invent the precision they could not remember. For any "
                    "fact that is computed from others, set formula and depends_on and make "
                    "numeric_value exactly what that formula produces. Prefer round, tractable numbers: "
                    "this is consulting math and a candidate should be able to do it in their head.\n\n"
                    "GATE THE EVIDENCE. Give roughly ten to sixteen facts. Put scene-setting at "
                    "'opening', background at 'broad_context', the data a targeted question earns at "
                    "'sharp_question', and the evidence that only makes sense once a hypothesis is on "
                    "the table at 'hypothesis_backed'. The candidate must not be able to reach the "
                    "diagnosis without doing the work.\n\n"
                    "Do not put the diagnosis into any released fact. It goes in hidden_diagnosis.",
                ),
                (
                    "human",
                    "The contributor's account of the case they sat:\n{extracted}\n\n"
                    "Build the case world.",
                ),
            ]
        )
        self._chain = prompt | model.with_structured_output(SynthesisedCase)

    def synthesise(self, extracted: ExtractedCase, *, contributor_id: str) -> dict[str, Any]:
        """Produce a stored-package payload from an extracted memory."""
        try:
            case = self._chain.invoke({"extracted": json.dumps(extracted.model_dump(), indent=1)})
        except Exception as error:
            logger.exception("Case synthesis failed")
            raise SynthesisUnavailable("The case could not be synthesised") from error

        return build_package(case, extracted, contributor_id=contributor_id)


def build_package(
    case: SynthesisedCase, extracted: ExtractedCase, *, contributor_id: str
) -> dict[str, Any]:
    """Assemble the stored payload. Pure, so it can be tested without a provider."""
    case_id = f"community-{slugify(case.title)}-v1"
    synthesized_fields = []
    if not extracted.pivotal_insight.strip():
        synthesized_fields.append("pivotal_insight")
    if len(extracted.common_traps) < 2:
        synthesized_fields.append("common_traps")
    if not extracted.takeaway_lesson.strip():
        synthesized_fields.append("takeaway_lesson")
    if not extracted.quantities:
        synthesized_fields.append("quantities")

    facts: list[dict[str, Any]] = [
        {
            "id": fact.id,
            "domain": fact.domain,
            "release_level": fact.release_level,
            "content": fact.content,
            "candidate_purpose": fact.candidate_purpose,
            "question_examples": fact.question_examples,
            "dependencies": fact.dependencies,
            "provenance": "authored_scenario",
            **({"numeric_value": fact.numeric_value} if fact.numeric_value is not None else {}),
            **({"formula": fact.formula, "depends_on": fact.depends_on} if fact.formula else {}),
        }
        for fact in case.facts
    ]
    if case.hidden_diagnosis.strip():
        # interviewer_only never reaches the browser or the interviewer prompt, so
        # this is the one place the answer can live inside the package.
        facts.append(
            {
                "id": "diagnosis.hidden",
                "domain": "diagnosis",
                "release_level": "interviewer_only",
                "content": case.hidden_diagnosis.strip(),
                "provenance": "authored_scenario",
            }
        )

    return {
        "case": {
            "schema_version": "reservoir-v1",
            "case_id": case_id,
            "title": case.title,
            "status": "draft",
            "rights_status": "original",
            "category": case.category,
            "industry": case.industry,
            "difficulty": case.difficulty if case.difficulty in {"foundation", "intermediate", "advanced"} else "intermediate",
            "source": "community",
            "supported_durations": [30],
            "skills_tested": case.skills_tested or ["clarification", "tailored structure", "analysis", "synthesis"],
            "candidate_opening": {
                "context": case.opening_context,
                "objective": case.opening_objective,
                "opening_requirements": [
                    "Name the client and its business.",
                    "State the performance problem.",
                    "State the decision and time horizon.",
                    "Invite clarifying questions before requesting a structure.",
                ],
            },
            "objective_function": {
                "primary_metric": case.primary_metric or "profitability",
                "decision_question": case.decision_question,
                "time_horizon": case.time_horizon or "twelve months",
                "expected_candidate_output": [
                    "Clear diagnosis supported by evidence.",
                    "Prioritised recommendation.",
                    "Main implementation risk.",
                ],
            },
            "case_essence": {
                "core_mechanism": case.core_mechanism,
                "what_the_case_wanted_to_test": case.what_the_case_wanted_to_test or extracted.what_it_tested,
                "pivotal_insight": case.pivotal_insight,
                "common_traps": case.common_traps or extracted.common_traps,
                "takeaway_lesson": case.takeaway_lesson or extracted.takeaway_lesson,
            },
            "provenance": {
                "source_type": "interview_recall",
                # Month precision only, and no firm unless the contributor offered
                # one. A full date plus a firm plus a round is close to identifying
                # for someone still in a live process.
                "firm": extracted.firm or None,
                "round": _round_number(extracted.interview_round),
                "geography": extracted.geography or None,
                "interview_month": _month(extracted.interview_month),
                "contributor_id": contributor_id,
                "attribution_mode": "pseudonymous",
                "synthesized_fields": synthesized_fields,
            },
            "session_contract": {
                "mode": "realistic",
                "live_fact_invention": "disabled",
                "quantitative_drills": "disabled",
                "transcript_visibility": "post_case_only",
            },
        },
        "facts": {"schema_version": "reservoir-facts-v1", "facts": facts},
        "conversation_policy": {
            "schema_version": "conversation-policy-v1",
            "mode": "realistic",
            "phase_policy": DEFAULT_PHASE_POLICY,
        },
    }


def _round_number(value: str) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else None


def _month(value: str) -> str | None:
    """Accept only YYYY-MM, discarding anything more precise.

    Truncating rather than rejecting: a contributor who says '2026-07-14' gets the
    month kept and the day dropped, which is the privacy outcome we want without
    losing the recency signal the whole feature depends on.
    """
    match = re.match(r"(\d{4})-(\d{2})", str(value or "").strip())
    return f"{match.group(1)}-{match.group(2)}" if match else None


def create_case_synthesiser() -> LangChainCaseSynthesiser | None:
    if not os.getenv("OPENROUTER_API_KEY"):
        return None
    return LangChainCaseSynthesiser()
