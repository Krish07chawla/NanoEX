"""In-process async publish/subscribe (Observer pattern).

Publishers call `publish(topic, payload)`; each subscriber owns a bounded
asyncio.Queue. Slow subscribers drop their oldest message instead of
blocking the market loop.
"""

import asyncio
import contextlib
from collections import defaultdict
from typing import Any

QUEUE_SIZE = 1000


class EventBus:
    """Topic-based fan-out to any number of async subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, *topics: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        for topic in topics:
            self._subscribers[topic].add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        for subs in self._subscribers.values():
            subs.discard(queue)

    def publish(self, topic: str, payload: Any) -> None:
        """Non-blocking publish; safe to call from the hot path."""
        message = {"topic": topic, "data": payload}
        for queue in list(self._subscribers.get(topic, ())):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            queue.put_nowait(message)

    def subscriber_count(self, topic: str) -> int:
        return len(self._subscribers.get(topic, ()))


class Topics:
    TICK = "tick"
    DEPTH = "depth"
    ORDER_UPDATE = "order_update"
    TRADE = "trade"
    ARB_OPPORTUNITY = "arb_opportunity"
    ARB_RESULT = "arb_result"
    WALLET = "wallet"
