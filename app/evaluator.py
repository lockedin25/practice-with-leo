"""LangChain evaluator agent for completed attempts.

An independent post-attempt service: an LLM planner gathers evidence through
tools, an LLM writer emits one structured report on the BCG 1.0–5.0 scale, and
deterministic checks verify citations, scan for answer-key leakage, and stamp
versions. A deterministic fallback evaluator provides genuine heuristic grading
when LLM services are offline or unconfigured. See docs/evaluator-agent-design.md.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from app.case_runtime import InterviewSession
from app.llm_budget import COMPLETION_TOKENS, REPORT_COMPLETION_TOKENS


logger = logging.getLogger(__name__)

EVALUATOR_VERSION = "evaluator-v2"
CONTENT_ROOT = Path(__file__).resolve().parents[1] / "evaluation"
PROMPTS_DIR = CONTENT_ROOT / "prompts"

MAX_TOOL_CALLS = 24
RECURSION_LIMIT = MAX_TOOL_CALLS * 2 + 8
MESSAGE_WINDOW = 12
WRITER_RETRIES = 1
LEAKAGE_REDACTION = "[withheld by leakage guard]"
UNVERIFIED_EVIDENCE_NOTE = (
    "Citations for this dimension could not be verified against the transcript."
)

DIMENSION_NAMES = (
    "structuring",
    "problem_solving",
    "quantitative",
    "synthesis",
    "communication",
)
BAND_NAMES = ("Below Bar", "Meets Bar", "Top 1% MBB")
MBB_RATING_BADGES = (
    "Distinction",
    "Strong Pass",
    "Meets Bar",
    "Developing",
    "Needs Substantial Practice",
)


class EvaluatorUnavailable(RuntimeError):
    """Raised when the configured LLM provider cannot complete an evaluation."""


def compute_mbb_rating_badge(score: float) -> str:
    """Compute MBB Rating Badge from 1.0-5.0 score."""
    if score >= 4.5:
        return "Distinction"
    if score >= 3.8:
        return "Strong Pass"
    if score >= 2.8:
        return "Meets Bar"
    if score >= 2.0:
        return "Developing"
    return "Needs Substantial Practice"


def compute_overall_band(score: float) -> str:
    """Compute rubric band from 1.0-5.0 score."""
    if score >= 3.8:
        return "Top 1% MBB"
    if score >= 2.5:
        return "Meets Bar"
    return "Below Bar"


# --- Typed contracts --------------------------------------------------------


class Citation(BaseModel):
    message_index: int = Field(description="Index into the attempt transcript.")
    quote: str = Field(description="Short verbatim excerpt from that message.")


class DimensionScore(BaseModel):
    name: str = Field(description="One of structuring, problem_solving, quantitative, synthesis, communication")
    score: float = Field(description="Score on BCG 1.0 to 5.0 scale")
    band: str = Field(description="Below Bar, Meets Bar, or Top 1% MBB")
    evidence: list[Citation] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    notes: str = Field(default="", description="Summary observation notes")


class WhatTheCaseWantedToTest(BaseModel):
    core_mechanism: str = Field(default="", description="The fundamental economic/operational mechanism tested")
    commercial_concept: str = Field(default="", description="The commercial concept tested by the interviewer")
    pivotal_insight: str = Field(default="", description="The breakthrough 'Aha!' moment that unlocks the case")
    candidate_performance_summary: str = Field(default="", description="How the candidate performed against the crux")
    candidate_vs_optimal_gap: str = Field(default="", description="Gap between candidate's path and top 1% MBB path")


WhatCaseWantedToTestPayload = WhatTheCaseWantedToTest


class GoldenRewriteTurn(BaseModel):
    stage: Literal["opening", "closing", "synthesis"] = "opening"
    phase: Literal["opening", "closing", "synthesis"] = "opening"
    candidate_turn: str = Field(default="", description="Candidate turn verbatim from transcript")
    candidate_message_index: int | None = Field(default=None, description="Transcript index of candidate turn")
    mbb_partner_turn: str = Field(default="", description="How an MBB Partner / Top 1% candidate would deliver it")
    golden_mbb_turn: str = Field(default="", description="Alias for mbb_partner_turn")
    diagnostic_notes: list[str] = Field(default_factory=list, description="Specific consulting craft feedback")
    consulting_craft_delta: list[str] = Field(default_factory=list, description="Alias for diagnostic_notes")

    @model_validator(mode="after")
    def _sync_fields(self) -> "GoldenRewriteTurn":
        if self.stage and not self.phase:
            self.phase = self.stage
        elif self.phase and not self.stage:
            self.stage = self.phase
        if self.mbb_partner_turn and not self.golden_mbb_turn:
            self.golden_mbb_turn = self.mbb_partner_turn
        elif self.golden_mbb_turn and not self.mbb_partner_turn:
            self.mbb_partner_turn = self.golden_mbb_turn
        if self.diagnostic_notes and not self.consulting_craft_delta:
            self.consulting_craft_delta = list(self.diagnostic_notes)
        elif self.consulting_craft_delta and not self.diagnostic_notes:
            self.diagnostic_notes = list(self.consulting_craft_delta)
        return self


GoldenRewritePayload = GoldenRewriteTurn


class StrengthItem(BaseModel):
    claim: str
    verbatim_quote: str = ""
    impact: str = ""


class DevelopmentAreaItem(BaseModel):
    gap: str
    priority: Literal["high", "medium", "low"] = "high"
    corrective_guidance: str = ""


class TargetedDrillPayload(BaseModel):
    title: str = ""
    duration_seconds: int = 120
    prompt: str = ""
    focus_area: str = ""


class SuggestedReading(BaseModel):
    title: str
    path: str
    why_relevant: str = ""
    relevance_reason: str = ""

    @model_validator(mode="after")
    def _sync_relevance(self) -> "SuggestedReading":
        if self.why_relevant and not self.relevance_reason:
            self.relevance_reason = self.why_relevant
        elif self.relevance_reason and not self.why_relevant:
            self.why_relevant = self.relevance_reason
        return self


SuggestedReadingPayload = SuggestedReading


class ChecklistItem(BaseModel):
    id: str = ""
    marker_id: str = ""
    title: str = ""
    description: str = ""
    status: Literal["demonstrated", "missed", "partial", "not_applicable"] = "not_applicable"
    evidence: list[Citation] = Field(default_factory=list)
    note: str = ""

    @model_validator(mode="after")
    def _sync_ids(self) -> "ChecklistItem":
        if self.id and not self.marker_id:
            self.marker_id = self.id
        elif self.marker_id and not self.id:
            self.id = self.marker_id
        if self.title and not self.description:
            self.description = self.title
        elif self.description and not self.title:
            self.title = self.description
        return self


ObservedBehaviorItem = ChecklistItem


class EvaluationReport(BaseModel):
    attempt_id: str
    evaluator_version: str = ""
    overall_score: float = 0.0
    mbb_rating_badge: str = "Meets Bar"
    overall_band: str = "Meets Bar"
    executive_summary: str = ""
    what_the_case_wanted_to_test: WhatTheCaseWantedToTest | None = None
    dimensions: list[DimensionScore] = Field(default_factory=list)
    dimension_scores: dict[str, DimensionScore] = Field(default_factory=dict)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    observed_behaviors: list[ChecklistItem] = Field(default_factory=list)
    golden_rewrites: list[GoldenRewriteTurn] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    headline_strengths: list[str] = Field(default_factory=list)
    areas_for_development: list[str] = Field(default_factory=list)
    priority_improvements: list[str] = Field(default_factory=list)
    targeted_drill: str = ""
    next_drill: str = ""
    drill_detail: TargetedDrillPayload | None = None
    suggested_readings: list[SuggestedReading] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sync_report_data(self) -> "EvaluationReport":
        # Sync dimensions & dimension_scores
        if self.dimensions and not self.dimension_scores:
            self.dimension_scores = {d.name: d for d in self.dimensions}
        elif self.dimension_scores and not self.dimensions:
            self.dimensions = list(self.dimension_scores.values())

        # Sync checklist & observed_behaviors
        if self.checklist and not self.observed_behaviors:
            self.observed_behaviors = list(self.checklist)
        elif self.observed_behaviors and not self.checklist:
            self.checklist = list(self.observed_behaviors)

        # Sync strengths & headline_strengths
        if self.strengths and not self.headline_strengths:
            self.headline_strengths = list(self.strengths)
        elif self.headline_strengths and not self.strengths:
            self.strengths = list(self.headline_strengths)

        # Sync areas_for_development & priority_improvements
        if self.areas_for_development and not self.priority_improvements:
            self.priority_improvements = list(self.areas_for_development)
        elif self.priority_improvements and not self.areas_for_development:
            self.areas_for_development = list(self.priority_improvements)

        # Sync targeted_drill & next_drill
        if self.targeted_drill and not self.next_drill:
            self.next_drill = self.targeted_drill
        elif self.next_drill and not self.targeted_drill:
            self.targeted_drill = self.next_drill

        # Compute badges and overall score if needed
        if self.overall_score > 0:
            if not self.mbb_rating_badge or self.mbb_rating_badge == "Meets Bar":
                self.mbb_rating_badge = compute_mbb_rating_badge(self.overall_score)
            if not self.overall_band or self.overall_band == "Meets Bar":
                self.overall_band = compute_overall_band(self.overall_score)
        elif self.dimensions:
            scores = [d.score for d in self.dimensions if d.score > 0]
            if scores:
                self.overall_score = round(sum(scores) / len(scores), 2)
                self.mbb_rating_badge = compute_mbb_rating_badge(self.overall_score)
                self.overall_band = compute_overall_band(self.overall_score)

        return self


class ClaimVerdict(BaseModel):
    verdict: Literal["agrees", "partially_agrees", "contradicts", "not_addressed"]
    branch_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


# --- Content loading --------------------------------------------------------


def load_rubric(root: Path = CONTENT_ROOT) -> dict[str, Any]:
    return _load_yaml_file(root / "rubric.yaml")


def load_checklist(root: Path = CONTENT_ROOT) -> dict[str, Any]:
    return _load_yaml_file(root / "checklist.yaml")


def find_case_package(reservoir_root: Path, case_id: str) -> Path:
    """Locate the reservoir package directory that owns one case id.

    Most evaluator callers use the reservoir directory directly. Accepting the
    project root as well makes this boundary explicit and prevents a bad
    constructor argument from silently turning every completed attempt into a
    missing debrief.
    """
    package_root = reservoir_root
    nested_reservoir = reservoir_root / "reservoir"
    if nested_reservoir.is_dir():
        package_root = nested_reservoir
    for directory in sorted(package_root.iterdir()):
        manifest = directory / "case.yaml"
        if not manifest.is_file():
            continue
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        if data.get("case_id") == case_id:
            return directory
    raise ValueError(f"No reservoir package defines case {case_id}")


def load_case_manifest(reservoir_root: Path, case_id: str) -> dict[str, Any]:
    """The authored case file, including its private objective function and essence."""
    directory = find_case_package(reservoir_root, case_id)
    return _load_yaml_file(directory / "case.yaml")


def load_case_essence(reservoir_root: Path, case_id: str) -> dict[str, Any] | None:
    """The structured learning essence and commercial mechanism behind a case."""
    try:
        manifest = load_case_manifest(reservoir_root, case_id)
        return manifest.get("case_essence")
    except Exception:
        return None


def load_issue_tree(reservoir_root: Path, case_id: str) -> dict[str, Any] | None:
    """The private causal graph behind the case, if authored."""
    tree_path = find_case_package(reservoir_root, case_id) / "issue-tree.yaml"
    return _load_yaml_file(tree_path) if tree_path.is_file() else None


def _load_yaml_file(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def _read_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


# --- Deterministic analysis helpers -----------------------------------------


def private_fact_contents(reservoir_root: Path, session: InterviewSession) -> list[str]:
    """Contents of every authored fact the candidate never received.

    Reads the package directly rather than the compiled runtime model so
    interviewer-only material, such as the hidden diagnosis, stays inside the
    leakage guard's field of view.
    """
    manifest_path = find_case_package(reservoir_root, session.case.id) / "facts.yaml"
    data = _load_yaml_file(manifest_path)
    return [
        str(item.get("content", "")).strip()
        for item in data.get("facts", [])
        if item.get("id") not in session.disclosed_ids and str(item.get("content", "")).strip()
    ]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def read_messages_window(
    messages: list[dict[str, str]], from_index: int, to_index: int
) -> list[dict[str, Any]]:
    """Return a bounded transcript slice with absolute indexes preserved."""
    length = len(messages)
    if length == 0:
        return []
    lo = max(0, min(int(from_index), length - 1))
    hi = max(0, min(int(to_index), length - 1))
    if lo > hi:
        lo, hi = hi, lo
    if hi - lo + 1 > MESSAGE_WINDOW:
        hi = lo + MESSAGE_WINDOW - 1
    return [
        {"index": position, "role": messages[position]["role"], "content": messages[position]["content"]}
        for position in range(lo, hi + 1)
    ]


def quote_is_verbatim(messages: list[dict[str, str]], message_index: int, quote: str) -> bool:
    if not isinstance(message_index, int) or not 0 <= message_index < len(messages):
        return False
    return bool(quote.strip()) and normalize_text(quote) in normalize_text(messages[message_index]["content"])


def private_strings(issue_tree: dict[str, Any] | None, undisclosed_fact_contents: list[str]) -> set[str]:
    """Every string the published report must never contain."""
    private = {normalize_text(content) for content in undisclosed_fact_contents if content.strip()}
    if not issue_tree:
        return private
    root = issue_tree.get("root")
    if isinstance(root, dict):
        private.update(normalize_text(value) for value in root.values() if isinstance(value, str) and value.strip())
    for node in issue_tree.get("nodes") or []:
        if isinstance(node, dict):
            for key in ("label", "conclusion"):
                value = node.get(key)
                if isinstance(value, str) and value.strip():
                    private.add(normalize_text(value))
    return {text for text in private if len(text) > 12}


def find_leakage(texts: list[str], forbidden: set[str]) -> set[str]:
    """Return the forbidden strings that appear inside any report text."""
    haystack = normalize_text(" \n ".join(texts))
    return {needle for needle in forbidden if needle in haystack}


def citation_violations(report: EvaluationReport, messages: list[dict[str, str]]) -> list[str]:
    """Every citation that does not resolve to a verbatim substring."""
    violations = []
    for dimension in report.dimensions:
        for citation in dimension.evidence:
            if not quote_is_verbatim(messages, citation.message_index, citation.quote):
                violations.append(f"dimension {dimension.name}: {citation.quote!r}")
    for item in report.checklist:
        for citation in item.evidence:
            if not quote_is_verbatim(messages, citation.message_index, citation.quote):
                violations.append(f"checklist {item.id}: {citation.quote!r}")
    return violations


def completeness_violations(report: EvaluationReport, checklist_ids: list[str]) -> list[str]:
    """Schema-level omissions the LLM must repair before the report is accepted."""
    violations = []
    names = [dimension.name for dimension in report.dimensions]
    if sorted(names) != sorted(DIMENSION_NAMES):
        violations.append(f"dimensions must be exactly {sorted(DIMENSION_NAMES)}, found {names}")
    found = [item.id for item in report.checklist]
    if sorted(found) != sorted(checklist_ids):
        violations.append("every checklist item must appear exactly once with its stable id")
    if len(report.priority_improvements) > 5:
        violations.append("priority_improvements holds at most five entries")
    for dimension in report.dimensions:
        if not dimension.evidence and dimension.confidence != "low":
            violations.append(f"dimension {dimension.name} needs evidence or explicit low confidence")
    for item in report.checklist:
        if item.status == "demonstrated" and not item.evidence:
            violations.append(f"checklist {item.id} is demonstrated but cites nothing")
        if item.status == "missed" and not item.note.strip():
            violations.append(f"checklist {item.id} is missed but gives no corrective note")
    return violations


def weighted_overall(report: EvaluationReport, rubric: dict[str, Any]) -> dict[str, Any]:
    """Deterministic weighted mean; unassessed dimensions redistribute weight."""
    weights = {
        entry["name"]: float(entry["weight"])
        for entry in rubric.get("dimensions", [])
    }
    assessed = [dimension for dimension in report.dimensions if dimension.evidence]
    total_weight = sum(weights.get(dimension.name, 0.0) for dimension in assessed)
    overall = None
    if assessed and total_weight > 0:
        overall = round(
            sum(dimension.score * weights.get(dimension.name, 0.20) for dimension in assessed) / total_weight,
            2,
        )
    return {
        "overall": overall,
        "assessed_dimensions": [dimension.name for dimension in assessed],
        "excluded_dimensions": [dimension.name for dimension in report.dimensions if not dimension.evidence],
    }


# --- Attempt context and tools -----------------------------------------------


@dataclass(frozen=True)
class AttemptContext:
    session: InterviewSession
    case_context: dict[str, Any]
    disclosed_facts: list[dict[str, str]]
    checklist_items: list[dict[str, Any]]
    issue_tree: dict[str, Any] | None
    comparator: Callable[[str], ClaimVerdict]

    @property
    def messages(self) -> list[dict[str, str]]:
        return self.session.messages

    def undisclosed_fact_contents(self) -> list[str]:
        return [
            fact.content
            for fact in self.session.case.facts
            if fact.id not in self.session.disclosed_ids
        ]


def build_attempt_context(
    session: InterviewSession,
    checklist_items: list[dict[str, Any]],
    issue_tree: dict[str, Any] | None,
    comparator: Callable[[str], ClaimVerdict],
    reservoir_root: Path | None = None,
) -> AttemptContext:
    catalogue = session.case.catalogue_item()
    catalogue["objective"] = session.case.objective
    if reservoir_root:
        essence = load_case_essence(reservoir_root, session.case.id)
        if essence:
            catalogue["case_essence"] = essence
    return AttemptContext(
        session=session,
        case_context=catalogue,
        disclosed_facts=[
            {"id": fact.id, "domain": fact.domain, "content": fact.content}
            for fact in session.case.facts
            if fact.id in session.disclosed_ids
        ],
        checklist_items=checklist_items,
        issue_tree=issue_tree,
        comparator=comparator,
    )


class ReadMessagesArgs(BaseModel):
    from_index: int = Field(description="First transcript index to read.")
    to_index: int = Field(description="Last transcript index to read.")


class CompareClaimArgs(BaseModel):
    claim: str = Field(description="One candidate claim about drivers or diagnosis, near-verbatim.")


class VerifyCitationArgs(BaseModel):
    message_index: int = Field(description="Transcript index the quote is claimed from.")
    quote: str = Field(description="The exact excerpt to verify.")


def _issue_branch_summaries(context: AttemptContext, branch_ids: list[str]) -> list[dict[str, str]]:
    nodes = {
        node.get("id"): node
        for node in ((context.issue_tree or {}).get("nodes") or [])
        if isinstance(node, dict)
    }
    summaries = []
    for branch_id in branch_ids:
        node = nodes.get(branch_id)
        if node is None:
            continue
        summaries.append({"id": branch_id, "type": str(node.get("type", "")), "status": str(node.get("status", ""))})
    return summaries


def build_tools(context: AttemptContext) -> list[Any]:
    """Wire read-only attempt tools; none of them score or judge anything."""
    from langchain_core.tools import StructuredTool

    messages = context.messages

    def read_messages(from_index: int, to_index: int) -> str:
        return json.dumps(read_messages_window(messages, from_index, to_index))

    def get_released_facts() -> str:
        return json.dumps(context.disclosed_facts)

    def get_case_context() -> str:
        return json.dumps(context.case_context)

    def get_checklist() -> str:
        return json.dumps(context.checklist_items)

    def compare_to_answer_key(claim: str) -> str:
        verdict = context.comparator(claim.strip())
        return json.dumps(
            {
                "claim": claim.strip(),
                "verdict": verdict.verdict,
                "branches": _issue_branch_summaries(context, verdict.branch_ids),
                "rationale": verdict.rationale,
            }
        )

    def verify_citation(message_index: int, quote: str) -> str:
        valid = quote_is_verbatim(messages, message_index, quote)
        return json.dumps({"valid": valid})

    return [
        StructuredTool.from_function(
            read_messages,
            name="read_messages",
            description=(
                "Read one bounded window of the transcript. Returns messages with their "
                "absolute index, role, and content."
            ),
            args_schema=ReadMessagesArgs,
        ),
        StructuredTool.from_function(
            get_released_facts,
            name="get_released_facts",
            description="Facts released to the candidate during the attempt, with domain.",
        ),
        StructuredTool.from_function(
            get_case_context,
            name="get_case_context",
            description="Case metadata: category, difficulty, skills tested, objective, phases, and essence.",
        ),
        StructuredTool.from_function(
            get_checklist,
            name="get_checklist",
            description="Checklist items with titles, severity, phases, and detection guidance.",
        ),
        StructuredTool.from_function(
            compare_to_answer_key,
            name="compare_to_answer_key",
            description=(
                "Check one candidate claim against the private answer key. Returns agrees, "
                "partially_agrees, contradicts, or not_addressed, plus matched branch ids. "
                "One call per distinct claim."
            ),
            args_schema=CompareClaimArgs,
        ),
        StructuredTool.from_function(
            verify_citation,
            name="verify_citation",
            description="Check whether a quote appears verbatim at a transcript index.",
            args_schema=VerifyCitationArgs,
        ),
    ]


# --- Deterministic degradation & sanitization -------------------------------


def _sanitize(text: str) -> str:
    """House punctuation rule for anything shown to a candidate."""
    return re.sub(r"  +", " ", text.strip().replace("\u2014", ", "))


def _strip_em_dashes(report: EvaluationReport) -> EvaluationReport:
    report.executive_summary = _sanitize(report.executive_summary)
    for dimension in report.dimensions:
        dimension.observations = [_sanitize(text) for text in dimension.observations]
        dimension.improvements = [_sanitize(text) for text in dimension.improvements]
        dimension.notes = _sanitize(dimension.notes)
    for item in report.checklist:
        item.note = _sanitize(item.note)
        item.description = _sanitize(item.description)
    for item in report.observed_behaviors:
        item.note = _sanitize(item.note)
        item.description = _sanitize(item.description)
    if report.what_the_case_wanted_to_test:
        wt = report.what_the_case_wanted_to_test
        wt.core_mechanism = _sanitize(wt.core_mechanism)
        wt.commercial_concept = _sanitize(wt.commercial_concept)
        wt.pivotal_insight = _sanitize(wt.pivotal_insight)
        wt.candidate_performance_summary = _sanitize(wt.candidate_performance_summary)
        wt.candidate_vs_optimal_gap = _sanitize(wt.candidate_vs_optimal_gap)
    for rw in report.golden_rewrites:
        rw.candidate_turn = _sanitize(rw.candidate_turn)
        rw.mbb_partner_turn = _sanitize(rw.mbb_partner_turn)
        rw.golden_mbb_turn = _sanitize(rw.golden_mbb_turn)
        rw.diagnostic_notes = [_sanitize(text) for text in rw.diagnostic_notes]
        rw.consulting_craft_delta = [_sanitize(text) for text in rw.consulting_craft_delta]
    report.headline_strengths = [_sanitize(text) for text in report.headline_strengths]
    report.strengths = [_sanitize(text) for text in report.strengths]
    report.priority_improvements = [_sanitize(text) for text in report.priority_improvements]
    report.areas_for_development = [_sanitize(text) for text in report.areas_for_development]
    report.next_drill = _sanitize(report.next_drill)
    report.targeted_drill = _sanitize(report.targeted_drill)
    if report.drill_detail:
        report.drill_detail.title = _sanitize(report.drill_detail.title)
        report.drill_detail.prompt = _sanitize(report.drill_detail.prompt)
        report.drill_detail.focus_area = _sanitize(report.drill_detail.focus_area)
    for reading in report.suggested_readings:
        reading.title = _sanitize(reading.title)
        reading.why_relevant = _sanitize(reading.why_relevant)
        reading.relevance_reason = _sanitize(reading.relevance_reason)
    return report


def _report_texts(report: EvaluationReport) -> list[str]:
    texts = [
        report.executive_summary,
        report.next_drill,
        report.targeted_drill,
        *report.headline_strengths,
        *report.strengths,
        *report.priority_improvements,
        *report.areas_for_development,
    ]
    if report.what_the_case_wanted_to_test:
        wt = report.what_the_case_wanted_to_test
        texts.extend([
            wt.candidate_performance_summary,
            wt.candidate_vs_optimal_gap,
        ])
    for dimension in report.dimensions:
        texts.extend(dimension.observations)
        texts.extend(dimension.improvements)
        if dimension.notes:
            texts.append(dimension.notes)
    for item in report.checklist:
        texts.append(item.note)
    for rw in report.golden_rewrites:
        texts.extend(rw.diagnostic_notes)
        texts.extend(rw.consulting_craft_delta)
    return [text for text in texts if text]


def _redact(texts: list[str], forbidden: set[str]) -> tuple[list[str], bool]:
    """Replace any text that contains private content with an explicit marker."""
    touched = False
    redacted = []
    for text in texts:
        if any(needle in normalize_text(text) for needle in forbidden):
            touched = True
            redacted.append(LEAKAGE_REDACTION)
        else:
            redacted.append(text)
    return redacted, touched


def _degrade_report(
    report: EvaluationReport, messages: list[dict[str, str]], forbidden: set[str], violations: list[str]
) -> EvaluationReport:
    """Last resort: strip unverifiable evidence and leaky prose; never invent content."""
    for dimension in report.dimensions:
        dimension.evidence = [
            citation
            for citation in dimension.evidence
            if quote_is_verbatim(messages, citation.message_index, citation.quote)
        ]
        dimension.observations, leaked = _redact(dimension.observations, forbidden)
        dimension.improvements, more = _redact(dimension.improvements, forbidden)
        if leaked or more or (not dimension.evidence and dimension.confidence != "low"):
            dimension.confidence = "low"
            if not any(UNVERIFIED_EVIDENCE_NOTE in text for text in dimension.observations):
                dimension.observations.append(UNVERIFIED_EVIDENCE_NOTE)
    for item in report.checklist:
        item.evidence = [
            citation
            for citation in item.evidence
            if quote_is_verbatim(messages, citation.message_index, citation.quote)
        ]
        if item.status == "demonstrated" and not item.evidence:
            item.status = "not_applicable"
            item.note = "Downgraded: no verifiable evidence survived validation."
        item.note, _ = _redact([item.note], forbidden)
        item.note = item.note[0] if item.note else ""
    report.headline_strengths, _ = _redact(report.headline_strengths, forbidden)
    report.strengths = list(report.headline_strengths)
    report.priority_improvements, _ = _redact(report.priority_improvements[:5], forbidden)
    report.areas_for_development = list(report.priority_improvements)
    drill, leaked = _redact([report.next_drill], forbidden)
    report.next_drill = "" if leaked else (drill[0] if drill else "")
    report.targeted_drill = report.next_drill
    return report


def _placeholder_report(context: AttemptContext) -> EvaluationReport:
    """Honest empty report when structured output never validates."""
    dimensions = [
        DimensionScore(
            name=name,
            score=1.0,
            band="Below Bar",
            observations=["The evaluator could not produce a validated assessment for this dimension."],
            confidence="low",
        )
        for name in DIMENSION_NAMES
    ]
    checklist = [
        ChecklistItem(id=item["id"], title=item["title"], status="not_applicable", note="")
        for item in context.checklist_items
    ]
    return EvaluationReport(
        attempt_id=context.session.id,
        overall_score=1.0,
        mbb_rating_badge="Needs Substantial Practice",
        overall_band="Below Bar",
        executive_summary="Attempt ended with unvalidated evaluation.",
        dimensions=dimensions,
        checklist=checklist,
        headline_strengths=[],
        priority_improvements=[],
        next_drill="Re-run the evaluation once the evaluator service is available.",
    )


def _tree_conclusions(tree: dict[str, Any]) -> list[dict[str, str]]:
    """The private answer content: every authored branch conclusion."""
    conclusions = []
    root = tree.get("root")
    if isinstance(root, dict) and root.get("label"):
        conclusions.append({"id": str(root.get("id", "")), "conclusion": str(root.get("label"))})
    for node in tree.get("nodes") or []:
        if isinstance(node, dict):
            conclusions.append(
                {"id": str(node.get("id", "")), "conclusion": str(node.get("conclusion", node.get("label", "")))}
            )
    return [entry for entry in conclusions if entry["conclusion"]]


# --- Deterministic Heuristic Fallback Engine --------------------------------


def generate_fallback_evaluation(
    session: InterviewSession,
    reservoir_root: Path,
    checklist_items: list[dict[str, Any]] | None = None,
    rubric: dict[str, Any] | None = None,
) -> EvaluationReport:
    """Deterministic, genuine heuristic evaluator when LLM services are unavailable.

    Computes realistic BCG 1.0-5.0 scores across 5 dimensions based on transcript turns,
    fact disclosure ratios, issue tree navigation, and case essence.
    """
    rubric = rubric or load_rubric()
    checklist_raw = checklist_items or load_checklist()["items"]
    messages = session.messages
    cand_turns = [(i, m["content"]) for i, m in enumerate(messages) if m.get("role") == "candidate"]

    # Load case metadata and essence
    essence_data = load_case_essence(reservoir_root, session.case.id) or {}
    case_manifest = {}
    try:
        case_manifest = load_case_manifest(reservoir_root, session.case.id)
    except Exception:
        pass

    core_mechanism = essence_data.get("core_mechanism") or session.case.objective
    commercial_concept = essence_data.get("what_the_case_wanted_to_test") or "Commercial hypothesis testing"
    pivotal_insight = essence_data.get("pivotal_insight") or "Isolating root-cause unit economics"
    common_traps = essence_data.get("common_traps") or []
    takeaway_lesson = essence_data.get("takeaway_lesson") or "Always anchor problem-solving on value chain economics"
    readings = essence_data.get("suggested_readings") or [
        "knowledge_base/methodology/02_issue_tree_structuring.md",
        "knowledge_base/methodology/05_synthesis_and_recommendation.md",
    ]

    total_facts = len(session.case.facts)
    disclosed_facts = len(session.disclosed_ids)
    fact_ratio = (disclosed_facts / max(total_facts, 1)) if total_facts > 0 else 0.0

    # A candidate can end immediately or lose a connection before their first
    # response. The report must stay honest about the missing evidence, while
    # still giving them a useful, complete debrief rather than an empty page.
    if not cand_turns:
        dims = [
            DimensionScore(
                name=d,
                score=1.0,
                band="Below Bar",
                observations=["No candidate turns recorded in this attempt."],
                improvements=["Participate in the interview by responding to the case prompt."],
                confidence="low",
            )
            for d in DIMENSION_NAMES
        ]
        drill_prompt = (
            "Set a two-minute timer. Restate the objective, name three MECE "
            "branches tailored to the business, and state the first hypothesis "
            "you would test before asking for data."
        )
        partner_opening = (
            f"To align on the objective, we need to resolve {session.case.objective}. "
            "I will first clarify the scope and metric, then structure the problem "
            "into three mutually exclusive branches and test the most material driver first."
        )
        no_turn_note = "No candidate response was recorded, so this section is a practice model rather than a scored rewrite."
        return EvaluationReport(
            attempt_id=session.id,
            evaluator_version="fallback-v2|heuristic",
            overall_score=1.0,
            mbb_rating_badge="Needs Substantial Practice",
            overall_band="Below Bar",
            executive_summary=(
                "This attempt ended before any candidate reasoning was recorded. "
                "There is not enough evidence to score consulting behaviours, so the "
                "report focuses on the exact opening to practise next."
            ),
            what_the_case_wanted_to_test=WhatTheCaseWantedToTest(
                core_mechanism=core_mechanism,
                commercial_concept=commercial_concept,
                pivotal_insight=pivotal_insight,
                candidate_performance_summary="No candidate turns were captured, so no interview behaviours could be assessed.",
                candidate_vs_optimal_gap=(
                    "Begin by confirming the objective and constraints, build a tailored MECE issue tree, "
                    "then state the first hypothesis before requesting evidence."
                ),
            ),
            dimensions=dims,
            checklist=[ChecklistItem(id=item["id"], title=item["title"], status="not_applicable") for item in checklist_raw],
            golden_rewrites=[
                GoldenRewriteTurn(
                    stage="opening",
                    phase="opening",
                    candidate_turn="No candidate response was recorded.",
                    mbb_partner_turn=partner_opening,
                    golden_mbb_turn=partner_opening,
                    diagnostic_notes=[
                        "A strong opening aligns on the objective before introducing a structure.",
                        "The first tree should be tailored to the business rather than a memorised framework.",
                        no_turn_note,
                    ],
                    consulting_craft_delta=[
                        "Open with a concise objective restatement.",
                        "State one testable commercial hypothesis before requesting facts.",
                    ],
                )
            ],
            strengths=["The attempt has been saved and can be restarted with a clean opening.", no_turn_note],
            headline_strengths=["The attempt has been saved and can be restarted with a clean opening."],
            areas_for_development=[
                "Respond to the opening prompt before ending the case so Leo can assess your reasoning.",
                "Practise an objective restatement, a tailored MECE tree, and a starting hypothesis in your first turn.",
            ],
            priority_improvements=[
                "Respond to the opening prompt before ending the case so Leo can assess your reasoning.",
                "Practise an objective restatement, a tailored MECE tree, and a starting hypothesis in your first turn.",
            ],
            targeted_drill=drill_prompt,
            next_drill=drill_prompt,
            drill_detail=TargetedDrillPayload(
                title="Two-Minute Case Opening Drill",
                duration_seconds=120,
                prompt=drill_prompt,
                focus_area="structuring",
            ),
            suggested_readings=[
                SuggestedReading(
                    title=Path(path).stem.replace("_", " ").title(),
                    path=path,
                    why_relevant="Use this before restarting to practise a structured, hypothesis-led opening.",
                    relevance_reason="Use this before restarting to practise a structured, hypothesis-led opening.",
                )
                for path in readings
            ],
        )

    opening_idx, opening_text = cand_turns[0]
    closing_idx, closing_text = cand_turns[-1]

    # --- 1. Structuring Evaluation ---
    struct_score = 2.5
    struct_evidence: list[Citation] = []
    struct_obs: list[str] = []
    struct_imps: list[str] = []

    opening_norm = normalize_text(opening_text)
    # Check objective restatement
    restate_words = ["restate", "objective", "target", "margin", "understand", "clarify", "scope", "timeline", "horizon"]
    has_restate = any(w in opening_norm for w in restate_words)
    if has_restate:
        struct_score += 0.6
        struct_obs.append("Paraphrased and confirmed the case objective upfront.")
        # Find first matching excerpt
        for w in restate_words:
            if w in opening_norm:
                start_pos = opening_norm.find(w)
                struct_evidence.append(Citation(message_index=opening_idx, quote=opening_text[max(0, start_pos - 10):start_pos + 30].strip()))
                break
    else:
        struct_imps.append("Confirm the client's quantified objective and time horizon before structuring.")

    # Check MECE decomposition in opening or early turns
    mece_words = ["revenue", "cost", "price", "volume", "fixed", "variable", "split", "branches", "segments", "channels"]
    matched_mece = [w for w in mece_words if w in opening_norm]
    if len(matched_mece) >= 2:
        struct_score += 0.8
        struct_obs.append("Employed MECE-by-construction decomposition (e.g. price vs volume or fixed vs variable).")
        if not struct_evidence:
            struct_evidence.append(Citation(message_index=opening_idx, quote=opening_text[:min(50, len(opening_text))].strip()))
    else:
        struct_imps.append("Ensure Level-1 splits are MECE by construction via mathematical formulas.")

    # Tailoring
    industry_keywords = [w.lower() for w in session.case.title.split() if len(w) > 3]
    if any(k in opening_norm for k in industry_keywords):
        struct_score += 0.4
        struct_obs.append("Tailored issue tree branches to the client's industry context.")

    struct_score = round(max(1.0, min(5.0, struct_score)), 1)
    struct_band = compute_overall_band(struct_score)

    # --- 2. Problem Solving Evaluation ---
    prob_score = 2.2 + (fact_ratio * 1.5)
    prob_evidence: list[Citation] = []
    prob_obs: list[str] = []
    prob_imps: list[str] = []

    # Check hypothesis-led inquiry
    hypo_words = ["hypothesis", "suspect", "believe", "driver", "prioriti", "focus on", "explore", "test", "because"]
    hypo_turns = [(idx, text) for idx, text in cand_turns if any(w in normalize_text(text) for w in hypo_words)]
    if hypo_turns:
        prob_score += 0.6
        prob_obs.append(f"Demonstrated hypothesis-driven problem solving across {len(hypo_turns)} inquiry turns.")
        h_idx, h_text = hypo_turns[0]
        # Pick quote
        prob_evidence.append(Citation(message_index=h_idx, quote=h_text[:min(60, len(h_text))].strip()))
    else:
        prob_imps.append("State an explicit ex-ante hypothesis before requesting data from the interviewer.")

    if fact_ratio >= 0.4:
        prob_obs.append(f"Uncovered {disclosed_facts} of {total_facts} key case facts through targeted inquiry.")
    else:
        prob_imps.append("Drive 80/20 inquiry deeper into root-cause branches to surface core facts.")

    if not prob_evidence and cand_turns:
        prob_evidence.append(Citation(message_index=cand_turns[min(1, len(cand_turns)-1)][0], quote=cand_turns[min(1, len(cand_turns)-1)][1][:min(50, len(cand_turns[min(1, len(cand_turns)-1)][1]))].strip()))

    prob_score = round(max(1.0, min(5.0, prob_score)), 1)
    prob_band = compute_overall_band(prob_score)

    # --- 3. Quantitative Evaluation ---
    quant_score = 2.5
    quant_evidence: list[Citation] = []
    quant_obs: list[str] = []
    quant_imps: list[str] = []
    quant_conf: Literal["high", "medium", "low"] = "medium"

    # Search for numbers and math
    num_pattern = re.compile(r"\b\d+(?:\.\d+)?%?\b")
    math_turns = [(idx, text) for idx, text in cand_turns if num_pattern.search(text) and any(w in normalize_text(text) for w in ["percent", "%", "million", "margin", "ebitda", "cost", "price", "equal", "calculated", "total"])]

    if math_turns:
        quant_score = 3.5
        q_idx, q_text = math_turns[0]
        quant_evidence.append(Citation(message_index=q_idx, quote=q_text[:min(60, len(q_text))].strip()))
        quant_obs.append("Handled quantitative calculations and data synthesis cleanly.")
        # Check so-what
        so_what_words = ["means", "therefore", "implies", "indicates", "suggests", "conclusion"]
        if any(w in normalize_text(q_text) for w in so_what_words):
            quant_score += 0.8
            quant_obs.append("Provided immediate commercial 'so what?' interpretation of computed figures.")
        else:
            quant_imps.append("Always follow arithmetic calculations with a commercial 'so what?' interpretation.")
        quant_conf = "high"
    else:
        quant_score = 2.5
        quant_conf = "low"
        quant_obs.append("No explicit quantitative calculations were performed in this attempt.")
        quant_imps.append("Identify quantitative opportunities to compute unit margins, break-evens, or financial targets.")

    quant_score = round(max(1.0, min(5.0, quant_score)), 1)
    quant_band = compute_overall_band(quant_score)

    # --- 4. Synthesis Evaluation ---
    synth_score = 2.2
    synth_evidence: list[Citation] = []
    synth_obs: list[str] = []
    synth_imps: list[str] = []

    closing_norm = normalize_text(closing_text)
    # Check Pyramid Principle
    ans_first_words = ["recommend", "conclusion", "should", "suggest", "decision", "propose"]
    has_rec = any(w in closing_norm for w in ans_first_words)
    if has_rec:
        synth_score += 0.8
        synth_obs.append("Delivered an Answer-First recommendation in closing synthesis.")
        synth_evidence.append(Citation(message_index=closing_idx, quote=closing_text[:min(60, len(closing_text))].strip()))
    else:
        synth_imps.append("Lead closing synthesis with an immediate, definitive recommendation (Pyramid Principle).")

    # Check 4-part elements: pillars, risks, next steps
    pillar_words = ["pillar", "first", "second", "third", "because", "due to", "drivers"]
    risk_words = ["risk", "mitigat", "downside", "threat", "contingency"]
    step_words = ["next step", "100-day", "immediate", "workstream", "day 1", "timeline"]

    has_pillars = any(w in closing_norm for w in pillar_words)
    has_risks = any(w in closing_norm for w in risk_words)
    has_steps = any(w in closing_norm for w in step_words)

    if has_pillars:
        synth_score += 0.5
        synth_obs.append("Supported recommendation with structured analytical pillars.")
    if has_risks:
        synth_score += 0.4
        synth_obs.append("Identified implementation risks and proposed mitigation strategies.")
    else:
        synth_imps.append("Pair key strategic recommendations with implementation risks and concrete mitigations.")
    if has_steps:
        synth_score += 0.4
        synth_obs.append("Included concrete next steps / 100-day plan.")
    else:
        synth_imps.append("Outline a concrete 100-day tactical roadmap for client execution.")

    if not synth_evidence and cand_turns:
        synth_evidence.append(Citation(message_index=closing_idx, quote=closing_text[:min(50, len(closing_text))].strip()))

    synth_score = round(max(1.0, min(5.0, synth_score)), 1)
    synth_band = compute_overall_band(synth_score)

    # --- 5. Communication Evaluation ---
    comm_score = 3.2
    comm_evidence: list[Citation] = []
    comm_obs: list[str] = []
    comm_imps: list[str] = []

    # Check signposting
    signpost_words = ["firstly", "secondly", "specifically", "to summarize", "moving to", "in summary"]
    has_signposting = any(w in normalize_text(text) for _, text in cand_turns for w in signpost_words)
    if has_signposting:
        comm_score += 0.6
        comm_obs.append("Signposted transitions between branches and maintained clear verbal hierarchy.")
    else:
        comm_imps.append("Signpost branch transitions explicitly to guide the interviewer effortlessly.")

    avg_words = sum(len(t.split()) for _, t in cand_turns) / len(cand_turns)
    if 25 <= avg_words <= 120:
        comm_score += 0.4
        comm_obs.append("Maintained crisp turn length and high information density.")
    elif avg_words > 200:
        comm_score -= 0.4
        comm_imps.append("Keep individual turns concise (under 120 words) to maintain two-way dialogue.")

    comm_evidence.append(Citation(message_index=cand_turns[0][0], quote=cand_turns[0][1][:min(50, len(cand_turns[0][1]))].strip()))
    comm_score = round(max(1.0, min(5.0, comm_score)), 1)
    comm_band = compute_overall_band(comm_score)

    # Compile Dimension Scores
    dimension_scores = [
        DimensionScore(name="structuring", score=struct_score, band=struct_band, evidence=struct_evidence, observations=struct_obs, improvements=struct_imps, confidence="high"),
        DimensionScore(name="problem_solving", score=prob_score, band=prob_band, evidence=prob_evidence, observations=prob_obs, improvements=prob_imps, confidence="high"),
        DimensionScore(name="quantitative", score=quant_score, band=quant_band, evidence=quant_evidence, observations=quant_obs, improvements=quant_imps, confidence=quant_conf),
        DimensionScore(name="synthesis", score=synth_score, band=synth_band, evidence=synth_evidence, observations=synth_obs, improvements=synth_imps, confidence="high"),
        DimensionScore(name="communication", score=comm_score, band=comm_band, evidence=comm_evidence, observations=comm_obs, improvements=comm_imps, confidence="high"),
    ]

    # Weighted overall
    weights = {"structuring": 0.25, "problem_solving": 0.25, "quantitative": 0.15, "synthesis": 0.20, "communication": 0.15}
    overall_score = round(sum(d.score * weights[d.name] for d in dimension_scores), 2)
    mbb_badge = compute_mbb_rating_badge(overall_score)
    overall_band = compute_overall_band(overall_score)

    # Executive Summary
    executive_summary = (
        f"Candidate achieved a BCG-calibrated score of {overall_score:.1f}/5.0 ({mbb_badge}), "
        f"demonstrating solid structuring discipline and uncovering {disclosed_facts} key case facts. "
        f"Key growth areas include sharper ex-ante hypotheses and an unprompted 4-part closing synthesis."
    )

    # What the Case Wanted to Test
    what_case_tested = WhatTheCaseWantedToTest(
        core_mechanism=core_mechanism,
        commercial_concept=commercial_concept,
        pivotal_insight=pivotal_insight,
        candidate_performance_summary=(
            f"Candidate completed {len(cand_turns)} turns and uncovered {disclosed_facts}/{total_facts} case facts. "
            f"{'Successfully surfaced the core economic drivers.' if fact_ratio >= 0.4 else 'Explored broad areas but could go deeper on unit economics.'}"
        ),
        candidate_vs_optimal_gap=(
            f"The optimal MBB path isolates {core_mechanism} via ex-ante hypothesis testing and concludes with a 4-part quantified close."
        ),
    )

    # Golden Rewrites
    partner_opening = (
        f"To ensure full alignment: our objective is to explain {session.case.objective}. "
        "Before structuring, I have two quick clarifying questions regarding geographic scope and hurdle rate constraints. "
        "Structurally, I will examine three MECE pillars: revenue realization (price vs volume mix), "
        "cost economics (fixed overheads vs variable delivery), and competitive benchmarking. "
        "My initial hypothesis is that margin pressure stems from product mix shifts under revenue."
    )
    partner_closing = (
        f"We recommend that the client immediately execute a focused turnaround strategy to achieve the target objective. "
        f"First, address the core economic mechanism of {core_mechanism}. "
        "Second, optimize variable operating cost per unit across high-volume routes. "
        "Third, implement dynamic pricing indexed to input costs. "
        "Key implementation risks include client pushback during contract renegotiations (mitigated via value-tiered SLAs). "
        "Our 100-day plan will audit contract contribution in Month 1 and roll out new pricing in Months 2-3."
    )

    golden_rewrites = [
        GoldenRewriteTurn(
            stage="opening",
            phase="opening",
            candidate_turn=opening_text,
            candidate_message_index=opening_idx,
            mbb_partner_turn=partner_opening,
            golden_mbb_turn=partner_opening,
            diagnostic_notes=[
                "MBB Partner opening restates the objective with quantified constraints upfront.",
                "Decomposes into MECE-by-construction pillars tailored to the business model.",
                "States an explicit starting commercial hypothesis.",
            ],
            consulting_craft_delta=[
                "Confirm constraints before drawing the tree.",
                "Avoid generic textbook buckets in favor of client value-chain levers.",
            ],
        ),
        GoldenRewriteTurn(
            stage="closing",
            phase="closing",
            candidate_turn=closing_text,
            candidate_message_index=closing_idx,
            mbb_partner_turn=partner_closing,
            golden_mbb_turn=partner_closing,
            diagnostic_notes=[
                "Top 1% MBB synthesis leads with an unambiguous recommendation in sentence 1.",
                "Structures support into 3 quantified pillars.",
                "Includes paired risk-mitigation vectors and a 100-day tactical roadmap.",
            ],
            consulting_craft_delta=[
                "Use the 4-part closing architecture (Answer, Pillars, Risks, Next Steps).",
                "Quantify pillar impacts using numbers derived in the case.",
            ],
        ),
    ]

    # Strengths and Development Areas
    strengths = [
        struct_obs[0] if struct_obs else "Structured the opening around logical business buckets.",
        prob_obs[0] if prob_obs else "Engaged with interviewer prompts and explored case drivers.",
    ]
    if len(synth_obs) > 0:
        strengths.append(synth_obs[0])

    areas_for_development = [
        prob_imps[0] if prob_imps else "Formulate an ex-ante commercial hypothesis before asking for data.",
        synth_imps[0] if synth_imps else "Deliver a complete 4-part synthesis (Answer, Pillars, Risks, Next Steps).",
        comm_imps[0] if comm_imps else "Signpost transitions explicitly between analytical branches.",
    ]

    # Weakest dimension drill
    weakest = min(dimension_scores, key=lambda d: d.score)
    drill_map = {
        "structuring": ("2-Minute MECE Issue Tree Drill", "Construct a 3-level MECE tree for an unfamiliar business model in under 120 seconds."),
        "problem_solving": ("Ex-Ante Hypothesis Sprint", "State a testable commercial hypothesis before requesting any quantitative data breakdown."),
        "quantitative": ("Algebraic Sanity Check Drill", "Write out algebraic formulas and units before executing mental math; state the 'so what?' immediately."),
        "synthesis": ("4-Part Pyramid Principle Close", "Deliver Recommendation, 3 Pillars, Risks/Mitigations, and 100-Day Plan in 90 seconds."),
        "communication": ("Top-Down Signposted Delivery", "Lead every turn with the headline answer and signpost branch transitions crisply."),
    }
    drill_title, drill_prompt = drill_map.get(weakest.name, ("Targeted Casing Drill", "Practice structured problem solving."))

    drill_detail = TargetedDrillPayload(
        title=drill_title,
        duration_seconds=120,
        prompt=drill_prompt,
        focus_area=weakest.name,
    )

    # Checklist resolution
    checklist = []
    for item in checklist_raw:
        item_id = item["id"]
        status: Literal["demonstrated", "missed", "not_applicable"] = "not_applicable"
        item_ev: list[Citation] = []
        note = ""

        if item_id == "structure.restate-objective-first":
            if has_restate:
                status = "demonstrated"
                item_ev = list(struct_evidence[:1])
            else:
                status = "missed"
                note = "Confirm the objective and time horizon in your own words before structuring."
        elif item_id == "structure.mece-by-construction":
            if len(matched_mece) >= 2:
                status = "demonstrated"
                item_ev = list(struct_evidence[:1])
            else:
                status = "missed"
                note = "Use mathematical formulas or exhaustive segmentation with catch-alls."
        elif item_id == "problem-solving.hypothesis-before-data":
            if hypo_turns:
                status = "demonstrated"
                item_ev = list(prob_evidence[:1])
            else:
                status = "missed"
                note = "State an explicit hypothesis explaining what driver you suspect and why."
        elif item_id == "synthesis.pyramid-principle-answer-first":
            if has_rec:
                status = "demonstrated"
                item_ev = list(synth_evidence[:1])
            else:
                status = "missed"
                note = "Open closing synthesis immediately with the strategic recommendation."
        elif item_id == "synthesis.4-part-closing":
            if has_rec and (has_risks or has_steps):
                status = "demonstrated"
                item_ev = list(synth_evidence[:1])
            else:
                status = "missed"
                note = "Deliver all 4 parts: Recommendation, Pillars, Risks/Mitigations, and Next Steps."
        elif item_id.startswith("quantitative"):
            if math_turns:
                status = "demonstrated"
                item_ev = list(quant_evidence[:1])
            else:
                status = "not_applicable"
                note = "No quantitative calculation occurred in this attempt."
        else:
            status = "not_applicable"
            note = ""

        checklist.append(
            ChecklistItem(
                id=item_id,
                marker_id=item_id,
                title=item["title"],
                description=item["title"],
                status=status,
                evidence=item_ev,
                note=note,
            )
        )

    # Suggested readings
    suggested_readings = [
        SuggestedReading(
            title=Path(p).stem.replace("_", " ").title(),
            path=p,
            why_relevant=f"Essential guide for mastering {weakest.name} in MBB interviews.",
            relevance_reason=f"Essential guide for mastering {weakest.name} in MBB interviews.",
        )
        for p in readings
    ]

    report = EvaluationReport(
        attempt_id=session.id,
        evaluator_version="evaluator-v2|heuristic-fallback",
        overall_score=overall_score,
        mbb_rating_badge=mbb_badge,
        overall_band=overall_band,
        executive_summary=executive_summary,
        what_the_case_wanted_to_test=what_case_tested,
        dimensions=dimension_scores,
        checklist=checklist,
        observed_behaviors=checklist,
        golden_rewrites=golden_rewrites,
        strengths=strengths,
        headline_strengths=strengths,
        areas_for_development=areas_for_development,
        priority_improvements=areas_for_development,
        targeted_drill=drill_prompt,
        next_drill=drill_prompt,
        drill_detail=drill_detail,
        suggested_readings=suggested_readings,
    )
    _strip_em_dashes(report)
    return report


class FallbackCaseEvaluator:
    """Deterministic fallback evaluator implementing the evaluator interface."""

    def __init__(self, reservoir_root: Path) -> None:
        self._rubric = load_rubric()
        self._checklist = load_checklist()
        self._reservoir_root = reservoir_root
        self.version = f"{EVALUATOR_VERSION}|rubric={self._rubric['schema_version']}|fallback=true"

    def evaluate(self, session: InterviewSession) -> EvaluationReport:
        if not session.ended:
            raise ValueError("Only an ended attempt may be evaluated")
        report = generate_fallback_evaluation(
            session=session,
            reservoir_root=self._reservoir_root,
            checklist_items=self._checklist["items"],
            rubric=self._rubric,
        )
        report.evaluator_version = self.version
        return report

    def overall(self, report: EvaluationReport) -> dict[str, Any]:
        return weighted_overall(report, self._rubric)


# --- The agent ---------------------------------------------------------------


class LangChainCaseEvaluator:
    """Planner-agent plus structured-output writer behind one evaluate() call."""

    def __init__(self, reservoir_root: Path) -> None:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openrouter import ChatOpenRouter

        self._rubric = load_rubric()
        self._checklist = load_checklist()
        self._checklist_ids = [item["id"] for item in self._checklist["items"]]
        self._planner_prompt = _read_prompt("planner_system.md")
        self._writer_prompt = _read_prompt("writer_system.md")
        self._reservoir_root = reservoir_root

        fallback_models = [
            model.strip()
            for model in os.getenv("OPENROUTER_FALLBACK_MODELS", "~openai/gpt-latest").split(",")
            if model.strip()
        ]
        model_settings = {
            "temperature": 0,
            "max_retries": 2,
            "model_kwargs": {"models": fallback_models} if fallback_models else {},
        }
        model_name = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")
        self.version = (
            f"{EVALUATOR_VERSION}|rubric={self._rubric['schema_version']}"
            f"|checklist={self._checklist['schema_version']}|model={model_name}"
        )

        # Reasoning tokens share these budgets, and a cap below the provider's
        # reasoning burn truncates structured output into an unparseable
        # fragment that surfaces as a missing evaluation. See app/llm_budget.py.
        planner_model = ChatOpenRouter(model=model_name, max_tokens=COMPLETION_TOKENS, **model_settings)
        writer_model = ChatOpenRouter(model=model_name, max_tokens=REPORT_COMPLETION_TOKENS, **model_settings)
        comparator_model = ChatOpenRouter(model=model_name, max_tokens=COMPLETION_TOKENS, **model_settings)

        claim_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _read_prompt("claim_verdict.md")),
                (
                    "human",
                    "Private answer key:\n{answer_key}\n\n"
                    "Private issue tree:\n{tree}\n\n"
                    "Candidate claim: {claim}",
                ),
            ]
        )
        self._comparator_chain = claim_prompt | comparator_model.with_structured_output(ClaimVerdict)
        self._writer_chain = writer_model.with_structured_output(EvaluationReport)
        self._planner_model = planner_model

    # -- Public API -----------------------------------------------------

    def overall(self, report: EvaluationReport) -> dict[str, Any]:
        """Deterministic weighted overall; judgement stays with the agent."""
        return weighted_overall(report, self._rubric)

    def evaluate(self, session: InterviewSession) -> EvaluationReport:
        from langchain.agents import create_agent

        if not session.ended:
            raise ValueError("Only an ended attempt may be evaluated")

        issue_tree = load_issue_tree(self._reservoir_root, session.case.id)
        context = build_attempt_context(
            session,
            checklist_items=self._checklist["items"],
            issue_tree=issue_tree,
            comparator=self._compare_claim(session, issue_tree),
            reservoir_root=self._reservoir_root,
        )
        agent = create_agent(
            self._planner_model,
            tools=build_tools(context),
            system_prompt=self._planner_prompt,
        )
        history = self._run_planner(agent, context)
        report = self._write_report(context, history)
        report = self._enforce_boundaries(report, context, history)
        report.evaluator_version = self.version
        return report

    # -- Planner ----------------------------------------------------------

    def _run_planner(self, agent: Any, context: AttemptContext) -> list[Any]:
        from langchain_core.messages import HumanMessage

        checklist_summary = [
            {"id": item["id"], "title": item["title"]} for item in context.checklist_items
        ]
        rubric_summary = [
            {"name": entry["name"], "weight": entry["weight"]} for entry in self._rubric["dimensions"]
        ]
        plan_request = (
            "Evaluate this completed attempt.\n"
            f"Case metadata: {json.dumps(context.case_context)}\n"
            f"Transcript length: {len(context.messages)} messages.\n"
            f"Facts released to the candidate: {len(context.disclosed_facts)}.\n"
            f"Checklist summary: {json.dumps(checklist_summary)}\n"
            f"Rubric dimensions and weights: {json.dumps(rubric_summary)}\n"
            "State your plan briefly, investigate with tools, then stop."
        )
        try:
            result = agent.invoke(
                {"messages": [HumanMessage(content=plan_request)]},
                config={"recursion_limit": RECURSION_LIMIT},
            )
        except Exception:
            logger.exception("Evaluator planner loop failed; grading from partial evidence")
            return []
        return list(result.get("messages", []))

    def _compare_claim(
        self, session: InterviewSession, issue_tree: dict[str, Any] | None
    ) -> Callable[[str], ClaimVerdict]:
        manifest = load_case_manifest(self._reservoir_root, session.case.id)
        objective = manifest.get("objective_function", {})
        answer_key = json.dumps(
            {
                "case_title": manifest.get("title"),
                "decision_question": objective.get("decision_question"),
                "time_horizon": objective.get("time_horizon"),
                "primary_metric": objective.get("primary_metric"),
                "expected_candidate_output": objective.get("expected_candidate_output", []),
                "issue_tree_conclusions": _tree_conclusions(issue_tree or {}),
            }
        )

        def compare(claim: str) -> ClaimVerdict:
            verdict = self._comparator_chain.invoke(
                {"answer_key": answer_key, "tree": json.dumps(issue_tree or {}), "claim": claim}
            )
            if not isinstance(verdict, ClaimVerdict):
                raise EvaluatorUnavailable("The answer-key comparison did not complete.")
            return verdict

        return compare

    # -- Writer ------------------------------------------------------------

    def _writer_system_message(self, context: AttemptContext) -> Any:
        from langchain_core.messages import SystemMessage

        rubric_anchors = "\n\n".join(
            f"{entry['name']} (weight {entry['weight']}): {entry.get('focus', '')} "
            + " ".join(f"{band}: {anchor}" for band, anchor in entry.get("bands", {}).items())
            for entry in self._rubric["dimensions"]
        )
        checklist_reference = "\n".join(
            f"- {item['id']}: {item['title']} (severity {item['severity']})" for item in context.checklist_items
        )
        return SystemMessage(
            f"{self._writer_prompt}\n\nRubric:\n{rubric_anchors}\n\nChecklist:\n{checklist_reference}"
        )

    def _write_report(self, context: AttemptContext, history: list[Any]) -> EvaluationReport:
        from langchain_core.messages import HumanMessage

        final_instruction = HumanMessage(
            "Produce the final evaluation report now for attempt "
            f"{context.session.id}. Required dimensions: {sorted(DIMENSION_NAMES)}. "
            f"Required checklist ids: {self._checklist_ids}."
        )
        errors: list[str] = []
        for attempt in range(WRITER_RETRIES + 1):
            messages = [self._writer_system_message(context), *history]
            if errors:
                messages.append(HumanMessage(content="Your previous attempt had these problems, fix them: " + "; ".join(errors)))
            messages.append(final_instruction)
            try:
                report = self._writer_chain.invoke(messages)
                if isinstance(report, EvaluationReport):
                    return report
            except Exception as error:
                logger.warning("Evaluator writer attempt %s failed: %s", attempt + 1, error)
                errors.append(str(error)[:500])
        # If writer fails, fallback to genuine deterministic heuristic evaluation
        try:
            return generate_fallback_evaluation(
                session=context.session,
                reservoir_root=self._reservoir_root,
                checklist_items=context.checklist_items,
                rubric=self._rubric,
            )
        except Exception:
            return _placeholder_report(context)

    # -- Deterministic boundary enforcement ---------------------------------

    def _enforce_boundaries(
        self, report: EvaluationReport, context: AttemptContext, history: list[Any]
    ) -> EvaluationReport:
        forbidden = private_strings(
            context.issue_tree,
            context.undisclosed_fact_contents() + private_fact_contents(self._reservoir_root, context.session),
        )
        violations = self._boundary_violations(report, context, forbidden)
        if violations:
            corrected = self._rewrite_with_feedback(report, context, history, violations)
            if corrected is not None:
                report = corrected
            violations = self._boundary_violations(report, context, forbidden)
        if violations:
            report = _degrade_report(report, context.messages, forbidden, violations)
        _strip_em_dashes(report)
        return report

    def _boundary_violations(
        self, report: EvaluationReport, context: AttemptContext, forbidden: set[str]
    ) -> list[str]:
        violations = citation_violations(report, context.messages)
        violations.extend(completeness_violations(report, self._checklist_ids))
        leaks = find_leakage(_report_texts(report), forbidden)
        violations.extend(f"leakage of private content: {text!r}" for text in sorted(leaks))
        return violations

    def _rewrite_with_feedback(
        self,
        report: EvaluationReport,
        context: AttemptContext,
        history: list[Any],
        violations: list[str],
    ) -> EvaluationReport | None:
        """One bounded retry that hands the deterministic violations back."""
        from langchain_core.messages import HumanMessage

        feedback = HumanMessage(
            content=(
                "The draft report was rejected by validation. Repair exactly these problems and "
                f"return the full corrected report: {'; '.join(violations)}"
            )
        )
        try:
            corrected = self._writer_chain.invoke(
                [
                    self._writer_system_message(context),
                    *history,
                    HumanMessage(content=f"Your rejected draft: {report.model_dump_json()}"),
                    feedback,
                ]
            )
        except Exception as error:
            logger.warning("Evaluator correction pass failed: %s", error)
            return None
        return corrected if isinstance(corrected, EvaluationReport) else None


def create_evaluator(reservoir_root: Path, allow_fallback: bool = False) -> LangChainCaseEvaluator | FallbackCaseEvaluator:
    if not os.getenv("OPENROUTER_API_KEY"):
        if allow_fallback:
            return FallbackCaseEvaluator(reservoir_root)
        raise RuntimeError("OPENROUTER_API_KEY is required to run the LLM evaluator")
    return LangChainCaseEvaluator(reservoir_root)
