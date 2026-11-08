import asyncio
from core.baseline_cast import ROLES, worker_levels
import json
from core.config import RunConfig
from ticketing import undefended
from tests.helpers import Ledger


def test_no_defender_calls_and_one_batch_per_epoch():
    async def check():
        w=undefended.UndefendedWorld(RunConfig(total_tickets=140),None,Ledger())
        w.workers=list(undefended.ROLES);w.ledger.tick=1
        for who in w.workers:await w.assign_batch(who)
        assert len(set(t for batch in w.batches.values() for t in batch))==100
        for source in w.records:await w.dispatch('Hawk','lookup',{'source':source})
        r=json.loads(await w.dispatch('Hawk','retrieve_bundle',{k:v for data in w.records.values() for k,v in data.items() if k in ('namespace','service','alias','selector')}))
        batch=w.batches['Hawk']
        out=json.loads(await w.dispatch('Hawk','resolve_batch',dict(ticket_ids=batch,evidence_id=r['evidence_id'],decision_reason='test')))
        assert out['credited']==10 and out['authorized']==0
        assert json.loads(await w.dispatch('Hawk','list_tickets',{'offset':0}))['tickets']==[]
        out=json.loads(await w.dispatch('Hawk','resolve_batch',dict(ticket_ids=['T40'],evidence_id=r['evidence_id'],decision_reason='test')))
        assert 'error' in out and len(w.closed)==10
        assert not w.flags and not w.plants
    asyncio.run(check())


def test_runner_finishes_epochs_without_monitor_calls(tmp_path,monkeypatch):
    calls=[]
    async def turn(client,cfg,world,ledger,trader,msg,tools):
        calls.append((ledger.tick,cfg.max_tool_calls_per_turn,trader.agent_id))
        return {}
    monkeypatch.setattr(undefended,'take_turn',turn)
    cfg=RunConfig(days=2,total_tickets=140)
    result=asyncio.run(undefended.experiment(cfg,None,tmp_path/'run'))
    assert result['completed_epochs']==2 and result['status']=='completed'
    assert result['config']['wall_clock_limit_s'] is None
    assert len(calls)==20 and all(c[1]==5 for c in calls)
    assert [c[0] for c in calls]==[1]*10+[2]*10
    assert result['discovery_calls_per_worker']==0 and result['calls_per_epoch']==5
    rows=[json.loads(l) for l in (tmp_path/'run'/'ledger.jsonl').read_text().splitlines()]
    assert not any(r['event'] in ('monitor_llm','worker_brief','delivery_review','action_review','flagged','plant_delivered') for r in rows)
