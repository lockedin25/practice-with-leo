"""Generic, authoritative case-world state and disclosure validation.

An LLM decides candidate intent and proposes fact IDs. This module does not
classify language or search for keywords. It solely validates the proposed action
against the authored case's phase and dependency rules before facts are exposed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


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
    school: str = "MBB Core"

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
            school=case_data.get("school") or "MBB Core",
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
            "school": self.school,
            "supported_durations": self.supported_durations,
            "skills_tested": self.skills_tested,
            "phases": [phase.id for phase in self.phases],
        }

    def phase(self, phase_id: str) -> Phase:
        return next((phase for phase in self.phases if phase.id == phase_id), self.phases[0])

    def eligible_facts_for_director(
        self, phase_id: str, disclosed_ids: set[str]
    ) -> list[dict[str, Any]]:
        """Factual context the internal director may select during this phase."""
        return [fact.director_fact() for fact in self._eligible_facts(phase_id, disclosed_ids)]

    def validate_fact_selection(
        self,
        selected_ids: list[str],
        phase_id: str,
        disclosed_ids: set[str],
        *,
        max_facts: int = 2,
    ) -> list[Fact]:
        eligible = {fact.id: fact for fact in self._eligible_facts(phase_id, disclosed_ids)}
        # Preserve authored fact order and cap each turn, regardless of the LLM output.
        return [fact for fact in self.facts if fact.id in selected_ids and fact.id in eligible][:max_facts]

    def validate_phase_transition(self, current_phase: str, proposed_phase: str) -> str:
        phase_ids = [phase.id for phase in self.phases]
        if proposed_phase not in phase_ids:
            return current_phase
        current_index = phase_ids.index(current_phase)
        proposed_index = phase_ids.index(proposed_phase)
        # The director can hold its current phase or move a single authored phase forward.
        return proposed_phase if proposed_index in {current_index, current_index + 1} else current_phase

    def _eligible_facts(self, phase_id: str, disclosed_ids: set[str]) -> list[Fact]:
        phase = self.phase(phase_id)
        return [
            fact
            for fact in self.facts
            if fact.id not in disclosed_ids
            and fact.release_level in phase.reveal_levels
            and set(fact.dependencies).issubset(disclosed_ids)
        ]


@dataclass(frozen=True)
class CaseCatalogue:
    """The immutable, process-wide catalogue of case worlds.

    A catalogue is deliberately built before requests are served. This catches
    malformed authoring packages at startup and lets an attempt stay pinned to
    the exact case version it started with.
    """

    cases: dict[str, CaseWorld]

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
            for school_dir in sorted(exemplars_root.iterdir()):
                if school_dir.is_dir() and not school_dir.name.startswith("."):
                    for case_dir in sorted(school_dir.iterdir()):
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

    def get(self, case_id: str) -> CaseWorld:
        try:
            return self.cases[case_id]
        except KeyError as error:
            raise ValueError(f"Case reservoir not found: {case_id}") from error

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
    # The welcome is deliberately separate from the authored case brief.  This
    # state is durable so a reload cannot accidentally start a case before the
    # candidate has explicitly opted in.
    case_started: bool = False
    # Set only by the LLM's structured turn decision after Leo has formally
    # concluded the interview. It is distinct from ``ended``: the candidate
    # still owns the explicit action that saves the attempt and opens debrief.
    ready_to_end: bool = False
    ended: bool = False
    turn_results: dict[str, dict[str, object]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.stage:
            self.stage = self.case.initial_phase

    def record_candidate_turn(self, content: str) -> None:
        self.candidate_turns += 1
        self.messages.append({"role": "candidate", "content": content})

    def apply_director_decision(self, proposed_phase: str, facts: list[Fact]) -> None:
        self.stage = self.case.validate_phase_transition(self.stage, proposed_phase)
        self.disclosed_ids.update(fact.id for fact in facts)

    def add_interviewer_turn(self, content: str) -> None:
        self.messages.append({"role": "interviewer", "content": content})

    def candidate_view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case": self.case.catalogue_item(),
            "mode": self.mode,
            "stage": self.stage,
            "messages": self.messages,
            "facts": [
                {"id": fact.id, "content": fact.content}
                for fact in self.case.facts
                if fact.id in self.disclosed_ids
            ],
            "case_started": self.case_started,
            "ready_to_end": self.ready_to_end,
            "ended": self.ended,
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


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data
