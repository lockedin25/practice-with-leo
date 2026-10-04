"""Section review, AI drafts, approval, attribution and metadata migration."""
import copy
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.case_author import ExtractedCase
from app.case_provenance import backfill, firm_tags, stamp_submission
from app.case_synthesis import build_package
from app.case_validator import validate_package
from app.contribution_review import revision
from conftest import sign_in
from test_contribution import _complete_extraction, _synthesised
from test_contribution_loop import reviewed_state


@pytest.fixture(autouse=True)
def restore_published_library():
    """Do not leak synthetic publications into later library lifecycle tests."""
    before = {(row['case_id'], row['version']) for row in main.CASES.list_all_versions()}
    yield
    for row in main.CASES.list_all_versions():
        if (row['case_id'], row['version']) not in before and row['status'] == 'published':
            main.CASES.set_status(row['case_id'], row['version'], 'unpublished')
    main.reload_contributed_cases()


def seed(client, *, status='validated', with_original=True, public=True):
    owner = sign_in(TestClient(main.app), f'{uuid4()}@example.com', name='Case Contributor')
    case = _synthesised()
    case.title = f'Review Case {uuid4().hex[:8]}'
    package = build_package(case,_complete_extraction(),contributor_id=owner.id)
    state = reviewed_state()
    state.extracted.firm = 'Bain & Company'
    state.messages = [{'role':'contributor','content':'Private recollection at Bain; contact example@example.com'}]
    stamp_submission(package,user=owner,state=state,public_credit=public)
    if not with_original:
        package.pop('contribution')
    package['validation'] = validate_package(package).as_dict()
    case_id = package['case']['case_id']
    version = main.CASES.save_package(case_id,package,status=status,contributor_id=owner.id)
    return case_id, version, owner, package


def test_review_page_is_linked_and_admin_only(admin_client,candidate_client):
    admin,_ = admin_client
    candidate,_ = candidate_client
    assert '/admin/contributions' in admin.get('/admin').text
    assert admin.get('/admin/contributions').status_code == 200
    assert candidate.get('/admin/contributions',follow_redirects=False).status_code == 303
    assert candidate.get('/api/admin/contributions').status_code == 403
    assert TestClient(main.app).get('/api/admin/contributions').status_code == 401


def test_submission_records_credit_firm_time_and_original_snapshot(candidate_client, monkeypatch):
    client, user = candidate_client

    class Synthesiser:
        def synthesise(self, extracted, *, contributor_id):
            case = _synthesised()
            case.title = f'Submission {uuid4().hex[:8]}'
            return build_package(case, extracted, contributor_id=contributor_id)

    monkeypatch.setattr(main, 'CASE_SYNTHESISER', Synthesiser())
    state = reviewed_state()
    state.extracted.firm = 'Boston Consulting Group'
    session = f'credit-{uuid4()}'
    main.CONTRIBUTIONS.create(session, user.id, state.as_dict())
    response = client.post(f'/api/contributions/{session}/submit', json={'public_credit':True})
    assert response.status_code == 200, response.text
    result = response.json()
    package = main.CASES.get_package(result['case_id'], result['version'])
    provenance = package['case']['provenance']
    assert provenance['contributor_id'] == user.id
    assert provenance['contributor_name'] == user.name
    assert provenance['attribution_mode'] == 'public'
    assert provenance['firm_tags'] == ['BCG']
    assert provenance['contributed_at'].endswith('+00:00')
    assert package['contribution']['state']['closed_fields'] == state.closed_fields
    assert result['case_id'] not in {item['id'] for item in client.get('/api/cases').json()['cases']}


def test_review_shows_original_sections_ai_draft_and_failed_validation_queue(admin_client):
    admin,_ = admin_client
    case_id,version,owner,package = seed(admin,status='needs_changes')
    queue = admin.get('/api/admin/contributions').json()['queue']
    assert any(r['case_id'] == case_id and r['contributor_name'] == owner.name for r in queue)
    view = admin.get(f'/api/admin/contributions/{case_id}/{version}').json()
    assert len(view['original_sections']) == len(ExtractedCase.model_fields)
    assert view['original_available']
    assert view['package']['case']['case_essence']['core_mechanism']
    assert view['firm_tags'] == ['Bain']
    assert view['contributed_at']
    assert view['transcript'][0]['role'] == 'contributor'


def test_approve_adds_to_library_with_credit_firm_and_timestamp(admin_client):
    admin,_ = admin_client
    case_id,version,owner,package = seed(admin)
    assert case_id not in {x['id'] for x in admin.get('/api/cases').json()['cases']}
    response = admin.post(f'/api/admin/contributions/{case_id}/{version}/decide',json={'decision':'publish','expected_revision':revision(package)})
    assert response.status_code == 200, response.text
    item = next(x for x in admin.get('/api/cases').json()['cases'] if x['id'] == case_id)
    assert item['contributor_name'] == owner.name
    assert item['firm_tags'] == ['Bain']
    assert item['contributed_at'] == package['case']['provenance']['contributed_at']
    assert 'contributor_id' not in item and 'contribution' not in item and 'email' not in item
    assert admin.post('/api/attempts',json={'case_id':case_id}).status_code == 200
    assert admin.post(f'/api/admin/contributions/{case_id}/{version}/decide',json={'decision':'withdraw'}).status_code == 200
    assert case_id not in {x['id'] for x in admin.get('/api/cases').json()['cases']}


def test_pseudonymous_contributor_stays_private_on_public_library(admin_client):
    admin,_ = admin_client
    case_id,version,owner,package = seed(admin,public=False)
    assert admin.post(f'/api/admin/contributions/{case_id}/{version}/decide',json={'decision':'publish'}).status_code == 200
    item = next(x for x in admin.get('/api/cases').json()['cases'] if x['id'] == case_id)
    assert item['contributor_name'] is None
    assert item['contributor_label'] == 'Community contributor'
    assert admin.get(f'/api/admin/contributions/{case_id}/{version}').json()['contributor_name'] == owner.name


def test_publish_revalidates_current_content_instead_of_trusting_old_pass(admin_client):
    admin,_ = admin_client
    case_id,version,owner,package = seed(admin)
    package['case']['case_essence']['core_mechanism'] = ''
    package['validation'] = {'passed':True,'findings':[]}
    main.CASES.save_package(case_id,package,status='validated',contributor_id=owner.id,version=version)
    assert admin.post(f'/api/admin/contributions/{case_id}/{version}/decide',json={'decision':'publish'}).status_code == 409


def test_edit_creates_private_new_version_and_preserves_original(admin_client):
    admin,_ = admin_client
    case_id,version,owner,package = seed(admin)
    assert admin.post(f'/api/admin/contributions/{case_id}/{version}/decide',json={'decision':'publish'}).status_code == 200
    view = admin.get(f'/api/admin/contributions/{case_id}/{version}').json()
    draft = copy.deepcopy(view['package'])
    draft['case']['title'] = 'Editor Improved Case'
    draft['case']['provenance']['contributed_at'] = 'made up'
    response = admin.post(f'/api/admin/contributions/{case_id}/{version}/draft',json={**{key:draft[key] for key in ('case','facts','conversation_policy')},'expected_revision':view['revision']})
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated['version'] > version
    assert updated['package']['contribution'] == package['contribution']
    assert updated['contributed_at'] == package['case']['provenance']['contributed_at']
    assert updated['contributor_id'] == owner.id
    assert main.CATALOGUE.get(case_id).title == package['case']['title']
    assert admin.post(f"/api/admin/contributions/{case_id}/{updated['version']}/decide",json={'decision':'publish','expected_revision':updated['revision']}).status_code == 200
    assert main.CATALOGUE.get(case_id).title == 'Editor Improved Case'
    assert main.CATALOGUE.get(case_id,version=version).title == package['case']['title']


def test_ai_regeneration_produces_reviewable_new_version_and_retains_recall(admin_client,monkeypatch):
    admin,_ = admin_client
    case_id,version,owner,package = seed(admin)
    class Synthesiser:
        def synthesise(self,extracted,*,contributor_id):
            assert extracted.firm == 'Bain & Company'
            assert contributor_id == owner.id
            proposal = copy.deepcopy(package)
            proposal['case']['title'] = 'AI Augmented Case'
            return proposal
    monkeypatch.setattr(main,'CASE_SYNTHESISER',Synthesiser())
    response = admin.post(f'/api/admin/contributions/{case_id}/{version}/augment',json={'expected_revision':revision(package)})
    assert response.status_code == 200
    view=response.json()
    assert view['version'] > version
    assert view['title'] == 'AI Augmented Case'
    assert view['package']['contribution'] == package['contribution']
    assert view['status'] != 'published'
    assert case_id not in {x['id'] for x in admin.get('/api/cases').json()['cases']}


def test_stale_review_cannot_publish_or_regenerate(admin_client):
    admin,_ = admin_client
    case_id,version,owner,package = seed(admin)
    assert admin.post(f'/api/admin/contributions/{case_id}/{version}/decide',json={'decision':'publish','expected_revision':'stale'}).status_code == 409
    assert admin.post(f'/api/admin/contributions/{case_id}/{version}/augment',json={'expected_revision':'stale'}).status_code == 409


def test_legacy_package_uses_saved_conversation_and_backfills_metadata(admin_client):
    admin,_ = admin_client
    case_id,version,owner,package = seed(admin,with_original=False,public=False)
    package['case'].pop('provenance')
    main.CASES.save_package(case_id,package,status='validated',contributor_id=owner.id,version=version)
    state = reviewed_state()
    main.CONTRIBUTIONS.create(f'legacy-{case_id}',owner.id,state.as_dict())
    main.CONTRIBUTIONS.finish(f'legacy-{case_id}',status='submitted',case_id=case_id)
    assert backfill(main.DATABASE_PATH) >= 1
    assert backfill(main.DATABASE_PATH) == 0
    view = admin.get(f'/api/admin/contributions/{case_id}/{version}').json()
    assert view['original_available']
    assert view['contributor_name'] == owner.name
    assert view['contributed_at']
    assert view['firm_tags'] == []
    assert view['package']['case']['provenance']['attribution_mode'] == 'pseudonymous'


def test_private_raw_evidence_does_not_contaminate_public_safety_checks(admin_client):
    admin,_=admin_client
    _,_,_,package=seed(admin)
    assert validate_package(package).passed
    package['facts']['facts'][0]['content'] += ' Email example@example.com'
    assert not validate_package(package).passed


def test_all_authored_cases_have_explicit_metadata_and_unknowns_are_honest():
    import yaml
    root=Path(__file__).resolve().parents[1]
    paths=list((root/'reservoir').glob('*/case.yaml'))+list((root/'corpus/exemplars').glob('*/*/case.yaml'))
    assert len(paths)==69
    for path in paths:
        provenance=yaml.safe_load(path.read_text())['provenance']
        assert {'contributed_at','contributor_name','firm_tags'} <= provenance.keys()
        if provenance['metadata_source']=='not_recorded':
            assert provenance['contributed_at'] is None
            assert provenance['firm_tags']==[]
    assert firm_tags('Bain & Company, Boston Consulting Group, McKinsey') == ['Bain','BCG','McKinsey']
