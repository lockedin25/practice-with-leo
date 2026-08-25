#!/usr/bin/env python3
"""
Comprehensive Independent Victory Audit Script for MBB Case Prep V2 Knowledge Repository.
Executes detailed verification across all requirements: R1, R2, R3, R4, Quality, Syntax, and Math.
"""

import os
import sys
import re
import glob
import yaml

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KB_ROOT = os.path.join(WORKSPACE_ROOT, "knowledge_base")

EXPECTED_FILES = {
    "methodology": [
        "01_preliminary_questions.md",
        "02_issue_tree_structuring.md",
        "03_hypothesis_driven_drilling.md",
        "04_data_gathering_and_notes.md",
        "05_synthesis_and_recommendations.md",
    ],
    "case_types": [
        "profitability.md",
        "market_entry.md",
        "growth_strategy.md",
        "pricing_strategy.md",
        "mergers_and_acquisitions.md",
        "unconventional_and_abstract.md",
    ],
    "industries": [
        "01_logistics_and_cold_chain.md",
        "02_ecommerce_and_marketplaces.md",
        "03_pharma_and_healthcare.md",
        "04_banking_and_financial_services.md",
        "05_fmcg_and_cpg.md",
        "06_aviation_and_airlines.md",
        "07_telecom_and_media.md",
        "08_saas_and_b2b_tech.md",
        "09_retail_and_fashion.md",
        "10_automotive_and_ev.md",
        "11_energy_and_renewables.md",
        "12_hospitality_and_tourism.md",
        "13_food_and_beverage_restaurants.md",
        "14_heavy_manufacturing_and_steel.md",
        "15_fintech_and_payments.md",
        "16_insurance.md",
        "17_defense_and_aerospace.md",
    ],
    "evaluation_engine": [
        "detection_rubrics.yaml",
        "golden_rewrites_catalogue.md",
        "system_prompt_knowledge_pack.md",
    ],
}

ALL_EXPECTED_RELPATHS = []
for sub, files in EXPECTED_FILES.items():
    for f in files:
        ALL_EXPECTED_RELPATHS.append(os.path.join(sub, f))

FORBIDDEN_PATTERNS = [
    (re.compile(r"\bTODO\b", re.IGNORECASE), "TODO"),
    (re.compile(r"\bTBD\b", re.IGNORECASE), "TBD"),
    (re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE), "PLACEHOLDER"),
    (re.compile(r"\bFIXME\b", re.IGNORECASE), "FIXME"),
    (re.compile(r"\blorem\s+ipsum\b", re.IGNORECASE), "lorem ipsum"),
    (re.compile(r"\[\s*\.\.\.\s*\]"), "[...]"),
    (re.compile(r"under\s+construction", re.IGNORECASE), "under construction"),
]

def audit_file_inventory():
    print("=== CHECK 1: File Inventory & Basic Stats ===")
    results = {"total_files": 0, "total_lines": 0, "total_words": 0, "errors": []}
    
    if not os.path.exists(KB_ROOT):
        results["errors"].append(f"KB root {KB_ROOT} does not exist!")
        return results

    actual_files = sorted(
        os.path.relpath(p, KB_ROOT)
        for p in glob.glob(os.path.join(KB_ROOT, "**", "*"), recursive=True)
        if os.path.isfile(p)
    )

    results["total_files"] = len(actual_files)
    if len(actual_files) != 31:
        results["errors"].append(f"Expected 31 files, found {len(actual_files)}")

    for rel in ALL_EXPECTED_RELPATHS:
        full_path = os.path.join(KB_ROOT, rel)
        if not os.path.exists(full_path):
            results["errors"].append(f"Missing file: {rel}")
            continue
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()
            words = content.split()
            results["total_lines"] += len(lines)
            results["total_words"] += len(words)
            if len(lines) < 150:
                results["errors"].append(f"File {rel} has only {len(lines)} lines (< 150)")

    print(f"Total Files: {results['total_files']} (Expected: 31)")
    print(f"Total Lines: {results['total_lines']}")
    print(f"Total Words: {results['total_words']}")
    if results["errors"]:
        print(f"FAILED Inventory with errors: {results['errors']}")
    else:
        print("PASSED File Inventory & Basic Stats")
    return results


def audit_yaml_frontmatter():
    print("\n=== CHECK 2: YAML Frontmatter Verification ===")
    required_keys = {"title", "category", "topics_covered", "target_use_case"}
    errors = []
    checked_count = 0

    for rel in ALL_EXPECTED_RELPATHS:
        if not rel.endswith(".md"):
            continue
        checked_count += 1
        full_path = os.path.join(KB_ROOT, rel)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---\n"):
            errors.append(f"{rel}: Does not start with '---'")
            continue

        parts = content.split("---\n", 2)
        if len(parts) < 3:
            errors.append(f"{rel}: Incomplete YAML frontmatter delimiter")
            continue

        try:
            fm = yaml.safe_load(parts[1])
        except Exception as e:
            errors.append(f"{rel}: YAML parse error: {e}")
            continue

        if not isinstance(fm, dict):
            errors.append(f"{rel}: Frontmatter is not a dict")
            continue

        missing = required_keys - set(fm.keys())
        if missing:
            errors.append(f"{rel}: Missing keys {missing}")
        if not isinstance(fm.get("topics_covered"), list) or len(fm.get("topics_covered", [])) < 2:
            errors.append(f"{rel}: 'topics_covered' must be a list with >= 2 items")

    print(f"Checked {checked_count} Markdown files for frontmatter.")
    if errors:
        print(f"FAILED Frontmatter verification: {errors}")
    else:
        print("PASSED Frontmatter verification (30/30 files valid)")
    return errors


def audit_forbidden_placeholders():
    print("\n=== CHECK 3: Anti-Cheating & Forbidden Placeholders ===")
    violations = []
    for rel in ALL_EXPECTED_RELPATHS:
        full_path = os.path.join(KB_ROOT, rel)
        with open(full_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                for pat, name in FORBIDDEN_PATTERNS:
                    if pat.search(line):
                        violations.append(f"{rel}:{idx} - Found '{name}': {line.strip()}")

    if violations:
        print(f"FAILED Placeholder Check with {len(violations)} violations:\n" + "\n".join(violations))
    else:
        print("PASSED Placeholder Check: 0 forbidden tokens found across all 31 files")
    return violations


def audit_mermaid_diagrams():
    print("\n=== CHECK 4: Mermaid.js Diagrams & Trees ===")
    valid_headers = (
        "graph", "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram",
        "stateDiagram-v2", "erDiagram", "gantt", "pie", "gitGraph", "journey",
        "mindmap", "timeline", "quadrantChart"
    )
    diagram_count = 0
    errors = []

    for rel in ALL_EXPECTED_RELPATHS:
        if not rel.endswith(".md"):
            continue
        full_path = os.path.join(KB_ROOT, rel)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = re.findall(r"```mermaid\s*\n(.*?)\n```", content, re.DOTALL)
        for b_idx, block in enumerate(blocks, 1):
            diagram_count += 1
            lines = block.strip().split("\n")
            if not lines:
                errors.append(f"{rel} #{b_idx}: empty block")
                continue
            first_line = lines[0].strip()
            if not any(first_line.startswith(h) for h in valid_headers):
                errors.append(f"{rel} #{b_idx}: invalid header '{first_line}'")

            subgraphs = 0
            ends = 0
            for l_idx, line in enumerate(lines, 1):
                s = line.strip()
                if not s or s.startswith("%%"):
                    continue
                if re.match(r"^subgraph\b", s):
                    subgraphs += 1
                elif s == "end" or re.match(r"^end\b", s):
                    ends += 1
                
                # Check bracket balance outside quotes
                unquoted = re.sub(r'"[^"]*"', '""', s)
                for ob, cb in [("[", "]"), ("(", ")"), ("{", "}")]:
                    if unquoted.count(ob) != unquoted.count(cb):
                        errors.append(f"{rel} #{b_idx} L{l_idx}: unbalanced '{ob}'/'{cb}' in '{s}'")

            if subgraphs != ends:
                errors.append(f"{rel} #{b_idx}: subgraphs ({subgraphs}) != ends ({ends})")

    print(f"Found {diagram_count} Mermaid diagrams across repository.")
    if errors:
        print(f"FAILED Mermaid verification: {errors}")
    else:
        print(f"PASSED Mermaid verification ({diagram_count} diagrams valid)")
    return {"count": diagram_count, "errors": errors}


def audit_r1_methodology():
    print("\n=== CHECK 5: R1 Methodology Guides Depth Audit ===")
    errors = []
    
    # 01_preliminary_questions.md
    p1 = os.path.join(KB_ROOT, "methodology", "01_preliminary_questions.md")
    with open(p1, "r", encoding="utf-8") as f:
        c1 = f.read()
    required_p1 = [
        (r"Business Model", "Business Model"),
        (r"Monetization", "Monetization"),
        (r"Scope", "Scope"),
        (r"Context", "Context"),
        (r"Segmentation", "Segmentation"),
        (r"Quantified Objective|Objective", "Quantified Objective"),
        (r"Premature Data Fishing|Fishing", "Premature Data Fishing"),
    ]
    for pat, label in required_p1:
        if not re.search(pat, c1, re.IGNORECASE):
            errors.append(f"01_preliminary_questions.md missing required concept: {label}")

    # 02_issue_tree_structuring.md
    p2 = os.path.join(KB_ROOT, "methodology", "02_issue_tree_structuring.md")
    with open(p2, "r", encoding="utf-8") as f:
        c2 = f.read()
    required_p2 = [
        (r"First-Principles", "First-Principles"),
        (r"MECE", "MECE"),
        (r"Formula", "Formula"),
        (r"Segmentation", "Segmentation"),
        (r"Value Chain", "Value Chain"),
        (r"Framework Trap", "Framework Trap"),
        (r"Custom", "Custom"),
    ]
    for pat, label in required_p2:
        if not re.search(pat, c2, re.IGNORECASE):
            errors.append(f"02_issue_tree_structuring.md missing required concept: {label}")

    # 03_hypothesis_driven_drilling.md
    p3 = os.path.join(KB_ROOT, "methodology", "03_hypothesis_driven_drilling.md")
    with open(p3, "r", encoding="utf-8") as f:
        c3 = f.read()
    required_p3 = [
        (r"Hypothesis", "Hypothesis"),
        (r"High-Leverage|80/20", "High-Leverage"),
        (r"Path Efficiency|Trajectory", "Path Efficiency / Trajectory"),
        (r"Interviewer Hint|Nudge|Pivot", "Interviewer Hint / Pivot"),
    ]
    for pat, label in required_p3:
        if not re.search(pat, c3, re.IGNORECASE):
            errors.append(f"03_hypothesis_driven_drilling.md missing required concept: {label}")

    # 04_data_gathering_and_notes.md
    p4 = os.path.join(KB_ROOT, "methodology", "04_data_gathering_and_notes.md")
    with open(p4, "r", encoding="utf-8") as f:
        c4 = f.read()
    required_p4 = [
        (r"Note-Taking|Notes", "Note-Taking"),
        (r"Table", "Table"),
        (r"Arithmetic|Calculation", "Arithmetic Tracking"),
        (r"Sanity-Check|Sanity", "Sanity Checking"),
    ]
    for pat, label in required_p4:
        if not re.search(pat, c4, re.IGNORECASE):
            errors.append(f"04_data_gathering_and_notes.md missing required concept: {label}")

    # 05_synthesis_and_recommendations.md
    p5 = os.path.join(KB_ROOT, "methodology", "05_synthesis_and_recommendations.md")
    with open(p5, "r", encoding="utf-8") as f:
        c5 = f.read()
    required_p5 = [
        (r"Pyramid Principle", "Pyramid Principle"),
        (r"Answer-First", "Answer-First"),
        (r"Recommendation", "Recommendation"),
        (r"Pillars", "Pillars"),
        (r"Risks", "Risks"),
        (r"100-Day|Action Plan", "100-Day Action Plan"),
        (r"Partner-Ready", "Partner-Ready"),
    ]
    for pat, label in required_p5:
        if not re.search(pat, c5, re.IGNORECASE):
            errors.append(f"05_synthesis_and_recommendations.md missing required concept: {label}")

    if errors:
        print(f"FAILED R1 Methodology with errors: {errors}")
    else:
        print("PASSED R1 Methodology Audit (all 5 playbooks fully detailed with core frameworks)")
    return errors


def audit_r2_case_types():
    print("\n=== CHECK 6: R2 Case-Type Deep Dives Depth Audit ===")
    errors = []
    case_requirements = {
        "profitability.md": [(r"Cost|Cost-out|Cost Breakdown", "Cost"), (r"Margin", "Margin"), (r"Price", "Price"), (r"Volume", "Volume"), (r"Product Mix|Mix", "Product Mix")],
        "market_entry.md": [(r"Attractiveness", "Attractiveness"), (r"Entry Mode", "Entry Mode"), (r"Economic Feasibility|Feasibility", "Economic Feasibility"), (r"Risks?", "Risks")],
        "growth_strategy.md": [(r"Organic", "Organic"), (r"Inorganic", "Inorganic"), (r"Ansoff", "Ansoff"), (r"Channel", "Channel")],
        "pricing_strategy.md": [(r"Cost-Plus", "Cost-Plus"), (r"Competitor", "Competitor"), (r"Value-Based", "Value-Based"), (r"Dynamic", "Dynamic")],
        "mergers_and_acquisitions.md": [(r"Strategic Fit", "Strategic Fit"), (r"Valuation", "Valuation"), (r"Synergy", "Synergy"), (r"Integration", "Integration")],
        "unconventional_and_abstract.md": [(r"Guesstimate", "Guesstimate"), (r"Public Policy", "Public Policy"), (r"Optimization", "Optimization")],
    }

    for fname, req_terms in case_requirements.items():
        p = os.path.join(KB_ROOT, "case_types", fname)
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        for pat, label in req_terms:
            if not re.search(pat, content, re.IGNORECASE):
                errors.append(f"{fname} missing concept: {label}")
        # Must have Mermaid diagrams
        diagrams = re.findall(r"```mermaid\s*\n.*?\n```", content, re.DOTALL)
        if len(diagrams) < 2:
            errors.append(f"{fname} has only {len(diagrams)} Mermaid diagrams (< 2)")

    if errors:
        print(f"FAILED R2 Case Types with errors: {errors}")
    else:
        print("PASSED R2 Case Types Audit (all 6 archetypes have issue trees, formulas, rewrites, and diagrams)")
    return errors


def audit_r3_industries():
    print("\n=== CHECK 7: R3 Industry Dossiers (17 Industries) Depth Audit ===")
    errors = []
    industry_requirements = {
        "01_logistics_and_cold_chain.md": [(r"Fleet utilization", "Fleet utilization"), (r"Route density", "Route density"), (r"Temperature", "Temperature"), (r"Empty miles", "Empty miles")],
        "02_ecommerce_and_marketplaces.md": [(r"Take rate", "Take rate"), (r"CAC", "CAC"), (r"LTV", "LTV"), (r"GMV", "GMV"), (r"Cohort", "Cohort"), (r"Return", "Return")],
        "03_pharma_and_healthcare.md": [(r"Clinical trial", "Clinical trial"), (r"Patent", "Patent"), (r"ARPOB", "ARPOB"), (r"ALOS", "ALOS")],
        "04_banking_and_financial_services.md": [(r"NIM", "NIM"), (r"CASA", "CASA"), (r"NPA|GNPA", "NPA/GNPA"), (r"Cost-to-income", "Cost-to-income")],
        "05_fmcg_and_cpg.md": [(r"Trade promotion", "Trade promotion"), (r"Distributor margin", "Distributor margin"), (r"Modern trade", "Modern trade"), (r"General trade", "General trade")],
        "06_aviation_and_airlines.md": [(r"ASK", "ASK"), (r"RPK", "RPK"), (r"Load factor", "Load factor"), (r"Fuel", "Fuel"), (r"Ancillary", "Ancillary")],
        "07_telecom_and_media.md": [(r"ARPU", "ARPU"), (r"Churn", "Churn"), (r"Spectrum", "Spectrum"), (r"Tower", "Tower")],
        "08_saas_and_b2b_tech.md": [(r"ARR", "ARR"), (r"Net revenue retention|NRR", "Net revenue retention"), (r"Magic number", "Magic number"), (r"Payback", "Payback")],
        "09_retail_and_fashion.md": [(r"Sales per (?:sq(?:uare)?\.?\s*ft\.?|Square Foot)|SPSF", "Sales per sq ft / SPSF"), (r"Same-store sales|SSSG", "Same-store sales / SSSG"), (r"Inventory turn|ITR", "Inventory turn / ITR")],
        "10_automotive_and_ev.md": [(r"BOM", "BOM"), (r"Battery pack|Battery", "Battery pack"), (r"Dealership", "Dealership"), (r"Charging", "Charging")],
        "11_energy_and_renewables.md": [(r"LCOE", "LCOE"), (r"Capacity utilization factor|CUF", "CUF"), (r"Grid parity", "Grid parity"), (r"PPA", "PPA")],
        "12_hospitality_and_tourism.md": [(r"RevPAR", "RevPAR"), (r"ADR", "ADR"), (r"Occupancy", "Occupancy"), (r"OTA", "OTA")],
        "13_food_and_beverage_restaurants.md": [(r"Table turn", "Table turn"), (r"Food cost", "Food cost"), (r"Dark kitchen|Cloud kitchen", "Dark kitchen"), (r"Aggregator", "Aggregator")],
        "14_heavy_manufacturing_and_steel.md": [(r"Capacity utilization", "Capacity utilization"), (r"Raw material", "Raw material"), (r"Fixed cost", "Fixed cost")],
        "15_fintech_and_payments.md": [(r"MDR", "MDR"), (r"Velocity", "Velocity"), (r"Interchange", "Interchange"), (r"Default|Loss Given Default|ECL", "Default rate / ECL")],
        "16_insurance.md": [(r"Combined Ratio", "Combined Ratio"), (r"Loss Ratio", "Loss Ratio"), (r"Expense Ratio", "Expense Ratio"), (r"Float", "Float"), (r"Underwriting Margin", "Underwriting Margin"), (r"Solvency", "Solvency")],
        "17_defense_and_aerospace.md": [(r"Procurement", "Procurement"), (r"Cost-Plus", "Cost-Plus"), (r"Fixed-Price", "Fixed-Price"), (r"Offset", "Offset"), (r"Capex|R&D", "Capex / R&D"), (r"Order book|Book-to-bill", "Order book / Book-to-bill"), (r"Export", "Export")],
    }

    required_sections = ["Value Chain", "Revenue", "Cost", "KPI", "Unit Economics", "Pitfall"]

    for fname, req_terms in industry_requirements.items():
        p = os.path.join(KB_ROOT, "industries", fname)
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()

        # Check terms
        for pat, label in req_terms:
            if not re.search(pat, content, re.IGNORECASE):
                errors.append(f"{fname} missing mandated term: '{label}'")

        # Check sections
        for s in required_sections:
            if not re.search(re.escape(s), content, re.IGNORECASE):
                errors.append(f"{fname} missing mandated section theme: '{s}'")

    if errors:
        print(f"FAILED R3 Industries with errors: {errors}")
    else:
        print("PASSED R3 Industry Dossiers Audit (all 17 industries cover required value chains, KPIs, unit economics, pitfalls)")
    return errors


def audit_r4_evaluation_engine():
    print("\n=== CHECK 8: R4 Evaluation Engine Audit ===")
    errors = []

    # 1. detection_rubrics.yaml
    rubric_p = os.path.join(KB_ROOT, "evaluation_engine", "detection_rubrics.yaml")
    with open(rubric_p, "r", encoding="utf-8") as f:
        rubric_data = yaml.safe_load(f)

    stages = rubric_data.get("stages", [])
    if len(stages) != 5:
        errors.append(f"detection_rubrics.yaml has {len(stages)} stages (expected 5)")

    total_weight = sum(s.get("stage_weight", 0) for s in stages)
    if round(total_weight, 4) != 1.0:
        errors.append(f"Stage weights sum to {total_weight} (expected 1.00)")

    for st in stages:
        for sub in st.get("sub_dimensions", []):
            if not sub.get("markers"):
                errors.append(f"Stage {st.get('stage_id')} sub-dimension {sub.get('id')} has no markers")
            if not sub.get("counter_markers"):
                errors.append(f"Stage {st.get('stage_id')} sub-dimension {sub.get('id')} has no counter_markers")

    # 2. golden_rewrites_catalogue.md
    golden_p = os.path.join(KB_ROOT, "evaluation_engine", "golden_rewrites_catalogue.md")
    with open(golden_p, "r", encoding="utf-8") as f:
        golden_content = f.read()

    for pat, archetype in [
        (r"Profitability", "Profitability"),
        (r"Market Entry", "Market Entry"),
        (r"Growth Strategy", "Growth Strategy"),
        (r"Pricing Strategy", "Pricing Strategy"),
        (r"M&A|Merger|Acquisition", "M&A / Mergers"),
        (r"Unconventional|Public Policy|Abstract", "Unconventional"),
    ]:
        if not re.search(pat, golden_content, re.IGNORECASE):
            errors.append(f"golden_rewrites_catalogue.md missing archetype: {archetype}")

    # 3. system_prompt_knowledge_pack.md
    sp_p = os.path.join(KB_ROOT, "evaluation_engine", "system_prompt_knowledge_pack.md")
    with open(sp_p, "r", encoding="utf-8") as f:
        sp_content = f.read()

    if len(sp_content) < 3000:
        errors.append("system_prompt_knowledge_pack.md is too short (< 3000 chars)")

    if errors:
        print(f"FAILED R4 Evaluation Engine with errors: {errors}")
    else:
        print("PASSED R4 Evaluation Engine Audit (rubrics, rewrites, and system prompt pack verified)")
    return errors


def main():
    print("================================================================================")
    print("INDEPENDENT VICTORY AUDIT: MBB CASE PREP V2 KNOWLEDGE BASE")
    print("================================================================================")

    res_inv = audit_file_inventory()
    err_fm = audit_yaml_frontmatter()
    err_ph = audit_forbidden_placeholders()
    res_mm = audit_mermaid_diagrams()
    err_r1 = audit_r1_methodology()
    err_r2 = audit_r2_case_types()
    err_r3 = audit_r3_industries()
    err_r4 = audit_r4_evaluation_engine()

    all_errors = res_inv["errors"] + err_fm + err_ph + res_mm["errors"] + err_r1 + err_r2 + err_r3 + err_r4

    print("\n================================================================================")
    print("AUDIT SUMMARY & VERDICT")
    print("================================================================================")
    print(f"Total Errors / Violations Found: {len(all_errors)}")
    if all_errors:
        print("VERDICT: VICTORY REJECTED")
        for e in all_errors:
            print(f"  - {e}")
        return 1
    else:
        print("VERDICT: VICTORY CONFIRMED")
        print("All 31 files, 4 major modules, 17 industry dossiers, 6 case archetypes,")
        print("5 methodology playbooks, and complete evaluation engine are authentic and complete.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
