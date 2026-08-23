"""Content-level tests for the launch catalogue.

These tests keep the library from silently shrinking to a set of thin metadata
records. A selectable case must contain enough gated factual material to support
an actual interview, not only a title for the landing page.
"""

from pathlib import Path

from app.case_runtime import CaseCatalogue


def test_launch_catalogue_has_twelve_distinct_playable_cases() -> None:
    catalogue = CaseCatalogue.from_reservoir(Path(__file__).resolve().parents[1])

    assert len(catalogue.cases) == 12
    assert len({case.title for case in catalogue.cases.values()}) == 12
    assert all(len(case.facts) >= 12 for case in catalogue.cases.values())
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
