"""
Comprehensive Forensic Audit Suite for MBB Case Prep V2
Author: Forensic Auditor (auditor_1)
"""

import os
import glob
import re
import sys
import yaml

BASE_DIR = '/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/knowledge_base'

def audit_file_inventory():
    expected_files = {
        'methodology': [
            '01_preliminary_questions.md',
            '02_issue_tree_structuring.md',
            '03_hypothesis_driven_drilling.md',
            '04_data_gathering_and_notes.md',
            '05_synthesis_and_recommendations.md',
        ],
        'case_types': [
            'profitability.md',
            'market_entry.md',
            'growth_strategy.md',
            'pricing_strategy.md',
            'mergers_and_acquisitions.md',
            'unconventional_and_abstract.md',
        ],
        'industries': [
            '01_logistics_and_cold_chain.md',
            '02_ecommerce_and_marketplaces.md',
            '03_pharma_and_healthcare.md',
            '04_banking_and_financial_services.md',
            '05_fmcg_and_cpg.md',
            '06_aviation_and_airlines.md',
            '07_telecom_and_media.md',
            '08_saas_and_b2b_tech.md',
            '09_retail_and_fashion.md',
            '10_automotive_and_ev.md',
            '11_energy_and_renewables.md',
            '12_hospitality_and_tourism.md',
            '13_food_and_beverage_restaurants.md',
            '14_heavy_manufacturing_and_steel.md',
            '15_fintech_and_payments.md',
            '16_insurance.md',
            '17_defense_and_aerospace.md',
        ],
        'evaluation_engine': [
            'detection_rubrics.yaml',
            'golden_rewrites_catalogue.md',
            'system_prompt_knowledge_pack.md',
        ]
    }

    results = {'pass': True, 'details': []}
    total_expected = 0
    total_found = 0

    for category, file_list in expected_files.items():
        total_expected += len(file_list)
        cat_dir = os.path.join(BASE_DIR, category)
        if not os.path.exists(cat_dir):
            results['pass'] = False
            results['details'].append(f'CRITICAL: Directory missing: {cat_dir}')
            continue
        for fname in file_list:
            fpath = os.path.join(cat_dir, fname)
            if not os.path.exists(fpath):
                results['pass'] = False
                results['details'].append(f'MISSING FILE: {category}/{fname}')
            else:
                sz = os.path.getsize(fpath)
                if sz < 1000:
                    results['pass'] = False
                    results['details'].append(f'SUSPICIOUSLY SMALL FILE (<1KB): {category}/{fname} ({sz} bytes)')
                else:
                    total_found += 1

    results['details'].append(f'Inventory check: {total_found}/{total_expected} files present and verified non-empty.')
    return results

def audit_frontmatter_and_placeholders():
    md_files = glob.glob(f'{BASE_DIR}/**/*.md', recursive=True)
    results = {'pass': True, 'details': []}

    placeholder_patterns = [
        r'\bTODO\b', r'\bTBD\b', r'\bFIXME\b', r'\bXXX\b', r'\bPLACEHOLDER\b',
        r'\[insert\b', r'\[add\b', r'lorem ipsum', r'\bto be added\b', r'\bcoming soon\b'
    ]

    for fpath in md_files:
        rel = os.path.relpath(fpath, BASE_DIR)
        with open(fpath, 'r', encoding='utf-8') as fp:
            content = fp.read()

        # Frontmatter check
        if not content.startswith('---'):
            results['pass'] = False
            results['details'].append(f'{rel}: Missing YAML frontmatter marker at start')
            continue
        parts = content.split('---', 2)
        if len(parts) < 3:
            results['pass'] = False
            results['details'].append(f'{rel}: Malformed YAML frontmatter (fewer than 2 delimiters)')
            continue
        try:
            fm = yaml.safe_load(parts[1])
            if not isinstance(fm, dict):
                results['pass'] = False
                results['details'].append(f'{rel}: Frontmatter is not a dictionary')
                continue
            req_keys = ['title', 'category', 'topics_covered', 'target_use_case']
            for k in req_keys:
                if k not in fm or not fm[k]:
                    results['pass'] = False
                    results['details'].append(f'{rel}: Missing or empty frontmatter field \"{k}\"')
        except Exception as e:
            results['pass'] = False
            results['details'].append(f'{rel}: YAML parsing error in frontmatter: {e}')

        # Placeholder check
        for pat in placeholder_patterns:
            matches = list(re.finditer(pat, content, re.IGNORECASE))
            for m in matches:
                # exclude legitimate case mentions (e.g. if any)
                start = max(0, m.start() - 25)
                end = min(len(content), m.end() + 25)
                snippet = content[start:end].replace('\n', ' ')
                results['pass'] = False
                results['details'].append(f'{rel}: Found placeholder match \"{m.group(0)}\" near \"{snippet}\"')

    return results

def audit_mermaid_diagrams():
    md_files = glob.glob(f'{BASE_DIR}/**/*.md', recursive=True)
    results = {'pass': True, 'diagram_count': 0, 'details': []}

    for fpath in md_files:
        rel = os.path.relpath(fpath, BASE_DIR)
        with open(fpath, 'r', encoding='utf-8') as fp:
            lines = fp.readlines()

        in_mermaid = False
        m_lines = []
        start_line = 0

        for line_idx, line in enumerate(lines, 1):
            if line.strip().startswith('```mermaid'):
                in_mermaid = True
                m_lines = []
                start_line = line_idx
            elif in_mermaid and line.strip().startswith('```'):
                in_mermaid = False
                results['diagram_count'] += 1
                # Validate mermaid block content
                non_empty = [l.strip() for l in m_lines if l.strip() and not l.strip().startswith('%%')]
                if not non_empty:
                    results['pass'] = False
                    results['details'].append(f'{rel} (L{start_line}): Empty mermaid block')
                    continue
                header = non_empty[0]
                valid_headers = ['graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 'stateDiagram', 'erDiagram', 'gantt', 'pie', 'mindmap', 'gitGraph', 'journey', 'timeline', 'quadrantChart']
                if not any(header.startswith(vh) for vh in valid_headers):
                    results['pass'] = False
                    results['details'].append(f'{rel} (L{start_line}): Unknown mermaid diagram type \"{header}\"')
            elif in_mermaid:
                m_lines.append(line)

    results['details'].append(f'Audited {results["diagram_count"]} Mermaid diagrams across all modules.')
    return results

def audit_eval_yaml():
    yaml_path = os.path.join(BASE_DIR, 'evaluation_engine', 'detection_rubrics.yaml')
    results = {'pass': True, 'details': []}
    if not os.path.exists(yaml_path):
        results['pass'] = False
        results['details'].append('detection_rubrics.yaml is missing')
        return results

    try:
        with open(yaml_path, 'r', encoding='utf-8') as fp:
            data = yaml.safe_load(fp)
        expected_keys = ['schema_version', 'metadata', 'scoring_scale', 'global_evaluation_principles', 'stages', 'penalty_matrix', 'distinction_triggers']
        for k in expected_keys:
            if k not in data:
                results['pass'] = False
                results['details'].append(f'detection_rubrics.yaml missing expected top-level key: {k}')
        
        stages = data.get('stages', [])
        if isinstance(stages, list):
            stage_ids = [s.get('stage_id') for s in stages if isinstance(s, dict)]
            results['details'].append(f'detection_rubrics.yaml loaded successfully. Stages defined: {stage_ids}')
        elif isinstance(stages, dict):
            results['details'].append(f'detection_rubrics.yaml loaded successfully. Stages defined: {list(stages.keys())}')
        else:
            results['pass'] = False
            results['details'].append(f'detection_rubrics.yaml stages field is invalid type: {type(stages)}')
    except Exception as e:
        results['pass'] = False
        results['details'].append(f'YAML parse error in detection_rubrics.yaml: {e}')

    return results

def audit_content_density_and_math():
    md_files = glob.glob(f'{BASE_DIR}/**/*.md', recursive=True)
    results = {'pass': True, 'details': [], 'stats': {}}

    for fpath in md_files:
        rel = os.path.relpath(fpath, BASE_DIR)
        with open(fpath, 'r', encoding='utf-8') as fp:
            content = fp.read()

        latex_blocks = len(re.findall(r'\$\$(.*?)\$\$', content, re.DOTALL))
        latex_inline = len(re.findall(r'\$([^\$\n]+)\$', content))
        tables = len(re.findall(r'\|.*?\|.*?\|\n\|[-:\s|]+\|\n(?:\|.*?\|\n)+', content))
        word_count = len(content.split())
        line_count = len(content.splitlines())

        results['stats'][rel] = {
            'words': word_count,
            'lines': line_count,
            'tables': tables,
            'latex_blocks': latex_blocks,
            'latex_inline': latex_inline
        }

        # Check thresholds
        if word_count < 1000:
            results['pass'] = False
            results['details'].append(f'LOW WORD COUNT: {rel} ({word_count} words)')

    return results

def audit_consulting_pedigree():
    """
    Check for authentic pedigree references (Victor Cheng, Case Interview Cracked, Crafting Cases,
    IIM casebooks, McKinsey/BCG/Bain specific terminology)
    """
    md_files = glob.glob(f'{BASE_DIR}/**/*.md', recursive=True)
    results = {'pass': True, 'details': [], 'pedigree_counts': {}}

    pedigree_terms = [
        'MECE', 'Pyramid Principle', 'Hypothesis', 'Issue Tree', 'First-Principles',
        'Victor Cheng', 'Case Interview Cracked', 'Crafting Cases', 'IIM',
        'McKinsey', 'BCG', 'Bain', 'Sanity Check', 'So What', '80/20'
    ]

    total_pedigree_hits = 0
    for fpath in md_files:
        rel = os.path.relpath(fpath, BASE_DIR)
        with open(fpath, 'r', encoding='utf-8') as fp:
            content = fp.read()

        file_hits = {}
        for term in pedigree_terms:
            c = len(re.findall(r'\b' + re.escape(term) + r'\b', content, re.IGNORECASE))
            if c > 0:
                file_hits[term] = c
                total_pedigree_hits += c
        results['pedigree_counts'][rel] = file_hits

    results['details'].append(f'Consulting pedigree scan: Total {total_pedigree_hits} references found across {len(md_files)} markdown files.')
    return results

if __name__ == '__main__':
    print('=' * 70)
    print('RUNNING COMPREHENSIVE FORENSIC AUDIT SUITE FOR MBB CASE PREP V2')
    print('=' * 70)

    inv = audit_file_inventory()
    print(f'[1] File Inventory: {"PASS" if inv["pass"] else "FAIL"}')
    for d in inv['details']:
        print(f'    {d}')

    fm = audit_frontmatter_and_placeholders()
    print(f'\n[2] Frontmatter & Placeholders: {"PASS" if fm["pass"] else "FAIL"}')
    if fm['details']:
        for d in fm['details']:
            print(f'    {d}')
    else:
        print('    All 30 Markdown files have valid frontmatter and zero placeholders.')

    mm = audit_mermaid_diagrams()
    print(f'\n[3] Mermaid Diagrams: {"PASS" if mm["pass"] else "FAIL"}')
    for d in mm['details']:
        print(f'    {d}')

    ev = audit_eval_yaml()
    print(f'\n[4] Evaluator YAML Rubric: {"PASS" if ev["pass"] else "FAIL"}')
    for d in ev['details']:
        print(f'    {d}')

    cd = audit_content_density_and_math()
    print(f'\n[5] Content Density & Math Formatting: {"PASS" if cd["pass"] else "FAIL"}')
    for rel, s in sorted(cd['stats'].items()):
        print(f'    {rel:48} | {s["words"]:5} words | {s["lines"]:4} lines | {s["tables"]:2} tables | {s["latex_blocks"]:2} LaTeX blocks | {s["latex_inline"]:3} inline math')

    cp = audit_consulting_pedigree()
    print(f'\n[6] Consulting Pedigree: {"PASS" if cp["pass"] else "FAIL"}')
    for d in cp['details']:
        print(f'    {d}')

