"""Tests for the Multi-School Exemplar Case Library and full Reservoir Package integrity.

Validates:
1. All 12 Reservoir packages have complete 5-file packages, valid case_essence, verified facts, and issue trees.
2. All 57 Multi-School Exemplar packages across IIMA (25), IIMB (10), IIMC (10), and ISB (12) are valid packages.
3. Every case has non-empty essence fields (core_mechanism, what_the_case_wanted_to_test, pivotal_insight, common_traps, takeaway_lesson, suggested_readings).
4. All suggested_readings point to genuine markdown files in knowledge_base/.
5. All facts have valid release levels and a diagnosis.hidden fact with release_level == 'interviewer_only'.
6. All issue-tree.yaml files have valid DAG nodes, acceptable routes, and recovery policies.
"""

from __future__ import annotations
from pathlib import Path
import pytest
import yaml

from app.case_loader import (
    load_case_package,
    load_reservoir_catalog,
    load_corpus_exemplars,
    validate_case_package,
)
from app.models import CasePackage, CaseEssenceModel

ROOT = Path(__file__).resolve().parents[1]
RESERVOIR_DIR = ROOT / "reservoir"
EXEMPLARS_DIR = ROOT / "corpus" / "exemplars"
KB_DIR = ROOT / "knowledge_base"


def test_reservoir_catalog_loads_all_12_full_packages() -> None:
    """Verify load_reservoir_catalog loads 12 valid 5-file CasePackages."""
    catalog = load_reservoir_catalog(ROOT)
    assert len(catalog) == 12

    for case_id, pkg in catalog.items():
        assert isinstance(pkg, CasePackage)
        assert pkg.manifest.case_id == case_id
        assert pkg.manifest.case_essence is not None
        assert len(pkg.manifest.case_essence.common_traps) >= 2
        assert len(pkg.manifest.case_essence.suggested_readings) >= 1
        assert len(pkg.facts.facts) >= 10
        assert pkg.issue_tree is not None
        assert len(pkg.issue_tree.nodes) >= 3
        assert len(pkg.issue_tree.acceptable_routes) >= 1

        # Check diagnosis.hidden is present and interviewer_only
        hidden_facts = [f for f in pkg.facts.facts if f.id == "diagnosis.hidden"]
        assert len(hidden_facts) == 1, f"Missing diagnosis.hidden in reservoir case {case_id}"
        assert hidden_facts[0].release_level == "interviewer_only"


def test_every_exemplar_package_still_loads() -> None:
    """The corpus directory grouping is internal; the count is what must not drift.

    This previously asserted a per-institution breakdown. That axis was removed
    from the product, but the packages themselves are unchanged, so the check that
    survives is that all 57 still parse into valid manifests.
    """
    exemplars = load_corpus_exemplars(ROOT)

    assert len(exemplars) == 57
    assert all(pkg.manifest.case_id for pkg in exemplars.values())


def test_no_exemplar_declares_itself_a_community_case() -> None:
    """Everything shipped in the repository is curated by definition."""
    exemplars = load_corpus_exemplars(ROOT)

    assert {pkg.manifest.source for pkg in exemplars.values()} == {"curated"}


def test_all_57_exemplars_validate_cleanly() -> None:
    """Run validate_case_package on all 57 multi-school exemplar packages."""
    exemplars = load_corpus_exemplars(ROOT)
    for case_id, pkg in exemplars.items():
        errors = validate_case_package(pkg)
        assert not errors, f"Validation errors in exemplar {case_id}: {errors}"


def test_all_suggested_readings_point_to_existing_kb_files() -> None:
    """Ensure every suggested reading in reservoir and exemplars points to a real file in knowledge_base/."""
    catalog = load_reservoir_catalog(ROOT)
    exemplars = load_corpus_exemplars(ROOT)
    all_packages = list(catalog.values()) + list(exemplars.values())

    checked_links = 0
    for pkg in all_packages:
        essence = pkg.manifest.case_essence
        assert essence is not None
        for reading in essence.suggested_readings:
            # reading can be relative to root (e.g. 'knowledge_base/industries/01_logistics_and_cold_chain.md')
            # or relative to knowledge_base/ (e.g. 'industries/01_logistics_and_cold_chain.md')
            if reading.startswith("knowledge_base/"):
                target = ROOT / reading
            else:
                target = KB_DIR / reading
            assert target.is_file(), f"Broken reading link '{reading}' in case '{pkg.manifest.case_id}' (target: {target})"
            checked_links += 1

    assert checked_links >= 150, f"Expected to check at least 150 links, checked {checked_links}"


def test_exemplar_issue_trees_have_valid_structure() -> None:
    """Ensure all 57 exemplars have root, branch, diagnosis, and recommendation nodes with connected edges."""
    exemplars = load_corpus_exemplars(ROOT)
    for case_id, pkg in exemplars.items():
        tree = pkg.issue_tree
        assert tree is not None, f"Missing issue tree in {case_id}"
        root_id = tree.root.id if hasattr(tree.root, "id") else tree.root.get("id")
        assert root_id.startswith("objective.")
        
        node_ids = {n.id for n in tree.nodes}
        assert "diagnosis" in node_ids, f"Missing diagnosis node in {case_id}"
        assert "actions" in node_ids, f"Missing actions node in {case_id}"

        # Check edges connect valid nodes
        for edge in tree.edges:
            assert edge.from_node in node_ids or edge.from_node == root_id
            assert edge.to_node in node_ids
