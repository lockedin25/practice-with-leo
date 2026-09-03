"""Extract a runnable case out of somebody's memory of an interview.

The intelligence here comes from typing the target, not from writing a question
list. The agent's job each turn is to find the highest-value thing still missing
from the package schema and ask the one question most likely to get it.

**Five phases, open-ended first.** A form destroys the texture that makes a case
worth solving. Someone who walked out of an interview an hour ago wants to talk
about it, so the first phase does almost nothing but listen. Structure,
quantification and the hunt for the case's teeth come after, and only then is the
reconstruction read back for correction.

**Numbers are elicited as magnitudes, not figures.** Contributors do not remember
the numbers. They remember the direction, roughly the ratio, and which quantities
were in play. Asking for exact figures produces confident invention, which is
worse than an honest approximation, because the synthesis pass can close an
approximation into a consistent set and cannot detect a fabricated one.

**Submission is thresholded, not exhaustive.** The client frame, decision and
core mechanism must come from the contributor. Once those anchors plus enough
supporting texture reach the synthesis threshold, the case can be submitted and
the synthesis pass may complete missing pedagogy such as traps or the takeaway.
The conversation still asks for those details because recalled teeth are better
than generated ones, but it no longer makes perfect recall a prerequisite.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ExtractionUnavailable(RuntimeError):
    """The provider could not complete an extraction turn."""


# Ordered. The agent may hold a phase or advance one, never skip.
PHASES: tuple[str, ...] = ("narration", "structure", "quantification", "teeth", "playback")

PHASE_GOALS: dict[str, str] = {
    "narration": (
        "LISTEN. Ask broad, open questions and let them talk at length about the case they were "
        "given. Do not interrupt to fill fields, do not ask for structure, do not ask for numbers. "
        "Your only job is to get the whole story in their own words, including how it felt and "
        "where it went wrong. Stay here for at least three exchanges unless they clearly have "
        "nothing more to say."
    ),
    "structure": (
        "Now establish the frame: who the client was, what industry, what decision the interviewer "
        "actually wanted answered, over what horizon, and what the interviewer told them up front "
        "versus what they had to ask for. Ask only about things they have not already covered."
    ),
    "quantification": (
        "Establish which quantities were in play and roughly how they moved. Ask for direction and "
        "rough ratios, never for exact figures: 'roughly what share', 'did it double or go up a "
        "tenth', 'which was bigger'. Explicitly tell them an approximation is fine and that you "
        "would rather have an honest guess than a made-up precise number. If this case had no "
        "numbers in it at all, accept that and move on; plenty of real cases are qualitative."
    ),
    "teeth": (
        "This is the most important phase. Find what made the case hard. What was the underlying "
        "mechanism the interviewer was driving at? What was the moment it clicked, or should have? "
        "What did they say that the interviewer pushed back on? What is the obvious first answer "
        "that turns out to be wrong? Press here. A case without traps and a pivotal insight is not "
        "worth publishing, so do not leave this phase until you have them."
    ),
    "playback": (
        "Read the reconstructed case back in plain language: the client, the decision, the hidden "
        "mechanism, the traps. Ask them to correct anything wrong or missing. Then finish."
    ),
}

# The full-fidelity targets the conversation continues to chase. They are not all
# submission blockers: once the synthesis threshold is reached, the LLM may
# complete missing recoverable fields before the final package is validated.
REQUIRED_FIELDS: tuple[str, ...] = (
    "client_and_industry",
    "decision_question",
    "core_mechanism",
    "pivotal_insight",
    "common_traps",
)

# The minimum viable recollection. These must come from the contributor because
# synthesising any one of them would change which case they are contributing.
SYNTHESIS_ANCHORS: tuple[str, ...] = (
    "client_and_industry",
    "decision_question",
    "core_mechanism",
)

# The three anchors total 0.60, so at least one meaningful piece of texture is
# also required. Named constants keep the threshold easy to tune from conversion
# and reviewer-quality data later.
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
    "client_and_industry": "who the client was and what they do",
    "decision_question": "the decision the interviewer wanted you to reach",
    "core_mechanism": "what was actually driving the problem underneath",
    "pivotal_insight": "the moment the case clicked, or should have",
    "common_traps": "the wrong answers that look right at first",
}

# What the agent should actually say to chase each gap. Ordered questions rather
# than field descriptions, because the agent's failure mode is asking about the
# topic in the abstract instead of asking a question a person can answer.
FIELD_QUESTIONS: dict[str, str] = {
    "client_and_industry": (
        "Ask who the client was and what business they are in. Industry and rough size are "
        "enough; you never want the real company name."
    ),
    "decision_question": (
        "Ask what the interviewer actually wanted them to decide or explain by the end, and "
        "over what time horizon."
    ),
    "core_mechanism": (
        "Ask what was really going on underneath. Not the symptom, the cause: what was the "
        "actual economic or operational driver the interviewer was steering toward?"
    ),
    "pivotal_insight": (
        "Ask about the turning point. What was the thing that, once you saw it, made the rest "
        "of the case fall into place? If they never got there, ask what they realised afterwards."
    ),
    "common_traps": (
        "Ask what the obvious-but-wrong answer was. What did they or someone else say that "
        "sounded reasonable and turned out to be a dead end? If they can remember two, get both."
    ),
}

# After this many asks on the same field with nothing recorded, stop being polite
# about it and tell the contributor plainly why the case cannot be submitted
# without it.
ESCALATE_AFTER_ATTEMPTS = 2


def describe_missing(missing: list[str]) -> str:
    """Human-readable list of gaps, for anything a contributor will read."""
    labels = [FIELD_LABELS.get(name, name) for name in missing]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} and {labels[-1]}"

MINIMUM_TRAPS = 2
# The narration phase is the one that produces the texture, so it has a floor.
# There is deliberately no hard conversation ceiling: a limit can strand an
# incomplete case in a state with neither a next question nor a valid submit path.
MINIMUM_NARRATION_TURNS = 3


SHARP_GAP_QUESTIONS: dict[str, str] = {
    "client_and_industry": (
        "Before we go further, who was the client in generic terms, and what kind of business "
        "were they in?"
    ),
    "decision_question": (
        "What exact decision or explanation did the interviewer want you to reach by the end?"
    ),
    "core_mechanism": (
        "What was actually causing the problem underneath the headline symptom?"
    ),
    "pivotal_insight": (
        "What was the turning-point insight that made the case click, or that you realised only "
        "afterwards?"
    ),
    "common_traps": (
        "What were the plausible answers that looked right at first but turned out to be wrong? "
        "If you can remember two, please give me both."
    ),
}


def _is_substantive_question(message: str) -> bool:
    """Reject polite closing moves masquerading as the next interview turn."""
    normalised = " ".join(str(message or "").strip().lower().split())
    if "?" not in normalised:
        return False
    vague_closers = (
        "anything else?",
        "anything more?",
        "is that all?",
        "are we done?",
    )
    return not any(normalised.endswith(closer) for closer in vague_closers)


def enforce_conversation_state(state: "ExtractionState", proposed: str) -> str:
    """Return either a real next question or a genuine completed-state message.

    Model prose is not state. The extraction can say "thanks" while required
    fields are still empty, so the runtime repairs that reply before it reaches
    the transcript. This keeps every persisted state actionable: Leo is asking a
    question, or the contributor has enough evidence for synthesis and a Submit
    button.
    """
    missing = state.extracted.missing_required()
    can_synthesise = state.extracted.sufficient_for_synthesis()
    if can_synthesise and not _is_substantive_question(proposed):
        return (
            "There is enough here to build a strong case. You can submit the case now, or keep "
            "answering questions if you want the reconstruction to stay closer to the original."
        )

    if missing and not _is_substantive_question(proposed):
        return SHARP_GAP_QUESTIONS[missing[0]]

    if not missing and not _is_substantive_question(proposed):
        return (
            "I have the essential pieces. Before submission, does the reconstruction sound "
            "accurate, or is there anything specific I should correct?"
        )

    return proposed.strip()


class ExtractedCase(BaseModel):
    """Everything the agent has managed to get so far.

    Flat and plain-language on purpose. The contributor is describing a memory,
    not filling in a case package, and the synthesis pass is what turns this into
    the authored schema.
    """

    client_and_industry: str = Field(default="", description="Who the client was and what they do.")
    situation: str = Field(default="", description="The situation as presented at the start.")
    decision_question: str = Field(default="", description="The decision the interviewer wanted answered.")
    time_horizon: str = Field(default="", description="Time horizon, if one was stated.")
    primary_metric: str = Field(default="", description="The metric the case turned on.")
    given_upfront: list[str] = Field(default_factory=list, description="What the interviewer volunteered.")
    had_to_ask_for: list[str] = Field(default_factory=list, description="What the candidate had to extract.")
    quantities: list[str] = Field(
        default_factory=list,
        description="Quantities in play with rough magnitudes or directions, never invented precision.",
    )
    core_mechanism: str = Field(default="", description="The underlying economic or operational driver.")
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
            if not hasattr(merged, key):
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


class ExtractionTurn(BaseModel):
    """One move by the extraction agent."""

    next_question: str = Field(description="The single question to ask the contributor next.")
    fields_filled: dict[str, Any] = Field(
        default_factory=dict,
        description="Partial patch of ExtractedCase fields learned from the contributor's last message.",
    )
    phase: str = Field(
        default="narration",
        description="The phase to be in after this turn: narration, structure, quantification, teeth, or playback.",
    )
    blocking_gaps: list[str] = Field(
        default_factory=list, description="Required fields still missing."
    )
    ready_to_submit: bool = Field(
        default=False,
        description="True only after playback, when the contributor has confirmed the reconstruction.",
    )


@dataclass
class ExtractionState:
    """Durable state of one contribution conversation."""

    phase: str = "narration"
    turns: int = 0
    phase_turns: int = 0
    extracted: ExtractedCase = field(default_factory=ExtractedCase)
    messages: list[dict[str, str]] = field(default_factory=list)
    ready_to_submit: bool = False
    # Which gap the agent was told to chase last turn, and how many times each
    # field has been chased without anything being recorded. Durable, because a
    # contributor who reloads mid-conversation must not reset the escalation and
    # be asked the same question in the same gentle way indefinitely.
    gap_focus: str = ""
    field_attempts: dict[str, int] = field(default_factory=dict)
    # Unsent composer text is saved when the contributor chooses "resume later".
    # It is deliberately not extracted until they actually send it as an answer.
    draft_text: str = ""

    def completeness(self) -> float:
        """Share of required fields captured, for the contributor's progress bar."""
        missing = len(self.extracted.missing_required())
        return round((len(REQUIRED_FIELDS) - missing) / len(REQUIRED_FIELDS), 2)

    def sufficiency_score(self) -> float:
        return self.extracted.sufficiency_score()

    def can_submit(self) -> bool:
        return self.extracted.sufficient_for_synthesis()

    def next_gap(self) -> str | None:
        """The one field the agent should chase next.

        One at a time, in conversational order. Handing the agent five gaps at
        once is what produces a turn that asks about everything and lands nothing.
        """
        missing = self.extracted.missing_required()
        return missing[0] if missing else None

    def as_dict(self) -> dict[str, Any]:
        return {
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
        return cls(
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


def gap_instruction(state: ExtractionState) -> str:
    """Tell the agent exactly which gap to close, and how hard to push.

    Built in code rather than left to the agent's judgement. The agent's observed
    failure mode is to summarise what it has, declare itself finished, and leave
    required fields empty, which is how a contributor ends up at a Submit button
    that refuses them.
    """
    gap = state.next_gap()
    if gap is None:
        return (
            "Everything required has been captured. Read the reconstruction back and ask them "
            "to correct anything wrong."
        )

    attempts = state.field_attempts.get(gap, 0)
    question = FIELD_QUESTIONS.get(gap, f"Ask about {FIELD_LABELS.get(gap, gap)}.")
    instruction = (
        f"REQUIRED GAP: '{gap}'. This turn's question must be aimed squarely at it. {question} "
        f"When they answer, you MUST record what they said in fields_filled under the key "
        f"'{gap}'. Recording it is not optional: an answer you do not record is an answer lost, "
        f"and the reconstruction will lose useful fidelity."
    )
    if attempts >= ESCALATE_AFTER_ATTEMPTS:
        instruction += (
            f" You have already asked about this {attempts} times without capturing an answer. "
            "Stop being indirect. Say in one sentence what you specifically need and ask again; "
            "the case cannot be published without this. "
            "If they truly do not remember and the synthesis threshold has been reached, remind "
            "them that they may submit and let Leo complete the remaining detail."
        )
    return instruction


def advance_phase(state: ExtractionState, proposed: str) -> str:
    """Validate a phase transition in code rather than trusting the model.

    Two rules the prompt cannot be relied on to keep. Narration has a floor,
    because an agent eager to make progress will otherwise cut short the one phase
    that produces the texture a form cannot. And the teeth phase cannot be left
    until the minimum synthesis threshold is real.
    """
    if proposed not in PHASES:
        return state.phase
    current_index = PHASES.index(state.phase)
    proposed_index = PHASES.index(proposed)
    if proposed_index < current_index:
        return state.phase
    if proposed_index > current_index + 1:
        proposed_index = current_index + 1

    if state.phase == "narration" and proposed_index > current_index:
        if state.phase_turns < MINIMUM_NARRATION_TURNS:
            return state.phase
    if state.phase == "teeth" and proposed_index > current_index:
        if not state.extracted.sufficient_for_synthesis():
            return state.phase
    return PHASES[proposed_index]


class LangChainCaseAuthor:
    """Schema-driven extraction over a normal chat or voice turn loop."""

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
            max_tokens=COMPLETION_TOKENS,
            model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6"),
            temperature=0.4,
            max_retries=2,
            model_kwargs={"models": fallback_models} if fallback_models else {},
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are helping someone reconstruct a consulting case interview they sat, so that "
                    "other candidates can practise it. You are warm, curious and genuinely interested "
                    "in their experience. This is a conversation, not a form, and it can take as long "
                    "as it needs to.\n\n"
                    "Ask exactly one question per turn. Never ask two things at once. Reference what "
                    "they just said so it feels like listening rather than interrogation.\n\n"
                    "Never invent case content. Everything in fields_filled must come from what the "
                    "contributor actually said. If they are unsure, record the uncertainty rather than "
                    "resolving it for them.\n\n"
                    "Never ask for a real company name, a person's name, or any contact detail. If they "
                    "volunteer one, do not record it: the published case is re-skinned, so those details "
                    "are not needed and must not be stored.\n\n"
                    "Be pushy about substance and never about pace. If an answer is vague on something "
                    "that matters, ask again from a different angle rather than accepting it and moving "
                    "on. It is much better to spend three extra turns getting the real mechanism than to "
                    "finish quickly with a hollow case.\n\n"
                    "RECORD WHAT YOU ARE TOLD. Every turn, put what the contributor just told you into "
                    "fields_filled under the matching key. Never summarise an answer back to them without "
                    "also recording it: a summary is not storage, and an unrecorded answer silently blocks "
                    "them from submitting later.\n\n"
                    "Never claim the original case has been fully reconstructed while a gap remains. "
                    "Once the synthesis threshold below is reached, you may instead say there is enough "
                    "to build a strong case and offer the contributor a choice: submit now, or keep "
                    "answering to improve fidelity.\n\n"
                    "Set ready_to_submit true when the synthesis threshold is reached and the contributor "
                    "signals that they want to finish, including during playback.",
                ),
                (
                    "human",
                    "Current phase: {phase}\n"
                    "Phase goal: {phase_goal}\n"
                    "Turns in this phase: {phase_turns}\n"
                    "Total turns so far: {turns}\n"
                    "Synthesis threshold reached: {can_submit}\n"
                    "Required fields still missing: {missing}\n"
                    "Gap instruction: {gap_instruction}\n"
                    "What has been captured so far: {captured}\n"
                    "Recent conversation:\n{history}\n"
                    "Contributor's latest message: {message}",
                ),
            ]
        )
        self._chain = prompt | model.with_structured_output(ExtractionTurn)

    def opening_prompt(self) -> str:
        """The first thing the contributor sees. Deliberately wide open."""
        return (
            "Thanks for doing this. Take your time and just talk me through the case you were "
            "given, from the top. What was the situation they put in front of you, and how did "
            "the conversation go?"
        )

    def respond(self, state: ExtractionState, message: str) -> ExtractionState:
        """Advance one extraction turn and return the updated state."""
        state.messages.append({"role": "contributor", "content": message})
        state.draft_text = ""
        state.turns += 1
        try:
            turn = self._chain.invoke(
                {
                    "phase": state.phase,
                    "phase_goal": PHASE_GOALS[state.phase],
                    "phase_turns": state.phase_turns,
                    "turns": state.turns,
                    "can_submit": state.can_submit(),
                    "missing": describe_missing(state.extracted.missing_required()) or "none",
                    "gap_instruction": gap_instruction(state),
                    "captured": json.dumps(state.extracted.model_dump(), indent=1),
                    "history": _render(state.messages[-8:-1]) or "Nothing yet.",
                    "message": message,
                }
            )
        except Exception as error:
            logger.exception("Extraction turn failed at phase %s", state.phase)
            # Roll the unserved turn back so a retry does not double-count it or
            # leave a contributor message with no reply beside it.
            state.messages.pop()
            state.turns -= 1
            raise ExtractionUnavailable("The extraction agent could not complete this turn.") from error

        # Record whether the gap we chased actually landed, before the merge is
        # folded in, so an ask that produced nothing escalates next turn instead
        # of repeating identically forever.
        chased = state.gap_focus
        state.extracted = state.extracted.merge(turn.fields_filled)
        if chased and chased in state.extracted.missing_required():
            state.field_attempts[chased] = state.field_attempts.get(chased, 0) + 1
        state.gap_focus = state.next_gap() or ""
        previous_phase = state.phase
        state.phase = advance_phase(state, turn.phase)
        state.phase_turns = 0 if state.phase != previous_phase else state.phase_turns + 1
        # The model may recommend finishing, but only the weighted runtime gate
        # can make that recommendation actionable. The UI separately exposes
        # submission as soon as this same threshold is reached.
        state.ready_to_submit = bool(turn.ready_to_submit and state.can_submit())
        state.messages.append(
            {"role": "agent", "content": enforce_conversation_state(state, turn.next_question)}
        )
        return state


def _render(messages: list[dict[str, str]]) -> str:
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in messages)


def create_case_author() -> LangChainCaseAuthor | None:
    """None when no provider key exists, matching how the rest of the app degrades."""
    if not os.getenv("OPENROUTER_API_KEY"):
        return None
    return LangChainCaseAuthor()
