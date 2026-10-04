"""Structured case draft and durable contribution state.

Question selection, evidence assessment and framing live in app.contribution.
Legacy phase fields are read only for compatibility with existing sessions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field



class ExtractionUnavailable(RuntimeError):
    """The provider could not complete an extraction turn."""


# The full-fidelity targets the conversation continues to chase. They are not all
# submission blockers: once the synthesis threshold is reached, the LLM may
# complete missing recoverable fields before the final package is validated.
REQUIRED_FIELDS: tuple[str, ...] = (
    "client_and_industry",
    "situation",
    "decision_question",
    "core_mechanism",
    "pivotal_insight",
    "common_traps",
)

# The minimum viable recollection. These must come from the contributor because
# synthesising any one of them would change which case they are contributing.
SYNTHESIS_ANCHORS: tuple[str, ...] = (
    "client_and_industry",
    "situation",
    "decision_question",
    "core_mechanism",
)

# Setting (client + situation), decision and cause total exactly 70%.
# Optional fidelity never substitutes for a missing mandatory criterion.
SYNTHESIS_THRESHOLD = 0.70
SUFFICIENCY_WEIGHTS: dict[str, float] = {
    "client_and_industry": 0.15,
    "situation": 0.10,
    "decision_question": 0.20,
    "core_mechanism": 0.25,
    "pivotal_insight": 0.10,
    "common_traps": 0.10,
    "quantities": 0.05,
    "what_it_tested": 0.05,
}

TRACKER_LABELS: dict[str, str] = {
    "client_and_industry": "Client and industry context",
    "situation": "Situation or performance problem",
    "decision_question": "Decision the case asks",
    "core_mechanism": "Underlying mechanism",
    "pivotal_insight": "Turning-point insight",
    "common_traps": "Two plausible wrong answers",
    "quantities": "Numbers or directional magnitudes",
    "what_it_tested": "What the case tested",
}

# Field names are schema identifiers. A contributor asked to supply a
# "core_mechanism" has no idea what is being requested, so every place a missing
# field is named to a human uses these instead.
FIELD_LABELS: dict[str, str] = {
    "situation": "the situation or performance problem presented",
    "client_and_industry": "who the client was and what they do",
    "decision_question": "the decision the interviewer wanted you to reach",
    "core_mechanism": "what was actually driving the problem underneath",
    "pivotal_insight": "the moment the case clicked, or should have",
    "common_traps": "the wrong answers that look right at first",
}

def describe_missing(missing: list[str]) -> str:
    """Human-readable list of gaps, for anything a contributor will read."""
    labels = [FIELD_LABELS.get(name, name) for name in missing]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} and {labels[-1]}"

MINIMUM_TRAPS = 2


class ExtractedCase(BaseModel):
    """Everything the agent has managed to get so far.

    Flat and plain-language on purpose. The contributor is describing a memory,
    not filling in a case package, and the synthesis pass is what turns this into
    the authored schema.
    """

    client_and_industry: str = Field(default="", description="Generic client type and business/industry. COMPLETE for a cold-chain logistics operator, retailer, airline, etc. No name, size, geography or market share is required.")
    competitors: list[str] = Field(default_factory=list, description="Competitor types, behavior, positioning and competitive pressure, anonymized.")
    situation: str = Field(default="", description="The observed problem or change presented at the start. COMPLETE when a problem is stated, e.g. revenue grew while margins fell. Do NOT require background, numbers, client type, geography or explanation of the cause here; those are other fields.")
    decision_question: str = Field(default="", description="What the interviewer wanted decided, diagnosed or explained. COMPLETE when the objective is known; a time horizon, exact numeric target and recommendation are not required unless part of the remembered objective.")
    time_horizon: str = Field(default="", description="Time horizon, if one was stated.")
    primary_metric: str = Field(default="", description="The metric the case turned on.")
    given_upfront: list[str] = Field(default_factory=list, description="What the interviewer volunteered.")
    had_to_ask_for: list[str] = Field(default_factory=list, description="What the candidate had to extract.")
    quantities: list[str] = Field(
        default_factory=list,
        description="Quantities in play with rough magnitudes or directions, never invented precision.",
    )
    core_mechanism: str = Field(default="", description="Cause and causal link to the problem. COMPLETE only when both driver and how it produced the outcome are known; costs went up alone is partial.")
    pivotal_insight: str = Field(default="", description="The moment the case unlocks.")
    common_traps: list[str] = Field(default_factory=list, description="Plausible first answers that are wrong.")
    interviewer_pushback: list[str] = Field(
        default_factory=list, description="What the interviewer challenged them on."
    )
    what_it_tested: str = Field(default="", description="The skill or concept being assessed.")
    takeaway_lesson: str = Field(default="", description="The durable lesson.")
    firm: str = Field(default="", description="Firm, if they choose to say.")
    interview_round: str = Field(default="", description="Round, if they choose to say.")
    geography: str = Field(default="", description="Where the interview took place.")
    interview_month: str = Field(default="", description="Month precision only, as YYYY-MM.")

    def missing_required(self) -> list[str]:
        missing = []
        for name in REQUIRED_FIELDS:
            value = getattr(self, name)
            if isinstance(value, list):
                if len(value) < (MINIMUM_TRAPS if name == "common_traps" else 1):
                    missing.append(name)
            elif not str(value or "").strip():
                missing.append(name)
        return missing

    def missing_synthesis_anchors(self) -> list[str]:
        return [
            name
            for name in SYNTHESIS_ANCHORS
            if not str(getattr(self, name, "") or "").strip()
        ]

    def sufficiency_score(self) -> float:
        """Weighted share of evidence captured for a credible synthesis pass."""
        score = 0.0
        for name, weight in SUFFICIENCY_WEIGHTS.items():
            value = getattr(self, name)
            if name == "common_traps":
                score += weight * min(len(value) / MINIMUM_TRAPS, 1.0)
            elif isinstance(value, list):
                if value:
                    score += weight
            elif str(value or "").strip():
                score += weight
        return round(score, 2)

    def sufficient_for_synthesis(self) -> bool:
        return (
            not self.missing_synthesis_anchors()
            and self.sufficiency_score() >= SYNTHESIS_THRESHOLD
        )

    def completion_tracker(self) -> list[dict[str, Any]]:
        """Human-facing evidence ledger behind readiness and completion."""
        tracker: list[dict[str, Any]] = []
        for name, weight in SUFFICIENCY_WEIGHTS.items():
            value = getattr(self, name)
            if name == "common_traps":
                count = len(value)
                fraction = min(count / MINIMUM_TRAPS, 1.0)
                progress = f"{min(count, MINIMUM_TRAPS)} of {MINIMUM_TRAPS} captured"
            elif isinstance(value, list):
                fraction = 1.0 if value else 0.0
                progress = "Captured" if value else "Not captured yet"
            else:
                fraction = 1.0 if str(value or "").strip() else 0.0
                progress = "Captured" if fraction else "Not captured yet"
            tracker.append(
                {
                    "key": name,
                    "label": TRACKER_LABELS[name],
                    "weight": weight,
                    "credit": round(weight * fraction, 2),
                    "status": (
                        "captured" if fraction == 1.0 else "partial" if fraction else "missing"
                    ),
                    "progress": progress,
                    "mandatory_for_submit": name in SYNTHESIS_ANCHORS,
                    "required_for_complete": name in REQUIRED_FIELDS,
                }
            )
        return tracker

    def merge(self, patch: dict[str, Any]) -> "ExtractedCase":
        """Fold one turn's findings in without losing what is already known.

        Lists accumulate and de-duplicate; a later turn adding one trap must not
        discard the two already captured. Strings only overwrite when the new value
        is non-empty, so an agent returning a partial patch cannot blank a field it
        simply did not mention this turn.
        """
        merged = self.model_copy(deep=True)
        for key, value in (patch or {}).items():
            if key not in type(self).model_fields:
                continue
            current = getattr(merged, key)
            if isinstance(current, list):
                if isinstance(value, str):
                    value = [value]
                if not isinstance(value, list):
                    continue
                combined = list(current)
                for item in value:
                    text = str(item).strip()
                    if text and text not in combined:
                        combined.append(text)
                setattr(merged, key, combined)
            elif isinstance(value, (str, int, float)) and str(value).strip():
                setattr(merged, key, str(value).strip())
        return merged


@dataclass
class ExtractionState:
    """Durable state of one contribution conversation."""

    phase: str = "narration"
    turns: int = 0
    phase_turns: int = 0
    extracted: ExtractedCase = field(default_factory=ExtractedCase)
    messages: list[dict[str, str]] = field(default_factory=list)
    ready_to_submit: bool = False
    # The selected field and durable attempt counts keyed by question ID.
    gap_focus: str = ""
    field_attempts: dict[str, int] = field(default_factory=dict)
    # Unsent composer text is saved when the contributor chooses "resume later".
    # It is deliberately not extracted until they actually send it as an answer.
    draft_text: str = ""
    schema_version: int = 4
    closed_fields: dict[str, dict[str, Any]] = field(default_factory=dict)
    mode: str = "collecting"
    active_question_id: str = "overview"
    overview_complete: bool = False
    improving: bool = False
    fact_ledger: list[dict[str, Any]] = field(default_factory=list)
    field_statuses: dict[str, dict[str, Any]] = field(default_factory=dict)

    def completion_tracker(self) -> list[dict[str, Any]]:
        from app.contribution import evidence_tracker
        return evidence_tracker(self)

    def question_tracker(self) -> list[dict[str, Any]]:
        from app.contribution import question_tracker
        return question_tracker(self)

    def active_question(self) -> dict[str, Any] | None:
        return next((q for q in self.question_tracker() if q["id"] == self.active_question_id), None)


    def completeness(self) -> float:
        """Share of required fields captured, for the contributor's progress bar."""
        rows = [row for row in self.completion_tracker() if row["required_for_complete"]]
        return round(sum(row["status"] == "captured" for row in rows) / len(rows), 2)

    def sufficiency_score(self) -> float:
        return round(sum(row["credit"] for row in self.completion_tracker()), 2)

    def has_core_evidence(self) -> bool:
        rows = {row["key"]: row for row in self.completion_tracker()}
        return all(rows[key]["status"] == "captured" for key in SYNTHESIS_ANCHORS) and self.sufficiency_score() >= SYNTHESIS_THRESHOLD

    def discussion_progress(self) -> float:
        return round(len(set(self.closed_fields) & set(ExtractedCase.model_fields)) / len(ExtractedCase.model_fields), 4)

    def can_submit(self) -> bool:
        return self.has_core_evidence() and set(ExtractedCase.model_fields).issubset(self.closed_fields)

    def synthesis_draft(self) -> ExtractedCase:
        """Exclude unresolved contradictions/retractions from case generation."""
        draft = self.extracted.model_copy(deep=True)
        for key, info in self.field_statuses.items():
            if key in type(draft).model_fields and info.get("status") in ("unavailable", "conflict"):
                setattr(draft, key, [] if isinstance(getattr(draft, key), list) else "")
        return draft

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "closed_fields": self.closed_fields,
            "mode": self.mode,
            "active_question_id": self.active_question_id,
            "overview_complete": self.overview_complete,
            "improving": self.improving,
            "fact_ledger": self.fact_ledger,
            "field_statuses": self.field_statuses,
            "phase": self.phase,
            "turns": self.turns,
            "phase_turns": self.phase_turns,
            "extracted": self.extracted.model_dump(),
            "messages": self.messages,
            "ready_to_submit": self.ready_to_submit,
            "gap_focus": self.gap_focus,
            "field_attempts": self.field_attempts,
            "draft_text": self.draft_text,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExtractionState":
        state = cls(
            schema_version=4,
            closed_fields=dict(payload.get("closed_fields") or {}),
            mode=payload.get("mode", "collecting"),
            active_question_id=payload.get("active_question_id", "overview"),
            overview_complete=bool(payload.get("overview_complete", payload.get("turns", 0))),
            improving=bool(payload.get("improving", False)),
            fact_ledger=list(payload.get("fact_ledger") or []),
            field_statuses=dict(payload.get("field_statuses") or {}),
            phase=payload.get("phase", "narration"),
            turns=int(payload.get("turns", 0)),
            phase_turns=int(payload.get("phase_turns", 0)),
            extracted=ExtractedCase.model_validate(payload.get("extracted") or {}),
            messages=list(payload.get("messages") or []),
            ready_to_submit=bool(payload.get("ready_to_submit", False)),
            gap_focus=str(payload.get("gap_focus") or ""),
            field_attempts={
                str(key): int(value)
                for key, value in (payload.get("field_attempts") or {}).items()
            },
            draft_text=str(payload.get("draft_text") or ""),
        )

        from app.contribution import reconcile
        return reconcile(state, legacy=payload.get("schema_version", 1) < 4)


class LangChainCaseAuthor:
    """Compatibility entry point for the question-led contribution engine."""

    def __init__(self) -> None:
        from app.contribution import build_chains
        self._assessor, self._framer = build_chains()

    def opening_prompt(self) -> str:
        from app.contribution import OPENING
        return OPENING

    def respond(self, state: ExtractionState, message: str) -> ExtractionState:
        from app.contribution import respond
        return respond(self, state, message)


def create_case_author() -> LangChainCaseAuthor | None:
    """None when no provider key exists, matching how the rest of the app degrades."""
    if not os.getenv("OPENROUTER_API_KEY"):
        return None
    return LangChainCaseAuthor()
