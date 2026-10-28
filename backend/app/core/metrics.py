"""Lightweight performance counters exposed on /metrics and the dashboard."""

import time
from collections import deque
from dataclasses import dataclass, field

WINDOW_SECONDS = 60
SAMPLE_LIMIT = 5000


@dataclass
class Metrics:
    """Process-wide counters. Latencies are kept as rolling samples (microseconds)."""

    started_at: float = field(default_factory=time.time)
    orders_total: int = 0
    trades_total: int = 0
    ticks_total: int = 0
    rejected_total: int = 0
    _order_times: deque = field(default_factory=lambda: deque(maxlen=SAMPLE_LIMIT))
    _order_latency_us: deque = field(default_factory=lambda: deque(maxlen=SAMPLE_LIMIT))
    _tick_to_trade_us: deque = field(default_factory=lambda: deque(maxlen=SAMPLE_LIMIT))

    def record_order(self, latency_us: float) -> None:
        self.orders_total += 1
        self._order_times.append(time.time())
        self._order_latency_us.append(latency_us)

    def record_tick_to_trade(self, latency_us: float) -> None:
        self._tick_to_trade_us.append(latency_us)

    def orders_per_sec(self) -> float:
        cutoff = time.time() - WINDOW_SECONDS
        recent = sum(1 for t in self._order_times if t >= cutoff)
        return round(recent / WINDOW_SECONDS, 3)

    @staticmethod
    def _avg(samples: deque) -> float:
        return round(sum(samples) / len(samples), 1) if samples else 0.0

    def snapshot(self) -> dict:
        return {
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "orders_total": self.orders_total,
            "trades_total": self.trades_total,
            "ticks_total": self.ticks_total,
            "rejected_total": self.rejected_total,
            "orders_per_sec": self.orders_per_sec(),
            "avg_order_latency_us": self._avg(self._order_latency_us),
            "avg_tick_to_trade_us": self._avg(self._tick_to_trade_us),
        }

    def prometheus(self) -> str:
        snap = self.snapshot()
        lines = []
        for key, value in snap.items():
            lines.append(f"# TYPE nanoex_{key} gauge")
            lines.append(f"nanoex_{key} {value}")
        return "\n".join(lines) + "\n"


metrics = Metrics()
