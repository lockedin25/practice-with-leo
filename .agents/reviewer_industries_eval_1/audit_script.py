import os
import re
import yaml
import sys

BASE_DIR = "/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2"
INDUSTRIES_DIR = os.path.join(BASE_DIR, "knowledge_base/industries")
EVAL_DIR = os.path.join(BASE_DIR, "knowledge_base/evaluation_engine")

MANDATORY_SECTIONS = [
    r"1\.\s+(?:Industry\s+)?Overview\s+&?\s+Macro\s+Dynamics",
    r"2\.\s+(?:Complete\s+)?(?:End-to-End\s+)?Value\s+Chain",
    r"3\.\s+Revenue\s+Models\s+&?\s+Monetization\s+(?:Mechanics|Drivers)",
    r"4\.\s+Detailed\s+Unit\s+Economics\s+&?\s+Contribution\s+Margin(?:\s+Breakdown)?",
    r"5\.\s+Comprehensive\s+Cost\s+Structure(?:\s+\(Fixed\s+vs\s+Variable\))?",
    r"6\.\s+Essential\s+KPI\s+Formulas\s+&?\s+Benchmark\s+Tables",
    r"7\.\s+Typical\s+Case\s+Scenarios\s+&?\s+Diagnostic\s+Issue\s+Trees",
    r"8\.\s+Common\s+Pitfalls\s+&?\s+Candidate\s+Landmines"
]

def check_frontmatter(content, filepath):
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not fm_match:
        return False, "Missing frontmatter delimiters (---)"
    fm_text = fm_match.group(1)
    try:
        data = yaml.safe_load(fm_text)
        if not isinstance(data, dict):
            return False, "Frontmatter is not a dict"
        required_keys = ["title", "category", "topics_covered", "target_use_case"]
        missing = [k for k in required_keys if k not in data]
        if missing:
            return False, f"Missing keys in frontmatter: {missing}"
        if not isinstance(data["topics_covered"], list) or len(data["topics_covered"]) == 0:
            return False, "topics_covered must be a non-empty list"
        return True, data
    except Exception as e:
        return False, f"YAML parse error: {e}"

def check_placeholders(content):
    patterns = [
        r"\bTODO\b",
        r"\bTBD\b",
        r"\bFIXME\b",
        r"\[placeholder\]",
        r"\[insert\b",
        r"\[TBD\]",
        r"Lorem ipsum",
        r"<!--\s*TODO",
        r"\.\.\.\s*$"
    ]
    findings = []
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        for pat in patterns:
            if re.search(pat, line, re.IGNORECASE):
                # check if it's a legitimate use of '...' or similar
                findings.append((i, line.strip(), pat))
    return findings

def audit_industries():
    print("=== AUDITING INDUSTRY DOSSIERS ===")
    files = sorted([f for f in os.listdir(INDUSTRIES_DIR) if f.endswith(".md")])
    if len(files) != 17:
        print(f"ERROR: Expected 17 files, found {len(files)}")
    
    results = {}
    for filename in files:
        filepath = os.path.join(INDUSTRIES_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 1. Frontmatter
        fm_ok, fm_info = check_frontmatter(content, filepath)
        
        # 2. Placeholders
        placeholders = check_placeholders(content)
        
        # 3. Mandatory Sections
        sections_found = []
        missing_sections = []
        for s_idx, sec_pat in enumerate(MANDATORY_SECTIONS, 1):
            match = re.search(r"^#+\s+" + sec_pat, content, re.MULTILINE | re.IGNORECASE)
            if match:
                sections_found.append((s_idx, match.group(0)))
            else:
                missing_sections.append((s_idx, sec_pat))
        
        # 4. Mermaid Diagrams
        mermaid_blocks = re.findall(r"```mermaid(.*?)```", content, re.DOTALL)
        
        # 5. Tables / P&L
        tables = re.findall(r"\|.*?\|.*?\n\|[-:\s|]+\|\n(?:\|.*?\|\n)+", content)
        
        # 6. Word count
        word_count = len(content.split())
        line_count = len(content.splitlines())
        
        results[filename] = {
            "fm_ok": fm_ok,
            "fm_info": fm_info if not fm_ok else None,
            "placeholders": placeholders,
            "sections_found_count": len(sections_found),
            "missing_sections": missing_sections,
            "mermaid_count": len(mermaid_blocks),
            "table_count": len(tables),
            "word_count": word_count,
            "line_count": line_count
        }
        
        status = "OK" if fm_ok and len(missing_sections) == 0 and len(mermaid_blocks) >= 1 and len(placeholders) == 0 else "FLAG"
        print(f"[{status}] {filename}: {word_count} words, {line_count} lines, {len(sections_found)}/8 sections, {len(mermaid_blocks)} mermaid, {len(tables)} tables, {len(placeholders)} placeholders")
        if not fm_ok:
            print(f"   Frontmatter Error: {fm_info}")
        if missing_sections:
            print(f"   Missing Sections: {missing_sections}")
        if placeholders:
            print(f"   Placeholders found: {placeholders[:5]}")
            
    return results

def audit_evaluation_engine():
    print("\n=== AUDITING EVALUATION ENGINE ===")
    eval_files = ["detection_rubrics.yaml", "golden_rewrites_catalogue.md", "system_prompt_knowledge_pack.md"]
    results = {}
    
    # 1. detection_rubrics.yaml
    yaml_path = os.path.join(EVAL_DIR, "detection_rubrics.yaml")
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_content = f.read()
        try:
            rubrics_data = yaml.safe_load(yaml_content)
            yaml_valid = isinstance(rubrics_data, dict)
            keys = list(rubrics_data.keys()) if isinstance(rubrics_data, dict) else []
            placeholders = check_placeholders(yaml_content)
            print(f"[OK] detection_rubrics.yaml: Valid YAML, top keys: {keys}, {len(yaml_content.splitlines())} lines, {len(placeholders)} placeholders")
            results["detection_rubrics.yaml"] = {"valid": yaml_valid, "keys": keys, "placeholders": placeholders}
        except Exception as e:
            print(f"[ERROR] detection_rubrics.yaml failed to parse: {e}")
            results["detection_rubrics.yaml"] = {"valid": False, "error": str(e)}
    else:
        print("[ERROR] detection_rubrics.yaml NOT FOUND")
        
    # 2. golden_rewrites_catalogue.md
    rewrites_path = os.path.join(EVAL_DIR, "golden_rewrites_catalogue.md")
    if os.path.exists(rewrites_path):
        with open(rewrites_path, "r", encoding="utf-8") as f:
            rw_content = f.read()
        fm_ok, fm_info = check_frontmatter(rw_content, rewrites_path)
        placeholders = check_placeholders(rw_content)
        word_count = len(rw_content.split())
        line_count = len(rw_content.splitlines())
        mermaid_blocks = re.findall(r"```mermaid(.*?)```", rw_content, re.DOTALL)
        print(f"[{'OK' if fm_ok else 'FLAG'}] golden_rewrites_catalogue.md: {word_count} words, {line_count} lines, {len(mermaid_blocks)} mermaid, {len(placeholders)} placeholders")
        if not fm_ok:
            print(f"   Frontmatter Error: {fm_info}")
        if placeholders:
            print(f"   Placeholders found: {placeholders[:5]}")
        results["golden_rewrites_catalogue.md"] = {"fm_ok": fm_ok, "word_count": word_count, "placeholders": placeholders}
        
    # 3. system_prompt_knowledge_pack.md
    pack_path = os.path.join(EVAL_DIR, "system_prompt_knowledge_pack.md")
    if os.path.exists(pack_path):
        with open(pack_path, "r", encoding="utf-8") as f:
            sp_content = f.read()
        fm_ok, fm_info = check_frontmatter(sp_content, pack_path)
        placeholders = check_placeholders(sp_content)
        word_count = len(sp_content.split())
        line_count = len(sp_content.splitlines())
        print(f"[{'OK' if fm_ok else 'FLAG'}] system_prompt_knowledge_pack.md: {word_count} words, {line_count} lines, {len(placeholders)} placeholders")
        if not fm_ok:
            print(f"   Frontmatter Error: {fm_info}")
        if placeholders:
            print(f"   Placeholders found: {placeholders[:5]}")
        results["system_prompt_knowledge_pack.md"] = {"fm_ok": fm_ok, "word_count": word_count, "placeholders": placeholders}

if __name__ == "__main__":
    audit_industries()
    audit_evaluation_engine()
