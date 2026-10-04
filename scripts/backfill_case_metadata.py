"""Backfill schema-complete provenance without guessing missing history.

Run from the repo root. Authored manifests get explicit unknown values; database
submissions recover names and original creation timestamps from stored records.
"""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yaml
from app.case_provenance import backfill


def backfill_manifests(root):
    changed = []
    paths = sorted((root / 'reservoir').glob('*/case.yaml')) + sorted((root / 'corpus/exemplars').glob('*/*/case.yaml'))
    for path in paths:
        text = path.read_text()
        case = yaml.safe_load(text)
        if case.get('provenance'):
            continue
        provenance = {'source_type':'authored', 'firm':None, 'firm_tags':[], 'contributor_id':None,
                      'contributor_name':None, 'attribution_mode':'anonymous', 'contributed_at':None,
                      'metadata_source':'not_recorded'}
        path.write_text(text.rstrip() + '\n\n' + yaml.safe_dump({'provenance':provenance}, sort_keys=False))
        changed.append(str(path.relative_to(root)))
    return changed


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    changed = backfill_manifests(root)
    import app.main as main
    migrated = backfill(main.DATABASE_PATH)
    print(json.dumps({'authored_manifests_updated':len(changed), 'database_versions_updated':migrated, 'missing_history':'Explicitly not recorded; no firms, identities or contribution dates invented.'},indent=2))
