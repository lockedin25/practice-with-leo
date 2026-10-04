"""Replay the reported stall through the real engine, API and persistence.

Only provider I/O is scripted. Field validation, merge, selection, score and
reloads use production code. Live-model evaluation is separately opt-in.
"""
import copy
import sqlite3

import pytest

import app.main as main
from app.case_author import ExtractedCase, ExtractionState, ExtractionUnavailable, LangChainCaseAuthor
from app.contribution import (
    AnswerAssessment, CasePatch, FramedQuestion, OPENING, REMINDER, REMINDER_EVERY, reconcile,
)


class ScriptedAssessor:
    def __init__(self, turns):
        self.turns = iter(turns)
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        result = next(self.turns)
        if isinstance(result, Exception):
            raise result
        return AnswerAssessment.model_validate(result if "updates" in result else {"updates": result})


class UnavailableFramer:
    def invoke(self, payload):
        raise RuntimeError("simulated framing outage")


def author(*turns):
    agent = LangChainCaseAuthor.__new__(LangChainCaseAuthor)
    agent._assessor = ScriptedAssessor(turns)
    agent._framer = UnavailableFramer()
    return agent


def fact(value, quote=None, status="complete", **kw):
    values = value if isinstance(value, list) else [value]
    return dict(values=values, evidence_quote=quote or " ".join(values), status=status, **kw)


def skeleton():
    return dict(client_and_industry="A cold-chain logistics operator", situation="Revenue grew but margins fell", decision_question="Explain falling margins and recommend a fix", core_mechanism="Sparse pharma routes increased delivery cost per kilo beyond the legacy price")


def ready_state():
    return reconcile(ExtractionState(extracted=ExtractedCase(**skeleton()), overview_complete=True))



def reviewed_state():
    state = ready_state()
    state.closed_fields = {key:{'quote':'Nothing more','turn':1} for key in ExtractedCase.model_fields}
    return reconcile(state)


def test_typed_schema_exposes_all_case_fields():
    schema = CasePatch.model_json_schema()
    assert set(schema['properties']) == set(ExtractedCase.model_fields)
    assert schema['additionalProperties'] is False


def test_rich_single_message_closes_complete_fields_and_moves_on():
    facts = skeleton()
    agent = author({key:fact(value) for key,value in facts.items()})
    state = agent.respond(ExtractionState(), '. '.join(facts.values()))
    assert state.sufficiency_score() == .70
    assert not state.can_submit()
    assert state.active_question_id == 'competitors'
    assert set(facts) <= set(state.closed_fields)
    assert state.discussion_progress() == round(4 / len(ExtractedCase.model_fields), 4)
    assert 'nothing more' not in state.messages[-1]['content'].lower()


def test_each_uncaptured_field_is_asked_once_and_state_survives_reload(candidate_client, monkeypatch):
    client, user = candidate_client
    fields = skeleton()
    monkeypatch.setattr(main,'CASE_AUTHOR',author({key:fact(value) for key,value in fields.items()}, *({} for _ in ExtractedCase.model_fields)))
    view = client.post('/api/contributions').json()
    session = view['id']
    turn = lambda content: client.post(f'/api/contributions/{session}/turn',json={'content':content})
    view = turn('. '.join(fields.values())).json()
    assert not view['can_submit']
    assert view['active_question']['id'] == 'competitors'
    visited = []
    while view['active_question'] is not None:
        visited.append(view['active_question']['id'])
        response = turn('I do not recall')
        assert response.status_code == 200
        view = response.json()
        assert client.get(f'/api/contributions/{session}').json() == view
    assert len(visited) == len(set(visited)) == len(ExtractedCase.model_fields) - len(fields)
    assert view['turns'] <= 20
    assert view['can_submit'] and view['active_question'] is None
    assert view['mode'] == 'submission_ready'
    assert client.post(f'/api/contributions/{session}/improve').status_code == 404


def test_complete_answer_advances_immediately_and_later_tangent_accumulates():
    state = ready_state()
    state.active_question_id = 'competitors'
    agent = author({'competitors':fact('Local carriers cut prices')}, {'competitors':fact('National rivals offered next-day delivery')}, {})
    state = agent.respond(state,'Local carriers cut prices')
    assert 'competitors' in state.closed_fields
    assert state.active_question_id != 'competitors'
    state = agent.respond(state,'National rivals offered next-day delivery')
    assert state.extracted.competitors == ['Local carriers cut prices','National rivals offered next-day delivery']
    assert state.active_question_id != 'competitors'


def test_fact_in_another_field_is_saved_without_closing_active_field():
    state = ready_state()
    agent = author({'common_traps':fact(['Blaming fuel','Exiting pharma'])})
    state = agent.respond(state,'Blaming fuel Exiting pharma')
    assert len(state.extracted.common_traps) == 2
    assert {'client_and_industry','common_traps'} <= set(state.closed_fields)
    assert state.active_question_id == 'situation'


def test_declining_a_field_does_not_erase_previously_captured_values():
    state = ready_state()
    original = state.extracted.client_and_industry
    state = author({'client_and_industry':fact([], 'I cannot recall',status='unavailable')}).respond(state,'I cannot recall')
    assert state.extracted.client_and_industry == original
    assert 'client_and_industry' in state.closed_fields


def test_quoted_explicit_decline_can_accompany_final_detail():
    state = ready_state()
    agent = author({'updates':{'client_and_industry':fact('It served hospitals')},'no_more_detail':True,'no_more_quote':'That is all I remember'})
    state = agent.respond(state,'It served hospitals. That is all I remember')
    assert 'It served hospitals' in state.extracted.client_and_industry
    assert 'client_and_industry' in state.closed_fields


def test_any_answer_to_an_active_question_gets_only_one_attempt():
    state = ready_state()
    state = author({'updates':{},'no_more_detail':True,'no_more_quote':'A retailer'}).respond(state,'A retailer')
    assert 'client_and_industry' in state.closed_fields
    assert state.active_question_id == 'situation'


def test_unquoted_evidence_and_assistant_history_are_rejected():
    state = ExtractionState(messages=[{'role':'agent','content':'Fuel costs doubled'}])
    state = author({'core_mechanism':fact('Fuel costs doubled')}).respond(state,'Answer the question')
    assert not state.extracted.core_mechanism
    assert state.sufficiency_score() == 0


def test_failure_does_not_mutate_draft_or_turns():
    state = ExtractionState(draft_text='Long unsent answer')
    before = copy.deepcopy(state.as_dict())
    with pytest.raises(ExtractionUnavailable):
        author(RuntimeError('provider down')).respond(state,'An answer')
    assert state.as_dict() == before


def test_partial_core_still_blocks_submission_after_all_discussions():
    state = reviewed_state()
    state.extracted.core_mechanism = 'Costs'
    state.field_statuses['core_mechanism'] = {'status':'partial','missing_detail':'which cost and why'}
    reconcile(state)
    assert state.mode == 'insufficient_evidence'
    assert not state.can_submit()
    assert state.active_question_id == ''


def test_correction_updates_a_closed_section_without_asking_it_again():
    state = reviewed_state()
    agent = author({'core_mechanism':fact('Actually the issue was lower prices on pharma contracts',replace=True)})
    state = agent.respond(state,'Actually the issue was lower prices on pharma contracts')
    assert 'core_mechanism' in state.closed_fields
    assert state.active_question_id == ''
    assert state.can_submit()


def test_old_ready_sessions_migrate_complete_answers_without_duplicate_evidence():
    payload = ready_state().as_dict()
    payload['schema_version'] = 2
    payload['active_question_id'] = ''
    payload['ready_to_submit'] = True
    payload['messages'] = [{'role':'agent','content':'Submit now'}]
    payload['fact_ledger'] = [{'field':'situation','values':['Margins fell'],'status':'accepted','source':'contributor'}]
    state = ExtractionState.from_dict(payload)
    assert state.active_question_id == 'competitors'
    assert not state.can_submit()
    assert len(state.fact_ledger) == 1
    assert state.messages[0]['content'] == 'Submit now'
    assert 'competitors' in state.messages[-1]['content'].lower()
    assert ExtractionState.from_dict(state.as_dict()).as_dict() == state.as_dict()


def test_framer_success_uses_selected_field_and_existing_answer():
    agent = author({'client_and_industry':fact('A retailer')})
    class Framer:
        def invoke(self,payload):
            assert payload['target_field'] == 'situation'
            assert 'A retailer' in payload['captured']
            return FramedQuestion(question_id='situation',target_field='situation',question='What problem was this retailer facing?')
    agent._framer = Framer()
    state = agent.respond(ExtractionState(),'A retailer')
    assert state.messages[-1]['content'] == 'What problem was this retailer facing?'


def test_opening_explains_skip_once_but_followups_do_not_repeat_it():
    opening = LangChainCaseAuthor.opening_prompt(None)
    assert 'do not recall' in opening.lower() and 'move on' in opening.lower()
    state = author({}).respond(ExtractionState(), 'A case I barely remember')
    followup = state.messages[-1]['content'].lower()
    assert 'nothing more' not in followup
    assert 'cannot recall' not in followup
    assert 'prefer not' not in followup

    class RepetitiveFramer:
        def invoke(self, payload):
            return FramedQuestion(
                question_id=payload['target_field'], target_field=payload['target_field'],
                question='What was the situation, or do you not recall?',
            )

    agent = author({})
    agent._framer = RepetitiveFramer()
    state = agent.respond(ExtractionState(), 'A case I barely remember')
    assert 'do you not recall' not in state.messages[-1]['content'].lower()


def test_the_reply_budget_is_reported_counting_down_and_then_as_closed(candidate_client, monkeypatch):
    """The contributor page renders completion_rule verbatim.

    A cap stated once as a number the contributor cannot see themselves against
    is not a budget they can spend, so the view reports what is left.
    """
    client, _ = candidate_client
    monkeypatch.setattr(main, 'CASE_AUTHOR', author(*({} for _ in range(25))))
    view = client.post('/api/contributions').json()
    session = view['id']
    assert view['turns_remaining'] == view['turn_limit'] == 20
    assert '20 of 20 replies left' in view['completion_rule']

    view = client.post(f'/api/contributions/{session}/turn', json={'content':'A case I remember'}).json()
    assert view['turns_remaining'] == 19
    assert '19 of 20 replies left' in view['completion_rule']

    while view['turns_remaining']:
        view = client.post(f'/api/contributions/{session}/turn', json={'content':'I do not recall'}).json()
    assert view['turns'] == 20
    assert 'conversation is closed' in view['completion_rule']
    assert view['active_question'] is None


def test_the_opt_out_is_re_offered_periodically_and_not_on_every_question():
    """Every question carrying the reminder is what made Leo read as pressing.

    Saying it once and never again loses the contributor who has forgotten it
    by the tenth question, so it returns on a fixed cadence instead.
    """
    facts = skeleton()
    agent = author({key: fact(value) for key, value in facts.items()}, *({} for _ in range(30)))
    state = agent.respond(ExtractionState(), '. '.join(facts.values()))
    carried = []
    while state.active_question_id:
        state = agent.respond(state, 'I do not recall')
        if REMINDER in state.messages[-1]['content']:
            carried.append(state.turns)

    assert carried == [REMINDER_EVERY, 2 * REMINDER_EVERY]
    agent_messages = [message for message in state.messages if message['role'] == 'agent']
    assert len(carried) < len(agent_messages) / 4
    # The reminder is a statement, so it cannot turn a question into two.
    assert all(message['content'].count('?') <= 1 for message in agent_messages)


def test_a_field_advances_after_first_unavailable_answer():
    state = ready_state()
    state.active_question_id = 'given_upfront'
    # Progress does not depend on the model recognising this exact contraction.
    state = author({}).respond(state, 'I don’t recall')
    assert state.active_question_id != 'given_upfront'
    assert state.field_attempts['given_upfront'] == 1
    assert state.field_statuses['given_upfront']['status'] == 'unavailable'


def test_twentieth_contributor_turn_is_a_hard_stop():
    state = ExtractionState(overview_complete=True, turns=19, active_question_id='client_and_industry')
    state = author({}).respond(state, 'I am not sure')
    assert state.turns == 20
    assert state.active_question_id == ''
    assert state.mode == 'insufficient_evidence'
    assert set(ExtractedCase.model_fields) <= set(state.closed_fields)


def test_turn_response_does_not_reopen_database_after_successful_save(candidate_client, monkeypatch):
    client, _ = candidate_client
    monkeypatch.setattr(main, 'CASE_AUTHOR', author({}))
    created = client.post('/api/contributions').json()
    real_get = main.CONTRIBUTIONS.get
    calls = 0

    def fail_on_second_read(session_id):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise sqlite3.OperationalError('unable to open database file')
        return real_get(session_id)

    monkeypatch.setattr(main.CONTRIBUTIONS, 'get', fail_on_second_read)
    response = client.post(f"/api/contributions/{created['id']}/turn", json={'content':'A case I remember'})
    assert response.status_code == 200, response.text
    assert calls == 1
    assert response.json()['turns'] == 1


def test_contribution_save_database_failure_is_a_readable_503(candidate_client, monkeypatch):
    client, _ = candidate_client
    monkeypatch.setattr(main, 'CASE_AUTHOR', author({}))
    created = client.post('/api/contributions').json()

    def unavailable(*_args, **_kwargs):
        raise sqlite3.OperationalError('unable to open database file')

    monkeypatch.setattr(main.CONTRIBUTIONS, 'save_state', unavailable)
    response = client.post(f"/api/contributions/{created['id']}/turn", json={'content':'A case I remember'})
    assert response.status_code == 503
    assert 'could not be saved' in response.json()['detail']


def test_conflicts_are_excluded_from_synthesis_until_resolved():
    state = ready_state()
    state.extracted.competitors = ['Prices fell']
    agent = author({'competitors':fact('Prices rose',status='conflict')},{'competitors':fact('Actually prices fell',replace=True)})
    state = agent.respond(state,'Prices rose')
    assert state.synthesis_draft().competitors == []
    state = agent.respond(state,'Actually prices fell')
    assert state.synthesis_draft().competitors == ['Actually prices fell']
