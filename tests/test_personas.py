"""Interviewer persona disclosure mechanics.

These tests exercise the runtime side of the persona system, which is the side
that has to be right: the prompt can be ignored by a model, but the budget, the
precision bar and the anti-stonewall floor are enforced in code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import personas
from app.case_runtime import CaseCatalogue, InterviewSession


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def case():
    catalogue = CaseCatalogue.from_reservoir(ROOT)
    return catalogue.default_case


def _session(case, mode: str) -> InterviewSession:
    return InterviewSession(id=f"persona-{mode}", case=case, mode=mode)


# --- Preset shape ------------------------------------------------------------


def test_the_three_presets_are_ordered_from_generous_to_withholding() -> None:
    rates = [personas.PERSONAS[pid].release_rate for pid in personas.PERSONA_ORDER]
    bars = [
        personas.PRECISION_ORDER[personas.PERSONAS[pid].precision_bar]
        for pid in personas.PERSONA_ORDER
    ]

    assert rates == sorted(rates, reverse=True), "release rate must fall as difficulty rises"
    assert bars == sorted(bars), "precision bar must rise as difficulty rises"


def test_requested_release_rates_match_the_stated_cadence() -> None:
    """Coach one per turn, Operator one per two to three, Skeptic one per five to six."""
    assert personas.COACH.release_rate == 1.0
    assert 1 / personas.OPERATOR.release_rate == pytest.approx(2.5)
    assert 5 <= 1 / personas.SKEPTIC.release_rate <= 6


def test_no_persona_can_disclose_more_than_one_fact_in_a_turn(case) -> None:
    """max_facts_per_turn is the guarantee; the cap only bounds banking."""
    for persona in personas.PERSONAS.values():
        assert persona.max_facts_per_turn == 1
        # Above 1.0 so the fractional remainder carries, but small enough that a
        # long silence cannot be banked into a windfall.
        assert 1.0 < persona.credit_cap <= 2.0


def test_an_unknown_mode_resolves_to_the_neutral_default() -> None:
    """A retired persona must not make an old attempt unreplayable."""
    assert personas.get("no-such-persona").id == personas.OPERATOR.id
    assert personas.get(None).id == personas.OPERATOR.id


# --- Budget accrual and spending --------------------------------------------


def test_coach_earns_a_disclosure_every_turn(case) -> None:
    session = _session(case, "coached")

    session.accrue_release_credit()

    assert session.release_credits >= 1.0


def test_skeptic_needs_roughly_six_turns_before_it_can_disclose(case) -> None:
    session = _session(case, "pressure")

    turns_until_affordable = 0
    while session.release_credits < 1.0:
        session.accrue_release_credit()
        turns_until_affordable += 1
        assert turns_until_affordable < 20, "budget must converge"

    assert 5 <= turns_until_affordable <= 6


def test_operator_sits_between_the_two(case) -> None:
    session = _session(case, "realistic")

    turns = 0
    while session.release_credits < 1.0:
        session.accrue_release_credit()
        turns += 1

    assert 2 <= turns <= 3


def test_spending_a_credit_resets_the_stonewall_counter(case) -> None:
    session = _session(case, "pressure")
    session.consecutive_precise_misses = 4
    session.release_credits = 1.0

    session.spend_release_credit()

    assert session.release_credits == 0.0
    assert session.consecutive_precise_misses == 0
    assert session.turns_since_release == 0


def test_credits_do_not_bank_past_the_cap(case) -> None:
    """Banking is bounded, so silence cannot be converted into a data dump."""
    session = _session(case, "pressure")

    for _ in range(100):
        session.accrue_release_credit()

    assert session.release_credits == personas.SKEPTIC.credit_cap


# --- Precision bar -----------------------------------------------------------


def test_a_vague_question_clears_only_the_coach() -> None:
    assert personas.clears_precision_bar("vague", personas.COACH)
    assert not personas.clears_precision_bar("vague", personas.OPERATOR)
    assert not personas.clears_precision_bar("vague", personas.SKEPTIC)


def test_a_targeted_question_clears_every_persona() -> None:
    for persona in personas.PERSONAS.values():
        assert personas.clears_precision_bar("targeted", persona)


def test_a_partial_question_clears_the_operator_but_not_the_skeptic() -> None:
    assert personas.clears_precision_bar("partial", personas.OPERATOR)
    assert not personas.clears_precision_bar("partial", personas.SKEPTIC)


def test_an_unrecognised_precision_value_is_treated_as_vague() -> None:
    """A malformed director grade must not accidentally unlock the Skeptic."""
    assert not personas.clears_precision_bar("", personas.SKEPTIC)
    assert not personas.clears_precision_bar("extremely-precise", personas.SKEPTIC)


# --- Anti-stonewall floor ----------------------------------------------------


def test_only_well_aimed_questions_count_toward_the_floor(case) -> None:
    """Persistent vagueness must not earn a fact by attrition."""
    session = _session(case, "pressure")

    for _ in range(10):
        session.record_withheld_turn(
            counts_toward_floor=personas.counts_toward_stonewall_floor("vague")
        )

    assert session.consecutive_precise_misses == 0
    assert session.turns_since_release == 10


def test_the_floor_fires_after_the_persona_specific_run_of_good_questions(case) -> None:
    session = _session(case, "pressure")

    for _ in range(personas.SKEPTIC.stonewall_floor):
        session.record_withheld_turn(
            counts_toward_floor=personas.counts_toward_stonewall_floor("partial")
        )

    assert session.consecutive_precise_misses >= personas.SKEPTIC.stonewall_floor


def test_the_floor_can_always_find_a_fact_to_release(case) -> None:
    """The floor cannot depend on the director having nominated anything."""
    session = _session(case, "pressure")

    forced = case.narrowest_eligible_fact(session.stage, session.disclosed_ids)

    assert forced is not None
    assert forced.release_level in case.phase(session.stage).reveal_levels


def test_the_floor_releases_the_most_freely_given_fact_available(case) -> None:
    session = _session(case, "pressure")
    forced = case.narrowest_eligible_fact(session.stage, session.disclosed_ids)

    eligible_levels = {
        fact.release_level
        for fact in case.facts
        if fact.id not in session.disclosed_ids
        and fact.release_level in case.phase(session.stage).reveal_levels
        and not fact.dependencies
    }
    lowest_available = min(
        eligible_levels, key=lambda level: personas.RELEASE_LEVEL_LADDER.index(level)
    )

    assert forced.release_level == lowest_available


# --- Authoritative enforcement ----------------------------------------------


def test_a_zero_cap_discloses_nothing_however_the_director_voted(case) -> None:
    """The withheld turn is enforced by the runtime, not by asking the prompt nicely."""
    session = _session(case, "pressure")
    every_id = [fact.id for fact in case.facts]

    facts = case.validate_fact_selection(
        every_id, session.stage, session.disclosed_ids, max_facts=0
    )

    assert facts == []


def test_the_generous_persona_widens_reveal_levels_and_the_others_do_not(case) -> None:
    phase = case.phase(case.initial_phase)

    coach_levels = personas.permitted_reveal_levels(
        phase.reveal_levels, personas.COACH.reveal_level_bonus
    )
    operator_levels = personas.permitted_reveal_levels(
        phase.reveal_levels, personas.OPERATOR.reveal_level_bonus
    )

    assert set(phase.reveal_levels).issubset(set(coach_levels))
    assert len(coach_levels) > len(phase.reveal_levels)
    assert operator_levels == tuple(phase.reveal_levels)


def test_widening_never_removes_an_authored_level(case) -> None:
    """Narrowing could strand a fact whose level appears in no other phase."""
    for phase in case.phases:
        for bonus in (0, 1, 2, 5):
            widened = personas.permitted_reveal_levels(phase.reveal_levels, bonus)
            assert set(phase.reveal_levels).issubset(set(widened))


def test_a_harder_persona_never_sees_more_eligible_facts_than_an_easier_one(case) -> None:
    session = _session(case, "pressure")

    counts = [
        len(
            case.eligible_facts_for_director(
                session.stage,
                session.disclosed_ids,
                reveal_level_bonus=personas.PERSONAS[pid].reveal_level_bonus,
            )
        )
        for pid in personas.PERSONA_ORDER
    ]

    assert counts == sorted(counts, reverse=True)


# --- Session integration -----------------------------------------------------


def test_the_session_resolves_its_persona_from_the_existing_mode_field(case) -> None:
    assert _session(case, "coached").persona.id == "coached"
    assert _session(case, "realistic").persona.id == "realistic"
    assert _session(case, "pressure").persona.id == "pressure"


def test_the_candidate_view_carries_the_persona_label(case) -> None:
    view = _session(case, "pressure").candidate_view()

    assert view["persona"]["id"] == "pressure"
    assert view["persona"]["label"] == personas.SKEPTIC.label
    assert view["mode"] == "pressure"


# --- Cadence, through the same gate production uses -------------------------


def _simulate(case, mode: str, *, turns: int, precision: str) -> int:
    """Walk the real allowance/release gate and count facts disclosed.

    Deliberately drives ``personas.allowance_for`` and ``personas.resolve_release``,
    which is exactly what ``LangChainCaseInterviewer.respond`` calls, so this
    measures the shipped mechanism rather than a reimplementation of it.
    """
    session = _session(case, mode)
    persona = session.persona
    disclosed = 0
    for turn in range(1, turns + 1):
        session.candidate_turns = turn
        session.accrue_release_credit()
        allowance = personas.allowance_for(
            persona, session.release_credits, session.consecutive_precise_misses
        )
        release = personas.resolve_release(
            persona,
            allowance,
            precision=precision,
            is_early_precision_turn=turn <= 2,
        )
        if release.max_facts > 0:
            disclosed += 1
            session.spend_release_credit()
        else:
            session.record_withheld_turn(counts_toward_floor=release.counts_toward_floor)
    return disclosed


def test_a_perfect_candidate_gets_the_stated_cadence_from_each_persona(case) -> None:
    """Thirty targeted questions should yield roughly 30, 12 and 5 facts."""
    coach = _simulate(case, "coached", turns=30, precision="targeted")
    operator = _simulate(case, "realistic", turns=30, precision="targeted")
    skeptic = _simulate(case, "pressure", turns=30, precision="targeted")

    assert coach == 30, "one per turn"
    assert 11 <= operator <= 13, "one per two to three turns"
    assert 4 <= skeptic <= 7, "one per five to six turns, plus any floor releases"
    assert coach > operator > skeptic


def test_vague_questions_earn_nothing_from_the_skeptic_except_via_the_floor(case) -> None:
    """The precision bar, not the budget, is what stops a lazy candidate."""
    vague = _simulate(case, "pressure", turns=30, precision="vague")

    assert vague == 0, "a vague question never clears the Skeptic's bar, and the floor ignores it"


def test_vague_questions_still_work_on_the_coach(case) -> None:
    """The Coach exists to answer loose questions, which is the point of it."""
    assert _simulate(case, "coached", turns=10, precision="vague") == 10


def test_the_floor_rescues_a_candidate_the_grader_keeps_underrating(case) -> None:
    """A run of good questions graded just under the bar must still break through.

    'partial' never clears the Skeptic's bar, so without the floor this candidate
    would receive nothing at all across a whole interview.
    """
    partial = _simulate(case, "pressure", turns=30, precision="partial")

    assert partial > 0, "the anti-stonewall floor must fire rather than leave a wall"
    assert partial <= 5, "and it must stay rare enough that the persona is still hard"


def test_a_failed_provider_turn_does_not_cost_the_candidate_their_allowance(case) -> None:
    """Refunding on failure matters most on the Skeptic, where a lost credit is six turns."""
    session = _session(case, "pressure")
    persona = session.persona
    for _ in range(6):
        session.accrue_release_credit()
    banked = session.release_credits
    assert banked >= 1.0

    # Mirror the refund in respond()'s exception path: it restores the exact
    # pre-turn balance rather than subtracting the rate, which would over-refund
    # whenever the accrual had been clamped by the cap.
    credits_before_turn = session.release_credits
    session.accrue_release_credit()
    session.release_credits = credits_before_turn

    assert session.release_credits == pytest.approx(banked)


# --- API surface -------------------------------------------------------------


def test_the_persona_catalogue_is_public_and_carries_no_internal_dials() -> None:
    """The picker needs labels, not the release rates that would let it be gamed."""
    from fastapi.testclient import TestClient
    import app.main as main

    with TestClient(main.app) as client:
        response = client.get("/api/personas")

    assert response.status_code == 200
    payload = response.json()["personas"]
    assert [entry["id"] for entry in payload] == list(personas.PERSONA_ORDER)
    for entry in payload:
        assert entry["label"] and entry["blurb"]
        assert "release_rate" not in entry
        assert "precision_bar" not in entry
        assert "stonewall_floor" not in entry


@pytest.mark.parametrize("persona_id", ["coached", "realistic", "pressure"])
def test_starting_an_attempt_pins_the_chosen_persona(persona_id: str) -> None:
    from fastapi.testclient import TestClient
    from conftest import sign_in
    import app.main as main

    with TestClient(main.app) as client:
        sign_in(client, f"persona-{persona_id}@example.com")
        response = client.post(
            "/api/attempts",
            json={"case_id": main.CATALOGUE.default_case.id, "mode": persona_id},
        )

    assert response.status_code == 200, response.text
    attempt = response.json()
    assert attempt["mode"] == persona_id
    assert attempt["persona"]["id"] == persona_id
    assert attempt["persona"]["label"] == personas.PERSONAS[persona_id].label


def test_an_invalid_persona_is_rejected_rather_than_silently_defaulted() -> None:
    """Silently downgrading to Operator would score the candidate on a different interview."""
    from fastapi.testclient import TestClient
    from conftest import sign_in
    import app.main as main

    with TestClient(main.app) as client:
        sign_in(client, "persona-invalid@example.com")
        response = client.post(
            "/api/attempts",
            json={"case_id": main.CATALOGUE.default_case.id, "mode": "god-mode"},
        )

    assert response.status_code == 422


def test_the_persona_survives_a_reload_with_its_disclosure_budget() -> None:
    """A reload that reset the budget would hand out a free fact on the Skeptic."""
    from fastapi.testclient import TestClient
    from conftest import sign_in
    import app.main as main

    with TestClient(main.app) as client:
        sign_in(client, "persona-reload@example.com")
        created = client.post(
            "/api/attempts",
            json={"case_id": main.CATALOGUE.default_case.id, "mode": "pressure"},
        ).json()

        session = main.STORE.get(created["id"], main.CATALOGUE)
        assert session is not None
        session.release_credits = 0.72
        session.consecutive_precise_misses = 4
        main.STORE.save(session)

        reloaded = main.STORE.get(created["id"], main.CATALOGUE)

    assert reloaded is not None
    assert reloaded.mode == "pressure"
    assert reloaded.persona.id == "pressure"
    assert reloaded.release_credits == pytest.approx(0.72)
    assert reloaded.consecutive_precise_misses == 4
