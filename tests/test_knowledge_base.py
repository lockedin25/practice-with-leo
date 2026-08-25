import os
import glob
import re
import yaml
import pytest

KB_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base")

EXPECTED_FILES = [
    # Methodology (5)
    "methodology/01_preliminary_questions.md",
    "methodology/02_issue_tree_structuring.md",
    "methodology/03_hypothesis_driven_drilling.md",
    "methodology/04_data_gathering_and_notes.md",
    "methodology/05_synthesis_and_recommendations.md",
    # Case Types (6)
    "case_types/profitability.md",
    "case_types/market_entry.md",
    "case_types/growth_strategy.md",
    "case_types/pricing_strategy.md",
    "case_types/mergers_and_acquisitions.md",
    "case_types/unconventional_and_abstract.md",
    # Industries (17)
    "industries/01_logistics_and_cold_chain.md",
    "industries/02_ecommerce_and_marketplaces.md",
    "industries/03_pharma_and_healthcare.md",
    "industries/04_banking_and_financial_services.md",
    "industries/05_fmcg_and_cpg.md",
    "industries/06_aviation_and_airlines.md",
    "industries/07_telecom_and_media.md",
    "industries/08_saas_and_b2b_tech.md",
    "industries/09_retail_and_fashion.md",
    "industries/10_automotive_and_ev.md",
    "industries/11_energy_and_renewables.md",
    "industries/12_hospitality_and_tourism.md",
    "industries/13_food_and_beverage_restaurants.md",
    "industries/14_heavy_manufacturing_and_steel.md",
    "industries/15_fintech_and_payments.md",
    "industries/16_insurance.md",
    "industries/17_defense_and_aerospace.md",
    # Evaluation Engine (3)
    "evaluation_engine/detection_rubrics.yaml",
    "evaluation_engine/golden_rewrites_catalogue.md",
    "evaluation_engine/system_prompt_knowledge_pack.md",
]


def test_knowledge_base_inventory_and_completeness():
    """Verify all 31 deliverable files exist, are non-empty, and meet minimum size constraints."""
    assert os.path.exists(KB_ROOT), f"Knowledge base root not found at {KB_ROOT}"

    actual_files = sorted(
        os.path.relpath(p, KB_ROOT)
        for p in glob.glob(os.path.join(KB_ROOT, "**", "*"), recursive=True)
        if os.path.isfile(p)
    )

    assert len(actual_files) == 31, f"Expected 31 files, but found {len(actual_files)}: {actual_files}"

    for rel_path in EXPECTED_FILES:
        abs_path = os.path.join(KB_ROOT, rel_path)
        assert os.path.exists(abs_path), f"Missing required deliverable file: {rel_path}"
        size = os.path.getsize(abs_path)
        assert size > 5000, f"File {rel_path} is suspiciously small ({size} bytes)"

        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) >= 150, f"File {rel_path} has only {len(lines)} lines (expected >= 150)"


def test_yaml_frontmatter_all_markdown_files():
    """Verify clean YAML frontmatter parsing and required fields on all 30 .md files."""
    md_files = [f for f in EXPECTED_FILES if f.endswith(".md")]
    assert len(md_files) == 30

    required_keys = {"title", "category", "topics_covered", "target_use_case"}

    for rel_path in md_files:
        abs_path = os.path.join(KB_ROOT, rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert content.startswith("---\n"), f"{rel_path} does not start with YAML frontmatter delimiter '---'"
        parts = content.split("---\n", 2)
        assert len(parts) >= 3, f"{rel_path} does not contain valid closing YAML frontmatter delimiter"

        frontmatter_raw = parts[1]
        try:
            frontmatter = yaml.safe_load(frontmatter_raw)
        except Exception as e:
            pytest.fail(f"YAML parsing error in {rel_path}: {e}")

        assert isinstance(frontmatter, dict), f"{rel_path} frontmatter did not parse into a dictionary"

        missing_keys = required_keys - set(frontmatter.keys())
        assert not missing_keys, f"{rel_path} is missing required frontmatter keys: {missing_keys}"

        assert isinstance(frontmatter["title"], str) and len(frontmatter["title"].strip()) > 3
        assert isinstance(frontmatter["category"], str) and len(frontmatter["category"].strip()) > 3
        assert isinstance(frontmatter["target_use_case"], str) and len(frontmatter["target_use_case"].strip()) > 3
        assert isinstance(frontmatter["topics_covered"], list) and len(frontmatter["topics_covered"]) >= 2
        for topic in frontmatter["topics_covered"]:
            assert isinstance(topic, str) and len(topic.strip()) > 0


def test_detection_rubrics_yaml_schema():
    """Verify complete YAML schema and structure of detection_rubrics.yaml."""
    rubric_path = os.path.join(KB_ROOT, "evaluation_engine", "detection_rubrics.yaml")
    assert os.path.exists(rubric_path)

    with open(rubric_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "detection_rubrics.yaml must parse to a dict"

    # Verify top-level root keys
    expected_root_keys = {
        "schema_version",
        "metadata",
        "scoring_scale",
        "global_evaluation_principles",
        "stages",
        "penalty_matrix",
        "distinction_triggers",
    }
    assert expected_root_keys.issubset(set(data.keys())), f"Missing root keys in rubric: {expected_root_keys - set(data.keys())}"

    # Verify stages
    stages = data.get("stages", [])
    assert len(stages) == 5, f"Expected 5 stages in detection_rubrics.yaml, got {len(stages)}"

    total_weight = 0.0
    stage_ids = set()
    for stage in stages:
        assert "stage_id" in stage and stage["stage_id"]
        assert "stage_name" in stage and stage["stage_name"]
        assert "stage_weight" in stage and isinstance(stage["stage_weight"], (int, float))
        assert "stage_objective" in stage and stage["stage_objective"]
        assert "sub_dimensions" in stage and isinstance(stage["sub_dimensions"], list) and len(stage["sub_dimensions"]) >= 3

        total_weight += stage["stage_weight"]
        stage_ids.add(stage["stage_id"])

        for sub in stage["sub_dimensions"]:
            assert "id" in sub and sub["id"]
            assert "name" in sub and sub["name"]
            assert "weight" in sub and isinstance(sub["weight"], (int, float))
            assert "focus" in sub and sub["focus"]
            assert "markers" in sub and isinstance(sub["markers"], list) and len(sub["markers"]) > 0
            assert "counter_markers" in sub and isinstance(sub["counter_markers"], list) and len(sub["counter_markers"]) > 0
            assert "scoring_criteria" in sub and isinstance(sub["scoring_criteria"], dict)

    assert round(total_weight, 4) == 1.0, f"Stage weights must sum to 1.0, got {total_weight}"
    assert len(stage_ids) == 5, "Duplicate stage_ids found"

    # Verify penalty_matrix and distinction_triggers
    assert "instant_red_flags" in data["penalty_matrix"]
    assert len(data["penalty_matrix"]["instant_red_flags"]) >= 3
    assert "top_1_percent_cues" in data["distinction_triggers"]
    assert len(data["distinction_triggers"]["top_1_percent_cues"]) >= 3


def test_no_forbidden_placeholders_in_knowledge_base():
    """Scan all 31 deliverable files for illegal placeholders (TODO, TBD, PLACEHOLDER, FIXME, lorem)."""
    forbidden_patterns = [
        (re.compile(r"\bTODO\b", re.IGNORECASE), "TODO"),
        (re.compile(r"\bTBD\b", re.IGNORECASE), "TBD"),
        (re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE), "PLACEHOLDER"),
        (re.compile(r"\bFIXME\b", re.IGNORECASE), "FIXME"),
        (re.compile(r"\blorem\s+ipsum\b", re.IGNORECASE), "lorem ipsum"),
        (re.compile(r"\[\s*\.\.\.\s*\]"), "[...]"),
    ]

    violations = []
    for rel_path in EXPECTED_FILES:
        abs_path = os.path.join(KB_ROOT, rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            for pattern, name in forbidden_patterns:
                if pattern.search(line):
                    violations.append(f"{rel_path}:{line_num} contains forbidden pattern '{name}': {line.strip()}")

    assert not violations, f"Found {len(violations)} forbidden placeholders:\n" + "\n".join(violations)


def test_mermaid_diagrams_syntax_and_integrity():
    """Extract and validate syntax of all Mermaid.js diagrams across all knowledge base files."""
    valid_headers = (
        "graph",
        "flowchart",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram",
        "stateDiagram-v2",
        "erDiagram",
        "gantt",
        "pie",
        "gitGraph",
        "journey",
        "mindmap",
        "timeline",
        "quadrantChart",
    )

    diagram_count = 0
    errors = []

    for rel_path in EXPECTED_FILES:
        if not rel_path.endswith(".md"):
            continue
        abs_path = os.path.join(KB_ROOT, rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()

        mermaid_blocks = re.findall(r"```mermaid\s*\n(.*?)\n```", content, re.DOTALL)
        for idx, block in enumerate(mermaid_blocks, 1):
            diagram_count += 1
            lines = block.strip().split("\n")
            if not lines:
                errors.append(f"{rel_path} diagram #{idx}: Empty diagram block")
                continue

            first_line = lines[0].strip()
            if not any(first_line.startswith(h) for h in valid_headers):
                errors.append(f"{rel_path} diagram #{idx}: Invalid header '{first_line}'")

            subgraphs = 0
            ends = 0
            for line_idx, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped or stripped.startswith("%%"):
                    continue

                if re.match(r"^subgraph\b", stripped):
                    subgraphs += 1
                elif stripped == "end" or re.match(r"^end\b", stripped):
                    ends += 1

                # Check quotes balance
                quotes_count = stripped.replace('\\"', "").count('"')
                if quotes_count % 2 != 0:
                    errors.append(f"{rel_path} diagram #{idx} line {line_idx}: Unbalanced quotes in '{stripped}'")

                # Remove content inside quotes before checking bracket balance
                unquoted = re.sub(r'"[^"]*"', '""', stripped)
                for open_ch, close_ch in [("[", "]"), ("(", ")"), ("{", "}")]:
                    if unquoted.count(open_ch) != unquoted.count(close_ch):
                        errors.append(
                            f"{rel_path} diagram #{idx} line {line_idx}: Unbalanced '{open_ch}'/'{close_ch}' in '{stripped}'"
                        )

            if subgraphs != ends:
                errors.append(f"{rel_path} diagram #{idx}: Unbalanced subgraphs ({subgraphs} subgraph vs {ends} end)")

    assert diagram_count >= 30, f"Expected at least 30 Mermaid diagrams across KB, found {diagram_count}"
    assert not errors, f"Mermaid syntax errors found in {len(errors)} places:\n" + "\n".join(errors)


def test_katex_math_and_formula_blocks():
    """Verify that all LaTeX/KaTeX math formula blocks have balanced delimiters."""
    math_errors = []
    for rel_path in EXPECTED_FILES:
        if not rel_path.endswith(".md"):
            continue
        abs_path = os.path.join(KB_ROOT, rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check block math $$ ... $$
        block_count = content.count("$$")
        if block_count % 2 != 0:
            math_errors.append(f"{rel_path}: Odd number of '$$' delimiters ({block_count})")

    assert not math_errors, f"Math block delimiter errors found:\n" + "\n".join(math_errors)
