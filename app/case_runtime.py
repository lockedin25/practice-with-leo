"""Generic, authoritative case-world state and disclosure validation.

An LLM decides candidate intent and proposes fact IDs. This module does not
classify language or search for keywords. It solely validates the proposed action
against the authored case's phase and dependency rules before facts are exposed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from app.personas import Persona


# The welcome/readiness exchange is not performance evidence. Two actual case
# turns is enough to make an end-of-practice score useful.
MIN_SUBSTANTIVE_TURNS = 2


@dataclass(frozen=True)
class Fact:
    id: str
    content: str
    domain: str
    release_level: str
    dependencies: tuple[str, ...] = ()
    candidate_purpose: str = ""
    question_examples: tuple[str, ...] = ()

    def director_fact(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "content": self.content,
            "candidate_purpose": self.candidate_purpose,
            "question_examples": self.question_examples,
        }


@dataclass(frozen=True)
class Phase:
    id: str
    interviewer_goal: str
    reveal_levels: tuple[str, ...]
    expected_candidate_behaviours: tuple[str, ...]


@dataclass(frozen=True)
class CaseWorld:
    id: str
    title: str
    category: str
    industry: str
    difficulty: str
    supported_durations: tuple[int, ...]
    skills_tested: tuple[str, ...]
    opening: str
    objective: str
    phases: tuple[Phase, ...]
    facts: tuple[Fact, ...]
    # Candidate-facing origin. Never an institution name: the library used to
    # surface which B-school a case came from, which the product does not want to
    # assert publicly and which is not accurate for a mixed-provenance corpus.
    source: str = "curated"
    # Monotonic per case_id. A live attempt pins the version it started on, so an
    # admin editing a published case cannot change the world under a candidate
    # mid-interview. Packages on disk are always version 1; only contributed cases
    # in the database ever go higher.
    version: int = 1
    contributor_label: str = "Curated collection"
    contributor_name: str | None = None
    contributed_at: str | None = None
    firm_tags: tuple[str, ...] = ()

    @classmethod
    def from_reservoir(cls, root: Path, case_id: str | None = None) -> "CaseWorld":
        """Load one authored reservoir for small tools and focused unit tests.

        The application itself uses :class:`CaseCatalogue`, which loads every
        playable reservoir. Keeping this helper makes it easy to validate one
        case in isolation without reintroducing case-specific application code.
        """
        catalogue = CaseCatalogue.from_reservoir(root)
        return catalogue.get(case_id or catalogue.default_case.id)

    @classmethod
    def _from_directory(cls, directory: Path, shared_policy: Path) -> "CaseWorld":
        """Compile one case directory into the runtime's immutable case model."""
        case_data = _load_yaml(directory / "case.yaml")
        facts_data = _load_yaml(directory / "facts.yaml")
        policy_path = directory / "conversation-policy.yaml"
        policy_data = _load_yaml(policy_path if policy_path.is_file() else shared_policy)
        return cls.from_mapping(case_data, facts_data, policy_data)

    @classmethod
    def from_mapping(
        cls,
        case_data: dict[str, Any],
        facts_data: dict[str, Any],
        policy_data: dict[str, Any],
        *,
        version: int = 1,
    ) -> "CaseWorld":
        """Compile already-parsed package data into a case world.

        Shared by the filesystem loader and the database loader so a contributed
        case is compiled by exactly the same code, and therefore obeys exactly the
        same disclosure rules, as one shipped in the repository.
        """
        from app.case_provenance import public_metadata
        metadata = public_metadata(case_data)
        opening = case_data["candidate_opening"]
        phases = tuple(
            Phase(
                id=phase_id,
                interviewer_goal=phase["interviewer_goal"],
                reveal_levels=tuple(phase["reveal_levels"]),
                expected_candidate_behaviours=tuple(phase.get("expected_candidate_behaviours", ())),
            )
            for phase_id, phase in policy_data["phase_policy"].items()
        )
        facts = tuple(
            Fact(
                id=item["id"],
                content=item["content"].strip(),
                domain=item["domain"],
                release_level=item["release_level"],
                dependencies=tuple(item.get("dependencies", ())),
                candidate_purpose=item.get("candidate_purpose", ""),
                question_examples=tuple(item.get("question_examples", ())),
            )
            for item in facts_data["facts"]
            if item["release_level"] != "interviewer_only"
        )
        return cls(
            id=case_data["case_id"],
            title=case_data["title"],
            category=case_data.get("category", "case interview"),
            industry=case_data.get("industry", "business"),
            difficulty=case_data.get("difficulty", "foundation"),
            supported_durations=tuple(case_data.get("supported_durations", (30,))),
            skills_tested=tuple(case_data.get("skills_tested", ("clarification", "tailored structure", "analysis", "synthesis"))),
            opening=opening["context"].strip() + " " + opening["objective"].strip(),
            objective=case_data["objective_function"]["decision_question"],
            phases=phases,
            facts=facts,
            source=_source_of(case_data),
            contributor_label=metadata["contributor_label"],
            contributor_name=metadata["contributor_name"],
            contributed_at=metadata["contributed_at"],
            firm_tags=tuple(metadata["firm_tags"]),
            version=int(case_data.get("version", version) or version),
        )

    @property
    def initial_phase(self) -> str:
        return self.phases[0].id

    def catalogue_item(self) -> dict[str, Any]:
        """Return only the metadata safe to show before an attempt begins."""
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.objective,
            "category": self.category,
            "industry": self.industry,
            "difficulty": self.difficulty,
            "source": self.source,
            "contributor_label": self.contributor_label,
            "contributor_name": self.contributor_name,
            "contributed_at": self.contributed_at,
            "firm_tags": list(self.firm_tags),
            "version": self.version,
            "supported_durations": self.supported_durations,
            "skills_tested": self.skills_tested,
            "phases": [phase.id for phase in self.phases],
        }

    def phase(self, phase_id: str) -> Phase:
        return next((phase for phase in self.phases if phase.id == phase_id), self.phases[0])

    def eligible_facts_for_director(
        self, phase_id: str, disclosed_ids: set[str], *, reveal_level_bonus: int = 0
    ) -> list[dict[str, Any]]:
        """Factual context the internal director may select during this phase."""
        return [
            fact.director_fact()
            for fact in self._eligible_facts(
                phase_id, disclosed_ids, reveal_level_bonus=reveal_level_bonus
            )
        ]

    def validate_fact_selection(
        self,
        selected_ids: list[str],
        phase_id: str,
        disclosed_ids: set[str],
        *,
        max_facts: int = 2,
        reveal_level_bonus: int = 0,
    ) -> list[Fact]:
        # A zero cap is a real instruction, not a missing argument: a withholding
        # persona that has not earned a release this turn must disclose nothing,
        # and slicing to [:0] is what enforces that on the authoritative side
        # rather than trusting the prompt to have refused.
        if max_facts <= 0:
            return []
        eligible = {
            fact.id: fact
            for fact in self._eligible_facts(
                phase_id, disclosed_ids, reveal_level_bonus=reveal_level_bonus
            )
        }
        # Preserve authored fact order and cap each turn, regardless of the LLM output.
        return [fact for fact in self.facts if fact.id in selected_ids and fact.id in eligible][:max_facts]

    def narrowest_eligible_fact(
        self, phase_id: str, disclosed_ids: set[str], *, reveal_level_bonus: int = 0
    ) -> Fact | None:
        """The most freely-given undisclosed fact available in this phase.

        Used by the anti-stonewall floor, which needs a fact to release without
        depending on the director having nominated one.
        """
        from app.personas import RELEASE_LEVEL_LADDER

        eligible = self._eligible_facts(
            phase_id, disclosed_ids, reveal_level_bonus=reveal_level_bonus
        )
        if not eligible:
            return None
        return min(
            eligible,
            key=lambda fact: (
                RELEASE_LEVEL_LADDER.index(fact.release_level)
                if fact.release_level in RELEASE_LEVEL_LADDER
                else len(RELEASE_LEVEL_LADDER),
                self.facts.index(fact),
            ),
        )

    def validate_phase_transition(self, current_phase: str, proposed_phase: str) -> str:
        phase_ids = [phase.id for phase in self.phases]
        if proposed_phase not in phase_ids:
            return current_phase
        current_index = phase_ids.index(current_phase)
        proposed_index = phase_ids.index(proposed_phase)
        # The director can hold its current phase or move a single authored phase forward.
        return proposed_phase if proposed_index in {current_index, current_index + 1} else current_phase

    def _eligible_facts(
        self, phase_id: str, disclosed_ids: set[str], *, reveal_level_bonus: int = 0
    ) -> list[Fact]:
        from app.personas import permitted_reveal_levels

        phase = self.phase(phase_id)
        permitted = (
            permitted_reveal_levels(phase.reveal_levels, reveal_level_bonus)
            if reveal_level_bonus
            else phase.reveal_levels
        )
        return [
            fact
            for fact in self.facts
            if fact.id not in disclosed_ids
            and fact.release_level in permitted
            and set(fact.dependencies).issubset(disclosed_ids)
        ]


@dataclass
class CaseCatalogue:
    """The process-wide registry of playable case worlds.

    Authored packages are still compiled from disk before requests are served, so
    a malformed one still fails at startup rather than at a candidate's first turn.
    What changed is that the registry is no longer frozen: contributed cases arrive
    from the database after start-up and must be able to join without a restart.

    Two indexes, for two different questions. ``cases`` answers "what should a
    candidate be offered now" and holds the latest published version of each case.
    ``versions`` answers "what exactly was this attempt started against" and keeps
    every version ever registered, because a live attempt is pinned and must keep
    resolving to its own world even after an admin publishes an edit.

    Individual :class:`CaseWorld` objects remain frozen. Mutability lives here, at
    the registry level, so a pinned attempt can never observe its own case change.
    """

    cases: dict[str, CaseWorld]
    versions: dict[tuple[str, int], CaseWorld] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for world in self.cases.values():
            self.versions.setdefault((world.id, world.version), world)

    @classmethod
    def from_reservoir(cls, root: Path) -> "CaseCatalogue":
        reservoir_root = root / "reservoir"
        exemplars_root = root / "corpus" / "exemplars"
        shared_policy = reservoir_root / "_shared-policy.yaml"

        case_directories: list[Path] = []
        if reservoir_root.is_dir():
            case_directories.extend(
                path
                for path in sorted(reservoir_root.iterdir())
                if path.is_dir() and not path.name.startswith("_") and (path / "case.yaml").is_file()
            )
        if exemplars_root.is_dir():
            for group_dir in sorted(exemplars_root.iterdir()):
                if group_dir.is_dir() and not group_dir.name.startswith("."):
                    for case_dir in sorted(group_dir.iterdir()):
                        if case_dir.is_dir() and (case_dir / "case.yaml").is_file():
                            case_directories.append(case_dir)

        if not case_directories:
            raise ValueError("No case reservoir was found")
        if not shared_policy.is_file():
            raise ValueError("Shared conversation policy is missing")

        worlds = [CaseWorld._from_directory(directory, shared_policy) for directory in case_directories]
        case_ids = [world.id for world in worlds]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Case IDs must be unique across the reservoir")
        return cls(cases={world.id: world for world in worlds})

    @property
    def default_case(self) -> CaseWorld:
        """Keep Meridian first when present; otherwise use stable ID ordering."""
        return self.cases.get("meridian-cold-chain-v1") or self.cases[sorted(self.cases)[0]]

    def get(self, case_id: str, version: int | None = None) -> CaseWorld:
        """Resolve a case, at a pinned version when one is given.

        An unpinned lookup returns the latest published version, which is what the
        library and a new attempt want. A pinned lookup is what an in-flight
        attempt uses, and it deliberately does not fall back to the latest: a
        silent substitution would resume the candidate into a different world and
        score them against evidence they were never shown.
        """
        if version is not None:
            try:
                return self.versions[(case_id, version)]
            except KeyError as error:
                raise ValueError(f"Case version not found: {case_id} v{version}") from error
        try:
            return self.cases[case_id]
        except KeyError as error:
            raise ValueError(f"Case reservoir not found: {case_id}") from error

    def register(self, world: CaseWorld) -> None:
        """Add or replace a case world, keeping every prior version resolvable.

        A lower version never displaces a higher one in the published index, so
        replaying an out-of-order batch from the database cannot roll the library
        backwards.
        """
        self.versions[(world.id, world.version)] = world
        current = self.cases.get(world.id)
        if current is None or world.version >= current.version:
            self.cases[world.id] = world

    def unregister(self, case_id: str) -> None:
        """Withdraw a case from the library without breaking in-flight attempts.

        Only the published index is touched. ``versions`` keeps its entries so an
        attempt already pinned to this case can still be resumed, scored and
        debriefed after an admin unpublishes it.
        """
        self.cases.pop(case_id, None)

    def catalogue_items(self) -> list[dict[str, Any]]:
        return [self.cases[case_id].catalogue_item() for case_id in sorted(self.cases)]


@dataclass
class InterviewSession:
    id: str
    case: CaseWorld
    mode: str
    stage: str = ""
    disclosed_ids: set[str] = field(default_factory=set)
    messages: list[dict[str, str]] = field(default_factory=list)
    candidate_turns: int = 0
    # Readiness remains in ``candidate_turns`` for transcript fidelity, but it
    # must not turn an early exit into scored performance.
    substantive_turns: int = 0
    # The welcome is deliberately separate from the authored case brief.  This
    # state is durable so a reload cannot accidentally start a case before the
    # candidate has explicitly opted in.
    case_started: bool = False
    # Set only by the LLM's structured turn decision after Leo has formally
    # concluded the interview. It is distinct from ``ended``: the candidate
    # still owns the explicit action that saves the attempt and opens debrief.
    ready_to_end: bool = False
    ended: bool = False
    disposition: str | None = None
    turn_results: dict[str, dict[str, object]] = field(default_factory=dict)
    # Persona disclosure budget. Durable, because a reload that reset these would
    # hand the candidate a free fact and quietly make every persona easier than
    # the one they chose.
    release_credits: float = 0.0
    consecutive_precise_misses: int = 0
    turns_since_release: int = 0

    def __post_init__(self) -> None:
        if not self.stage:
            self.stage = self.case.initial_phase

    @property
    def persona(self) -> "Persona":
        """The interviewer preset this attempt is being run under.

        ``mode`` already carried the three-value enum and was already persisted,
        so personas reuse it rather than introducing a second field that could
        disagree with it.
        """
        from app.personas import get

        return get(self.mode)

    def accrue_release_credit(self) -> None:
        """Bank this turn's disclosure allowance, up to the persona's cap."""
        persona = self.persona
        self.release_credits = min(
            persona.credit_cap, self.release_credits + persona.release_rate
        )

    def spend_release_credit(self) -> None:
        self.release_credits = max(0.0, self.release_credits - 1.0)
        self.consecutive_precise_misses = 0
        self.turns_since_release = 0

    def record_withheld_turn(self, *, counts_toward_floor: bool) -> None:
        """Track a turn that disclosed nothing, for the anti-stonewall floor.

        Only a question that named a relevant area counts. A candidate who keeps
        asking vague questions should keep getting nothing however long they
        persist, which is the whole point of the precision bar.
        """
        self.turns_since_release += 1
        if counts_toward_floor:
            self.consecutive_precise_misses += 1

    def record_candidate_turn(self, content: str, *, substantive: bool = True) -> None:
        self.candidate_turns += 1
        if substantive:
            self.substantive_turns += 1
        self.messages.append({"role": "candidate", "content": content})

    @property
    def default_end_disposition(self) -> str:
        return "scored" if self.substantive_turns >= MIN_SUBSTANTIVE_TURNS else "abandoned"

    def apply_director_decision(self, proposed_phase: str, facts: list[Fact]) -> None:
        self.stage = self.case.validate_phase_transition(self.stage, proposed_phase)
        self.disclosed_ids.update(fact.id for fact in facts)

    def add_interviewer_turn(self, content: str) -> None:
        self.messages.append({"role": "interviewer", "content": content})

    def candidate_view(self) -> dict[str, Any]:
        persona = self.persona
        return {
            "id": self.id,
            "case": self.case.catalogue_item(),
            "mode": self.mode,
            # The candidate must be able to see which interviewer produced their
            # score, so the label travels with the attempt rather than being
            # re-derived by the browser from the raw mode value.
            "persona": {
                "id": persona.id,
                "label": persona.label,
                "blurb": persona.blurb,
            },
            "stage": self.stage,
            "messages": self.messages,
            "substantive_turns": self.substantive_turns,
            "facts": [
                {"id": fact.id, "content": fact.content}
                for fact in self.case.facts
                if fact.id in self.disclosed_ids
            ],
            "case_started": self.case_started,
            "ready_to_end": self.ready_to_end,
            "ended": self.ended,
            "disposition": self.disposition,
        }

    def scorecard(self) -> dict[str, Any]:
        phase_ids = [phase.id for phase in self.case.phases]
        current_index = phase_ids.index(self.stage)
        return {
            "status": "complete" if current_index == len(phase_ids) - 1 else "partial",
            "dimensions": [
                {"name": "Clarification", "band": "Strong" if self.disclosed_ids else "Developing", "evidence": "Asked questions that released case context."},
                {"name": "Structure", "band": "Strong" if current_index >= 1 else "Developing", "evidence": "The director advanced the attempt beyond clarification."},
                {"name": "Analysis", "band": "Strong" if current_index >= 1 and len(self.disclosed_ids) >= 2 else "Developing", "evidence": "Tested case evidence through the active case phase."},
                {"name": "Synthesis", "band": "Strong" if current_index == len(phase_ids) - 1 else "Developing", "evidence": "Reached the final authored phase."},
            ],
            "next_drill": "State a testable hypothesis and the evidence you would request next.",
        }



def _source_of(case_data: dict[str, Any]) -> str:
    """Resolve the candidate-facing origin from a possibly legacy manifest.

    Authored packages predate this field and many still carry a ``school:`` value.
    Rather than rewrite 57 files to say the same thing, anything shipped with the
    product reads as ``curated``; only a contributed case is ``community``. The
    legacy value is not surfaced, which is the point of the change.
    """
    declared = str(case_data.get("source") or "").strip().lower()
    return declared if declared in {"curated", "community"} else "curated"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data
