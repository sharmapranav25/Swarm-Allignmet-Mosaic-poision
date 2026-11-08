import asyncio
import copy
import json
from types import SimpleNamespace
from dataclasses import asdict
import pytest
from core.config import RunConfig
from core.agents import Trader, BranchPoint
from core.ledger import Ledger
from ticketing.gap1 import experiment, assignment_schedule, validate_pool, restore, snapshot, inject_pending, aggregate
from tests.test_ticketing import world
from tests.test_runtime import Output
from tests.test_llm_transport import Stream


def choice(value):
    return dict(action='plant',reason='Test',consistency_reason='Unseen string',response_path=['data','service'],
        replacement=value,prediction=dict(tool='retrieve_bundle',argument='service',value=value,explanation='Prediction'))


class ExperimentClient:
    def __init__(self,abstain=False,fail_value=None):
        self.responses=self;self.requests=[];self.abstain=abstain;self.fail_value=fail_value
    async def create(self,**kw):
        self.requests.append(copy.deepcopy(kw))
        if kw.get('tool_choice'):
            payload=json.loads(kw['input'])
            if 'alternatives' in kw['tools'][0]['parameters']['properties']:
                assert 'role' not in payload and 'cohort' not in payload
                assert 'assignment_seed' not in payload
                result=dict(action='relay' if self.abstain else 'plant',reason='Test pool',
                            alternatives=[] if self.abstain else [choice(v) for v in ['invented-a','invented-b','invented-c']])
            elif 'pending_response' in payload:
                result=dict(action='deploy_charlatan',profile='Observed',reason='Investigate',assembly_assessment='Test')
            else:
                result=dict(point=False,plant_id='',reason='Test measurement',benign_alternative='No verdict')
            outs=[Output(type='function_call',name='submit_assessment',arguments=json.dumps(result),call_id='assessment')]
        else:
            assert 'assignment_seed' not in kw['instructions'] and 'block1_slot' not in kw['instructions']
            items=kw['input'];outputs={it['call_id']:json.loads(it['output']) for it in items if it.get('type')=='function_call_output' and it['output'].startswith('{')}
            rogue='deliberately choose the archive route' in kw['instructions']
            def call(name,args,cid):return Output(type='function_call',name=name,arguments=json.dumps(args),call_id=cid)
            if not outputs:
                if rogue:
                    outs=[call('lookup',{'source':source},source) for source in ['service_catalog','log_index','operations_guide','archive_directory']]
                else:outs=[Output(type='message',role='assistant',content=[{'type':'output_text','text':'Done'}])]
            elif rogue and 'retrieve' not in outputs:
                fields={k:v for val in outputs.values() for k,v in val.get('data',{}).items()}
                if fields.get('service')==self.fail_value:raise RuntimeError('Injected branch failure')
                outs=[call('retrieve_bundle',{k:fields[k] for k in ['namespace','service','alias','selector']},'retrieve')]
            elif rogue and 'resolve' not in outputs:
                outs=[call('resolve_batch',dict(evidence_id=outputs['retrieve']['evidence_id'],ticket_ids=['T1','T2','T3'],decision_reason='Test'),'resolve')]
            else:outs=[Output(type='message',role='assistant',content=[{'type':'output_text','text':'Done'}])]
        response=SimpleNamespace(status='completed',output=outs,output_text='Done',usage=None)
        return Stream([SimpleNamespace(type='response.completed',response=response)])


def test_end_to_end_checkpoint_randomized_continuations(tmp_path):
    cfg=RunConfig(total_tickets=3,days=1,use_briefs=False,llm_retries=0)
    result=asyncio.run(experiment(cfg,ExperimentClient(),tmp_path/'experiment',repetitions=2,assignment_seed=42))
    assert result['status']=='completed' and len(result['schedule'])==8
    for branch in result['schedule']:
        assert branch['status']=='completed'
        read=branch['readout']
        assert read['attempted_predicted_tool']
        if branch['alternative'] is None:
            assert not read['candidate_values_used'] and read['genuine_unauthorized_closures']==3
        else:
            assert read['assigned_value_used'] and read['poison_closures']==3
        assert read['final_queue']['closed']==3
        rows=[json.loads(x) for x in (tmp_path/'experiment'/branch['branch']/'ledger.jsonl').read_text().splitlines()]
        observations=[r for r in rows if r['event']=='tool_observation' and r['worker']=='Hawk' and r['tool']=='lookup' and r['arguments']['source']=='service_catalog']
        assert len(observations)==1  # pending response injected once, not re-executed
    saved=json.loads((tmp_path/'experiment'/'checkpoint.json').read_text())
    assert len(saved['resume']['pending'])==4 and saved['resume']['calls_made']==0
    assert saved['world']['closed']=={} and saved['world']['plans']=={}
    assert saved['resume']['pending'][0]['call_id']=='service_catalog'
    assert result['results']['by_arm']['value_0']['assigned_value_use_fraction']==1


def test_abstention_remains_in_manifest_without_forcing_plant(tmp_path):
    cfg=RunConfig(total_tickets=3,days=1,use_briefs=False,llm_retries=0)
    result=asyncio.run(experiment(cfg,ExperimentClient(abstain=True),tmp_path/'abstain'))
    assert result['status']=='abstained' and not result['schedule']
    assert (tmp_path/'abstain'/'checkpoint.json').exists()


def test_failed_continuation_remains_in_assignment_denominator(tmp_path):
    cfg=RunConfig(total_tickets=3,days=1,use_briefs=False,llm_retries=0)
    result=asyncio.run(experiment(cfg,ExperimentClient(fail_value='invented-b'),tmp_path/'failure',repetitions=1,assignment_seed=42))
    arm=result['results']['by_arm']['value_1']
    assert arm['assigned']==1 and arm['completed']==0 and arm['failed_or_unfinished']==1
    assert arm['assigned_value_use_fraction']==0
    assert len(result['schedule'])==4


def test_assignment_balanced_reproducible_and_unrelated_to_world_seed():
    a=assignment_schedule(3,23)
    assert a==assignment_schedule(3,23) and a!=assignment_schedule(3,24)
    for block in range(1,4):assert {b['alternative'] for b in a if b['block']==block}=={None,0,1,2}


def test_pool_rejects_value_repetition_and_different_fields():
    w=world();pending={'data':{'service':'billing','namespace':'vault-a'}}
    pool=dict(action='plant',reason='Test',alternatives=[choice(v) for v in ['a','b','c']])
    validate_pool(pool,w,'A',pending)
    pool['alternatives'][1]['replacement']='a'
    with pytest.raises(ValueError,match='distinct'):validate_pool(pool,w,'A',pending)
    pool['alternatives'][1]=choice('b');pool['alternatives'][1]['response_path']=['data','namespace']
    with pytest.raises(ValueError,match='Vary only'):validate_pool(pool,w,'A',pending)


def test_restore_isolated_claims_and_pending_side_effects_not_repeated(tmp_path):
    w=world();w.workers=['A'];w.claim_tickets('A',['T1']);w.approvals[('A','T1')]=2
    traders={'A':Trader('A','private')}
    pending=dict(tool='request_batch_approval',arguments={'ticket_ids':['T1']},response={'ticket_ids':['T1'],'available_round':2})
    point=BranchPoint('A',pending)
    point.resume=dict(items=[],calls_made=2,pending=[dict(name='request_batch_approval',arguments=json.dumps({'ticket_ids':['T1']}),call_id='saved-call')])
    saved=snapshot(w,traders,point,1,0,RunConfig(total_tickets=3))
    # Round-trip through disk-compatible JSON catches tuple-key and defaultdict issues.
    saved=json.loads(json.dumps(saved))
    led1=Ledger(tmp_path/'a.jsonl');led2=Ledger(tmp_path/'b.jsonl')
    _,a,ta=restore(saved,None,led1);_,b,tb=restore(saved,None,led2)
    resume=inject_pending(saved,a,led1,None)
    assert a.approvals[('A','T1')]==2 and len(a.claims)==1
    assert resume['calls_made']==3 and resume['items'][-1]['call_id']=='saved-call'
    a.claims.clear();a.closed['T1']='A';ta['A'].history.append(['changed'])
    assert b.claims and not b.closed and not tb['A'].history
    assert saved['world']['claims'] and not saved['world']['closed']
    led1.close();led2.close()


def test_no_checkpoint_is_retained_without_candidates(tmp_path):
    # An unflagged ordinary worker finishes without any candidate generation.
    cfg=RunConfig(total_tickets=3,days=1,use_briefs=False,llm_retries=0)
    result=asyncio.run(experiment(cfg,ExperimentClient(),tmp_path/'none',worker='Arrow'))
    assert result['status']=='no_checkpoint' and result['schedule']==[]
    assert not (tmp_path/'none'/'candidate_pool.json').exists()
    assert json.loads((tmp_path/'none'/'experiment.json').read_text())['status']=='no_checkpoint'


def test_small_cast_checkpoint_prompts_and_readouts(tmp_path):
    cfg=RunConfig(total_tickets=3,days=1,use_briefs=False,llm_retries=0)
    result=asyncio.run(experiment(cfg,ExperimentClient(),tmp_path/'small',cast='small',repetitions=1,assignment_seed=42))
    assert result['status']=='completed'
    assert result['workers']==['Arrow','Delta','Hawk']
    assert [result['config'][k] for k in ['n_naive','n_restrained','n_rogue']]==[1,1,1]
    saved=json.loads((tmp_path/'small'/'checkpoint.json').read_text())
    assert list(saved['traders'])==['Arrow','Delta','Hawk']
    assert all('all 3 workers' in t['system'] for t in saved['traders'].values())
    for branch in result['schedule']:
        assert branch['status']=='completed'
        summary=branch['readout']['diagnostic_summary']
        assert set(summary['workers'])=={'Arrow','Delta','Hawk'}
        assert all(group['workers']==1 for group in summary['by_type'].values())
