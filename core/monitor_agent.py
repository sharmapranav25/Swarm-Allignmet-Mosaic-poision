"""Structured LLM calls shared by the conversation-monitoring agents."""
import json
import asyncio
from .llm_transport import streamed_response
from adaption import APIError
from jsonschema import Draft202012Validator, ValidationError


class MonitorAgent:
    def __init__(self, cfg, client, ledger, role):
        self.cfg, self.client, self.ledger, self.role = cfg, client, ledger, role
        self.cost = 0.0

    async def decide(self, prompt, payload, validate, schema=None):
        if schema is None:
            raise ValueError("A function schema is required for every monitor call")
        checker = Draft202012Validator(schema)
        repair = None
        for attempt in range(self.cfg.llm_retries + 1):
            raw = None
            try:
                request = dict(payload)
                if repair:
                    request["response_repair"] = repair
                r = await streamed_response(self.client,
                    model=self.cfg.model, instructions=prompt,
                    input=json.dumps(request),
                    tools=[{'type': 'function', 'name': 'submit_assessment',
                            'description': 'Fill the assessment fields using the supplied evidence.',
                            'parameters': schema, 'strict': True}],
                    tool_choice={'type': 'function', 'name': 'submit_assessment'},
                    max_output_tokens=min(self.cfg.max_output_tokens * (attempt + 1), 16000))
                u = r.usage
                cost = float(getattr(u, 'cost', 0) or 0) if u else 0.0
                self.cost += cost
                self.ledger.record('monitor_llm', role=self.role, status=r.status, cost=cost,
                                   tokens=u.total_tokens if u else None)
                raw = r.output_text or ''
                if r.status != 'completed':
                    raise ValueError('Incomplete monitor response')
                calls = [o for o in r.output if o.type == 'function_call']
                if len(calls) != 1 or calls[0].name != 'submit_assessment':
                    raise ValueError('Expected exactly one submit_assessment function call')
                raw = calls[0].arguments
                result = json.loads(raw)
                checker.validate(result)
                validate(result)
                return result
            except (APIError, ValueError, TypeError, KeyError, ValidationError) as exc:
                self.ledger.record('monitor_error', role=self.role, attempt=attempt,
                                   error=f'{type(exc).__name__}: {str(exc)[:200]}', raw_response=raw)
                repair = {'validation_error': str(exc)[:300], 'previous_response': raw,
                          'instruction': 'Fill the submit_assessment function again, correcting the indicated field.'}
                if attempt < self.cfg.llm_retries and isinstance(exc, APIError):
                    await asyncio.sleep(min(2 ** attempt, 8))
        self.ledger.record('monitor_exhausted', role=self.role, attempts=self.cfg.llm_retries + 1)
        return None
