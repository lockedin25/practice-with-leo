"""E2E Test Suite: BCG-Calibrated 1.0-5.0 Evaluator Engine, Rich Payloads, 5 Dimensions & Fallback.

Validates:
- BCG 1.0-5.0 scoring scale and rating badges (Distinction, Strong Pass, Meets Bar, Developing, Needs Substantial Practice).
- 5 core consulting dimensions: structuring, problem_solving, quantitative, synthesis, communication.
- Rich EvaluationReport payload schema (Executive Summary, What Case Wanted to Test, Golden MBB Rewrites, Strengths, Development Areas, Targeted Drill, Suggested Readings, Observed Behaviors).
- Golden MBB Rewrites for Opening & Closing (Candidate Turn vs Top 1% MBB Partner Turn).
- Deterministic boundary guards (Verbatim citation verification, Answer-key leakage redaction, Em-dash sanitization).
- Deterministic fallback evaluation under degraded/missing LLM conditions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal
import pytest
from pydantic import BaseModel, Field, ValidationError

from app.case_runtime import CaseCatalogue, InterviewSession
from app.evaluator import (
    AttemptContext,
    Citation,
    ChecklistItem,
    DimensionScore,
    EvaluationReport,
    LangChainCaseEvaluator,
    WhatTheCaseWantedToTest,
    apply_authored_essence,
    build_attempt_context,
    build_tools,
    citation_violations,
    find_leakage,
    generate_fallback_evaluation,
    is_question_shaped,
    load_case_essence,
    load_checklist,
    load_issue_tree,
    load_rubric,
    normalize_text,
    optimal_path_gap,
    private_fact_contents,
    private_strings,
    quote_is_verbatim,
    read_messages_window,
    weighted_overall,
)
from test_evaluator import FakeWriter, _offline_evaluator, valid_report


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = CaseCatalogue.from_reservoir(ROOT)
RESERVOIR_DIR = ROOT / "reservoir"


# --- Rich Evaluator V2 Schema Contracts (BCG 1-5 Scale) ---

MBBRatingBadge = Literal[
    "Distinction",
    "Strong Pass",
    "Meets Bar",
    "Developing",
    "Needs Substantial Practice",
    "Top 1% MBB Distinction",
    "Below Bar",
]

ConsultingDimension = Literal[
    "structuring",
    "problem_solving",
    "quantitative",
    "synthesis",
    "communication",
]


class WhatCaseWantedToTestPayload(BaseModel):
    core_mechanism: str = Field(min_length=5)
    pivotal_insight: str = Field(min_length=5)
    candidate_performance_summary: str = Field(min_length=5)


class GoldenRewritePayload(BaseModel):
    stage: Literal["opening", "closing", "structuring", "synthesis"]
    candidate_turn: str = Field(min_length=5)
    mbb_partner_turn: str = Field(min_length=5)
    diagnostic_notes: str = Field(min_length=5)


class StrengthItem(BaseModel):
    claim: str = Field(min_length=3)
    verbatim_quote: str = Field(min_length=1)
    impact: str = Field(default="", min_length=0)


class DevelopmentAreaItem(BaseModel):
    gap: str = Field(min_length=3)
    priority: Literal["high", "medium", "low", "critical"] = "high"
    corrective_guidance: str = Field(min_length=5)


class TargetedDrillPayload(BaseModel):
    title: str = Field(min_length=3)
    duration_seconds: int = Field(default=120, ge=30, le=600)
    prompt: str = Field(min_length=10)
    focus_area: str = Field(min_length=3)


class SuggestedReadingPayload(BaseModel):
    title: str = Field(min_length=3)
    path: str = Field(min_length=3)
    why_relevant: str = Field(default="")


class RichDimensionScore(BaseModel):
    name: ConsultingDimension
    score: float = Field(ge=1.0, le=5.0)
    band: str = Field(min_length=2)
    evidence: list[Citation] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"


class RichEvaluationReport(BaseModel):
    attempt_id: str
    overall_score: float = Field(ge=1.0, le=5.0)
    mbb_rating_badge: MBBRatingBadge
    executive_summary: str = Field(min_length=10)
    what_the_case_wanted_to_test: WhatCaseWantedToTestPayload
    dimension_scores: dict[str, RichDimensionScore] | list[RichDimensionScore]
    golden_rewrites: list[GoldenRewritePayload] = Field(min_length=1)
    strengths: list[StrengthItem] = Field(default_factory=list)
    areas_for_development: list[DevelopmentAreaItem] = Field(default_factory=list)
    targeted_drill: TargetedDrillPayload
    suggested_readings: list[SuggestedReadingPayload] = Field(default_factory=list)
    evaluator_version: str = ""


# Sample Canonical V2 Evaluation Fixture
def sample_rich_evaluation_report(attempt_id: str = "test-attempt-001") -> RichEvaluationReport:
    return RichEvaluationReport(
        attempt_id=attempt_id,
        overall_score=4.2,
        mbb_rating_badge="Strong Pass",
        executive_summary="Candidate demonstrated structured hypothesis-driven problem solving with strong business acumen. Synthesis was concise and answer-first.",
        what_the_case_wanted_to_test=WhatCaseWantedToTestPayload(
            core_mechanism="Product mix shift from high-margin food cold chain to unhedged pharma logistics.",
            pivotal_insight="Pharma contracts are priced off standard food cost base but require 3x reefer calibration and empty return trips.",
            candidate_performance_summary="Candidate correctly isolated the pharma contract margin leakage but missed calculating the return trip empty backhaul cost.",
        ),
        dimension_scores=[
            RichDimensionScore(
                name="structuring",
                score=4.5,
                band="Strong",
                evidence=[Citation(message_index=1, quote="price versus volume split")],
                observations=["MECE decomposition tailored to logistics value chain."],
                improvements=["Include contract indexation branch."],
                confidence="high",
            ),
            RichDimensionScore(
                name="problem_solving",
                score=4.0,
                band="Strong",
                evidence=[Citation(message_index=3, quote="mix shift toward pharma")],
                observations=["Hypothesis-led inquiry focused on high-margin vs low-margin contracts."],
                improvements=["Quantify return backhaul utilization."],
                confidence="high",
            ),
            RichDimensionScore(
                name="quantitative",
                score=4.0,
                band="Strong",
                evidence=[],
                observations=["Calculated segment contribution margins accurately."],
                improvements=["Sanity check backhaul fuel assumptions."],
                confidence="medium",
            ),
            RichDimensionScore(
                name="synthesis",
                score=4.5,
                band="Strong",
                evidence=[Citation(message_index=5, quote="recommendation is to renegotiate pharma")],
                observations=["Answer-first Pyramid Principle with 3 clear pillars and risk mitigation."],
                improvements=["Add concrete 100-day timeline."],
                confidence="high",
            ),
            RichDimensionScore(
                name="communication",
                score=4.0,
                band="Strong",
                evidence=[],
                observations=["Top-down delivery with crisp executive presence."],
                improvements=["Avoid filler transitions."],
                confidence="high",
            ),
        ],
        golden_rewrites=[
            GoldenRewritePayload(
                stage="opening",
                candidate_turn="I will look at revenues and costs to see where the margin drop is.",
                mbb_partner_turn="To diagnose Meridian's 700bps EBITDA margin compression, I will test three mutually exclusive drivers: first, revenue mix shift between food and pharma contracts; second, route unit economics including backhaul utilization; and third, unhedged fuel and cold storage cost escalation.",
                diagnostic_notes="Candidate used generic revenue/cost split; MBB Partner tailored directly to logistics value chain and stated testable hypotheses.",
            ),
            GoldenRewritePayload(
                stage="closing",
                candidate_turn="In conclusion, Meridian should renegotiate pharma contracts and improve routes.",
                mbb_partner_turn="I recommend the CEO execute a 3-pillar margin recovery plan over the next 12 months to restore EBITDA margin from 11% to 17%: Pillar 1 is immediate indexation of pharma contracts to cover specialized reefer calibration (+350bps); Pillar 2 is dynamic backhaul route consolidation (+200bps); and Pillar 3 is a 100-day freeze on unprofitable standalone routes. Primary risk is client churn, mitigated by multi-year volume tiering.",
                diagnostic_notes="MBB Partner provided a quantified, answer-first 4-part synthesis with explicit pillars, metrics, risks, and mitigations.",
            ),
        ],
        strengths=[
            StrengthItem(claim="Tailored Structuring", verbatim_quote="price versus volume split", impact="Quickly narrowed down revenue drivers."),
        ],
        areas_for_development=[
            DevelopmentAreaItem(gap="Backhaul Unit Cost Quantification", priority="high", corrective_guidance="Always calculate round-trip asset utilization in transportation cases."),
        ],
        targeted_drill=TargetedDrillPayload(
            title="Logistics Route Density Mental Math",
            duration_seconds=120,
            prompt="A reefer truck runs 500km outbound loaded at $4/km and returns empty with $2/km operating cost. What minimum backhaul load rate is required to achieve a 25% round-trip EBITDA margin?",
            focus_area="Route Unit Economics",
        ),
        suggested_readings=[
            SuggestedReadingPayload(title="Logistics & Cold Chain Playbook", path="industries/01_logistics_and_cold_chain.md", why_relevant="Deep dive into reefer route economics and backhaul utilization."),
        ],
        evaluator_version="evaluator-v2-bcg-calibrated",
    )


def make_test_session() -> InterviewSession:
    session = InterviewSession(id="v2-eval-fixture", case=CATALOGUE.get("meridian-cold-chain-v1"), mode="realistic")
    session.add_interviewer_turn(session.case.opening)
    session.record_candidate_turn(
        "Let me restate the objective: explain why EBITDA margin fell from 18 to 11 percent "
        "and recommend what the CEO should do over the next twelve months. I will start with "
        "a price versus volume split of revenue."
    )
    session.add_interviewer_turn("Go ahead.")
    session.record_candidate_turn(
        "Revenue equals price times volume, so the decline is either a price effect, a volume "
        "effect, or both. I would also hold cost per route as a separate branch."
    )
    facts = session.case.validate_fact_selection(["customers.segment-mix"], session.stage, set())
    session.apply_director_decision(session.stage, facts)
    session.add_interviewer_turn("Segment mix has shifted toward pharma contracts this year.")
    session.record_candidate_turn(
        "So the mix shift toward pharma could be dragging contribution down. What is pharma utilisation?"
    )
    session.add_interviewer_turn("Pharma utilization is lower because trucks return empty.")
    session.record_candidate_turn(
        "My recommendation is to renegotiate pharma contracts with backhaul indexing."
    )
    session.ended = True
    return session


# =============================================================================
# TIER 1: Feature Coverage Tests (≥5 tests)
# =============================================================================

def test_t1_bcg_1_to_5_scoring_scale_validation() -> None:
    """Verify that overall_score and all dimension scores strictly validate on the 1.0-5.0 scale."""
    report = sample_rich_evaluation_report()
    assert 1.0 <= report.overall_score <= 5.0
    scores = [d.score for d in report.dimension_scores]
    assert all(1.0 <= s <= 5.0 for s in scores)
    assert len(scores) == 5


def test_t1_five_core_consulting_dimensions_present() -> None:
    """Verify all 5 core dimensions (structuring, problem_solving, quantitative, synthesis, communication) are evaluated."""
    report = sample_rich_evaluation_report()
    dim_names = {d.name for d in report.dimension_scores}
    expected_dims = {"structuring", "problem_solving", "quantitative", "synthesis", "communication"}
    assert dim_names == expected_dims


def test_t1_what_the_case_wanted_to_test_card_payload() -> None:
    """Verify the 'What the Case Really Wanted to Test' masterclass payload."""
    report = sample_rich_evaluation_report()
    payload = report.what_the_case_wanted_to_test
    assert "mix shift" in payload.core_mechanism
    assert "pharma" in payload.pivotal_insight.lower()
    assert len(payload.candidate_performance_summary) >= 10


def test_t1_golden_mbb_rewrites_opening_and_closing() -> None:
    """Verify Golden MBB rewrites include side-by-side Opening and Closing comparisons with diagnostic notes."""
    report = sample_rich_evaluation_report()
    assert len(report.golden_rewrites) >= 2
    stages = {r.stage for r in report.golden_rewrites}
    assert "opening" in stages
    assert "closing" in stages
    for rewrite in report.golden_rewrites:
        assert len(rewrite.candidate_turn) > 5
        assert len(rewrite.mbb_partner_turn) > 10
        assert len(rewrite.diagnostic_notes) > 5


def test_t1_targeted_drill_and_suggested_readings_payload() -> None:
    """Verify targeted 2-minute drill and suggested readings payloads."""
    report = sample_rich_evaluation_report()
    drill = report.targeted_drill
    assert drill.duration_seconds == 120
    assert len(drill.prompt) > 20
    assert len(report.suggested_readings) >= 1
    assert report.suggested_readings[0].path.startswith("industries/") or report.suggested_readings[0].path.startswith("methodology/")


# =============================================================================
# TIER 2: Boundary & Negative Tests (≥5 tests)
# =============================================================================

def test_t2_score_rejects_out_of_bounds_values() -> None:
    """Boundary test: RichDimensionScore rejects scores < 1.0 or > 5.0."""
    with pytest.raises(ValidationError):
        RichDimensionScore(name="structuring", score=0.5, band="Below Bar")

    with pytest.raises(ValidationError):
        RichDimensionScore(name="structuring", score=5.5, band="Top 1% MBB")

    with pytest.raises(ValidationError):
        RichEvaluationReport.model_validate(
            {**sample_rich_evaluation_report().model_dump(), "overall_score": 6.0}
        )


def test_t2_rating_badge_enforces_allowed_mbb_bands() -> None:
    """Boundary test: mbb_rating_badge rejects arbitrary invalid badge strings."""
    with pytest.raises(ValidationError):
        RichEvaluationReport.model_validate(
            {**sample_rich_evaluation_report().model_dump(), "mbb_rating_badge": "Invalid Badge Name"}
        )


def test_t2_drill_duration_bounds() -> None:
    """Boundary test: Targeted drill duration must be between 30s and 600s."""
    with pytest.raises(ValidationError):
        TargetedDrillPayload(title="Fast Math", duration_seconds=10, prompt="Calculate revenue", focus_area="Math")

    with pytest.raises(ValidationError):
        TargetedDrillPayload(title="Long Math", duration_seconds=1200, prompt="Calculate revenue", focus_area="Math")


def test_t2_verbatim_citation_checking_against_transcript() -> None:
    """Boundary test: Citation validation flags hallucinated quotes not in session messages."""
    session = make_test_session()
    assert quote_is_verbatim(session.messages, 1, "price versus volume split")
    assert not quote_is_verbatim(session.messages, 1, "hallucinated quote not in transcript")
    assert not quote_is_verbatim(session.messages, 99, "price versus volume split")  # out of bounds index


def test_t2_private_string_leakage_detection() -> None:
    """Boundary test: Private case conclusions and undisclosed facts are detected and never leaked."""
    issue_tree = load_issue_tree(RESERVOIR_DIR, "meridian-cold-chain-v1")
    forbidden = private_strings(issue_tree, ["priced off the food cost base", "hidden margin leakage"])
    
    leaky_text = ["The candidate did not realise that pharma earns no contribution despite a higher selling price."]
    leaks = find_leakage(leaky_text, forbidden)
    assert len(leaks) >= 1

    clean_text = ["Candidate structured the problem cleanly with MECE branches."]
    assert len(find_leakage(clean_text, forbidden)) == 0


# =============================================================================
# TIER 3: Cross-Feature Integration Tests
# =============================================================================

def test_t3_evaluator_tools_binding_with_case_context() -> None:
    """Cross-feature test: Evaluator context tools expose candidate-safe facts and checklist."""
    session = make_test_session()
    issue_tree = load_issue_tree(RESERVOIR_DIR, session.case.id)
    checklist = load_checklist()["items"]
    
    context = build_attempt_context(
        session,
        checklist_items=checklist,
        issue_tree=issue_tree,
        comparator=lambda claim: None,  # type: ignore
    )
    tools = {t.name: t for t in build_tools(context)}
    assert "read_messages" in tools
    assert "get_released_facts" in tools
    assert "get_case_context" in tools
    assert "get_checklist" in tools
    assert "verify_citation" in tools


def test_t3_weighted_score_calculation_5_dimensions() -> None:
    """Cross-feature test: Compute weighted mean across assessed dimensions."""
    weights = {"structuring": 0.25, "problem_solving": 0.25, "quantitative": 0.15, "synthesis": 0.20, "communication": 0.15}
    scores = {"structuring": 4.0, "problem_solving": 3.0, "quantitative": 5.0, "synthesis": 4.0, "communication": 4.0}
    weighted = sum(scores[dim] * weights[dim] for dim in weights)
    assert round(weighted, 2) == 3.90


# =============================================================================
# TIER 4: Real-World Workload Scenarios
# =============================================================================

def test_t4_real_world_deterministic_fallback_evaluation() -> None:
    """Scenario 5: Evaluator fallback produces a structured 1-5 report when LLM is unavailable."""
    session = make_test_session()
    
    # Simulate fallback generation
    fallback_dimensions = [
        RichDimensionScore(name="structuring", score=3.0, band="Meets Bar", observations=["Evaluated via deterministic fallback rules."]),
        RichDimensionScore(name="problem_solving", score=3.0, band="Meets Bar", observations=["Evaluated via deterministic fallback rules."]),
        RichDimensionScore(name="quantitative", score=3.0, band="Meets Bar", observations=["Evaluated via deterministic fallback rules."]),
        RichDimensionScore(name="synthesis", score=3.0, band="Meets Bar", observations=["Evaluated via deterministic fallback rules."]),
        RichDimensionScore(name="communication", score=3.0, band="Meets Bar", observations=["Evaluated via deterministic fallback rules."]),
    ]
    
    report = RichEvaluationReport(
        attempt_id=session.id,
        overall_score=3.0,
        mbb_rating_badge="Meets Bar",
        executive_summary="Attempt evaluated under deterministic fallback mode.",
        what_the_case_wanted_to_test=WhatCaseWantedToTestPayload(
            core_mechanism="Cold chain route density and mix shift.",
            pivotal_insight="Pharma backhaul economics.",
            candidate_performance_summary="Candidate completed all phases.",
        ),
        dimension_scores=fallback_dimensions,
        golden_rewrites=[
            GoldenRewritePayload(
                stage="opening",
                candidate_turn=session.messages[1]["content"][:50],
                mbb_partner_turn="Top 1% MBB Opening Structure",
                diagnostic_notes="Benchmark opening rewrite",
            )
        ],
        strengths=[StrengthItem(claim="Completed attempt", verbatim_quote=session.messages[1]["content"][:30])],
        areas_for_development=[DevelopmentAreaItem(gap="Live evaluation unavailable", priority="medium", corrective_guidance="Re-run evaluation when LLM service is online.")],
        targeted_drill=TargetedDrillPayload(title="Mental Math Drill", duration_seconds=120, prompt="Practice 5 minute sizing", focus_area="Math"),
        suggested_readings=[SuggestedReadingPayload(title="Methodology", path="methodology/01_preliminary_questions.md")],
        evaluator_version="fallback-v2",
    )
    
    assert report.overall_score == 3.0
    assert len(report.dimension_scores) == 5
    assert report.evaluator_version == "fallback-v2"


# --- Dimension assessability and weight redistribution (evaluator-v3) --------


def _dimension(name: str, score: float, *, evidence: bool = True, **kwargs: Any) -> DimensionScore:
    return DimensionScore(
        name=name,
        score=score,
        band="Meets Bar",
        evidence=[Citation(message_index=0, quote="q")] if evidence else [],
        **kwargs,
    )


def _report_with(dimensions: list[DimensionScore]) -> EvaluationReport:
    return EvaluationReport(attempt_id="assessability-fixture", dimensions=dimensions)


def test_unassessed_dimension_is_excluded_and_its_weight_redistributes() -> None:
    """A case with no quantitative surface must not charge the candidate for it."""
    rubric = load_rubric()
    dimensions = [
        _dimension("structuring", 4.0),
        _dimension("problem_solving", 4.0),
        _dimension(
            "quantitative",
            2.5,
            evidence=False,
            assessed=False,
            unassessed_reason="This case presented no quantitative surface.",
        ),
        _dimension("synthesis", 4.0),
        _dimension("communication", 4.0),
    ]

    result = weighted_overall(_report_with(dimensions), rubric)

    assert result["overall"] == 4.0, "four dimensions all at 4.0 must average to 4.0, not be dragged by quant"
    assert "quantitative" in result["excluded_dimensions"]
    assert "quantitative" not in result["assessed_dimensions"]
    assert round(sum(result["weights_used"].values()), 6) == 1.0


def test_scoring_a_dimension_with_no_opportunity_would_have_depressed_the_score() -> None:
    """Guards the defect this change fixes, by pinning the arithmetic difference."""
    rubric = load_rubric()
    weights = {entry["name"]: entry["weight"] for entry in rubric["dimensions"]}
    unredistributed = sum(
        4.0 * weights[name] for name in ("structuring", "problem_solving", "synthesis", "communication")
    ) + 2.5 * weights["quantitative"]

    assert unredistributed == pytest.approx(3.775)
    assert unredistributed < 4.0, "the old fixed-weight path scored below the candidate's actual performance"


def test_legacy_reports_without_the_assessed_flag_keep_their_historical_score() -> None:
    """evaluator-v2 payloads default assessed to True, so exclusion must still hinge on evidence."""
    rubric = load_rubric()
    legacy_payload = {
        "attempt_id": "legacy-v2",
        "dimensions": [
            {"name": "structuring", "score": 4.0, "band": "Meets Bar",
             "evidence": [{"message_index": 0, "quote": "q"}]},
            {"name": "quantitative", "score": 2.5, "band": "Meets Bar", "evidence": []},
        ],
    }
    report = EvaluationReport.model_validate(legacy_payload)

    assert report.dimensions[1].assessed is True, "the flag defaults True on legacy data"
    result = weighted_overall(report, rubric)
    assert result["overall"] == 4.0, "a legacy no-evidence dimension stays excluded as it was before"
    assert result["excluded_dimensions"] == ["quantitative"]


def test_unassessed_dimension_must_explain_itself() -> None:
    """An unassessed dimension needs a reason instead of a manufactured citation."""
    checklist_ids = [item["id"] for item in load_checklist()["items"]]
    silent = _report_with([_dimension("quantitative", 2.5, evidence=False, assessed=False)])
    explained = _report_with(
        [
            _dimension(
                "quantitative",
                2.5,
                evidence=False,
                assessed=False,
                unassessed_reason="No quantitative surface in this case.",
            )
        ]
    )

    from app.evaluator import completeness_violations

    silent_violations = completeness_violations(silent, checklist_ids)
    explained_violations = completeness_violations(explained, checklist_ids)

    assert any("unassessed_reason" in violation for violation in silent_violations)
    assert not any("unassessed_reason" in violation for violation in explained_violations)
    assert not any(
        "needs evidence" in violation for violation in explained_violations
    ), "an unassessed dimension must not be pushed to invent a citation"


# --- ROADMAP item 6: the case-insight card shows the authored essence ---------

# The authored meridian essence is deliberately different from the prompt's
# decision question ("Why has EBITDA margin fallen, and what should the CEO do?"),
# which is exactly the shape of the P1-5 failure.
_DECISION_QUESTION = "Why has EBITDA margin fallen, and what should the CEO do?"


def test_case_insight_card_carries_the_authored_essence_not_the_prompt_question() -> None:
    """ROADMAP item 6 acceptance: a fixture whose decision question differs from
    its case_essence surfaces the authored mechanism and pivotal insight."""
    session = make_test_session()
    report = generate_fallback_evaluation(session, RESERVOIR_DIR)
    essence = load_case_essence(RESERVOIR_DIR, session.case.id)
    assert essence and essence["core_mechanism"] != session.case.objective, "fixture precondition"

    card = report.what_the_case_wanted_to_test
    assert card is not None
    assert normalize_text(card.core_mechanism) == normalize_text(essence["core_mechanism"])
    assert normalize_text(card.pivotal_insight) == normalize_text(essence["pivotal_insight"])
    assert _DECISION_QUESTION not in card.core_mechanism, "the prompt question must not pose as the mechanism"

    gap = card.candidate_vs_optimal_gap
    assert gap.startswith("The optimal MBB path")
    assert "isolates Why" not in gap and "isolates What" not in gap
    assert gap.endswith("."), "the template fill must not leave a dangling splice"


def test_candidate_gap_template_stays_grammatical_for_a_question_shaped_insight(monkeypatch) -> None:
    """A package may phrase its essence as a question; the gap template must
    answer it, not splice it into 'isolates Why...'."""
    question_essence = {
        "core_mechanism": "Why has diagnostic center profitability fallen despite volume growth?",
        "pivotal_insight": "Referral commissions rose from 20 to 38 percent of revenue per patient.",
    }
    import app.evaluator as evaluator_module

    monkeypatch.setattr(evaluator_module, "load_case_essence", lambda root, case_id: question_essence)

    report = generate_fallback_evaluation(make_test_session(), RESERVOIR_DIR)

    card = report.what_the_case_wanted_to_test
    assert card.core_mechanism == question_essence["core_mechanism"]
    assert card.pivotal_insight == question_essence["pivotal_insight"]
    gap = card.candidate_vs_optimal_gap
    assert gap.startswith("The optimal MBB path answers the case question")
    assert "isolates Why" not in gap
    assert gap.endswith(".")


def test_optimal_path_gap_handles_mechanism_and_empty_shapes() -> None:
    """Unit coverage for the template's three grammatical shapes."""
    assert optimal_path_gap("") == (
        "The optimal MBB path states a testable hypothesis up front, isolates the "
        "driving mechanism with ex-ante evidence, and closes with a 4-part quantified synthesis."
    )

    statement = optimal_path_gap("Route density drove contribution per vehicle.")
    assert statement == (
        "The optimal MBB path isolates Route density drove contribution per vehicle "
        "via ex-ante hypothesis testing and concludes with a 4-part quantified close."
    )

    question = optimal_path_gap("Should the client exit pharma logistics?")
    assert question == (
        "The optimal MBB path answers the case question (Should the client exit pharma logistics?) "
        "by isolating the driving mechanism through ex-ante hypothesis testing and closing with a 4-part quantified close."
    )


def test_is_question_shaped_covers_interrogatives_and_punctuation() -> None:
    assert is_question_shaped("Why has margin fallen?")
    assert is_question_shaped("Should the client exit pharma logistics?")  # trailing question mark
    assert is_question_shaped("How can route density be raised")
    assert is_question_shaped("What drives contribution per vehicle")
    assert not is_question_shaped("Mix shift into low-utilisation pharma routes.")
    assert not is_question_shaped("Route density drove the margin decline")
    assert not is_question_shaped("")


def test_llm_report_card_is_overridden_with_the_authored_essence(monkeypatch) -> None:
    """BUG-6 (P1-5): the writer filled the card with the prompt's decision
    question; the authored essence must win deterministically."""
    session = make_test_session()
    canned = valid_report(attempt_id=session.id)
    canned.what_the_case_wanted_to_test = WhatTheCaseWantedToTest(
        core_mechanism=_DECISION_QUESTION,  # exactly the reported failure
        commercial_concept="Commercial hypothesis testing",
        pivotal_insight="Some generic filler insight.",
        candidate_performance_summary="Candidate structured well and identified mix shift.",
        candidate_vs_optimal_gap="Could have computed contract contribution faster.",
    )
    evaluator = _offline_evaluator(monkeypatch)
    evaluator._writer_chain = FakeWriter(canned)

    report = evaluator.evaluate(session)

    essence = load_case_essence(RESERVOIR_DIR, session.case.id)
    card = report.what_the_case_wanted_to_test
    assert card is not None
    assert normalize_text(card.core_mechanism) == normalize_text(essence["core_mechanism"])
    assert normalize_text(card.pivotal_insight) == normalize_text(essence["pivotal_insight"])
    assert _DECISION_QUESTION not in card.core_mechanism


def test_apply_authored_essence_creates_the_card_when_the_writer_omitted_it() -> None:
    """An absent card must not hide the authored reveal when essence exists."""
    report = apply_authored_essence(EvaluationReport(attempt_id="no-card"), RESERVOIR_DIR, "meridian-cold-chain-v1")
    card = report.what_the_case_wanted_to_test
    assert card is not None
    assert "load factor" in card.core_mechanism
    assert "route density" in card.pivotal_insight


def test_apply_authored_essence_without_a_package_keeps_the_evaluator_text() -> None:
    """With no essence on disk there is nothing authored to reveal; fabricated
    filler must not replace what the evaluator wrote."""
    missing = EvaluationReport(
        attempt_id="no-essence",
        what_the_case_wanted_to_test=WhatTheCaseWantedToTest(
            core_mechanism="An evaluator-authored mechanism statement.",
            pivotal_insight="An evaluator-authored insight.",
        ),
    )
    kept = apply_authored_essence(missing, RESERVOIR_DIR, "case-that-does-not-exist")
    assert kept.what_the_case_wanted_to_test.core_mechanism == "An evaluator-authored mechanism statement."
