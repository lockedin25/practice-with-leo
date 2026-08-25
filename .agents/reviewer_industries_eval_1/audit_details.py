import os
import re
import yaml

BASE_DIR = "/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2"
ind_dir = os.path.join(BASE_DIR, "knowledge_base/industries")

files = sorted(os.listdir(ind_dir))
print(f"Total industry files: {len(files)}")

for f in files:
    if not f.endswith(".md"): 
        continue
    path = os.path.join(ind_dir, f)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    
    # Frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    fm = yaml.safe_load(fm_match.group(1)) if fm_match else None
    
    # H2s
    h2s = re.findall(r"^##\s+(.+)$", text, re.MULTILINE)
    
    # Tables
    tables = len(re.findall(r"\|[-:\s|]+\|", text))
    
    # Code blocks
    code_blocks = len(re.findall(r"```", text)) // 2
    
    # Words & Lines
    words = len(text.split())
    lines = len(text.splitlines())
    
    title = fm.get("title") if fm else "NO FM"
    category = fm.get("category") if fm else "NO FM"
    topics_cnt = len(fm.get("topics_covered", [])) if fm else 0
    target_use = fm.get("target_use_case") if fm else "NO FM"
    
    print("\n" + "="*50)
    print(f"FILE: {f}")
    print(f"Title: {title}")
    print(f"Category: {category}")
    print(f"Topics count: {topics_cnt} | Target Use Case: {target_use[:40]}...")
    print(f"Words: {words} | Lines: {lines} | Tables: {tables} | Code Blocks: {code_blocks}")
    print("H2 Sections:")
    for idx, h2 in enumerate(h2s, 1):
        print(f"  {idx}. {h2}")
