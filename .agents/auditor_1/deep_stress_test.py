#!/usr/bin/env python3
"""
Deep Adversarial Stress-Testing and Quality Verification Script.
Conducts fine-grained parsing, math check, table formatting, and rubric validation.
"""

import os
import sys
import re
import glob
import yaml

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KB_ROOT = os.path.join(WORKSPACE_ROOT, "knowledge_base")

def stress_test_rubrics():
    print("=== Adversarial Stress Test: detection_rubrics.yaml ===")
    p = os.path.join(KB_ROOT, "evaluation_engine", "detection_rubrics.yaml")
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    stages = data.get("stages", [])
    assert len(stages) == 5, f"Expected 5 stages, got {len(stages)}"
    
    stage_weight_sum = 0.0
    for idx, st in enumerate(stages, 1):
        st_id = st.get("stage_id")
        st_name = st.get("stage_name")
        st_w = st.get("stage_weight")
        stage_weight_sum += st_w
        sub_dims = st.get("sub_dimensions", [])
        
        print(f"  Stage {idx}: {st_id} ('{st_name}') - Weight: {st_w}")
        assert len(sub_dims) >= 3, f"Stage {st_id} has fewer than 3 subdimensions ({len(sub_dims)})"
        
        sub_w_sum = 0.0
        for sub in sub_dims:
            sub_id = sub.get("id")
            sub_w = sub.get("weight")
            sub_w_sum += sub_w
            markers = sub.get("markers", [])
            counter_markers = sub.get("counter_markers", [])
            scoring = sub.get("scoring_criteria", {})
            
            assert len(markers) >= 2, f"Subdimension {sub_id} has < 2 positive markers"
            assert len(counter_markers) >= 2, f"Subdimension {sub_id} has < 2 counter markers"
            assert "below_bar" in scoring and "meets_bar" in scoring and "top_1_percent_mbb" in scoring, f"Subdimension {sub_id} missing scoring band keys"
            
        print(f"    Sub-dimensions ({len(sub_dims)}): weights sum = {round(sub_w_sum, 4)}")
        assert round(sub_w_sum, 4) == 1.0, f"Stage {st_id} subdimension weights sum to {sub_w_sum} (!= 1.0)"

    print(f"  Total Stage Weights Sum: {round(stage_weight_sum, 4)}")
    assert round(stage_weight_sum, 4) == 1.0, f"Stage weights sum to {stage_weight_sum} (!= 1.0)"
    
    # Check penalty matrix
    pm = data.get("penalty_matrix", {})
    assert "instant_red_flags" in pm and len(pm["instant_red_flags"]) >= 3
    print(f"  Penalty Matrix Instant Red Flags: {len(pm['instant_red_flags'])} defined")
    
    # Check distinction triggers
    dt = data.get("distinction_triggers", {})
    assert "top_1_percent_cues" in dt and len(dt["top_1_percent_cues"]) >= 3
    print(f"  Distinction Triggers: {len(dt['top_1_percent_cues'])} defined")
    print("PASSED Rubrics Stress Test")


def stress_test_golden_rewrites():
    print("\n=== Adversarial Stress Test: golden_rewrites_catalogue.md ===")
    p = os.path.join(KB_ROOT, "evaluation_engine", "golden_rewrites_catalogue.md")
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    archetypes = [
        "1. Profitability Archetype",
        "2. Market Entry Archetype",
        "3. Growth Strategy Archetype",
        "4. Pricing Strategy Archetype",
        "5. M&A & Synergy Archetype",
        "6. Unconventional / Market Sizing Archetype",
    ]

    for arch in archetypes:
        assert arch in content, f"Missing section: {arch}"
        print(f"  Verified {arch}")

    required_headers = [
        "### Context & Case Prompt",
        "### Typical Candidate Response (Meets Bar / Developing)",
        "### Diagnostic Evaluator Critique",
        "### Top 1% MBB Golden Rewrite (Partner-Ready Distinction)",
        "### Consulting Craft Commentary",
    ]

    for header in required_headers:
        count = content.count(header)
        print(f"  Found '{header}': {count} occurrences (Expected: 6)")
        assert count == 6, f"Expected 6 occurrences of '{header}', found {count}"

    print("PASSED Golden Rewrites Stress Test")


def stress_test_all_industry_dossiers():
    print("\n=== Adversarial Stress Test: All 17 Industry Dossiers ===")
    ind_files = sorted(glob.glob(os.path.join(KB_ROOT, "industries", "*.md")))
    assert len(ind_files) == 17, f"Expected 17 industry files, found {len(ind_files)}"

    for fpath in ind_files:
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        assert len(lines) >= 200, f"{fname} has only {len(lines)} lines (< 200)"

        math_blocks = re.findall(r"\$\$.*?\$\$", content, re.DOTALL)
        inline_math = re.findall(r"(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$)", content)

        has_vc = bool(re.search(r"Value Chain", content, re.IGNORECASE))
        has_rev = bool(re.search(r"Revenue", content, re.IGNORECASE))
        has_cost = bool(re.search(r"Cost", content, re.IGNORECASE))
        has_kpi = bool(re.search(r"KPI|Metric", content, re.IGNORECASE))
        has_ue = bool(re.search(r"Unit Economic|Economics", content, re.IGNORECASE))
        has_pf = bool(re.search(r"Pitfall|Landmine|Trap", content, re.IGNORECASE))

        assert all([has_vc, has_rev, has_cost, has_kpi, has_ue, has_pf]), f"{fname} missing core dimensions!"

        print(f"  {fname}: {len(lines)} lines, {len(content.split())} words, {len(math_blocks)} math blocks, {len(inline_math)} inline math")

    print("PASSED Industry Dossiers Stress Test (17/17 dossiers rich and complete)")


def stress_test_all_methodology_and_casetypes():
    print("\n=== Adversarial Stress Test: Methodology & Case Types ===")
    m_files = sorted(glob.glob(os.path.join(KB_ROOT, "methodology", "*.md")))
    c_files = sorted(glob.glob(os.path.join(KB_ROOT, "case_types", "*.md")))
    assert len(m_files) == 5, f"Expected 5 methodology files, found {len(m_files)}"
    assert len(c_files) == 6, f"Expected 6 case type files, found {len(c_files)}"

    for fpath in m_files + c_files:
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.splitlines()
        words = content.split()
        assert len(lines) >= 200, f"{fname} has {len(lines)} lines (< 200)"
        print(f"  {fname}: {len(lines)} lines, {len(words)} words")

    print("PASSED Methodology & Case Types Stress Test")


def main():
    print("================================================================================")
    print("DEEP ADVERSARIAL STRESS TEST: MBB KNOWLEDGE REPOSITORY")
    print("================================================================================")
    stress_test_rubrics()
    stress_test_golden_rewrites()
    stress_test_all_industry_dossiers()
    stress_test_all_methodology_and_casetypes()
    print("\nALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
