"""Case attribution and firm labels with honest legacy defaults."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app import db


def firm_tags(value: str | None) -> list[str]:
    text = str(value or '').casefold()
    names = []
    for pattern, label in [(r'\bbain\b', 'Bain'), (r'\bbcg\b|boston consulting', 'BCG'), (r'\bmckinsey\b|mc kinsey', 'McKinsey')]:
        if re.search(pattern, text):
            names.append(label)
    if text.strip() and not names and text.strip() not in {'unknown', 'not recorded', 'n/a'}:
        names.append(str(value).strip())
    return names


def public_metadata(case: dict) -> dict:
    provenance = case.get('provenance') or {}
    public = provenance.get('attribution_mode') == 'public'
    return {
        'contributor_name': provenance.get('contributor_name') if public else None,
        'contributor_label': provenance.get('contributor_name') if public and provenance.get('contributor_name') else ('Community contributor' if case.get('source') == 'community' else 'Curated collection'),
        'firm_tags': firm_tags(provenance.get('firm')),
        'contributed_at': provenance.get('contributed_at'),
    }


def backfill(database_path) -> int:
    """Idempotent stored-package migration; never invent firms, authors or dates.

    First version creation is the recoverable submission date. The current account
    name is private metadata, not retroactive consent to public attribution.
    """
    count = 0
    with db.transaction(database_path) as connection:
        records = connection.execute('SELECT case_id, version, contributor_id, created_at, package_json FROM cases').fetchall()
        for case_id, version, owner, created_at, raw in records:
            package = json.loads(raw)
            manifest = package.setdefault('case', {})
            provenance = manifest.setdefault('provenance', {})
            before = json.dumps(package, sort_keys=True)
            user = connection.execute('SELECT name FROM users WHERE id = ?', (owner,)).fetchone() if owner else None
            provenance.setdefault('contributor_id', owner)
            provenance.setdefault('contributor_name', user[0] if user else None)
            provenance.setdefault('attribution_mode', 'pseudonymous')
            first_created = connection.execute('SELECT MIN(created_at) FROM cases WHERE case_id = ?', (case_id,)).fetchone()[0]
            provenance.setdefault('contributed_at', (first_created.replace(' ', 'T') + 'Z') if first_created else None)
            provenance.setdefault('firm', None)
            provenance['firm_tags'] = firm_tags(provenance.get('firm'))
            provenance.setdefault('metadata_source', 'legacy_record')
            if before != json.dumps(package, sort_keys=True):
                connection.execute('UPDATE cases SET package_json = ? WHERE case_id = ? AND version = ?', (json.dumps(package), case_id, version))
                count += 1
    return count


def stamp_submission(package: dict, *, user, state, public_credit: bool):
    provenance = package['case'].setdefault('provenance', {})
    provenance.update(contributor_id=user.id, contributor_name=user.name,
                      contributed_at=datetime.now(timezone.utc).isoformat(),
                      attribution_mode='public' if public_credit else 'pseudonymous',
                      firm=state.extracted.firm or None, firm_tags=firm_tags(state.extracted.firm),
                      metadata_source='contribution')
    package['contribution'] = {'state': state.as_dict(), 'contributor_id': user.id}
