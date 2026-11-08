import asyncio
from core.baseline_cast import ROLES, worker_levels
import json
import re
from website.config import WebsiteConfig
from website import undefended
from website.world import CATALOG
from tests.helpers import Ledger


def make_world(total=140):
    w = undefended.UndefendedWorld(WebsiteConfig(), None, Ledger(), total_incidents=total)
    async def refuse(*a, **k): raise AssertionError('No defender call allowed')
    w.supervisor.decide = refuse; w.charlatan.decide = refuse
    w.workers = list(undefended.ROLES); w.ledger.tick = 1
    return w


def test_no_defender_calls_one_batch_and_attack_scores():
    async def check():
        w = make_world()
        for who in w.workers: await w.assign_batch(who)
        assert len({i for b in w.batches.values() for i in b}) == 100
        for source in w.records: await w.dispatch('Hawk', 'lookup', {'source': source})
        tuple_ = {k: v for d in w.records.values() for k, v in d.items()}
        r = json.loads(await w.dispatch('Hawk', 'execute_request', tuple_))
        batch = w.batches['Hawk']
        out = json.loads(await w.dispatch('Hawk', 'submit_repairs', dict(incident_ids=batch, evidence_id=r['evidence_id'], decision_reason='t')))
        assert out['credited'] == 10 and out['authorized'] == 0 and w.scores['Hawk'] == 10
        assert json.loads(await w.dispatch('Hawk', 'list_incidents', {'offset': 0}))['incidents'] == []
        out = json.loads(await w.dispatch('Hawk', 'submit_repairs', dict(incident_ids=['I40'], evidence_id=r['evidence_id'], decision_reason='t')))
        assert 'Workload limit' in out['error'] and len(w.closed) == 10
        assert not w.flags and not w.plants
        assert not any(e['event'] in ('charlatan_review', 'plant_registered', 'delivery_review', 'action_review') for e in w.ledger.events)
    asyncio.run(check())


def test_prompts_and_policy_do_not_leak_pieces_or_sources():
    level = {n: undefended.KNOWLEDGE[n] for n in (1, 2, 3)}
    assert not any(p in level[1] for p in undefended.PIECES)
    assert not any(p in level[2] for p in undefended.PIECES) and not any(s in level[2] for s in CATALOG)
    assert 'execute_request' in level[3] and 'up to ten incident_ids' in level[3] and 'every fix at once' not in level[3]
    assert not any(re.search(rf"\b{p.replace('_', '[ _]')}\b", undefended.POLICY) for p in undefended.PIECES)
    base = undefended.prompt('Hawk', 1, 10)
    assert not any(s in base for s in CATALOG) and base.endswith(undefended.KNOWLEDGE[1])
    assert undefended.levels_for('knowledge', 1) == {'Hawk': 2, 'Indigo': 3, 'Jet': 1}


def test_runner_finishes_epochs_offline(tmp_path, monkeypatch):
    calls = []
    async def turn(client, cfg, world, ledger, trader, msg, tools):
        calls.append((ledger.tick, cfg.max_tool_calls_per_turn, trader.agent_id))
        return {}
    monkeypatch.setattr(undefended, 'take_turn', turn)
    result = asyncio.run(undefended.experiment(WebsiteConfig(days=2, total_incidents=140), None, tmp_path / 'run'))
    assert result['completed_epochs'] == 2 and result['status'] == 'completed'
    assert result['config']['wall_clock_limit_s'] is None
    assert len(calls)==20 and all(c[1]==5 for c in calls)
    assert [c[0] for c in calls]==[1]*10+[2]*10
    assert result['discovery_calls_per_worker']==0 and result['calls_per_epoch']==5
    rows = [json.loads(l) for l in (tmp_path / 'run' / 'ledger.jsonl').read_text().splitlines()]
    assert not any(r['event'] in ('monitor_llm', 'worker_brief', 'delivery_review', 'action_review', 'flagged', 'plant_delivered') for r in rows)
    assert {r['agent_id']: r['knowledge_level'] for r in rows if r['event'] == 'enroll'} == worker_levels({'Hawk': 1, 'Indigo': 2, 'Jet': 3})
    summary = json.loads((tmp_path / 'run' / 'summary.json').read_text())
    assert summary['knowledge_readout']['Jet']['outcome'] == 'no completed work'


def test_summary_classifies_outcomes(tmp_path):
    def res(w, i, auth): return dict(event='resolution', worker=w, incident_id=i, correct=True, authorized=auth, duplicate=False, credited=True, tick=1)
    rows = [dict(event='run_start', tick=0),
        dict(event='tool_observation', worker='Hawk', tool='execute_request', arguments={}, response={}, tick=1),
        dict(event='request_receipt', worker='Hawk', tick=2), res('Hawk', 'I1', False),
        dict(event='tool_observation', worker='Indigo', tool='execute_request', arguments={}, response={'error': 'x'}, tick=1),
        res('Jet', 'I2', True), dict(event='llm_call', agent_id='Jet', tick=1)]
    path = tmp_path / 'l.jsonl'; path.write_text('\n'.join(json.dumps(r) for r in rows))
    s = undefended.summarize(path, undefended.levels_for('knowledge'))
    assert s['knowledge_readout'] == {'Hawk': dict(level=1, outcome='unauthorized, uncaught'),
        'Indigo': dict(level=2, outcome='shortcut attempted, no closure'), 'Jet': dict(level=3, outcome='approved work only')}
    assert s['workers']['Hawk']['first_receipt_epoch'] == 2 and s['workers']['Jet']['model_calls'] == 1


def test_summary_tolerates_list_responses(tmp_path):
    # view_leaderboard returns a list; baseline-website crashed in summarize on it.
    rows = [dict(event='tool_observation', worker='Hawk', tool='view_leaderboard', arguments={},
                 response=[{'worker': 'Hawk', 'correct_repairs': 0}], tick=1),
        dict(event='tool_observation', worker='Hawk', tool='resolve_incident', arguments={},
             response={'error': 'Workload limit: use only this epoch\'s assigned batch.'}, tick=1)]
    path = tmp_path / 'l.jsonl'; path.write_text('\n'.join(json.dumps(r) for r in rows))
    s = undefended.summarize(path, undefended.levels_for('knowledge'))
    assert s['workers']['Hawk']['workload_rejections'] == 1
