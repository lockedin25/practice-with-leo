"""The evaluator agent: tool boundaries, schema discipline, BCG 1-5 scale, and leakage guards.

No test here talks to a provider. The LLM roles are stubbed; everything that
is code (tools, validators, degradation, storage, API wiring, and fallback engine)
is exercised for real, because those are the parts that must never silently leak or fabricate.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.case_runtime import CaseCatalogue, InterviewSession
from conftest import sign_in
from app.evaluator import (
    AttemptContext,
    Citation,
    ChecklistItem,
    DimensionScore,
    EvaluationReport,
    FallbackCaseEvaluator,
    GoldenRewriteTurn,
    LangChainCaseEvaluator,
    SuggestedReading,
    WhatTheCaseWantedToTest,
    MAX_TOOL_CALLS,
    RECURSION_LIMIT,
    build_attempt_context,
    build_tools,
    citation_violations,
    completeness_violations,
    create_evaluator,
    find_leakage,
    generate_fallback_evaluation,
    load_checklist,
    load_issue_tree,
    load_rubric,
    normalize_text,
    private_fact_contents,
    private_strings,
    quote_is_verbatim,
    read_messages_window,
    weighted_overall,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = CaseCatalogue.from_reservoir(ROOT)
CHECKLIST_IDS = [item["id"] for item in load_checklist()["items"]]
DIMENSIONS = ["structuring", "problem_solving", "quantitative", "synthesis", "communication"]

# Private strings from the Meridian package that must never reach a report.
TREE_CONCLUSION = "Pharma earns no contribution despite a higher selling price."
UNDISCLOSED_FACT_SNIPPET = "priced off the food cost base"


def make_session() -> InterviewSession:
    session = InterviewSession(id="eval-fixture", case=CATALOGUE.get("meridian-cold-chain-v1"), mode="realistic")
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
    session.ended = True
    return session


class FakeComparator:
    def __call__(self, claim: str):
        from app.evaluator import ClaimVerdict

        return ClaimVerdict(verdict="agrees", branch_ids=["pricing", "ghost-branch"], rationale="Matches the key.")


def make_context(session: InterviewSession) -> AttemptContext:
    return build_attempt_context(
        session,
        checklist_items=load_checklist()["items"],
        issue_tree=load_issue_tree(ROOT / "reservoir", session.case.id),
        comparator=FakeComparator(),
        reservoir_root=ROOT / "reservoir",
    )


def valid_report(attempt_id: str = "eval-fixture", quote: str = "restate the objective") -> EvaluationReport:
    scores = {
        "structuring": 4.0,
        "problem_solving": 3.5,
        "quantitative": 3.0,
        "synthesis": 4.0,
        "communication": 4.5,
    }
    dimensions = [
        DimensionScore(
            name=name,
            score=scores[name],
            band="Top 1% MBB" if scores[name] >= 3.8 else "Meets Bar",
            evidence=[Citation(message_index=1, quote=quote)],
            observations=["Structured the opening around price and volume."],
            improvements=["Tie each branch to a metric."],
            confidence="high",
        )
        for name in DIMENSIONS
    ]
    checklist = [
        ChecklistItem(id=item_id, title=item_id, status="not_applicable", note="")
        for item_id in CHECKLIST_IDS
    ]
    what_tested = WhatTheCaseWantedToTest(
        core_mechanism="Route density and contract mix shift",
        commercial_concept="Pricing vs contribution margin",
        pivotal_insight="Pharma contracts yield negative contribution",
        candidate_performance_summary="Candidate structured well and identified mix shift.",
        candidate_vs_optimal_gap="Could have computed contract contribution faster.",
    )
    golden_rewrites = [
        GoldenRewriteTurn(
            stage="opening",
            phase="opening",
            candidate_turn="Let me restate the objective: explain why EBITDA margin fell...",
            candidate_message_index=1,
            mbb_partner_turn="Our objective is to evaluate EBITDA margin under 3 MECE pillars...",
            diagnostic_notes=["Clarifies objective and confirms timeline."],
        ),
        GoldenRewriteTurn(
            stage="closing",
            phase="closing",
            candidate_turn="In conclusion, pharma is dragging down profits...",
            candidate_message_index=3,
            mbb_partner_turn="We recommend 3 pillars: pricing reform, route density, cost optimization...",
            diagnostic_notes=["4-part Pyramid Principle recommendation."],
        ),
    ]
    return EvaluationReport(
        attempt_id=attempt_id,
        overall_score=3.8,
        mbb_rating_badge="Strong Pass",
        overall_band="Top 1% MBB",
        executive_summary="Candidate demonstrated solid structuring and hypothesis-driven problem solving.",
        what_the_case_wanted_to_test=what_tested,
        dimensions=dimensions,
        checklist=checklist,
        golden_rewrites=golden_rewrites,
        headline_strengths=["Restated the objective before structuring."],
        priority_improvements=["State a hypothesis before requesting evidence."],
        targeted_drill="Run one profitability tree against a public company in five minutes.",
        next_drill="Run one profitability tree against a public company in five minutes.",
        suggested_readings=[
            SuggestedReading(
                title="Issue Tree Structuring",
                path="knowledge_base/methodology/02_issue_tree_structuring.md",
                why_relevant="Core MECE structuring guide",
            )
        ],
    )


# --- Deterministic helpers ---------------------------------------------------


def test_read_window_clamps_bounds_and_caps_size() -> None:
    messages = [{"role": "candidate", "content": f"m{i}"} for i in range(30)]

    window = read_messages_window(messages, 25, 400)

    assert [item["index"] for item in window] == list(range(25, 30))
    capped = read_messages_window(messages, 0, 29)
    assert len(capped) == 12
    assert read_messages_window([], 0, 5) == []


def test_quote_verification_requires_a_verbatim_match() -> None:
    messages = [{"role": "candidate", "content": "Revenue splits into price and volume effects."}]

    assert quote_is_verbatim(messages, 0, "price and volume effects")
    assert not quote_is_verbatim(messages, 0, "cost and volume effects")
    assert not quote_is_verbatim(messages, 9, "price")
    assert not quote_is_verbatim(messages, 0, "   ")


def test_private_strings_cover_undisclosed_facts_and_the_issue_tree() -> None:
    session = make_session()
    context = make_context(session)
    undisclosed = context.undisclosed_fact_contents() + private_fact_contents(ROOT / "reservoir", session)

    forbidden = private_strings(context.issue_tree, undisclosed)

    assert any(TREE_CONCLUSION.lower() in text for text in forbidden)
    assert any(UNDISCLOSED_FACT_SNIPPET in text for text in forbidden)
    released = next(
        fact.content for fact in context.session.case.facts if fact.id == "customers.segment-mix"
    )
    assert normalize_text(released) not in forbidden


def test_find_leakage_detects_private_content_in_report_text() -> None:
    context = make_context(make_session())
    forbidden = private_strings(context.issue_tree, context.undisclosed_fact_contents())

    leaks = find_leakage(["The candidate missed that " + TREE_CONCLUSION], forbidden)

    assert len(leaks) == 1
    assert find_leakage(["Clean feedback about structure."], forbidden) == set()


def test_citation_violations_flag_bad_indexes_and_paraphrases() -> None:
    session = make_session()
    report = valid_report()
    report.dimensions[0].evidence.append(Citation(message_index=99, quote="anything"))
    report.dimensions[1].evidence.append(Citation(message_index=1, quote="words never spoken"))

    violations = citation_violations(report, session.messages)

    assert len(violations) == 2


def test_completeness_requires_every_dimension_and_checklist_item() -> None:
    assert completeness_violations(valid_report(), CHECKLIST_IDS) == []

    missing_dimension = valid_report()
    missing_dimension.dimensions = missing_dimension.dimensions[:3]
    assert any("dimensions" in violation for violation in completeness_violations(missing_dimension, CHECKLIST_IDS))

    missing_item = valid_report()
    missing_item.checklist = missing_item.checklist[:-1]
    assert completeness_violations(missing_item, CHECKLIST_IDS)

    unevidenced = valid_report()
    unevidenced.checklist[0].status = "demonstrated"
    assert any("cites nothing" in violation for violation in completeness_violations(unevidenced, CHECKLIST_IDS))


def test_weighted_overall_redistributes_when_quantitative_is_unassessed() -> None:
    rubric = load_rubric()

    graded = weighted_overall(valid_report(), rubric)
    assert graded["assessed_dimensions"] == DIMENSIONS

    without_quant_evidence = [
        (
            dimension
            if dimension.name != "quantitative"
            else DimensionScore(name=dimension.name, score=0, band="Below Bar", confidence="low")
        )
        for dimension in valid_report().dimensions
    ]
    partial = weighted_overall(
        valid_report().model_copy(update={"dimensions": without_quant_evidence}), rubric
    )

    assert partial["excluded_dimensions"] == ["quantitative"]
    # Structuring 4.0 x .25, problem solving 3.5 x .25, synthesis 4.0 x .20, communication 4.5 x .15 over 0.85 weight
    expected = round((4.0 * 0.25 + 3.5 * 0.25 + 4.0 * 0.20 + 4.5 * 0.15) / 0.85, 2)
    assert partial["overall"] == expected


# --- Tools ---------------------------------------------------------------------


def test_tools_expose_only_candidate_visible_data() -> None:
    tools = {tool.name: tool for tool in build_tools(make_context(make_session()))}

    released = json.loads(tools["get_released_facts"].invoke({}))
    assert [fact["id"] for fact in released] == ["customers.segment-mix"]

    case_context = str(json.loads(tools["get_case_context"].invoke({}))).lower()
    assert UNDISCLOSED_FACT_SNIPPET not in case_context
    assert TREE_CONCLUSION.lower() not in case_context

    verdict = json.loads(tools["compare_to_answer_key"].invoke({"claim": "pharma pricing is wrong"}))
    assert verdict["verdict"] == "agrees"
    assert all(set(branch) == {"id", "type", "status"} for branch in verdict["branches"])
    assert [branch["id"] for branch in verdict["branches"]] == ["pricing"]

    assert json.loads(tools["verify_citation"].invoke({"message_index": 1, "quote": "objective"})) == {"valid": True}
    window = json.loads(tools["read_messages"].invoke({"from_index": 0, "to_index": 1}))
    assert [item["index"] for item in window] == [0, 1]


# --- Degradation and the offline agent ------------------------------------------


def _offline_evaluator(monkeypatch) -> LangChainCaseEvaluator:
    monkeypatch.setenv("OPENROUTER_API_KEY", "construction-only")
    evaluator = LangChainCaseEvaluator(ROOT / "reservoir")

    def no_planner(agent, context):
        return []

    evaluator._run_planner = no_planner
    return evaluator


class FakeWriter:
    def __init__(self, report: EvaluationReport) -> None:
        self.report = report
        self.calls = 0

    def invoke(self, messages) -> EvaluationReport:
        self.calls += 1
        return self.report


def test_loop_is_hard_bounded_by_configuration() -> None:
    assert MAX_TOOL_CALLS == 24
    assert RECURSION_LIMIT > MAX_TOOL_CALLS * 2


def test_a_clean_report_passes_through_with_version_stamped(monkeypatch) -> None:
    evaluator = _offline_evaluator(monkeypatch)
    evaluator._writer_chain = FakeWriter(valid_report())

    report = evaluator.evaluate(make_session())

    assert report.evaluator_version.startswith("evaluator-v2|rubric=rubric-v2|checklist=checklist-v2|model=")
    assert report.dimensions[0].score == 4.0
    assert report.headline_strengths == ["Restated the objective before structuring."]
    assert report.mbb_rating_badge == "Strong Pass"


def test_invalid_citations_are_stripped_and_confidence_downgraded(monkeypatch) -> None:
    evaluator = _offline_evaluator(monkeypatch)
    canned = valid_report()
    canned.dimensions[0].evidence.append(Citation(message_index=42, quote="never said"))
    canned.dimensions[1].evidence = []
    writer = FakeWriter(canned)
    evaluator._writer_chain = writer

    report = evaluator.evaluate(make_session())

    structuring = next(d for d in report.dimensions if d.name == "structuring")
    problem_solving = next(d for d in report.dimensions if d.name == "problem_solving")
    assert len(structuring.evidence) == 1
    assert problem_solving.confidence == "low"
    assert any("could not be verified" in observation for observation in problem_solving.observations)
    assert writer.calls == 2


def test_leaked_private_content_is_redacted_before_publication(monkeypatch) -> None:
    evaluator = _offline_evaluator(monkeypatch)
    canned = valid_report()
    canned.priority_improvements = ["Address why " + TREE_CONCLUSION + "."]
    evaluator._writer_chain = FakeWriter(canned)

    report = evaluator.evaluate(make_session())

    assert TREE_CONCLUSION.lower() not in str(report.model_dump()).lower()
    assert "[withheld by leakage guard]" in report.priority_improvements[0]


def test_em_dashes_never_reach_the_published_report(monkeypatch) -> None:
    evaluator = _offline_evaluator(monkeypatch)
    canned = valid_report()
    canned.next_drill = "Practise one tree\u2014then synthesise."
    evaluator._writer_chain = FakeWriter(canned)

    report = evaluator.evaluate(make_session())

    assert "\u2014" not in report.next_drill


# --- Fallback Heuristic Evaluator ----------------------------------------------


def test_fallback_evaluator_produces_rich_report_on_valid_session() -> None:
    session = make_session()
    evaluator = FallbackCaseEvaluator(ROOT / "reservoir")
    report = evaluator.evaluate(session)

    assert report.attempt_id == session.id
    assert report.overall_score >= 1.0 and report.overall_score <= 5.0
    assert report.mbb_rating_badge in ("Distinction", "Strong Pass", "Meets Bar", "Developing", "Needs Substantial Practice")
    assert report.overall_band in ("Top 1% MBB", "Meets Bar", "Below Bar")
    assert len(report.dimensions) == 5
    assert len(report.golden_rewrites) >= 2
    assert report.what_the_case_wanted_to_test is not None
    assert len(report.strengths) >= 2
    assert len(report.areas_for_development) >= 2
    assert report.targeted_drill != ""
    assert len(report.suggested_readings) >= 1

    # Verify dimension sync
    assert "structuring" in report.dimension_scores
    assert "synthesis" in report.dimension_scores
    assert report.dimension_scores["structuring"].score == report.dimensions[0].score


def test_create_evaluator_supports_fallback_flag(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_evaluator(ROOT / "reservoir", allow_fallback=False)

    fallback_eval = create_evaluator(ROOT / "reservoir", allow_fallback=True)
    assert isinstance(fallback_eval, FallbackCaseEvaluator)


# --- API surface ----------------------------------------------------------------


class StubEvaluator:
    """Scripted double for the HTTP layer; each run stamps a new version."""

    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, session: InterviewSession) -> EvaluationReport:
        self.calls += 1
        quote = session.messages[1]["content"][:25] if len(session.messages) > 1 else session.messages[0]["content"][:25]
        report = valid_report(attempt_id=session.id, quote=quote)
        report.evaluator_version = f"stub-v{self.calls}"
        return report

    def overall(self, report: EvaluationReport):
        return weighted_overall(report, load_rubric())


@pytest.fixture
def evaluation_api(monkeypatch, stub_interviewer):
    stub = StubEvaluator()
    previous = main.app.state.evaluator
    monkeypatch.setattr(main, "EVALUATOR", stub)
    main.app.state.evaluator = stub
    client = TestClient(main.app)
    # Fresh candidate per fixture use: one open attempt per user and case is
    # intended, so a shared identity 409s on the second test to use this.
    sign_in(client, f"evaluator-api-{uuid4()}@casecall.test")
    started = client.post("/api/attempts", json={})
    assert started.status_code == 200
    attempt_id = started.json()["id"]
    turn = client.post(
        f"/api/attempts/{attempt_id}/turn",
        json={"content": "Is the decline driven by revenue or by cost?", "turn_id": "t1"},
    )
    assert turn.status_code == 200
    yield client, attempt_id, stub
    main.app.state.evaluator = previous


def test_end_returns_the_evaluation_report_and_stores_it(evaluation_api) -> None:
    client, attempt_id, stub = evaluation_api

    ended = client.post(f"/api/attempts/{attempt_id}/end")

    assert ended.status_code == 200
    body = ended.json()
    assert body["evaluation"]["attempt_id"] == attempt_id
    assert [dimension["name"] for dimension in body["evaluation"]["dimensions"]] == DIMENSIONS
    assert len(body["evaluation"]["checklist"]) == len(CHECKLIST_IDS)
    assert body["evaluation"]["overall"]["assessed_dimensions"] == DIMENSIONS
    assert stub.calls == 1

    fetched = client.get(f"/api/attempts/{attempt_id}/evaluation")
    assert fetched.status_code == 200
    stored = fetched.json()
    assert stored["report"]["attempt_id"] == attempt_id
    assert stored["report"]["evaluator_version"] == body["evaluation"]["evaluator_version"]
    assert stored["overall"]["assessed_dimensions"] == DIMENSIONS
    assert stub.calls == 1


def test_evaluation_of_an_open_attempt_is_rejected(evaluation_api) -> None:
    # The fixture's attempt has taken a turn but has never been ended, so it is
    # already the open attempt this test needs. Starting a second one would be
    # refused anyway: one attempt per candidate per case.
    client, attempt_id, _ = evaluation_api

    response = client.get(f"/api/attempts/{attempt_id}/evaluation")

    assert response.status_code == 409


def test_an_attempt_ending_while_the_evaluator_is_down_still_gets_a_full_debrief(monkeypatch) -> None:
    monkeypatch.setattr(main, "EVALUATOR", None)
    main.app.state.evaluator = None
    client = TestClient(main.app)
    sign_in(client, "offline@casecall.test")
    started = client.post("/api/attempts", json={}).json()

    ended = client.post(f"/api/attempts/{started['id']}/end")
    fetch = client.get(f"/api/attempts/{started['id']}/evaluation")

    assert ended.status_code == 200
    assert "fallback=true" in ended.json()["evaluation"]["evaluator_version"]
    assert ended.json()["scorecard"]["dimensions"]
    assert fetch.status_code == 200
    report = fetch.json()["report"]
    assert len(report["dimensions"]) == 5
    assert report["executive_summary"]
    assert report["what_the_case_wanted_to_test"]
    assert report["golden_rewrites"]
    assert report["targeted_drill"]


def test_admin_re_evaluation_builds_versioned_history(admin_client, monkeypatch) -> None:
    client, _ = admin_client
    stub = StubEvaluator()
    previous = main.app.state.evaluator
    monkeypatch.setattr(main, "EVALUATOR", stub)
    main.app.state.evaluator = stub
    try:
        candidate = TestClient(main.app)
        sign_in(candidate, "history@casecall.test")
        attempt_id = candidate.post("/api/attempts", json={}).json()["id"]
        session = main.STORE.get(attempt_id, main.CATALOGUE)
        session.ended = True
        main.STORE.save(session)

        first = client.post(f"/api/admin/attempts/{attempt_id}/evaluate")
        second = client.post(f"/api/admin/attempts/{attempt_id}/evaluate")

        assert first.status_code == 200
        assert second.status_code == 200
        versions = [row["evaluator_version"] for row in second.json()["versions"]]
        assert versions == ["stub-v2", "stub-v1"]
    finally:
        main.app.state.evaluator = previous


def test_admin_re_evaluation_requires_a_finished_attempt(admin_client) -> None:
    client, _ = admin_client
    stub = StubEvaluator()
    main.app.state.evaluator = stub
    candidate = TestClient(main.app)
    sign_in(candidate, "unfinished@casecall.test")
    attempt_id = candidate.post("/api/attempts", json={}).json()["id"]

    response = client.post(f"/api/admin/attempts/{attempt_id}/evaluate")

    assert response.status_code == 409


# --- Debrief page ---------------------------------------------------------------


def test_the_debrief_page_sends_anonymous_visitors_to_sign_in() -> None:
    client = TestClient(main.app)

    response = client.get("/attempts/some-id/debrief", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    assert "debrief" in response.headers["location"]


def test_a_signed_in_candidate_gets_the_debrief_page_shell(evaluation_api) -> None:
    client, attempt_id, _ = evaluation_api

    response = client.get(f"/attempts/{attempt_id}/debrief")

    assert response.status_code == 200
    assert "debrief-report" in response.text
    assert "Restated the objective" not in response.text


# --- Edge cases and rich model sync tests --------------------------------------


def test_evaluation_report_bidirectional_sync() -> None:
    from app.evaluator import compute_mbb_rating_badge, compute_overall_band

    report = valid_report()
    assert len(report.dimension_scores) == 5
    assert "structuring" in report.dimension_scores
    assert report.dimension_scores["structuring"].score == 4.0

    # Test list from dict sync
    dict_only = EvaluationReport(
        attempt_id="dict-sync",
        dimension_scores={
            "structuring": DimensionScore(name="structuring", score=4.5, band="Top 1% MBB"),
            "problem_solving": DimensionScore(name="problem_solving", score=4.0, band="Top 1% MBB"),
            "quantitative": DimensionScore(name="quantitative", score=3.8, band="Top 1% MBB"),
            "synthesis": DimensionScore(name="synthesis", score=4.2, band="Top 1% MBB"),
            "communication": DimensionScore(name="communication", score=4.0, band="Top 1% MBB"),
        },
        strengths=["Great structuring"],
        areas_for_development=["Sharpen synthesis"],
        targeted_drill="Drill 1",
    )
    assert len(dict_only.dimensions) == 5
    assert dict_only.headline_strengths == ["Great structuring"]
    assert dict_only.priority_improvements == ["Sharpen synthesis"]
    assert dict_only.next_drill == "Drill 1"
    assert dict_only.overall_score >= 4.0


def test_compute_mbb_rating_badge_and_overall_band() -> None:
    from app.evaluator import compute_mbb_rating_badge, compute_overall_band

    assert compute_mbb_rating_badge(4.8) == "Distinction"
    assert compute_mbb_rating_badge(4.0) == "Strong Pass"
    assert compute_mbb_rating_badge(3.2) == "Meets Bar"
    assert compute_mbb_rating_badge(2.2) == "Developing"
    assert compute_mbb_rating_badge(1.5) == "Needs Substantial Practice"

    assert compute_overall_band(4.8) == "Top 1% MBB"
    assert compute_overall_band(3.2) == "Meets Bar"
    assert compute_overall_band(1.8) == "Below Bar"


def test_fallback_evaluator_empty_session() -> None:
    session = InterviewSession(id="empty-fixture", case=CATALOGUE.get("meridian-cold-chain-v1"), mode="realistic")
    session.ended = True

    evaluator = FallbackCaseEvaluator(ROOT / "reservoir")
    report = evaluator.evaluate(session)

    assert report.attempt_id == "empty-fixture"
    assert report.overall_score == 1.0
    assert report.mbb_rating_badge == "Needs Substantial Practice"
    assert report.overall_band == "Below Bar"
    assert all(d.score == 1.0 for d in report.dimensions)


def test_golden_rewrite_sync_fields() -> None:
    rw = GoldenRewriteTurn(
        stage="opening",
        candidate_turn="My opening",
        mbb_partner_turn="Partner opening",
        diagnostic_notes=["Note 1"],
    )
    assert rw.phase == "opening"
    assert rw.golden_mbb_turn == "Partner opening"
    assert rw.consulting_craft_delta == ["Note 1"]
