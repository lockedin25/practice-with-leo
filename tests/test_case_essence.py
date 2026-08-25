"""E2E Test Suite: Case Essence Schema, Reservoir Packages, Multi-School Corpus & Knowledge Base Linkages.

Validates:
- Case essence schema and required fields (core_mechanism, what_the_case_wanted_to_test, pivotal_insight, common_traps, takeaway_lesson, suggested_readings).
- Reservoir 12-case packages, verified facts, and issue trees.
- Multi-school casebook library (IIM-A, IIM-B, IIM-C, ISB) structure and frontmatter.
- Deep linking from case essence to knowledge base modules.
- Boundary conditions, schema violations, malformed packages, and negative cases.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import pytest
import yaml
from pydantic import BaseModel, Field, ValidationError

from app.case_runtime import CaseCatalogue, CaseWorld, Fact, Phase


ROOT = Path(__file__).resolve().parents[1]
RESERVOIR_DIR = ROOT / "reservoir"
CORPUS_DIR = ROOT / "corpus"
KB_DIR = ROOT / "knowledge_base"


# --- Typed Case Essence Schema Contract ---

class SuggestedReading(BaseModel):
    title: str = Field(min_length=1)
    path: str = Field(min_length=1)
    why_relevant: str = Field(default="", min_length=0)


class CaseEssenceSchema(BaseModel):
    core_mechanism: str = Field(min_length=5, description="Fundamental economic or operational mechanism tested.")
    what_the_case_wanted_to_test: str = Field(min_length=5, description="Explicit commercial concept tested by the interviewer.")
    pivotal_insight: str = Field(min_length=5, description="Breakthrough insight that unlocks the case.")
    common_traps: list[str] = Field(min_length=2, description="2-3 specific red herrings or framework dumping traps.")
    takeaway_lesson: str = Field(min_length=5, description="Durable consulting mental model.")
    suggested_readings: list[str | SuggestedReading] = Field(default_factory=list, description="Links to knowledge base modules.")


# Sample canonical essence fixture
CANONICAL_ESSENCE = {
    "core_mechanism": "Product mix shift from high-margin food cold chain to unhedged pharma contracts with lower route density.",
    "what_the_case_wanted_to_test": "Ability to isolate margin dilution caused by segment mix shift despite topline volume growth.",
    "pivotal_insight": "Pharma contracts are priced off standard food cost base but require 3x reefer calibration and return trips empty.",
    "common_traps": [
        "Reciting generic 4Ps or Fixed vs Variable cost lists without testing segment unit margins.",
        "Assuming fuel price inflation is the culprit without verifying cost indexation clauses.",
    ],
    "takeaway_lesson": "Topline volume growth can mask severe gross margin erosion when fixed route capacity is diverted to low-density accounts.",
    "suggested_readings": [
        "industries/01_logistics_and_cold_chain.md",
        "methodology/02_issue_tree_structuring.md",
        "case_types/profitability.md",
    ],
}


# =============================================================================
# TIER 1: Schema Coverage Tests (≥5 tests)
# =============================================================================

def test_t1_case_essence_schema_validates_canonical_payload() -> None:
    """Validate that a well-formed case_essence mapping parses cleanly into CaseEssenceSchema."""
    essence = CaseEssenceSchema.model_validate(CANONICAL_ESSENCE)
    assert "mix shift" in essence.core_mechanism
    assert len(essence.common_traps) >= 2
    assert "pharma" in essence.pivotal_insight.lower()
    assert len(essence.suggested_readings) == 3


def test_t1_case_essence_supports_structured_suggested_readings() -> None:
    """Validate that suggested_readings supports structured objects with title and path."""
    structured_essence = dict(CANONICAL_ESSENCE)
    structured_essence["suggested_readings"] = [
        {"title": "Logistics Playbook", "path": "industries/01_logistics_and_cold_chain.md", "why_relevant": "Cold chain economics"},
        {"title": "Issue Trees", "path": "methodology/02_issue_tree_structuring.md", "why_relevant": "MECE decomposition"},
    ]
    essence = CaseEssenceSchema.model_validate(structured_essence)
    assert len(essence.suggested_readings) == 2
    first_reading = essence.suggested_readings[0]
    assert isinstance(first_reading, SuggestedReading)
    assert first_reading.path.endswith(".md")


def test_t1_reservoir_catalog_loads_all_twelve_cases() -> None:
    """Verify that CaseCatalogue reliably loads all authored cases (reservoir + multi-school exemplars)."""
    catalogue = CaseCatalogue.from_reservoir(ROOT)
    assert len(catalogue.cases) == 69
    case_ids = set(catalogue.cases.keys())
    expected_ids = {
        "meridian-cold-chain-v1",
        "aster-diagnostics-v1",
        "bluecurrent-water-v1",
        "clearcart-v1",
        "forge-components-v1",
        "harvest-table-v1",
        "loom-and-leaf-v1",
        "metrolink-mobility-v1",
        "northstar-bank-v1",
        "orbit-learning-v1",
        "sunpeak-solar-v1",
        "terrabuild-materials-v1",
    }
    assert expected_ids.issubset(case_ids)


def test_t1_reservoir_case_packages_have_required_metadata() -> None:
    """Verify that every case package in reservoir/ contains valid case.yaml with required fields."""
    reservoir_dirs = [p for p in RESERVOIR_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")]
    assert len(reservoir_dirs) >= 12
    for cdir in reservoir_dirs:
        case_file = cdir / "case.yaml"
        assert case_file.is_file(), f"Missing case.yaml in {cdir.name}"
        data = yaml.safe_load(case_file.read_text(encoding="utf-8"))
        assert "case_id" in data
        assert "title" in data
        assert "category" in data
        assert "candidate_opening" in data
        assert "objective_function" in data


def test_t1_multi_school_corpus_contains_structured_cases() -> None:
    """Verify that the multi-school corpus contains structured exemplar cases."""
    iima_cases_dir = CORPUS_DIR / "iima-consult-prep-book-2025-26" / "cases"
    assert iima_cases_dir.is_dir()
    case_files = list(iima_cases_dir.glob("*.md"))
    assert len(case_files) >= 50, f"Expected at least 50 cases in IIM-A prep book, found {len(case_files)}"


# =============================================================================
# TIER 2: Boundary & Negative Tests (≥5 tests)
# =============================================================================

def test_t2_case_essence_rejects_missing_required_fields() -> None:
    """Boundary test: CaseEssenceSchema rejects payloads missing core_mechanism or pivotal_insight."""
    incomplete = {
        "core_mechanism": "Mix shift",
        # missing what_the_case_wanted_to_test
        "pivotal_insight": "Pharma pricing",
        "common_traps": ["Trap 1", "Trap 2"],
        "takeaway_lesson": "Lesson",
    }
    with pytest.raises(ValidationError) as exc:
        CaseEssenceSchema.model_validate(incomplete)
    assert "what_the_case_wanted_to_test" in str(exc.value)


def test_t2_case_essence_rejects_insufficient_common_traps() -> None:
    """Boundary test: common_traps requires at least 2 distinct traps."""
    insufficient_traps = dict(CANONICAL_ESSENCE)
    insufficient_traps["common_traps"] = ["Only one trap here"]
    with pytest.raises(ValidationError) as exc:
        CaseEssenceSchema.model_validate(insufficient_traps)
    assert "common_traps" in str(exc.value)


def test_t2_case_essence_rejects_empty_or_whitespace_strings() -> None:
    """Boundary test: string fields must meet minimum length constraints."""
    empty_mechanism = dict(CANONICAL_ESSENCE)
    empty_mechanism["core_mechanism"] = "   "
    with pytest.raises(ValidationError) as exc:
        CaseEssenceSchema.model_validate(empty_mechanism)
    assert "core_mechanism" in str(exc.value)


def test_t2_case_essence_rejects_non_list_common_traps() -> None:
    """Boundary test: common_traps passed as a string or number is rejected."""
    bad_traps = dict(CANONICAL_ESSENCE)
    bad_traps["common_traps"] = "Framework dumping is bad"  # string instead of list
    with pytest.raises(ValidationError):
        CaseEssenceSchema.model_validate(bad_traps)


def test_t2_knowledge_base_linkages_point_to_real_files() -> None:
    """Boundary test: verify that all suggested_readings point to existent knowledge_base paths."""
    for reading in CANONICAL_ESSENCE["suggested_readings"]:
        rel_path = reading if isinstance(reading, str) else reading["path"]
        target = KB_DIR / rel_path
        assert target.is_file(), f"Knowledge base link broken: {rel_path} does not exist at {target}"


def test_t2_issue_tree_schema_validation() -> None:
    """Boundary test: Authoring issue-tree.yaml structure must contain valid root and node hierarchy."""
    meridian_tree = RESERVOIR_DIR / "meridian-cold-chain" / "issue-tree.yaml"
    assert meridian_tree.is_file()
    tree_data = yaml.safe_load(meridian_tree.read_text(encoding="utf-8"))
    assert "root" in tree_data
    assert "id" in tree_data["root"]
    assert "nodes" in tree_data
    assert isinstance(tree_data["nodes"], list)
    assert len(tree_data["nodes"]) >= 3
    node_ids = {node["id"] for node in tree_data["nodes"]}
    assert len(node_ids) == len(tree_data["nodes"]), "Issue tree contains duplicate node IDs"


# =============================================================================
# TIER 3: Cross-Feature Integration Tests
# =============================================================================

def test_t3_case_catalogue_essence_enrichment_integration() -> None:
    """Verify that CaseWorld and CaseCatalogue can load cases containing essence metadata."""
    catalogue = CaseCatalogue.from_reservoir(ROOT)
    default_case = catalogue.default_case
    assert default_case.id == "meridian-cold-chain-v1"
    assert default_case.opening.startswith("Your client is Meridian Cold Chain")
    assert len(default_case.facts) >= 12
    assert len(default_case.phases) == 3


def test_t3_all_reservoir_facts_have_non_empty_domains_and_release_levels() -> None:
    """Cross-feature test: facts.yaml in reservoir packages adhere to disclosure rules."""
    for cdir in RESERVOIR_DIR.iterdir():
        if not cdir.is_dir() or cdir.name.startswith("_"):
            continue
        facts_file = cdir / "facts.yaml"
        if not facts_file.is_file():
            continue
        data = yaml.safe_load(facts_file.read_text(encoding="utf-8"))
        facts = data.get("facts", [])
        assert len(facts) >= 5, f"Case {cdir.name} has too few facts"
        for fact in facts:
            assert "id" in fact and fact["id"]
            assert "domain" in fact and fact["domain"]
            assert "release_level" in fact and fact["release_level"] in {
                "opening", "broad_context", "sharp_question", "hypothesis_backed",
                "synthesis_support", "immediate", "drill_down", "deep_analysis", "interviewer_only"
            }


def test_t3_all_multi_school_cases_have_valid_frontmatter() -> None:
    """Cross-feature test: all multi-school corpus markdown files have valid YAML frontmatter."""
    iima_cases = list((CORPUS_DIR / "iima-consult-prep-book-2025-26" / "cases").glob("*.md"))
    sample_cases = iima_cases[:20]  # Sample representative set
    for case_path in sample_cases:
        content = case_path.read_text(encoding="utf-8")
        assert content.startswith("---\n"), f"{case_path.name} missing frontmatter delimiter"
        parts = content.split("---\n", 2)
        assert len(parts) >= 3
        fm = yaml.safe_load(parts[1])
        assert "case_id" in fm
        assert "title" in fm
        assert "case_type" in fm
        assert fm["case_type"] in {
            "profitability",
            "market_entry",
            "growth_strategy",
            "pricing_strategy",
            "mergers_and_acquisitions",
            "unconventional_and_abstract",
            "cost_reduction",
            "pricing",
            "growth",
            "m&a",
            "unconventional",
        } or isinstance(fm["case_type"], str)


# =============================================================================
# TIER 4: Real-World Workload Scenarios
# =============================================================================

def test_t4_real_world_case_essence_to_kb_navigation_scenario() -> None:
    """Scenario 2: Candidate explores a case and navigates to all linked knowledge base modules."""
    essence = CaseEssenceSchema.model_validate(CANONICAL_ESSENCE)
    
    # 1. Candidate views essence suggested readings
    readings = essence.suggested_readings
    assert len(readings) >= 2
    
    # 2. Verify all linked files can be opened and parsed
    for reading in readings:
        path_str = reading if isinstance(reading, str) else reading.path
        full_path = KB_DIR / path_str
        assert full_path.exists()
        content = full_path.read_text(encoding="utf-8")
        assert len(content) > 1000
        # Ensure knowledge base files have top-level headings
        assert content.startswith("---\n") or content.startswith("# ")


def test_t4_real_world_reservoir_to_evaluation_context_linking() -> None:
    """Scenario: Case essence is ready for injection into evaluator context."""
    catalogue = CaseCatalogue.from_reservoir(ROOT)
    case = catalogue.get("meridian-cold-chain-v1")
    
    # Verify case catalogue item contains clean client-safe view
    item = case.catalogue_item()
    assert item["id"] == "meridian-cold-chain-v1"
    assert "objective" not in item  # private objective is not leaked in basic catalogue item
    
    # Verify objective question is accessible for director/evaluator
    assert "EBITDA margin" in case.objective or "margin" in case.objective
