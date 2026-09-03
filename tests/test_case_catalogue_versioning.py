"""The mutable, versioned case catalogue and the contributed-case store.

The property that matters most here is pinning: a live attempt must keep
resolving to the exact world it started against, even after an admin publishes
an edit to that case.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from app.case_runtime import CaseCatalogue, CaseWorld
from app.store import CaseStore


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def catalogue() -> CaseCatalogue:
    return CaseCatalogue.from_reservoir(ROOT)


@pytest.fixture
def case_store(tmp_path) -> CaseStore:
    return CaseStore(tmp_path / "cases.db")



@pytest.fixture(autouse=True)
def _withdraw_contributed_cases():
    """Leave the shared catalogue exactly as the test found it.

    Published rows live in the session-wide throwaway database, so without this a
    case published by one test is re-registered by the next test that reloads, and
    every later assertion on the library size drifts.
    """
    yield
    import app.main as main

    for record in main.CASES.list_all_versions():
        if record["status"] == "published":
            main.CASES.set_status(record["case_id"], record["version"], "unpublished")
    main.reload_contributed_cases()


def _package_of(world: CaseWorld, case_id: str) -> dict:
    """Build a stored-package payload equivalent to the given world."""
    return {
        "case": {
            "case_id": case_id,
            "title": f"Contributed {case_id}",
            "category": "profitability",
            "industry": "logistics",
            "difficulty": "intermediate",
            "source": "community",
            "candidate_opening": {"context": "Context.", "objective": "Objective."},
            "objective_function": {"decision_question": "Why did margin fall?"},
        },
        "facts": {
            "facts": [
                {
                    "id": "company.identity",
                    "domain": "company",
                    "release_level": "opening",
                    "content": "The client is a contributed test company.",
                }
            ]
        },
        "conversation_policy": {
            "phase_policy": {
                "clarification": {
                    "interviewer_goal": "Confirm scope.",
                    "reveal_levels": ["opening", "broad_context"],
                }
            }
        },
    }


# --- Registry semantics ------------------------------------------------------


def test_authored_packages_all_load_at_version_one(catalogue: CaseCatalogue) -> None:
    assert len(catalogue.cases) == 69
    assert {world.version for world in catalogue.cases.values()} == {1}


def test_registering_a_case_makes_it_immediately_playable(catalogue: CaseCatalogue) -> None:
    registry = CaseCatalogue(cases=dict(catalogue.cases))
    payload = _package_of(catalogue.default_case, "contributed-alpha-v1")
    world = CaseWorld.from_mapping(
        payload["case"], payload["facts"], payload["conversation_policy"], version=1
    )

    registry.register(world)

    assert registry.get("contributed-alpha-v1").title == "Contributed contributed-alpha-v1"
    assert registry.get("contributed-alpha-v1").source == "community"


def test_a_new_version_supersedes_the_old_one_in_the_library(catalogue: CaseCatalogue) -> None:
    registry = CaseCatalogue(cases=dict(catalogue.cases))
    payload = _package_of(catalogue.default_case, "contributed-beta-v1")
    first = CaseWorld.from_mapping(
        payload["case"], payload["facts"], payload["conversation_policy"], version=1
    )
    edited = copy.deepcopy(payload)
    edited["case"]["title"] = "Corrected title"
    second = CaseWorld.from_mapping(
        edited["case"], edited["facts"], edited["conversation_policy"], version=2
    )

    registry.register(first)
    registry.register(second)

    assert registry.get("contributed-beta-v1").title == "Corrected title"
    assert registry.get("contributed-beta-v1").version == 2


def test_a_live_attempt_pinned_to_the_old_version_still_sees_its_own_world(
    catalogue: CaseCatalogue,
) -> None:
    """The reason versioning exists at all.

    An admin correcting a published case must not change the evidence under a
    candidate who is midway through it and will be scored on what they saw.
    """
    registry = CaseCatalogue(cases=dict(catalogue.cases))
    payload = _package_of(catalogue.default_case, "contributed-gamma-v1")
    first = CaseWorld.from_mapping(
        payload["case"], payload["facts"], payload["conversation_policy"], version=1
    )
    edited = copy.deepcopy(payload)
    edited["case"]["title"] = "Corrected title"
    edited["facts"]["facts"][0]["content"] = "A completely different fact."
    second = CaseWorld.from_mapping(
        edited["case"], edited["facts"], edited["conversation_policy"], version=2
    )
    registry.register(first)
    registry.register(second)

    pinned = registry.get("contributed-gamma-v1", 1)

    assert pinned.title == "Contributed contributed-gamma-v1"
    assert pinned.facts[0].content == "The client is a contributed test company."


def test_a_pinned_lookup_never_silently_falls_back_to_the_latest(
    catalogue: CaseCatalogue,
) -> None:
    """Substituting a different world would score a candidate on unseen evidence."""
    registry = CaseCatalogue(cases=dict(catalogue.cases))

    with pytest.raises(ValueError, match="v7"):
        registry.get(catalogue.default_case.id, 7)


def test_registering_an_older_version_does_not_roll_the_library_backwards(
    catalogue: CaseCatalogue,
) -> None:
    """Guards against an out-of-order replay from the database."""
    registry = CaseCatalogue(cases=dict(catalogue.cases))
    payload = _package_of(catalogue.default_case, "contributed-delta-v1")
    newer = CaseWorld.from_mapping(
        payload["case"], payload["facts"], payload["conversation_policy"], version=3
    )
    older = CaseWorld.from_mapping(
        payload["case"], payload["facts"], payload["conversation_policy"], version=2
    )

    registry.register(newer)
    registry.register(older)

    assert registry.get("contributed-delta-v1").version == 3
    assert registry.get("contributed-delta-v1", 2).version == 2


def test_unpublishing_keeps_an_in_flight_attempt_resumable(catalogue: CaseCatalogue) -> None:
    """Withdrawal removes a case from the library, not from history."""
    registry = CaseCatalogue(cases=dict(catalogue.cases))
    payload = _package_of(catalogue.default_case, "contributed-epsilon-v1")
    world = CaseWorld.from_mapping(
        payload["case"], payload["facts"], payload["conversation_policy"], version=1
    )
    registry.register(world)

    registry.unregister("contributed-epsilon-v1")

    with pytest.raises(ValueError):
        registry.get("contributed-epsilon-v1")
    assert registry.get("contributed-epsilon-v1", 1).version == 1


def test_a_contributed_case_is_compiled_by_the_same_disclosure_rules(
    catalogue: CaseCatalogue,
) -> None:
    """Same loader, so a contributed case cannot dodge the fact-gating runtime."""
    payload = _package_of(catalogue.default_case, "contributed-zeta-v1")
    world = CaseWorld.from_mapping(
        payload["case"], payload["facts"], payload["conversation_policy"]
    )

    eligible = world.eligible_facts_for_director("clarification", set())
    assert [fact["id"] for fact in eligible] == ["company.identity"]
    assert world.validate_fact_selection(
        ["company.identity"], "clarification", set(), max_facts=0
    ) == []


# --- Store -------------------------------------------------------------------


def test_versions_increment_per_case(case_store: CaseStore) -> None:
    first = case_store.save_package("c1", {"case": {}}, status="draft", contributor_id="u1")
    second = case_store.save_package("c1", {"case": {}}, status="draft", contributor_id="u1")
    other = case_store.save_package("c2", {"case": {}}, status="draft", contributor_id="u1")

    assert (first, second, other) == (1, 2, 1)


def test_only_published_packages_reach_the_library(case_store: CaseStore) -> None:
    """Admin review is the gate, so anything short of published stays invisible."""
    for status in ("draft", "submitted", "validated", "needs_changes", "unpublished"):
        case_store.save_package(f"case-{status}", {"case": {}}, status=status, contributor_id="u1")
    case_store.save_package("case-live", {"case": {}}, status="published", contributor_id="u1")

    published = case_store.published_packages()

    assert [record["case_id"] for record in published] == ["case-live"]


def test_only_the_latest_published_version_of_a_case_is_offered(case_store: CaseStore) -> None:
    """Two published versions must not register the same case twice."""
    case_store.save_package("c1", {"case": {"v": 1}}, status="published", contributor_id="u1")
    case_store.save_package("c1", {"case": {"v": 2}}, status="published", contributor_id="u1")

    published = case_store.published_packages()

    assert len(published) == 1
    assert published[0]["version"] == 2
    assert published[0]["package"]["case"]["v"] == 2


def test_an_earlier_version_stays_readable_after_a_newer_one_publishes(
    case_store: CaseStore,
) -> None:
    case_store.save_package("c1", {"case": {"v": 1}}, status="published", contributor_id="u1")
    case_store.save_package("c1", {"case": {"v": 2}}, status="published", contributor_id="u1")

    assert case_store.get_package("c1", 1) == {"case": {"v": 1}}


def test_the_review_queue_holds_what_awaits_a_decision(case_store: CaseStore) -> None:
    case_store.save_package("waiting", {"case": {}}, status="submitted", contributor_id="u1")
    case_store.save_package("checked", {"case": {}}, status="validated", contributor_id="u2")
    case_store.save_package("scratch", {"case": {}}, status="draft", contributor_id="u3")
    case_store.save_package("live", {"case": {}}, status="published", contributor_id="u4")

    queued = {record["case_id"] for record in case_store.list_for_review()}

    assert queued == {"waiting", "checked"}


def test_an_unknown_status_is_refused_rather_than_stored(case_store: CaseStore) -> None:
    with pytest.raises(ValueError, match="Unknown case status"):
        case_store.save_package("c1", {"case": {}}, status="approved", contributor_id="u1")


# --- Attempt counts ----------------------------------------------------------


def test_attempt_counts_accumulate_separately(case_store: CaseStore) -> None:
    case_store.record_attempt_started("c1")
    case_store.record_attempt_started("c1")
    case_store.record_attempt_started("c1")
    case_store.record_attempt_completed("c1")

    stats = case_store.stats()["c1"]

    assert stats == {"times_attempted": 3, "times_completed": 1}


def test_a_completion_without_a_recorded_start_does_not_corrupt_the_row(
    case_store: CaseStore,
) -> None:
    """The two hooks are on different endpoints, so one can fire without the other."""
    case_store.record_attempt_completed("c1")

    assert case_store.stats()["c1"] == {"times_attempted": 0, "times_completed": 1}


def test_stats_for_an_untouched_case_are_simply_absent(case_store: CaseStore) -> None:
    """The API defaults these to zero, so the store does not need placeholder rows."""
    assert case_store.stats() == {}


# --- End to end through the API ---------------------------------------------


def test_the_catalogue_api_reports_attempt_counts() -> None:
    """The count a candidate sees on a card, which the contribution feature needs."""
    from fastapi.testclient import TestClient
    from conftest import sign_in
    import app.main as main

    with TestClient(main.app) as client:
        sign_in(client, "counts@example.com")
        case_id = main.CATALOGUE.default_case.id
        before = next(
            item for item in client.get("/api/cases").json()["cases"] if item["id"] == case_id
        )

        client.post("/api/attempts", json={"case_id": case_id})

        after = next(
            item for item in client.get("/api/cases").json()["cases"] if item["id"] == case_id
        )

    # Relative, not absolute: the counter is library-wide and shared with every
    # other test that touches this case, so only the delta is this test's claim.
    assert after["times_attempted"] == before["times_attempted"] + 1
    assert after["times_completed"] == before["times_completed"], "starting is not completing"


def test_a_published_contributed_case_joins_the_library_without_a_restart() -> None:
    """The whole point of making the catalogue mutable."""
    from fastapi.testclient import TestClient
    import app.main as main

    payload = _package_of(main.CATALOGUE.default_case, "contributed-live-v1")
    main.CASES.save_package(
        "contributed-live-v1", payload, status="published", contributor_id="u1"
    )
    registered = main.reload_contributed_cases()
    with TestClient(main.app) as client:
        cases = client.get("/api/cases").json()["cases"]
    ids = {item["id"] for item in cases}
    sources = {item["id"]: item["source"] for item in cases}

    assert registered >= 1
    assert "contributed-live-v1" in ids
    assert sources["contributed-live-v1"] == "community"


def test_one_malformed_contribution_does_not_take_down_the_library() -> None:
    """A single bad package must not cost 69 working cases."""
    from fastapi.testclient import TestClient
    import app.main as main

    main.CASES.save_package(
        "contributed-broken-v1",
        {"case": {"case_id": "contributed-broken-v1"}},  # no facts, no policy
        status="published",
        contributor_id="u1",
    )
    good = _package_of(main.CATALOGUE.default_case, "contributed-good-v1")
    main.CASES.save_package(
        "contributed-good-v1", good, status="published", contributor_id="u1"
    )
    main.reload_contributed_cases()
    with TestClient(main.app) as client:
        ids = {item["id"] for item in client.get("/api/cases").json()["cases"]}

    assert "contributed-broken-v1" not in ids
    assert "contributed-good-v1" in ids
    assert len(ids) >= 69


def test_an_attempt_resumes_against_the_version_it_started_on() -> None:
    """Pinning, verified through the real save and load path rather than in memory."""
    from fastapi.testclient import TestClient
    from conftest import sign_in
    import app.main as main

    payload = _package_of(main.CATALOGUE.default_case, "contributed-pinned-v1")
    main.CASES.save_package(
        "contributed-pinned-v1", payload, status="published", contributor_id="u1"
    )
    main.reload_contributed_cases()

    with TestClient(main.app) as client:
        sign_in(client, "pinned@example.com")
        started = client.post("/api/attempts", json={"case_id": "contributed-pinned-v1"}).json()

        # An admin publishes a correction while the attempt is live.
        edited = copy.deepcopy(payload)
        edited["case"]["title"] = "Corrected mid-attempt"
        main.CASES.save_package(
            "contributed-pinned-v1", edited, status="published", contributor_id="u1"
        )
        main.reload_contributed_cases()

        resumed = client.get(f"/api/attempts/{started['id']}").json()
        library = next(
            item
            for item in client.get("/api/cases").json()["cases"]
            if item["id"] == "contributed-pinned-v1"
        )

    assert resumed["case"]["title"] != "Corrected mid-attempt", "the live attempt must not shift"
    assert resumed["case"]["version"] == 1
    assert library["title"] == "Corrected mid-attempt", "but the library must show the correction"
    assert library["version"] == 2
