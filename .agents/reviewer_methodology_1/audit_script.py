import os
import glob
import re

methodology_dir = "knowledge_base/methodology"
case_types_dir = "knowledge_base/case_types"

files_methodology = [
    "01_preliminary_questions.md",
    "02_issue_tree_structuring.md",
    "03_hypothesis_driven_drilling.md",
    "04_data_gathering_and_notes.md",
    "05_synthesis_and_recommendations.md"
]

files_case_types = [
    "profitability.md",
    "market_entry.md",
    "growth_strategy.md",
    "pricing_strategy.md",
    "mergers_and_acquisitions.md",
    "unconventional_and_abstract.md"
]

all_files = [(methodology_dir, f) for f in files_methodology] + [(case_types_dir, f) for f in files_case_types]

print(f"Auditing {len(all_files)} files...\n" + "="*60)

placeholder_patterns = [
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE),
    re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE),
    re.compile(r"\[insert\b", re.IGNORECASE),
    re.compile(r"\[to be\b", re.IGNORECASE),
    re.compile(r"\[add\b", re.IGNORECASE)
]

def parse_simple_frontmatter(fm_str):
    data = {}
    lines = fm_str.strip().splitlines()
    current_key = None
    list_items = []
    
    for line in lines:
        if not line.strip() or line.strip().startswith('#'):
            continue
        if line.startswith('  - ') or line.startswith('- '):
            item = line.strip().lstrip('- ').strip().strip('"').strip("'")
            list_items.append(item)
            if current_key:
                data[current_key] = list_items
        elif ':' in line:
            if current_key and list_items:
                data[current_key] = list_items
                list_items = []
            parts = line.split(':', 1)
            key = parts[0].strip()
            val = parts[1].strip().strip('"').strip("'")
            current_key = key
            if val:
                data[key] = val
            else:
                data[key] = []
                list_items = []
    if current_key and list_items:
        data[current_key] = list_items
    return data

total_words = 0
total_lines = 0
total_mermaid = 0
files_passed = 0

for d, f in all_files:
    path = os.path.join(d, f)
    if not os.path.exists(path):
        print(f"[MISSING] {path}")
        continue
    
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
        
    lines = content.splitlines()
    words = len(content.split())
    total_words += words
    total_lines += len(lines)
    
    # Frontmatter check
    fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    fm_valid = False
    fm_data = {}
    if fm_match:
        try:
            fm_data = parse_simple_frontmatter(fm_match.group(1))
            required_keys = ["title", "category", "topics_covered", "target_use_case"]
            missing_keys = [k for k in required_keys if k not in fm_data]
            if not missing_keys and isinstance(fm_data.get("topics_covered"), list) and len(fm_data["topics_covered"]) > 0:
                fm_valid = True
            else:
                print(f"[FRONTMATTER ERROR] {path}: missing keys or invalid topics_covered: {missing_keys}, data={fm_data}")
        except Exception as e:
            print(f"[FRONTMATTER PARSE ERROR] {path}: {e}")
    else:
        print(f"[NO FRONTMATTER] {path}")
        
    # Placeholder scan
    found_placeholders = []
    for line_idx, line in enumerate(lines, 1):
        for pat in placeholder_patterns:
            if pat.search(line):
                found_placeholders.append((line_idx, line.strip()))
                
    # Mermaid diagrams
    mermaid_blocks = re.findall(r"```mermaid\n(.*?)```", content, re.DOTALL)
    total_mermaid += len(mermaid_blocks)
    
    title = fm_data.get("title", "No title")
    print(f"File: {path}")
    print(f"  - Lines: {len(lines)}, Words: {words}, Size: {len(content.encode('utf-8'))} bytes")
    print(f"  - Frontmatter valid: {fm_valid} | Title: '{title}'")
    print(f"  - Category: {fm_data.get('category', 'N/A')}")
    print(f"  - Topics ({len(fm_data.get('topics_covered', []))}): {fm_data.get('topics_covered', [])}")
    print(f"  - Target use case: {fm_data.get('target_use_case', 'N/A')}")
    print(f"  - Mermaid blocks: {len(mermaid_blocks)}")
    if found_placeholders:
        print(f"  - Placeholders found ({len(found_placeholders)}):")
        for l_num, l_txt in found_placeholders:
            print(f"      L{l_num}: {l_txt[:80]}")
    else:
        print(f"  - Placeholders: 0 found")
    print("-" * 60)
    if fm_valid and not found_placeholders:
        files_passed += 1

print(f"\nSummary:")
print(f"Total files checked: {len(all_files)}")
print(f"Files meeting automated pass: {files_passed}/{len(all_files)}")
print(f"Total lines: {total_lines}")
print(f"Total words: {total_words}")
print(f"Total Mermaid diagrams: {total_mermaid}")
