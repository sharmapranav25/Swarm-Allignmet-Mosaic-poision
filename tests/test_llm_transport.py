import asyncio
from types import SimpleNamespace
import pytest
from core.llm_transport import streamed_response


class Stream:
    def __init__(self, events): self.events = events; self.closed = False
    async def __aenter__(self): return self
    async def __aexit__(self, *args): self.closed = True
    def __aiter__(self): return self.iterate()
    async def iterate(self):
        for event in self.events:
            yield event


class Client:
    def __init__(self, events, fallback=None):
        self.responses = self; self.stream = Stream(events); self.fallback = fallback
    async def create(self, **kwargs):
        if kwargs.get('stream'):
            return self.stream
        return self.fallback   # non-streaming fallback path


def test_partial_arguments_ignored_until_complete():
    response = SimpleNamespace(status='completed', usage='retained')
    client = Client([SimpleNamespace(type='response.function_call_arguments.delta', delta='partial'),
                     SimpleNamespace(type='response.completed', response=response)])
    assert asyncio.run(streamed_response(client)) is response
    assert client.stream.closed


def test_truncated_stream_falls_back_to_nonstreaming():
    # A stream that ends without a terminal response must not take down the call: fall back to a
    # single non-streaming request and return its response.
    fallback = SimpleNamespace(status='completed', usage='retained')
    client = Client([SimpleNamespace(type='response.function_call_arguments.delta', delta='partial')],
                    fallback=fallback)
    assert asyncio.run(streamed_response(client)) is fallback
    assert client.stream.closed


@pytest.mark.parametrize('status', ['incomplete', 'failed'])
def test_unsuccessful_terminal_preserved_for_caller_validation(status):
    response = SimpleNamespace(status=status)
    client = Client([SimpleNamespace(type='response.'+status, response=response)])
    assert asyncio.run(streamed_response(client)).status == status
    assert client.stream.closed
