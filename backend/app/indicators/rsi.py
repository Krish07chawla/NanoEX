"""Relative Strength Index with Wilder's smoothing (0..100)."""

from collections.abc import Sequence

from app.indicators._validate import check_period

RSI_MAX = 100.0


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    check_period(period)
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return RSI_MAX if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return RSI_MAX - RSI_MAX / (1 + rs)
