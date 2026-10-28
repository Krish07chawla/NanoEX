"""Exponential moving average, seeded with the SMA of the first `period` values."""

from collections.abc import Sequence

from app.indicators._validate import check_period


def ema(values: Sequence[float | None], period: int) -> list[float | None]:
    """EMA series. Leading None inputs are skipped (lets EMA run on another indicator's output)."""
    check_period(period)
    alpha = 2.0 / (period + 1)
    out: list[float | None] = []
    seed: list[float] = []
    prev: float | None = None
    for v in values:
        if v is None:
            out.append(None)
            continue
        if prev is None:
            seed.append(v)
            if len(seed) == period:
                prev = sum(seed) / period
                out.append(prev)
            else:
                out.append(None)
            continue
        prev = alpha * v + (1 - alpha) * prev
        out.append(prev)
    return out
