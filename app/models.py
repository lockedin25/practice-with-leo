"""Core domain data models and schemas for MBB Case Prep V2.

Defines Pydantic models for case manifests, structured case essence,
facts packages, issue tree causal DAGs, conversation policies, and
full case packages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field


class CaseEssenceModel(BaseModel):
    """Structured learning essence and commercial mechanism behind a case."""

    core_mechanism: str = Field(
        ...,
        description="The fundamental economic, commercial, or operational mechanism driving the problem.",
    )
    what_the_case_wanted_to_test: str = Field(
        ...,
        description="The explicit commercial principle, problem-solving muscle, or business concept being tested.",
    )
    pivotal_insight: str = Field(
        ...,
        description="The breakthrough 'Aha!' moment or unit-economic insight that unlocks the case.",
    )
    common_traps: list[str] = Field(
        default_factory=list,
        description="2-3 specific red herrings, framework dumping traps, or superficial conclusions candidates fall into.",
    )
    takeaway_lesson: str = Field(
        ...,
        description="The durable management consulting mental model or strategic takeaway.",
    )
    suggested_readings: list[str] = Field(
        default_factory=list,
        description="Direct relative paths to relevant modules in knowledge_base/.",
    )


class CandidateOpeningModel(BaseModel):
    """Candidate-facing opening context and objective."""

    context: str = Field(..., description="Client background, context, and baseline situation.")
    objective: str = Field(..., description="Clear decision question and timeline.")
    opening_requirements: list[str] = Field(
        default_factory=list,
        description="Expected candidate behaviors in the opening turn.",
    )


class ObjectiveFunctionModel(BaseModel):
    """Private objective function and decision criteria."""

    primary_metric: str = Field(..., description="Primary metric evaluated (e.g. EBITDA margin, ROIC).")
    decision_question: str = Field(..., description="Core decision question to be answered.")
    time_horizon: str = Field(..., description="Target execution or evaluation time horizon.")
    expected_candidate_output: list[str] = Field(
        default_factory=list,
        description="Key deliverables expected in candidate synthesis.",
    )
    design_principle: str = Field(
        default="",
        description="Guiding case design and facilitation principle.",
    )


class FactItem(BaseModel):
    """Atomic fact with gated disclosure rules."""

    id: str = Field(..., description="Unique fact identifier (e.g. 'company.model', 'economics.cost_split').")
    domain: str = Field(..., description="Business domain (e.g. 'company', 'financials', 'economics', 'operations').")
    release_level: str = Field(
        ...,
        description="Disclosure level: 'opening', 'broad_context', 'sharp_question', 'hypothesis_backed', 'synthesis_support', 'interviewer_only'.",
    )
    content: str = Field(..., description="Verbatim factual disclosure text.")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Fact IDs that must be disclosed before this fact becomes eligible.",
    )
    candidate_purpose: str = Field(
        default="",
        description="Pedagogical purpose of this fact in candidate problem solving.",
    )
    question_examples: list[str] = Field(
        default_factory=list,
        description="Example candidate inquiries that unlock this fact.",
    )
    provenance: str = Field(
        default="source_derived",
        description="Source provenance of the fact.",
    )
    formula: str = Field(
        default="",
        description=(
            "For a derived fact, the arithmetic that produces it, in terms of the names in "
            "'depends_on'. Present so the case-world rule that derived facts are reproducible "
            "becomes machine-checkable instead of aspirational. Evaluated by app.expressions, "
            "never by a model."
        ),
    )
    depends_on: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Maps each name in 'formula' to the fact ID supplying its value. Separate from "
            "'dependencies', which gates disclosure order rather than arithmetic."
        ),
    )
    numeric_value: float | None = Field(
        default=None,
        description="The fact's value as a number, when it has one. Required for a formula input.",
    )


class QuantStep(BaseModel):
    """One calculation the case expects the candidate to perform.

    Modelled on how consulting math is actually graded rather than on arithmetic:
    deriving the approach and stating assumptions matter more than the digits, and
    an order-of-magnitude error is far worse than a small slip caught on a sanity
    check. Optional per case, permanently. A case with no quantitative surface is
    a valid case, not an incomplete one.
    """

    id: str = Field(..., description="Unique step identifier (e.g. 'quant.pharma-contribution').")
    intent: str = Field(..., description="What the candidate is expected to compute, in plain language.")
    kind: Literal[
        "market_sizing",
        "breakeven",
        "profitability",
        "growth",
        "unit_economics",
        "exhibit_read",
    ] = Field(default="unit_economics", description="The family of consulting math being tested.")
    release_level: str = Field(
        default="hypothesis_backed",
        description="When the interviewer may ask for this calculation, using the fact release ladder.",
    )
    inputs: dict[str, str] = Field(
        default_factory=dict,
        description="Maps each formula variable to the fact ID that supplies it.",
    )
    formula: str = Field(default="", description="The arithmetic, in terms of the input names.")
    expected_value: float | None = Field(default=None, description="The value the formula produces.")
    unit: str = Field(default="", description="Unit of the expected value, e.g. 'INR per kg'.")
    close_tolerance: float = Field(
        default=0.25,
        description="Relative band counted as a correct answer. Generous, because aggressive rounding is correct practice.",
    )
    magnitude_factor: float = Field(
        default=2.0,
        description="Factor within which an answer is still the right order of magnitude.",
    )
    graded_behaviours: list[str] = Field(
        default_factory=lambda: [
            "states_formula_before_computing",
            "names_assumptions_explicitly",
            "sanity_checks_plausibility",
            "states_commercial_so_what",
        ],
        description="Process behaviours scored alongside the number, and weighted above it.",
    )
    interviewer_behaviour: str = Field(
        default="Ask the candidate to set it up. Confirm or correct the setup. Never supply the arithmetic.",
        description="How the interviewer handles this step.",
    )


class QuantPackage(BaseModel):
    """Container for a case's quantitative steps. Absent for a qualitative case."""

    schema_version: str = Field(default="quant-v1")
    quant_steps: list[QuantStep] = Field(default_factory=list)


class ProvenanceModel(BaseModel):
    """Where a case came from, and how its contributor may be credited.

    Month precision on the interview date is deliberate. A full date plus a firm
    plus a round is close to identifying for someone in a live process.
    """

    source_type: Literal["authored", "interview_recall"] = Field(default="authored")
    firm: str | None = Field(default=None, description="Firm the case was asked at, when recalled.")
    round: int | None = Field(default=None, description="Interview round, when recalled.")
    geography: str | None = Field(default=None)
    interview_month: str | None = Field(
        default=None, description="Month precision only, as YYYY-MM. Never a full date."
    )
    contributor_id: str | None = Field(default=None)
    contributor_name: str | None = None
    contributed_at: str | None = None
    firm_tags: list[str] = Field(default_factory=list)
    metadata_source: str = "not_recorded"
    attribution_mode: Literal["anonymous", "pseudonymous", "public"] = Field(
        default="pseudonymous",
        description="Only 'public' contributors may ever be named on a public surface.",
    )
    embargo_until: str | None = Field(
        default=None,
        description=(
            "ISO date before which the case stays unpublished. Lets a candidate still in a live "
            "process contribute now and publish after their process closes."
        ),
    )


class FactsPackage(BaseModel):
    """Container for authored facts in a case package."""

    schema_version: str = Field(default="reservoir-facts-v1")
    facts: list[FactItem] = Field(default_factory=list)


class IssueTreeNode(BaseModel):
    """Node in the private causal issue DAG."""

    id: str = Field(..., description="Node identifier.")
    type: Literal["branch", "mechanism", "evidence", "diagnosis", "recommendation"] = Field(
        ...,
        description="Type of node in the causal issue hierarchy.",
    )
    label: str = Field(..., description="Human-readable node label.")
    status: str = Field(
        default="valid_branch",
        description="Status marker: 'valid_branch', 'bounded_branch', 'pivotal_test', 'hidden_target', 'synthesis'.",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Fact IDs or upstream node IDs supporting this node.",
    )
    conclusion: str = Field(
        default="",
        description="Synthesized analytical takeaway for this node.",
    )


class IssueTreeEdge(BaseModel):
    """Directed edge in the causal DAG."""

    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    relation: str = Field(default="investigate")

    model_config = {"populate_by_name": True}


class AcceptableRoute(BaseModel):
    """Valid path through the issue tree."""

    id: str
    sequence: list[str]
    interviewer_behaviour: str = ""


class RecoveryPolicy(BaseModel):
    """Guidance for redirecting stuck or wandering candidates."""

    maximum_unproductive_follow_ups: int = 2
    recovery_order: list[str] = Field(default_factory=list)


class IssueTreePackage(BaseModel):
    """Container for the private causal issue tree."""

    schema_version: str = Field(default="issue-tree-v1")
    visibility: str = Field(default="post_case_only")
    root: dict[str, Any] = Field(default_factory=dict)
    nodes: list[IssueTreeNode] = Field(default_factory=list)
    edges: list[IssueTreeEdge] = Field(default_factory=list)
    acceptable_routes: list[AcceptableRoute] = Field(default_factory=list)
    recovery_policy: RecoveryPolicy | None = None


class PhasePolicyItem(BaseModel):
    """Policy rules for an interview phase."""

    interviewer_goal: str
    reveal_levels: list[str] = Field(default_factory=list)
    expected_candidate_behaviours: list[str] = Field(default_factory=list)


class ConversationPolicyPackage(BaseModel):
    """Interviewer conversation policies and phase transition rules."""

    schema_version: str = Field(default="conversation-policy-v1")
    mode: str = Field(default="realistic")
    principles: list[str] = Field(default_factory=list)
    phase_policy: dict[str, PhasePolicyItem] = Field(default_factory=dict)
    generation_policy: list[str] = Field(default_factory=list)


class CaseManifest(BaseModel):
    """Complete authored case manifest loaded from case.yaml."""

    schema_version: str = Field(default="reservoir-v1")
    case_id: str
    title: str
    status: str = Field(default="approved")
    rights_status: str = Field(default="original")
    category: str
    industry: str
    difficulty: Literal["foundation", "intermediate", "advanced"] = Field(default="intermediate")
    # The candidate-facing origin axis. Deliberately not an institution: cases come
    # from a mix of sources and naming any one school on a public surface is both
    # inaccurate and not something the product should assert.
    source: Literal["curated", "community"] = Field(
        default="curated",
        description="'curated' for cases shipped with the product, 'community' for contributed ones.",
    )
    supported_durations: list[int] = Field(default_factory=lambda: [30])
    skills_tested: list[str] = Field(default_factory=list)
    candidate_opening: CandidateOpeningModel
    objective_function: ObjectiveFunctionModel
    case_essence: CaseEssenceModel
    provenance: ProvenanceModel | None = None
    session_contract: dict[str, Any] | None = None
    reservoir_files: list[str] = Field(default_factory=list)


class CasePackage(BaseModel):
    """In-memory bundle of all 5 files making up a complete case package."""

    manifest: CaseManifest
    facts: FactsPackage
    issue_tree: IssueTreePackage | None = None
    conversation_policy: ConversationPolicyPackage | None = None
    quant: QuantPackage | None = None
    validation_notes: str = ""
    package_dir: str = ""

    @property
    def case_id(self) -> str:
        return self.manifest.case_id

    @property
    def title(self) -> str:
        return self.manifest.title

    @property
    def category(self) -> str:
        return self.manifest.category

    @property
    def industry(self) -> str:
        return self.manifest.industry

    @property
    def difficulty(self) -> str:
        return self.manifest.difficulty

    @property
    def essence(self) -> CaseEssenceModel:
        return self.manifest.case_essence

    def get_hidden_diagnosis(self) -> FactItem | None:
        for fact in self.facts.facts:
            if fact.release_level == "interviewer_only" or "diagnosis" in fact.id.lower():
                return fact
        return None

    def get_candidate_facts(self) -> list[FactItem]:
        return [f for f in self.facts.facts if f.release_level != "interviewer_only"]
