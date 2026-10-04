"""Private admin review projections and draft editing for contributed cases."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException

from app import db
from app.case_author import ExtractedCase, ExtractionState
from app.case_provenance import firm_tags
from app.case_validator import validate_package
from app.contribution import FIELD_NAMES


def revision(package: dict) -> str:
    return hashlib.sha256(json.dumps(package, sort_keys=True).encode()).hexdigest()


def check_revision(package, expected):
    if expected is not None and revision(package) != expected:
        raise HTTPException(status_code=409, detail='This draft changed. Reload it before saving or approving.')


def record_for(store, case_id, version):
    return next((r for r in store.list_all_versions() if r['case_id'] == case_id and r['version'] == version), None)


def original_state(request, package, case_id):
    snapshot = (package.get('contribution') or {}).get('state')
    if snapshot:
        return snapshot
    # Pre-snapshot submissions retained their original contribution session.
    with db.transaction(request.app.state.database_path) as connection:
        row = connection.execute("SELECT state_json FROM contribution_sessions WHERE case_id = ? AND status = 'submitted' ORDER BY created_at LIMIT 1", (case_id,)).fetchone()
    return json.loads(row[0]) if row else None


def summary(request, record):
    package = request.app.state.cases.get_package(record['case_id'], record['version'])
    case = package.get('case', {})
    provenance = case.get('provenance') or {}
    owner = request.app.state.accounts.get(record['contributor_id']) if record['contributor_id'] else None
    return {**record, 'title':case.get('title', record['case_id']),
            'contributor_name':owner.name if owner else provenance.get('contributor_name'),
            'contributor_email':owner.email if owner else None,
            'contributed_at':provenance.get('contributed_at'), 'firm_tags':firm_tags(provenance.get('firm'))}


def details(request, case_id, version):
    store = request.app.state.cases
    package = store.get_package(case_id, version)
    record = record_for(store, case_id, version)
    if package is None or record is None:
        raise HTTPException(status_code=404, detail='Case version not found')
    original = original_state(request, package, case_id)
    extracted = (original or {}).get('extracted') or {}
    return {**summary(request, record), 'package':package, 'revision':revision(package),
            'validation':package.get('validation'), 'solvability':package.get('solvability'),
            'original_available':original is not None,
            'original_sections':[{'key':key, 'label':FIELD_NAMES[key], 'value':extracted.get(key),
                                  'evidence':[f for f in (original or {}).get('fact_ledger', []) if f.get('field') == key and f.get('status') == 'accepted'],
                                  'discussion':(original or {}).get('closed_fields', {}).get(key)} for key in ExtractedCase.model_fields],
            'transcript':(original or {}).get('messages', [])}


def save_draft(request, case_id, version, proposal, expected_revision, action):
    store = request.app.state.cases
    existing = store.get_package(case_id, version)
    if existing is None:
        raise HTTPException(status_code=404, detail='Case version not found')
    check_revision(existing, expected_revision)
    package = copy.deepcopy(existing)
    for key in ('case', 'facts', 'conversation_policy', 'quant'):
        if key in proposal:
            package[key] = copy.deepcopy(proposal[key])
    package['case']['case_id'] = case_id
    package['case']['source'] = 'community'
    provenance = package['case'].setdefault('provenance', {})
    original_provenance = existing['case'].get('provenance') or {}
    for key in ('contributor_id', 'contributor_name', 'attribution_mode', 'contributed_at', 'metadata_source'):
        provenance[key] = original_provenance.get(key)
    provenance['firm_tags'] = firm_tags(provenance.get('firm'))
    package.pop('solvability', None)
    package['validation'] = validate_package(package).as_dict()
    from app.accounts import current_user
    actor = current_user(request)
    package.setdefault('review_history', []).append({'action':action, 'reviewer_id':actor.id, 'at':datetime.now(timezone.utc).isoformat()})
    record = record_for(store, case_id, version)
    # Editing never changes an already published or pinned world. New drafts
    # always receive a new version, which also prevents concurrent overwrite.
    new_version = store.save_package(case_id, package, status='validated' if package['validation']['passed'] else 'needs_changes', contributor_id=record['contributor_id'])
    return details(request, case_id, new_version)
