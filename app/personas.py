"""Interviewer personas: how hard a fact is to extract, and how it feels to ask.

Two independent dials, not one difficulty slider. A brusque interviewer who
answers every question directly is as real as a warm one who tells you almost
nothing, and collapsing those into a single "difficulty" loses the distinction
that makes practice transfer. So ``disclosure_regime`` governs how hard evidence
is to earn and ``demeanour`` governs tone, and a persona is a named preset over
the pair.

**Why a release budget rather than a per-turn cap.** The target rates are one fact
per turn, one per two to three turns, and one per five to six turns. A per-turn
maximum cannot express a rate below one, so each candidate turn accrues credits
and a release spends one. Credits bank up to a small cap, which is what stops a
patient candidate from converting six silent turns into a data dump.

**Why a precision bar on top of the budget.** A pure timer produces an
interviewer that stonewalls a perfectly targeted question, which reads as a broken
product rather than a hard one. Real interviewers withhold from *vague* questions,
not from good ones. So the director grades how targeted the question was and the
runtime decides whether that clears this persona's bar. A genuinely sharp question
lands early even against the Skeptic; a loose one earns nothing even when credits
are available.

**Why an anti-stonewall floor.** Precision grading is a judgement and will
sometimes be wrong. Without a floor, a run of misgraded good questions leaves the
candidate facing a wall with no way through, which is indistinguishable from a
bug. After a persona-specific number of consecutive well-aimed questions that
earned nothing, the narrowest eligible fact is released regardless of budget.
"""

from __future__ import annotations

from dataclasses import dataclass


# Ordered from most freely given to most earned. Used to widen what a phase will
# release for a generous persona.
RELEASE_LEVEL_LADDER: tuple[str, ...] = (
    "opening",
    "broad_context",
    "sharp_question",
    "hypothesis_backed",
    "synthesis_support",
)

# How targeted the candidate's question was, as graded by the director.
PRECISION_ORDER: dict[str, int] = {"vague": 0, "partial": 1, "targeted": 2}

DEFAULT_PERSONA_ID = "realistic"


@dataclass(frozen=True)
class Persona:
    """One preset over the disclosure and demeanour dials.

    ``id`` reuses the values already validated on ``StartAttemptRequest.mode`` and
    already persisted in the attempt payload, so adding personas needs no new
    session field and no store migration.
    """

    id: str
    label: str
    blurb: str
    disclosure_regime: str
    demeanour: str
    # Credits accrued per candidate turn. 1.0 is one fact per turn.
    release_rate: float
    # Maximum banked credits. This must sit above 1.0, because clamping accrual at
    # exactly one credit silently discards the fractional remainder and turns a
    # rate of 0.4 into a fact every three turns rather than every two and a half.
    # It stays small so a patient candidate cannot bank a long silence into a
    # windfall, and ``max_facts_per_turn`` is what actually caps a single turn.
    credit_cap: float
    # Minimum question precision that may spend a credit.
    precision_bar: str
    # Consecutive well-aimed questions that earned nothing before the floor fires.
    stonewall_floor: int
    # Extra ladder levels a phase will release beyond those it authored. Only ever
    # widens. Narrowing would risk making an authored fact unreachable in a phase,
    # and difficulty is already carried by the budget and the precision bar.
    reveal_level_bonus: int
    max_facts_per_turn: int
    disclosure_policy: str
    pushback_policy: str
    demeanour_policy: str


COACH = Persona(
    id="coached",
    label="The Coach",
    blurb="Supportive. Answers readily, signposts the path, and helps you recover when you stall.",
    disclosure_regime="generous",
    demeanour="warm",
    release_rate=1.0,
    credit_cap=2.0,
    precision_bar="vague",
    stonewall_floor=1,
    reveal_level_bonus=1,
    max_facts_per_turn=1,
    disclosure_policy=(
        "GENEROUS DISCLOSURE. Answer any question that is even loosely relevant with the single "
        "most useful eligible fact. If the candidate is drifting, name the area worth examining "
        "next. If they stall for one turn, give them the narrowest fact that unblocks them rather "
        "than asking again."
    ),
    pushback_policy=(
        "MINIMAL PUSHBACK. Challenge only a claim that is actually wrong, and when you do, point "
        "at the specific evidence that contradicts it rather than asking them to find it."
    ),
    demeanour_policy=(
        "Warm and encouraging. Acknowledge a good point briefly before answering. Never sarcastic, "
        "never impatient. You want this candidate to succeed and it shows."
    ),
)

OPERATOR = Persona(
    id="realistic",
    label="The Operator",
    blurb="Neutral and professional. Answers exactly what you asked, nothing more. One challenge per phase.",
    disclosure_regime="neutral",
    demeanour="neutral",
    release_rate=0.4,
    credit_cap=2.0,
    precision_bar="partial",
    stonewall_floor=3,
    reveal_level_bonus=0,
    max_facts_per_turn=1,
    disclosure_policy=(
        "NEUTRAL DISCLOSURE. Answer a question that names what it wants. Do not volunteer adjacent "
        "context, and do not confirm a direction the candidate has not argued for. If the question "
        "is broad, ask them to narrow it before you answer."
    ),
    pushback_policy=(
        "MEASURED PUSHBACK. Challenge roughly one substantive claim per phase, whether or not it is "
        "wrong, and see whether the candidate defends it with evidence or abandons it."
    ),
    demeanour_policy=(
        "Neutral, precise and professional. Do not praise, do not reassure, do not editorialise. "
        "State facts plainly and move on."
    ),
)

SKEPTIC = Persona(
    id="pressure",
    label="The Skeptic",
    blurb="Demanding. Gives almost nothing away, challenges everything, and lets you walk into dead ends.",
    disclosure_regime="withholding",
    demeanour="clipped",
    release_rate=0.18,
    credit_cap=2.0,
    precision_bar="targeted",
    stonewall_floor=6,
    reveal_level_bonus=0,
    max_facts_per_turn=1,
    disclosure_policy=(
        "WITHHOLDING DISCLOSURE. Release evidence only for a question that names the exact quantity, "
        "segment or driver it wants and implies why it matters. For anything looser, turn it back: "
        "ask what they expect to find and why, or ask them to commit to a hypothesis first. Do not "
        "signpost. Do not confirm that a branch is worth pursuing. If they are heading somewhere "
        "unproductive, let them go and let them discover it."
    ),
    pushback_policy=(
        "HEAVY PUSHBACK. Challenge substantive claims whether or not they are correct, because the "
        "point is to test whether the position is defensible. Never reveal which it was. Watch for "
        "the candidate folding immediately or restating without engaging, and keep the pressure on."
    ),
    demeanour_policy=(
        "Clipped and impatient. Short sentences. No praise, no reassurance, no softening. You are "
        "unimpressed by default and you do not pretend otherwise. Stay professional: cold is the "
        "register, not rude, and never demeaning about the person."
    ),
)

PERSONAS: dict[str, Persona] = {persona.id: persona for persona in (COACH, OPERATOR, SKEPTIC)}

# Presentation order, easiest first, for the picker.
PERSONA_ORDER: tuple[str, ...] = (COACH.id, OPERATOR.id, SKEPTIC.id)


def get(persona_id: str | None) -> Persona:
    """Resolve a persona, falling back to the neutral default.

    An unknown value resolves rather than raising because an attempt persisted
    before a persona was retired must still be replayable and still receive a
    debrief.
    """
    return PERSONAS.get(persona_id or DEFAULT_PERSONA_ID, OPERATOR)


def catalogue() -> list[dict[str, object]]:
    """Candidate-safe persona list for the picker."""
    return [
        {
            "id": persona.id,
            "label": persona.label,
            "blurb": persona.blurb,
            "disclosure_regime": persona.disclosure_regime,
            "demeanour": persona.demeanour,
        }
        for persona in (PERSONAS[persona_id] for persona_id in PERSONA_ORDER)
    ]


def permitted_reveal_levels(
    authored_levels: tuple[str, ...] | list[str], bonus: int
) -> tuple[str, ...]:
    """Widen a phase's authored reveal levels by ``bonus`` steps up the ladder.

    Only ever adds. A persona that narrowed the set could strand an authored fact
    whose level appears in no other phase, turning a difficulty setting into an
    unreachable-content bug.
    """
    permitted = list(authored_levels)
    if bonus <= 0:
        return tuple(permitted)
    ladder_positions = [
        RELEASE_LEVEL_LADDER.index(level)
        for level in permitted
        if level in RELEASE_LEVEL_LADDER
    ]
    if not ladder_positions:
        return tuple(permitted)
    highest = max(ladder_positions)
    for step in range(1, bonus + 1):
        candidate_index = highest + step
        if candidate_index < len(RELEASE_LEVEL_LADDER):
            level = RELEASE_LEVEL_LADDER[candidate_index]
            if level not in permitted:
                permitted.append(level)
    return tuple(permitted)


def clears_precision_bar(precision: str, persona: Persona) -> bool:
    """Whether a question this targeted may spend a release credit."""
    return PRECISION_ORDER.get(precision, 0) >= PRECISION_ORDER[persona.precision_bar]


# A question at or above this grade counts as the candidate genuinely trying, even
# when it falls short of a demanding persona's bar.
FLOOR_CREDIT_PRECISION = "partial"


def counts_toward_stonewall_floor(precision: str) -> bool:
    """Whether a turn that disclosed nothing should count toward the floor.

    Deliberately a lower threshold than the persona's own bar. Counting only
    bar-clearing questions would make the floor useless: those are exactly the
    turns the release budget is intentionally withholding, so the counter would
    reset on every disclosure and never reach the floor. The stonewall this
    guards against is a candidate asking reasonable, area-naming questions that
    keep landing just under a demanding bar and receiving nothing at all.

    A vague question still earns nothing, however often it is repeated, so the
    floor cannot be farmed by persistence alone.
    """
    return PRECISION_ORDER.get(precision, 0) >= PRECISION_ORDER[FLOOR_CREDIT_PRECISION]


@dataclass(frozen=True)
class Allowance:
    """What this persona could disclose this turn, decided before the LLM runs."""

    budget_available: bool
    floor_reached: bool
    brief: str


@dataclass(frozen=True)
class Release:
    """What this persona will actually disclose, decided after the LLM runs."""

    max_facts: int
    question_was_precise: bool
    # Whether this turn, if it disclosed nothing, should advance the floor counter.
    counts_toward_floor: bool
    forced_by_floor: bool


def allowance_for(persona: Persona, credits: float, consecutive_precise_misses: int) -> Allowance:
    """Compute the pre-turn disclosure allowance and the brief describing it.

    Separate from :func:`resolve_release` because the director needs to be told
    what it may do before it answers, while the precision grade that decides
    whether it actually may only exists afterwards.
    """
    budget_available = credits >= 1.0
    floor_reached = consecutive_precise_misses >= persona.stonewall_floor
    if floor_reached:
        brief = (
            "The candidate has now asked several well-aimed questions without receiving anything. "
            "Disclose the single narrowest fact that helps them, then continue in persona."
        )
    elif budget_available:
        brief = (
            "You may disclose at most one fact this turn if the question clears the persona's "
            "precision bar."
        )
    else:
        brief = (
            "You have no disclosure allowance this turn. Nominate no facts and respond within the "
            "persona policy instead: turn the question back, or ask for a hypothesis."
        )
    return Allowance(budget_available=budget_available, floor_reached=floor_reached, brief=brief)


def resolve_release(
    persona: Persona,
    allowance: Allowance,
    *,
    precision: str,
    is_early_precision_turn: bool,
) -> Release:
    """Decide how many facts may be disclosed, from the persona and the grade.

    This is the authoritative gate. The prompt is told the allowance as context,
    but the cap returned here is what the runtime enforces, so a model that
    over-nominates or ignores its policy still cannot widen the disclosure the
    candidate chose.
    """
    question_was_precise = clears_precision_bar(precision, persona)
    may_release = (question_was_precise and allowance.budget_available) or allowance.floor_reached
    toward_floor = counts_toward_stonewall_floor(precision)
    if not may_release:
        return Release(
            max_facts=0,
            question_was_precise=question_was_precise,
            counts_toward_floor=toward_floor,
            forced_by_floor=False,
        )
    cap = min(persona.max_facts_per_turn, 1 if is_early_precision_turn else 2)
    return Release(
        max_facts=cap,
        question_was_precise=question_was_precise,
        counts_toward_floor=toward_floor,
        forced_by_floor=allowance.floor_reached and not (question_was_precise and allowance.budget_available),
    )
