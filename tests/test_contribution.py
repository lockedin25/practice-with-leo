"""The crowdsourced contribution engine.

The properties under test include the mandatory submission gate, the privacy handling of
provenance, and the rule that nothing reaches a candidate without admin approval.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.case_author import (
    ExtractedCase,
    ExtractionState,
)
from app.case_synthesis import SynthesisedCase, SynthesisedFact, build_package, slugify
from app.case_validator import validate_package
from app.store import ContributionStore
from conftest import sign_in


def _complete_extraction() -> ExtractedCase:
    return ExtractedCase(
        client_and_industry="A cold chain logistics operator.",
        situation="Revenue grew while margins fell.",
        decision_question="Why has margin fallen and what should the CEO do?",
        core_mechanism="Mix shift into low-utilisation pharma routes priced off the food cost base.",
        pivotal_insight="Volume grew while contribution per kilo collapsed to nothing.",
        common_traps=[
            "Blaming fuel inflation without testing segment cost-to-serve.",
            "Proposing an exit from pharma rather than repricing.",
        ],
    )


def _threshold_extraction() -> ExtractedCase:
    """The three anchors plus one piece of texture: exactly the 0.70 gate."""
    return ExtractedCase(
        client_and_industry="A cold chain logistics operator.",
        situation="Revenue was growing while margins were falling.",
        decision_question="Why has margin fallen and what should the CEO do?",
        core_mechanism="Mix shifted into low-utilisation routes priced off the old cost base.",
    )


# Question routing, partial evidence and turn replay are covered in
# test_contribution_loop.py. The former three-turn phase-floor tests were removed
# with the obsolete phase engine; the new flow intentionally has no phase floor.

# --- Accumulating what the contributor said ----------------------------------


def test_a_later_turn_never_discards_earlier_findings() -> None:
    """A patch adding one trap must not drop the two already captured."""
    state = _complete_extraction()

    merged = state.merge({"common_traps": ["A third trap."]})

    assert len(merged.common_traps) == 3
    assert "Blaming fuel inflation without testing segment cost-to-serve." in merged.common_traps


def test_an_empty_value_does_not_blank_a_field_already_filled() -> None:
    """A partial patch means 'nothing new', not 'erase what you knew'."""
    original = _complete_extraction()

    merged = original.merge({"core_mechanism": "", "decision_question": "   "})

    assert merged.core_mechanism == original.core_mechanism
    assert merged.decision_question == original.decision_question


def test_repeating_a_fact_does_not_duplicate_it() -> None:
    original = _complete_extraction()

    merged = original.merge({"common_traps": original.common_traps})

    assert len(merged.common_traps) == 2


def test_an_unknown_field_in_a_patch_is_ignored() -> None:
    merged = _complete_extraction().merge({"salary_expectation": "lots"})

    assert not hasattr(merged, "salary_expectation")


def test_completeness_tracks_the_required_fields() -> None:
    empty = ExtractionState()
    full = ExtractionState(extracted=_complete_extraction())

    assert empty.completeness() == 0.0
    assert full.completeness() == 1.0


def test_synthesis_threshold_is_70_percent_with_three_non_negotiable_anchors() -> None:
    extracted = _threshold_extraction()

    assert extracted.sufficiency_score() == 0.70
    assert extracted.sufficient_for_synthesis() is True
    assert extracted.missing_required(), "recoverable enrichment may still be missing"


def test_a_high_score_cannot_compensate_for_a_missing_core_anchor() -> None:
    extracted = _complete_extraction()
    extracted.core_mechanism = ""
    extracted.situation = "A detailed situation."
    extracted.quantities = ["Revenue rose by roughly a third."]
    extracted.what_it_tested = "Commercial judgement."

    assert extracted.sufficiency_score() >= 0.70
    assert extracted.sufficient_for_synthesis() is False


def test_completion_tracker_explains_every_field_behind_the_gate() -> None:
    tracker = _threshold_extraction().completion_tracker()

    assert len(tracker) == 8
    assert sum(item["mandatory_for_submit"] for item in tracker) == 4
    assert sum(item["required_for_complete"] for item in tracker) == 6
    assert sum(item["credit"] for item in tracker) == pytest.approx(0.70)
    assert {item["status"] for item in tracker} == {"captured", "missing"}


def test_a_single_trap_does_not_satisfy_the_requirement() -> None:
    partial = _complete_extraction()
    partial.common_traps = ["Only one."]

    assert "common_traps" in partial.missing_required()


def test_state_survives_a_round_trip_through_storage() -> None:
    state = ExtractionState(phase="teeth", turns=9, extracted=_complete_extraction())
    state.messages.append({"role": "agent", "content": "What pushed back?"})

    restored = ExtractionState.from_dict(state.as_dict())

    assert restored.mode == "collecting"
    assert restored.turns == 9
    assert restored.extracted.core_mechanism == state.extracted.core_mechanism
    assert restored.messages == state.messages


# --- Synthesis ---------------------------------------------------------------


def _synthesised() -> SynthesisedCase:
    return SynthesisedCase(
        title="Northwind Cold Chain",
        category="profitability",
        industry="temperature_controlled_logistics",
        difficulty="intermediate",
        opening_context="Northwind moves temperature-controlled freight.",
        opening_objective="Explain the margin decline over twelve months.",
        decision_question="Why has margin fallen?",
        core_mechanism="Mix shift into low-utilisation routes priced off a legacy cost base.",
        pivotal_insight="Volume grew while contribution per unit collapsed.",
        common_traps=["Blaming fuel.", "Proposing an exit."],
        takeaway_lesson="Price to route density.",
        hidden_diagnosis="Pharma routes carry zero contribution per kilo.",
        facts=[
            SynthesisedFact(
                id="company.identity",
                domain="company",
                release_level="opening",
                content="Northwind operates a national cold chain network.",
            ),
            SynthesisedFact(
                id="economics.rate",
                domain="economics",
                release_level="sharp_question",
                content="Realised rate is 20 per unit.",
                numeric_value=20.0,
            ),
            SynthesisedFact(
                id="economics.cost",
                domain="economics",
                release_level="sharp_question",
                content="Cost to serve is 20 per unit.",
                numeric_value=20.0,
            ),
            SynthesisedFact(
                id="economics.contribution",
                domain="economics",
                release_level="hypothesis_backed",
                content="Contribution per unit is zero.",
                numeric_value=0.0,
                formula="rate - cost",
                depends_on={"rate": "economics.rate", "cost": "economics.cost"},
            ),
        ],
    )


def test_a_synthesised_package_passes_the_validation_gate() -> None:
    package = build_package(_synthesised(), _complete_extraction(), contributor_id="u1")

    result = validate_package(package)

    assert result.passed, [f.message for f in result.errors]


def test_the_synthesised_case_is_marked_community_and_starts_unpublished() -> None:
    package = build_package(_synthesised(), _complete_extraction(), contributor_id="u1")

    assert package["case"]["source"] == "community"
    assert package["case"]["status"] == "draft"
    assert package["case"]["case_id"].startswith("community-")


def test_the_hidden_diagnosis_is_stored_interviewer_only() -> None:
    """The one release level the runtime never surfaces to a browser or a prompt."""
    package = build_package(_synthesised(), _complete_extraction(), contributor_id="u1")

    diagnosis = next(f for f in package["facts"]["facts"] if f["id"] == "diagnosis.hidden")
    assert diagnosis["release_level"] == "interviewer_only"
    released = [f for f in package["facts"]["facts"] if f["release_level"] != "interviewer_only"]
    assert all("zero contribution per kilo" not in f["content"] for f in released)


def test_the_teeth_survive_synthesis_verbatim() -> None:
    """Everything else can be regenerated; these came from a real interview."""
    extracted = _complete_extraction()
    package = build_package(_synthesised(), extracted, contributor_id="u1")

    essence = package["case"]["case_essence"]
    assert "low-utilisation" in essence["core_mechanism"]
    assert essence["pivotal_insight"]
    assert len(essence["common_traps"]) >= 2


# --- Provenance privacy ------------------------------------------------------


def test_an_over_precise_interview_date_is_truncated_to_the_month() -> None:
    """A full date plus a firm plus a round is close to identifying."""
    extracted = _complete_extraction()
    extracted.interview_month = "2026-07-14"

    package = build_package(_synthesised(), extracted, contributor_id="u1")

    assert package["case"]["provenance"]["interview_month"] == "2026-07"


def test_an_unparseable_date_is_dropped_rather_than_guessed() -> None:
    extracted = _complete_extraction()
    extracted.interview_month = "last summer"

    package = build_package(_synthesised(), extracted, contributor_id="u1")

    assert package["case"]["provenance"]["interview_month"] is None


def test_attribution_defaults_to_pseudonymous() -> None:
    """Someone in a live process must not be publicly identifiable by default."""
    package = build_package(_synthesised(), _complete_extraction(), contributor_id="u1")

    assert package["case"]["provenance"]["attribution_mode"] == "pseudonymous"
    assert package["case"]["provenance"]["contributor_id"] == "u1"


def test_a_round_is_read_out_of_free_text() -> None:
    extracted = _complete_extraction()
    extracted.interview_round = "Round 2 with a partner"

    package = build_package(_synthesised(), extracted, contributor_id="u1")

    assert package["case"]["provenance"]["round"] == 2


def test_slugify_never_produces_an_empty_identifier() -> None:
    assert slugify("") == "contributed-case"
    assert slugify("!!!") == "contributed-case"
    assert slugify("Northwind Cold Chain") == "northwind-cold-chain"


# --- Session store -----------------------------------------------------------


def test_a_contributor_may_only_have_one_live_conversation(tmp_path) -> None:
    """Enforced by a partial unique index, so two racing requests cannot both win."""
    import sqlite3

    store = ContributionStore(tmp_path / "contrib.db")
    store.create("s1", "u1", {"phase": "narration"})

    with pytest.raises(sqlite3.IntegrityError):
        store.create("s2", "u1", {"phase": "narration"})


def test_finishing_a_conversation_frees_the_contributor_to_start_another(tmp_path) -> None:
    store = ContributionStore(tmp_path / "contrib.db")
    store.create("s1", "u1", {"phase": "narration"})

    store.finish("s1", status="submitted", case_id="community-x-v1")
    store.create("s2", "u1", {"phase": "narration"})

    assert store.live_for_user("u1")["id"] == "s2"
    assert store.get("s1")["case_id"] == "community-x-v1"


def test_restarting_archives_the_old_session_and_creates_one_live_replacement(tmp_path) -> None:
    store = ContributionStore(tmp_path / "contrib.db")
    store.create("old", "u1", ExtractionState().as_dict())

    store.restart("old", "u1", "new", ExtractionState().as_dict())

    assert store.get("old")["status"] == "abandoned"
    assert store.live_for_user("u1")["id"] == "new"


def test_two_contributors_do_not_block_each_other(tmp_path) -> None:
    store = ContributionStore(tmp_path / "contrib.db")

    store.create("s1", "u1", {"phase": "narration"})
    store.create("s2", "u2", {"phase": "narration"})

    assert store.live_for_user("u1")["id"] == "s1"
    assert store.live_for_user("u2")["id"] == "s2"


# --- API ---------------------------------------------------------------------


def test_contribution_requires_sign_in() -> None:
    with TestClient(main.app) as client:
        assert client.post("/api/contributions").status_code == 401


def test_one_contributor_cannot_read_another_ones_conversation() -> None:
    """404 rather than 403, so the endpoint cannot enumerate other sessions."""
    with TestClient(main.app) as client:
        sign_in(client, "owner@example.com")
        main.CONTRIBUTIONS.create("borrowed-session", "someone-else", ExtractionState().as_dict())

        response = client.get("/api/contributions/borrowed-session")

    assert response.status_code == 404


def test_submitting_without_the_teeth_is_refused() -> None:
    """The gate is a hard stop, not a warning the contributor can click past."""
    with TestClient(main.app) as client:
        user = sign_in(client, "hollow@example.com")
        main.CONTRIBUTIONS.create("hollow-session", user.id, ExtractionState().as_dict())

        response = client.post("/api/contributions/hollow-session/submit")

    assert response.status_code == 422
    # Phrased for a person, not for the schema. See the plain-language test below.
    assert "who the client was" in response.json()["detail"]


def test_reviewed_case_can_submit_without_formal_playback(monkeypatch) -> None:
    class StubSynthesiser:
        @staticmethod
        def synthesise(extracted, *, contributor_id):
            return build_package(_synthesised(), extracted, contributor_id=contributor_id)

    monkeypatch.setattr(main, "CASE_SYNTHESISER", StubSynthesiser())
    with TestClient(main.app) as client:
        user = sign_in(client, "unconfirmed@example.com")
        state = ExtractionState(phase="structure", extracted=_threshold_extraction())
        state.closed_fields = {key: {"quote": "Nothing more", "turn": 1} for key in ExtractedCase.model_fields}
        main.CONTRIBUTIONS.create("unconfirmed-session", user.id, state.as_dict())

        response = client.post("/api/contributions/unconfirmed-session/submit")

    assert response.status_code == 200
    package = main.CASES.get_package(response.json()["case_id"], response.json()["version"])
    assert "pivotal_insight" in package["case"]["provenance"]["synthesized_fields"]
    assert "common_traps" in package["case"]["provenance"]["synthesized_fields"]


def test_a_submitted_case_is_not_playable_until_an_admin_publishes_it() -> None:
    """The single most important rule in the contribution feature."""
    package = build_package(_synthesised(), _complete_extraction(), contributor_id="u1")
    package["validation"] = validate_package(package).as_dict()
    case_id = package["case"]["case_id"]
    version = main.CASES.save_package(
        case_id, package, status="validated", contributor_id="u1"
    )
    main.reload_contributed_cases()

    with TestClient(main.app) as client:
        sign_in(client, "browser@example.com")
        library = {item["id"] for item in client.get("/api/cases").json()["cases"]}
        started = client.post("/api/attempts", json={"case_id": case_id})

    assert case_id not in library, "an unreviewed case must never appear in the library"
    assert started.status_code == 404, "and must not be startable by guessing its ID"
    assert main.CASES.get_package(case_id, version) is not None, "but it is still stored for review"


def test_publishing_makes_it_playable_and_withdrawing_takes_it_back(admin_client) -> None:
    client, _ = admin_client
    package = build_package(_synthesised(), _complete_extraction(), contributor_id="u1")
    package["validation"] = validate_package(package).as_dict()
    case_id = package["case"]["case_id"]
    version = main.CASES.save_package(
        case_id, package, status="validated", contributor_id="u1"
    )

    published = client.post(
        f"/api/admin/contributions/{case_id}/{version}/decide", json={"decision": "publish"}
    )
    after_publish = {item["id"] for item in client.get("/api/cases").json()["cases"]}

    client.post(
        f"/api/admin/contributions/{case_id}/{version}/decide", json={"decision": "withdraw"}
    )
    after_withdraw = {item["id"] for item in client.get("/api/cases").json()["cases"]}

    assert published.status_code == 200, published.text
    assert case_id in after_publish
    assert case_id not in after_withdraw, "withdrawal must actually remove it, not wait for a restart"


def test_a_case_with_blocking_errors_cannot_be_published(admin_client) -> None:
    """The reviewer may return it, but there is no route to a candidate."""
    client, _ = admin_client
    package = build_package(_synthesised(), _complete_extraction(), contributor_id="u1")
    package["facts"]["facts"][3]["numeric_value"] = 99.0  # arithmetic no longer closes
    package["validation"] = validate_package(package).as_dict()
    case_id = "community-broken-numbers-v1"
    package["case"]["case_id"] = case_id
    version = main.CASES.save_package(
        case_id, package, status="needs_changes", contributor_id="u1"
    )

    response = client.post(
        f"/api/admin/contributions/{case_id}/{version}/decide", json={"decision": "publish"}
    )

    assert response.status_code == 409
    assert "blocking validation errors" in response.json()["detail"]


def test_the_review_queue_is_admin_only() -> None:
    with TestClient(main.app) as client:
        sign_in(client, "ordinary@example.com")

        assert client.get("/api/admin/contributions").status_code == 403


# --- Page routing ------------------------------------------------------------


def test_the_contribute_page_requires_sign_in() -> None:
    with TestClient(main.app) as client:
        response = client.get("/contribute", follow_redirects=False)

    assert response.status_code == 303
    assert "/login" in response.headers["location"]
    assert "next=/contribute" in response.headers["location"]


def test_a_signed_in_contributor_gets_the_page(candidate_client) -> None:
    client, _ = candidate_client

    response = client.get("/contribute")

    assert response.status_code == 200
    assert "Talk me through it" in response.text
    assert "Start again" in response.text
    assert "Save &amp; resume later" in response.text
    assert "Case details and review progress" in response.text
    assert "revisit every section" in response.text
    assert "Improve fidelity" not in response.text


def test_pause_saves_an_unsent_draft_for_the_next_visit() -> None:
    with TestClient(main.app) as client:
        user = sign_in(client, "pause@example.com")
        main.CONTRIBUTIONS.create("pause-session", user.id, ExtractionState().as_dict())

        response = client.post(
            "/api/contributions/pause-session/pause",
            json={"draft": "I remember that the client was a regional airline."},
        )
        resumed = client.get("/api/contributions/pause-session").json()

    assert response.status_code == 200
    assert resumed["draft"] == "I remember that the client was a regional airline."


def test_reset_archives_the_old_draft_and_returns_a_clean_session(monkeypatch) -> None:
    class OpeningAuthor:
        @staticmethod
        def opening_prompt() -> str:
            return "Tell me the case from the top?"

    monkeypatch.setattr(main, "CASE_AUTHOR", OpeningAuthor())
    with TestClient(main.app) as client:
        user = sign_in(client, "reset-contribution@example.com")
        old = ExtractionState(turns=4, draft_text="unsent")
        main.CONTRIBUTIONS.create("old-contribution", user.id, old.as_dict())

        fresh = client.post("/api/contributions/old-contribution/reset").json()

    assert main.CONTRIBUTIONS.get("old-contribution")["status"] == "abandoned"
    assert fresh["id"] != "old-contribution"
    assert fresh["turns"] == 0
    assert fresh["draft"] == ""
    assert fresh["messages"][-1]["content"].endswith("?")


def test_contribute_appears_in_the_site_navigation(candidate_client) -> None:
    """A contribution flow nobody can find is a contribution flow nobody uses."""
    client, _ = candidate_client

    body = client.get("/cases").text

    assert 'href="/contribute"' in body


# --- Gap chasing -------------------------------------------------------------
#
# The reported failure: the agent summarised what it had, declared itself done,
# and offered a Submit that was then refused for fields the contributor had never
# been asked about and could not name.


# --- Human-readable gaps -----------------------------------------------------


def test_a_contributor_never_sees_a_schema_field_name() -> None:
    """They cannot answer for 'core_mechanism'; they have no idea what it is."""
    from app.case_author import describe_missing

    described = describe_missing(["core_mechanism", "pivotal_insight", "common_traps"])

    assert "core_mechanism" not in described
    assert "pivotal_insight" not in described
    assert "what was actually driving the problem underneath" in described
    assert described.count(" and ") == 1


def test_describing_one_gap_reads_naturally() -> None:
    from app.case_author import describe_missing

    assert describe_missing(["common_traps"]) == "the wrong answers that look right at first"
    assert describe_missing([]) == ""


def test_a_refused_submission_explains_itself_in_plain_language() -> None:
    with TestClient(main.app) as client:
        user = sign_in(client, "plainlanguage@example.com")
        main.CONTRIBUTIONS.create("plain-session", user.id, ExtractionState().as_dict())

        detail = client.post("/api/contributions/plain-session/submit").json()["detail"]

    assert "core_mechanism" not in detail
    assert "client_and_industry" not in detail
    assert "who the client was" in detail


def test_the_contributor_view_carries_a_readable_gap_line() -> None:
    with TestClient(main.app) as client:
        user = sign_in(client, "gapline@example.com")
        main.CONTRIBUTIONS.create("gapline-session", user.id, ExtractionState().as_dict())

        view = client.get("/api/contributions/gapline-session").json()

    assert view["missing"], "raw names stay available for the client's own logic"
    assert "who the client was" in view["missing_label"]


# --- The submit control ------------------------------------------------------


def test_a_session_below_threshold_is_never_marked_ready_to_submit() -> None:
    with TestClient(main.app) as client:
        user = sign_in(client, "notready@example.com")
        state = ExtractionState(phase="playback", ready_to_submit=True)
        main.CONTRIBUTIONS.create("notready-session", user.id, state.as_dict())

        view = client.get("/api/contributions/notready-session").json()

    assert view["can_submit"] is False
    assert view["sufficiency_score"] == 0.0


def test_the_hidden_attribute_is_defended_against_class_display_rules() -> None:
    """Regression guard for the actual bug behind the reported failure.

    `.btn { display: inline-flex }` is a class selector and outranks the user
    agent's `[hidden] { display: none }`, so the Submit button rendered and was
    clickable no matter what the state said. Without this rule the fix is a
    one-line CSS change that nothing would notice being reverted.
    """
    from pathlib import Path

    tokens = (Path(__file__).resolve().parents[1] / "app" / "static" / "tokens.css").read_text()

    assert "[hidden]" in tokens
    hidden_rule = tokens.split("[hidden]", 1)[1].split("}", 1)[0]
    assert "display: none !important" in hidden_rule


def test_the_submit_control_uses_the_server_owned_threshold() -> None:
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "app" / "static" / "contribute.js").read_text()

    assert "els.submit.hidden = !view.can_submit;" in script


def test_readiness_is_derived_from_sufficiency_not_read_back_from_storage() -> None:
    with TestClient(main.app) as client:
        user = sign_in(client, "derived@example.com")
        optimistic = ExtractionState(phase="playback", ready_to_submit=True)
        main.CONTRIBUTIONS.create("derived-session", user.id, optimistic.as_dict())

        view = client.get("/api/contributions/derived-session").json()

    assert view["ready_to_submit"] is False
    assert view["missing"]


def test_evidence_threshold_does_not_skip_followups() -> None:
    with TestClient(main.app) as client:
        user = sign_in(client, "threshold-ready@example.com")
        state = ExtractionState(extracted=_threshold_extraction())
        main.CONTRIBUTIONS.create("threshold-ready-session", user.id, state.as_dict())

        view = client.get("/api/contributions/threshold-ready-session").json()

    assert view["can_submit"] is False
    assert view["ready_to_submit"] is False
    assert view["sufficiency_score"] == 0.70
    assert view["fully_complete"] is False
    assert len(view["completion_tracker"]) == len(ExtractedCase.model_fields)
    assert "pivotal_insight" in view["missing"]
    assert "common_traps" in view["missing"]


def test_readiness_is_reported_once_the_gaps_really_are_closed() -> None:
    with TestClient(main.app) as client:
        user = sign_in(client, "genuine@example.com")
        done = ExtractionState(
            phase="playback", ready_to_submit=True, extracted=_complete_extraction()
        )
        done.closed_fields = {key: {"quote": "Nothing more", "turn": 1} for key in ExtractedCase.model_fields}
        main.CONTRIBUTIONS.create("genuine-session", user.id, done.as_dict())

        view = client.get("/api/contributions/genuine-session").json()

    assert view["ready_to_submit"] is True
    assert view["fully_complete"] is True
    assert view["missing"] == []
    assert view["missing_label"] == ""


# --- UI & Light Mode Visibility ----------------------------------------------


def test_contribute_css_uses_canonical_design_tokens_and_no_undefined_dark_fallbacks() -> None:
    """The contribute page must use system tokens so text is never invisible in light mode."""
    from pathlib import Path

    css = (Path(__file__).resolve().parents[1] / "app" / "static" / "contribute.css").read_text(
        encoding="utf-8"
    )

    # Must NOT use the undefined fallback tokens that caused light mode white-on-white text
    for undefined_token in (
        "--text-strong",
        "--text-base",
        "--text-muted",
        "--text-faint",
        "--radius-lg",
        "--radius-md",
    ):
        assert undefined_token not in css, f"Found undefined token {undefined_token} in contribute.css"

    # Must use canonical design system tokens
    assert "var(--ink-primary)" in css
    assert "var(--ink-secondary)" in css
    assert "var(--bg-surface)" in css
    assert "var(--font-serif)" in css
    assert "var(--line-base)" in css
    assert "var(--brand-primary)" in css


def test_contribute_page_renders_full_accessible_markup(candidate_client) -> None:
    """The contribute page served to candidates links stylesheets and essential UI nodes."""
    client, _ = candidate_client

    response = client.get("/contribute")

    assert response.status_code == 200
    assert "contribute.css" in response.text
    assert "contribute.js" in response.text
    assert 'id="progress"' in response.text
    assert 'id="thread"' in response.text
    assert 'id="composer"' in response.text
    assert 'id="composer-input"' in response.text
    assert 'id="start-button"' in response.text
    assert 'id="send-button"' in response.text
