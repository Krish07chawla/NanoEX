"""MACD: EMA(fast) - EMA(slow), its signal EMA, and the histogram."""

from collections.abc import Sequence

from app.indicators.ema import ema


def macd(
    values: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    if fast >= slow:
        raise ValueError("fast period must be shorter than slow period")
    fast_ema, slow_ema = ema(values, fast), ema(values, slow)
    line = [f - s if f is not None and s is not None else None for f, s in zip(fast_ema, slow_ema, strict=True)]
    sig = ema(line, signal)
    hist = [m - s if m is not None and s is not None else None for m, s in zip(line, sig, strict=True)]
    return line, sig, hist
