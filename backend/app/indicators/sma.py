"""Simple moving average."""

from collections.abc import Sequence

from app.indicators._validate import check_period


def sma(values: Sequence[float], period: int) -> list[float | None]:
    """SMA series; the first `period - 1` entries are None (not enough data)."""
    check_period(period)
    out: list[float | None] = []
    window_sum = 0.0
    for i, v in enumerate(values):
        window_sum += v
        if i >= period:
            window_sum -= values[i - period]
        out.append(window_sum / period if i >= period - 1 else None)
    return out
