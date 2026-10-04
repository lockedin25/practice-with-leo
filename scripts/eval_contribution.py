"""Opt-in live evaluation of the one-question contribution policy.

.venv/bin/python scripts/eval_contribution.py
Uses synthetic recollection, no app accounts or production case submissions.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/'.env')
from app.case_author import ExtractedCase, ExtractionState, LangChainCaseAuthor

STORY = ('The client was a cold-chain logistics operator delivering food and pharmaceuticals. '
'Revenue grew but margins fell. The interviewer wanted us to explain the falling margins and recommend how to restore profitability over the next year. '
'The cause was a mix shift into sparse pharma routes. Fewer deliveries per trip raised cost per kilo but prices were still based on dense food routes, so the growth reduced margins. '
'Local competitors undercut prices on dense routes. Two wrong paths were blaming fuel inflation without checking route density, and exiting pharma rather than repricing sparse routes. '
'The insight was that route density, not revenue, determines unit economics. This was a Bain interview in August 2026.')


def run():
    agent=LangChainCaseAuthor()
    state=ExtractionState(messages=[{'role':'agent','content':agent.opening_prompt()}])
    trace=[]
    def turn(message):
        nonlocal state
        state=agent.respond(state,message)
        assert ExtractionState.from_dict(state.as_dict()).as_dict()==state.as_dict()
        row={'message':message,'active_field':state.active_question_id,'review_progress':state.discussion_progress(),'evidence_score':state.sufficiency_score(),'can_submit':state.can_submit(),'reply':state.messages[-1]['content']}
        trace.append(row); print(json.dumps(row),flush=True)
    turn(STORY)
    assert state.has_core_evidence(), 'Rich overview lost core evidence'
    assert state.extracted.competitors and len(state.extracted.common_traps)>=2
    assert 'bain' in state.extracted.firm.lower()
    assert state.turns == 1
    answers = {
        'client_and_industry':'It served regional hospitals through dedicated delivery contracts.',
        'situation':'The margin decline was the central performance problem.',
        'decision_question':'We had to diagnose the decline and recommend a fix.',
        'core_mechanism':'Sparse routes reduced stops per trip, raising cost per kilo above the legacy price.',
        'competitors':'Local carriers undercut dense-route prices.',
        'time_horizon':'The case covered the next twelve months.',
        'primary_metric':'The primary metric was operating margin.',
        'given_upfront':'The prompt was purely verbal and there were no initial exhibits.',
        'had_to_ask_for':'I had to ask for route density and cost per kilo.',
        'quantities':'I do not recall.',
        'pivotal_insight':'Route density rather than revenue determined unit economics.',
        'common_traps':'Blaming fuel and exiting pharma were the two wrong paths.',
        'interviewer_pushback':'The interviewer pushed back when I focused only on revenue.',
        'what_it_tested':'It tested unit economics and mix-shift analysis.',
        'takeaway_lesson':'I would test contribution per route before celebrating growth.',
        'firm':'Bain.',
        'interview_round':'I do not recall.',
        'geography':'I do not recall.',
        'interview_month':'August 2026.',
    }
    visited=[]
    while state.active_question_id:
        active=state.active_question_id
        assert active not in visited, f'{active} was asked more than once'
        visited.append(active)
        turn(answers[active])
        assert state.active_question_id != active, f'{active} did not advance after one answer'
        assert state.field_attempts[active] == 1
        if state.active_question_id:
            reply=state.messages[-1]['content'].lower()
            assert 'nothing more' not in reply and 'do you not recall' not in reply
        assert state.turns <= 20, 'Conversation exceeded the hard stop'
    assert state.can_submit() and state.discussion_progress()==1
    target=Path('docs/evals/contribution-live-replay-v4.json')
    target.write_text(json.dumps(trace,indent=2)+'\n')
    print(f'PASS: {len(visited)} missing fields asked once; finished in {state.turns} contributor replies.',flush=True)


if __name__=='__main__': run()
