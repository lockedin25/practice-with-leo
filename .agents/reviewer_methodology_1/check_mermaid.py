import os
import re

case_types_dir = "knowledge_base/case_types"
files_case_types = [
    "profitability.md",
    "market_entry.md",
    "growth_strategy.md",
    "pricing_strategy.md",
    "mergers_and_acquisitions.md",
    "unconventional_and_abstract.md"
]

total_diagrams = 0
for f in files_case_types:
    path = os.path.join(case_types_dir, f)
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    
    diagrams = re.findall(r"```mermaid\n(.*?)```", content, re.DOTALL)
    print(f"=== {f} ({len(diagrams)} diagrams) ===")
    for i, diag in enumerate(diagrams, 1):
        total_diagrams += 1
        lines = [l for l in diag.strip().splitlines() if l.strip()]
        header = lines[0] if lines else "EMPTY"
        print(f"  Diagram {i}: Header='{header}', Lines={len(lines)}")
        
        # Check for balanced parentheses, brackets, quotes within node definitions
        errors = []
        for line_idx, line in enumerate(lines, 1):
            # Check balanced brackets
            if line.count('[') != line.count(']'):
                errors.append(f"Unbalanced square brackets on line {line_idx}: {line}")
            if line.count('(') != line.count(')'):
                # Note: node ID like A(some text) is ok, but unbalanced inside node is bad
                errors.append(f"Unbalanced parentheses on line {line_idx}: {line}")
            if line.count('{') != line.count('}'):
                errors.append(f"Unbalanced curly braces on line {line_idx}: {line}")
            if line.count('"') % 2 != 0:
                errors.append(f"Unbalanced double quotes on line {line_idx}: {line}")
        if errors:
            print(f"    ERRORS in diagram {i}:")
            for err in errors:
                print(f"      - {err}")
        else:
            print(f"    Syntax check: PASS (clean brackets & quotes)")

print(f"\nTotal Mermaid diagrams validated: {total_diagrams}")
