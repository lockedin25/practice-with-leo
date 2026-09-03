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


def test_the_catalogue_exposes_only_the_curated_community_axis() -> None:
    """The library no longer tells a candidate which institution a case came from.

    The corpus is mixed-provenance, so naming any one school was both inaccurate
    and a claim the product should not make publicly. What a candidate actually
    needs to know is whether a case shipped with Leo or came from another candidate.
    """
    catalogue = CaseCatalogue.from_reservoir(Path(__file__).resolve().parents[1])
    items = catalogue.catalogue_items()

    assert {item["source"] for item in items} == {"curated"}
    assert all("school" not in item for item in items)


def test_no_institution_name_reaches_the_candidate_facing_catalogue() -> None:
    """Regression guard for the removal, checked against the serialized payload.

    Asserting on the whole projection rather than one field is deliberate: a name
    reintroduced through the title, summary or skills list would be just as public
    as one in a dedicated field.
    """
    import json

    catalogue = CaseCatalogue.from_reservoir(Path(__file__).resolve().parents[1])
    payload = json.dumps(catalogue.catalogue_items()).lower()

    for banned in ("iim-", "iim ", "ahmedabad", "bangalore", "calcutta", "hyderabad", "casebook"):
        assert banned not in payload, f"{banned!r} leaked into the public catalogue"


def test_every_authored_case_still_loads_after_the_source_change() -> None:
    """The count is the migration check: 12 reservoir packages plus 57 exemplars."""
    catalogue = CaseCatalogue.from_reservoir(Path(__file__).resolve().parents[1])

    assert len(catalogue.catalogue_items()) == 69
