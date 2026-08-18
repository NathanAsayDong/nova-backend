"""Helpers for consuming the agent loop's synchronous event stream from async code."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any


async def iter_in_thread(generator: Iterator[Any]) -> AsyncIterator[Any]:
    """
    Consume a sync generator without blocking the event loop.

    conversation_loop_events does blocking network I/O and tool execution, so
    stepping it directly from a coroutine would stall every other connection
    on the process for the length of a turn.
    """
    sentinel = object()
    while True:
        item = await asyncio.to_thread(next, generator, sentinel)
        if item is sentinel:
            return
        yield item
