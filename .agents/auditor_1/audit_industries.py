"""
Forensic Audit of all 17 Industry Dossiers in knowledge_base/industries/
"""

import os
import glob
import re
import yaml

BASE_DIR = '/Users/shubhamkorde/Desktop/Projects/MBB Case Prep V2/knowledge_base/industries'

def audit_industry_files():
    files = sorted(glob.glob(f'{BASE_DIR}/*.md'))
    print(f'Auditing {len(files)} industry dossiers...')

    required_sections = [
        'Executive Summary',
        'Industry Value Chain',
        'Revenue Models',
        'Cost Structure',
        'Key Performance Indicators',
        'Unit Economics',
        'Case Pitfalls',
    ]

    report = []

    for fpath in files:
        fname = os.path.basename(fpath)
        with open(fpath, 'r', encoding='utf-8') as fp:
            content = fp.read()

        file_res = {
            'file': fname,
            'passed': True,
            'missing_sections': [],
            'kpi_count': len(re.findall(r'\$\$.*?\$\$', content, re.DOTALL)),
            'tables': len(re.findall(r'\|.*?\|.*?\|\n\|[-:\s|]+\|\n(?:\|.*?\|\n)+', content)),
            'words': len(content.split()),
            'lines': len(content.splitlines()),
            'issues': []
        }

        # Check required sections
        for sec in required_sections:
            if not re.search(re.escape(sec), content, re.IGNORECASE):
                file_res['missing_sections'].append(sec)
                file_res['passed'] = False

        if file_res['kpi_count'] < 5:
            file_res['issues'].append(f'Low formula count ({file_res["kpi_count"]} math blocks)')
        
        if file_res['tables'] < 1:
            file_res['issues'].append(f'No markdown tables found')

        report.append(file_res)

    return report

if __name__ == '__main__':
    results = audit_industry_files()
    all_pass = True
    print('=' * 80)
    print(f'{"File Name":38} | {"Words":5} | {"Lines":4} | {"KPI Math":8} | {"Tables":6} | {"Status"}')
    print('=' * 80)
    for r in results:
        status = 'PASS' if r['passed'] and not r['issues'] else 'FAIL/WARN'
        if status != 'PASS':
            all_pass = False
        print(f'{r["file"]:38} | {r["words"]:5} | {r["lines"]:4} | {r["kpi_count"]:8} | {r["tables"]:6} | {status}')
        if r['missing_sections']:
            print(f'   --> Missing sections: {r["missing_sections"]}')
        if r['issues']:
            print(f'   --> Issues: {r["issues"]}')
    print('=' * 80)
    print(f'Overall Industry Dossiers Result: {"PASS" if all_pass else "FAIL"}')
