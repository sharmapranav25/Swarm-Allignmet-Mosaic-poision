import asyncio
import json
from types import SimpleNamespace
from core.config import RunConfig
from core.monitor_agent import MonitorAgent
from core.schemas import obj, TEXT
from tests.helpers import Ledger
from tests.test_llm_transport import Stream


class Client:
    def __init__(self, answers):
        self.responses = self
        self.answers = iter(answers)
        self.calls = []
    async def create(self, **kwargs):
        self.calls.append(kwargs)
        result=next(self.answers)
        response=SimpleNamespace(status='completed',output_text='',usage=None,
            output=[SimpleNamespace(type='function_call',name='submit_assessment',arguments=json.dumps(result))])
        return Stream([SimpleNamespace(type='response.completed',response=response)])


def test_schema_repair_before_acceptance():
    client=Client([{'wrong':'field'},{'reason':'observed evidence'}])
    agent=MonitorAgent(RunConfig(llm_retries=1),client,Ledger(),'supervisor')
    result=asyncio.run(agent.decide('Test',{'observed':'record'},lambda r:None,schema=obj({'reason':TEXT})))
    assert result=={'reason':'observed evidence'}
    assert 'response_repair' in json.loads(client.calls[1]['input'])
    assert all(c['stream'] and c['tools'][0]['strict'] for c in client.calls)


def test_invalid_evidence_is_rejected_until_retries_exhaust():
    client=Client([{'reason':'unsupported'}])
    ledger=Ledger()
    agent=MonitorAgent(RunConfig(llm_retries=0),client,ledger,'supervisor')
    def reject(result): raise ValueError('No delivered plant supports this action')
    assert asyncio.run(agent.decide('Test',{},reject,schema=obj({'reason':TEXT}))) is None
    assert ledger.events[-1]['event']=='monitor_exhausted'
