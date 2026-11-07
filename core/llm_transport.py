"""Consume streaming responses without exposing partial tool calls to execution.

If the stream fails or ends without a terminal response, fall back to a single non-streaming
request so a flaky stream does not take down a trader turn or a monitor review.
"""
import httpx


async def _nonstream(client, **request):
    request.pop("stream", None)
    return await client.responses.create(**request)


async def streamed_response(client, **request):
    try:
        stream = await client.responses.create(**request, stream=True)
        async with stream:
            async for event in stream:
                if event.type in ('response.completed', 'response.incomplete', 'response.failed'):
                    # Existing callers log usage and reject non-completed responses.
                    return event.response
                if event.type == 'error':
                    # one non-streaming retry before giving up
                    return await _nonstream(client, **request)
        return await _nonstream(client, **request)
    except httpx.TransportError:
        return await _nonstream(client, **request)
