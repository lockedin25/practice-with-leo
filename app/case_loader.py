"""Case package loader and validator for MBB Case Prep V2.

Provides loaders for the 5-file standard case packages, parsing manifests,
structured case essence, facts packages with hidden diagnoses, issue trees,
and conversation policies across reservoir and multi-school corpus directories.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from app.models import (
    CandidateOpeningModel,
    CaseEssenceModel,
    CaseManifest,
    CasePackage,
    ConversationPolicyPackage,
    FactItem,
    FactsPackage,
    IssueTreePackage,
    ObjectiveFunctionModel,
)

logger = logging.getLogger(__name__)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data


def load_case_manifest(case_dir: Path) -> CaseManifest:
    """Load and validate case.yaml from a case package directory."""
    manifest_path = case_dir / "case.yaml"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing case.yaml in {case_dir}")

    raw_data = _load_yaml(manifest_path)
    return CaseManifest.model_validate(raw_data)


def load_facts(facts_file: Path) -> FactsPackage:
    """Load facts.yaml with support for atomic facts and dependencies."""
    if not facts_file.is_file():
        raise FileNotFoundError(f"Missing facts.yaml at {facts_file}")

    raw_data = _load_yaml(facts_file)
    return FactsPackage.model_validate(raw_data)


def load_issue_tree(tree_file: Path) -> IssueTreePackage | None:
    """Load issue-tree.yaml if present."""
    if not tree_file.is_file():
        return None

    raw_data = _load_yaml(tree_file)
    return IssueTreePackage.model_validate(raw_data)


def load_conversation_policy(policy_file: Path) -> ConversationPolicyPackage | None:
    """Load conversation-policy.yaml if present."""
    if not policy_file.is_file():
        return None

    raw_data = _load_yaml(policy_file)
    return ConversationPolicyPackage.model_validate(raw_data)


def load_case_package(case_dir: Path, shared_policy_path: Path | None = None) -> CasePackage:
    """Load complete 5-file case package from a directory."""
    manifest = load_case_manifest(case_dir)
    facts = load_facts(case_dir / "facts.yaml")

    issue_tree_path = case_dir / "issue-tree.yaml"
    issue_tree = load_issue_tree(issue_tree_path) if issue_tree_path.is_file() else None

    policy_path = case_dir / "conversation-policy.yaml"
    if not policy_path.is_file() and shared_policy_path and shared_policy_path.is_file():
        policy_path = shared_policy_path
    conversation_policy = load_conversation_policy(policy_path) if policy_path.is_file() else None

    validation_path = case_dir / "validation.md"
    validation_notes = validation_path.read_text(encoding="utf-8") if validation_path.is_file() else ""

    return CasePackage(
        manifest=manifest,
        facts=facts,
        issue_tree=issue_tree,
        conversation_policy=conversation_policy,
        validation_notes=validation_notes,
        package_dir=str(case_dir.resolve()),
    )


def load_reservoir_catalog(reservoir_root: Path) -> dict[str, CasePackage]:
    """Load all playable case packages from reservoir/."""
    res_dir = reservoir_root / "reservoir" if (reservoir_root / "reservoir").is_dir() else reservoir_root
    shared_policy = res_dir / "_shared-policy.yaml"
    packages: dict[str, CasePackage] = {}

    for directory in sorted(res_dir.iterdir()):
        if not directory.is_dir() or directory.name.startswith("_"):
            continue
        if (directory / "case.yaml").is_file():
            try:
                pkg = load_case_package(directory, shared_policy_path=shared_policy)
                packages[pkg.case_id] = pkg
            except Exception as err:
                logger.error("Failed to load reservoir package at %s: %s", directory, err)
                raise

    return packages


def load_corpus_exemplars(corpus_root: Path) -> dict[str, CasePackage]:
    """Load curated exemplar packages from corpus/exemplars/ or multi-school directories."""
    corp_dir = corpus_root / "corpus" if (corpus_root / "corpus").is_dir() else corpus_root
    packages: dict[str, CasePackage] = {}
    search_dirs = [
        corp_dir / "exemplars",
        corp_dir / "multi_school",
        corp_dir / "cases",
    ]

    for root_dir in search_dirs:
        if not root_dir.is_dir():
            continue
        for directory in sorted(root_dir.glob("**/")):
            if (directory / "case.yaml").is_file():
                try:
                    pkg = load_case_package(directory)
                    packages[pkg.case_id] = pkg
                except Exception as err:
                    logger.warning("Error loading corpus package at %s: %s", directory, err)

    return packages


def validate_case_package(
    package: CasePackage, knowledge_base_root: Path | None = None
) -> list[str]:
    """Verify integrity, essence richness, issue tree validity, and fact dependencies."""
    errors: list[str] = []

    # 1. Manifest and Essence validation
    manifest = package.manifest
    if not manifest.case_id or not manifest.case_id.strip():
        errors.append("Manifest missing case_id")
    if not manifest.title or not manifest.title.strip():
        errors.append("Manifest missing title")

    essence = manifest.case_essence
    if not essence.core_mechanism or len(essence.core_mechanism.strip()) < 15:
        errors.append("Essence core_mechanism is too short or missing")
    if not essence.what_the_case_wanted_to_test or len(essence.what_the_case_wanted_to_test.strip()) < 15:
        errors.append("Essence what_the_case_wanted_to_test is too short or missing")
    if not essence.pivotal_insight or len(essence.pivotal_insight.strip()) < 15:
        errors.append("Essence pivotal_insight is too short or missing")
    if not essence.takeaway_lesson or len(essence.takeaway_lesson.strip()) < 15:
        errors.append("Essence takeaway_lesson is too short or missing")
    if not essence.common_traps:
        errors.append("Essence common_traps list is empty")

    if knowledge_base_root and knowledge_base_root.is_dir():
        for reading_path_str in essence.suggested_readings:
            full_path = knowledge_base_root.parent / reading_path_str
            if not full_path.is_file():
                errors.append(f"Suggested reading not found: {reading_path_str}")

    # 2. Facts validation
    fact_ids = {fact.id for fact in package.facts.facts}
    for fact in package.facts.facts:
        if not fact.content.strip():
            errors.append(f"Fact {fact.id} has empty content")
        for dep in fact.dependencies:
            if dep not in fact_ids:
                errors.append(f"Fact {fact.id} has missing dependency {dep}")

    # Check for hidden diagnosis fact in reservoir packages
    hidden_diagnosis = package.get_hidden_diagnosis()
    if not hidden_diagnosis:
        errors.append("Package has no interviewer_only or hidden diagnosis fact")

    # 3. Issue Tree validation (if present)
    if package.issue_tree:
        tree = package.issue_tree
        node_ids = {node.id for node in tree.nodes}
        root_id = tree.root.id if hasattr(tree.root, "id") else tree.root.get("id")
        for edge in tree.edges:
            if edge.from_node not in node_ids and edge.from_node != root_id:
                errors.append(f"IssueTree edge from_node '{edge.from_node}' not in node list")
            if edge.to_node not in node_ids:
                errors.append(f"IssueTree edge to_node '{edge.to_node}' not in node list")

        for route in tree.acceptable_routes:
            for node_id in route.sequence:
                if node_id not in node_ids:
                    errors.append(f"AcceptableRoute '{route.id}' references non-existent node '{node_id}'")

    return errors
