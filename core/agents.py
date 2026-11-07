"""World-independent agent state and streamed, schema-validated tool loop."""
from __future__ import annotations
import asyncio
import copy
import json
from dataclasses import dataclass, field
from adaption import APIError, AsyncAdaption
from jsonschema import Draft202012Validator, ValidationError
from .llm_transport import streamed_response


class BranchPoint(Exception):
    """Optional world checkpoint preserving a pending tool-call continuation."""
    def __init__(self, trader_id, response):
        self.trader_id, self.response = trader_id, copy.deepcopy(response)
        self.resume = None
        super().__init__('Declared world checkpoint')


@dataclass
class Trader:
    agent_id: str
    system: str
    history: list[list[dict]] = field(default_factory=list)
    turns: int = 0

def _dump(o) -> dict:
    d = o.model_dump(exclude_none=True)
    if d.get("type") == "message":
        d["content"] = [{"type": "output_text", "text": c.get("text", "")} for c in d.get("content", [])
                        if c.get("type") == "output_text"]
        d.pop("id", None)
    return d

async def take_turn(client: AsyncAdaption, cfg, world, ledger, trader: Trader, day_msg: str, resume=None, tools=None) -> dict:
    if tools is None:
        raise ValueError("A world-specific tool catalog is required")
    items: list[dict] = [{"role": "user", "content": day_msg}]
    context = [it for t in trader.history[-cfg.history_days_kept:] for it in t]
    calls_made, cost, tokens, final = 0, 0.0, 0, ""
    pending = []
    if resume:
        items, calls_made, pending = resume['items'], resume['calls_made'], resume['pending']
    while True:
        if pending:
            for index, c in enumerate(pending):
                try:
                    if calls_made >= cfg.max_tool_calls_per_turn:
                        items.append({'type':'function_call_output','call_id':c['call_id'],'output':'Daily tool budget exhausted. This call was not executed.'})
                        continue
                    schema = next(t['parameters'] for t in tools if t['name']==c['name'])
                    args = json.loads(c['arguments'])
                    Draft202012Validator(schema).validate(args)
                    result = await world.dispatch(trader.agent_id, c['name'], args)
                except BranchPoint as point:
                    import copy
                    point.resume = copy.deepcopy(dict(items=items,calls_made=calls_made,pending=pending[index:]))
                    raise
                except (ValueError, ValidationError, StopIteration) as exc:
                    ledger.record('tool_validation_error', agent_id=trader.agent_id, error=str(exc)[:300])
                    result = 'Tool fields invalid: '+str(exc)[:300]+'. Fill the declared schema correctly.'
                items.append({'type':'function_call_output','call_id':c['call_id'],'output':result})
                calls_made += 1
            pending = []
            if calls_made >= cfg.max_tool_calls_per_turn:
                break
        r = None
        for attempt in range(cfg.llm_retries + 1):
            try:
                r = await streamed_response(client,model=cfg.model, instructions=trader.system,
                                                  input=context + items, tools=tools,
                                                  max_output_tokens=min(cfg.max_output_tokens * (attempt + 1), 16000))
                u = r.usage
                cost += float(getattr(u, "cost", 0) or 0) if u else 0.0
                tokens += u.total_tokens if u else 0
                ledger.record("llm_call", agent_id=trader.agent_id, status=r.status,
                              tokens=u.total_tokens if u else None,
                              cost=float(getattr(u, "cost", 0) or 0) if u else 0.0)
                if r.status != "completed" or not any(o.type in ("message", "function_call") for o in r.output):
                    raise ValueError("Incomplete or empty trader response; no tools executed")
                break
            except (APIError, ValueError) as e:
                r = None
                ledger.record("llm_error", agent_id=trader.agent_id, attempt=attempt,
                              error=f"{type(e).__name__}: {str(e)[:200]}")
                if attempt < cfg.llm_retries:
                    await asyncio.sleep(min(2 ** attempt, 8))
        if r is None:
            break
        outs = [o for o in r.output if o.type in ("message", "function_call")]
        calls = [o for o in outs if o.type == "function_call"]
        # capture the model's own words + what it chose to do, so a refusal / stall is visible
        ledger.record("agent_output", agent_id=trader.agent_id, status=r.status,
                      text=(r.output_text or ""), tool_calls=[c.name for c in calls])
        for o in outs:
            items.append(_dump(o))
            if o.type == "message":
                final = r.output_text
        if not calls:
            break
        pending = [_dump(c) for c in calls]
    trader.history.append(items)
    trader.turns += 1
    return {"calls": calls_made, "cost": cost, "tokens": tokens, "text": final}
