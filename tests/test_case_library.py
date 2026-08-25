"""Content-level tests for the launch catalogue.

These tests keep the library from silently shrinking to a set of thin metadata
records. A selectable case must contain enough gated factual material to support
an actual interview, not only a title for the landing page.
"""

from pathlib import Path

from app.case_runtime import CaseCatalogue


def test_launch_catalogue_has_twelve_distinct_playable_cases() -> None:
    catalogue = CaseCatalogue.from_reservoir(Path(__file__).resolve().parents[1])

    assert len(catalogue.cases) == 69
    assert len({case.title for case in catalogue.cases.values()}) >= 57
    assert all(len(case.facts) >= 7 for case in catalogue.cases.values())
    assert all(len(case.phases) == 3 for case in catalogue.cases.values())


def test_catalogue_metadata_never_contains_private_diagnosis_facts() -> None:
    catalogue = CaseCatalogue.from_reservoir(Path(__file__).resolve().parents[1])

    metadata = catalogue.catalogue_items()
    assert "diagnosis.hidden" not in str(metadata)
    assert "priced off the food cost base" not in str(metadata).lower()


def test_runtime_can_cap_an_early_turn_to_one_atomic_fact() -> None:
    catalogue = CaseCatalogue.from_reservoir(Path(__file__).resolve().parents[1])
    case = catalogue.default_case
    eligible_ids = [fact["id"] for fact in case.eligible_facts_for_director(case.initial_phase, set())]

    facts = case.validate_fact_selection(eligible_ids[:2], case.initial_phase, set(), max_facts=1)

    assert len(facts) == 1


def test_catalogue_contains_all_target_schools() -> None:
    catalogue = CaseCatalogue.from_reservoir(Path(__file__).resolve().parents[1])
    items = catalogue.catalogue_items()
    schools = {item["school"] for item in items}
    assert schools == {"MBB Core", "IIM-A", "IIM-B", "IIM-C", "ISB"}


def test_catalogue_school_breakdown_counts() -> None:
    catalogue = CaseCatalogue.from_reservoir(Path(__file__).resolve().parents[1])
    items = catalogue.catalogue_items()
    iima = [i for i in items if i["school"] == "IIM-A"]
    iimb = [i for i in items if i["school"] == "IIM-B"]
    iimc = [i for i in items if i["school"] == "IIM-C"]
    isb = [i for i in items if i["school"] == "ISB"]
    core = [i for i in items if i["school"] == "MBB Core"]

    assert len(core) == 12
    assert len(iima) == 25
    assert len(iimb) == 10
    assert len(iimc) == 10
    assert len(isb) == 12
    assert len(items) == 69
