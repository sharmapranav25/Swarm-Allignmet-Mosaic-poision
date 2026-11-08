import asyncio
import json
from types import SimpleNamespace
from core.agents import Trader, take_turn
from core.config import RunConfig
from core.ledger import Ledger
from tests.test_llm_transport import Stream
from ticketing.run import run, summarize, tools_for, ROLES
from ticketing.world import TOOLS


class Output(SimpleNamespace):
    def model_dump(self,**kwargs):return vars(self).copy()


class ScriptedClient:
    def __init__(self,**kwargs):self.responses=self
    async def close(self):pass
    async def create(self,**kwargs):
        assert kwargs['stream']
        previous=kwargs['input']
        # Every worker requests scoped approval; repeated round completes without more tools.
        if any(x.get('type')=='function_call_output' for x in previous):
            output=[Output(type='message',role='assistant',content=[{'type':'output_text','text':'Done'}])]
        else:
            output=[Output(type='function_call',name='request_batch_approval',
                arguments=json.dumps({'ticket_ids':['T1']}),call_id='approval')]
        response=SimpleNamespace(status='completed',output=output,output_text='Done',usage=None)
        return Stream([SimpleNamespace(type='response.completed',response=response)])


def test_standalone_runner_writes_complete_ledger_and_summary(tmp_path,monkeypatch):
    monkeypatch.setattr('ticketing.run.AsyncAdaption',ScriptedClient)
    cfg=RunConfig(out_dir=str(tmp_path),run_id='offline',days=1,use_briefs=False)
    asyncio.run(run(cfg))
    directory=tmp_path/'offline'
    rows=[json.loads(s) for s in (directory/'ledger.jsonl').read_text().splitlines()]
    assert rows[-1]['event']=='run_end'
    assert rows[-1]['reason']=='rounds'
    assert len([r for r in rows if r['event']=='enroll'])==10
    assert json.loads((directory/'summary.json').read_text())==summarize(directory/'ledger.jsonl')
    assert rows[0]['config']['use_briefs'] is False


def test_naive_cannot_call_retrieval_tool():
    assert 'retrieve_bundle' not in {t['name'] for t in tools_for('naive')}
    assert 'retrieve_bundle' in {t['name'] for t in tools_for('restrained')}
    assert tools_for('restrained')==tools_for('rogue')


def test_tool_schema_validation_blocks_bad_arguments(tmp_path):
    class BadClient(ScriptedClient):
        async def create(self,**kwargs):
            out=Output(type='function_call',name='request_batch_approval',arguments='{"day":0}',call_id='bad')
            response=SimpleNamespace(status='completed',output=[out],output_text='',usage=None)
            return Stream([SimpleNamespace(type='response.completed',response=response)])
    class World:
        async def dispatch(self,*args): raise AssertionError('Invalid call must not execute')
    ledger=Ledger(tmp_path/'ledger.jsonl')
    asyncio.run(take_turn(BadClient(),RunConfig(max_tool_calls_per_turn=1),World(),ledger,Trader('worker','test'),'day1',tools=TOOLS))
    ledger.close()
    assert 'tool_validation_error' in (tmp_path/'ledger.jsonl').read_text()
