"""Bollinger Bands: SMA +/- k standard deviations (population std)."""

import math
from collections.abc import Sequence

from app.indicators._validate import check_period


def bollinger(
    values: Sequence[float], period: int = 20, k: float = 2.0
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Return (middle, upper, lower) series."""
    check_period(period)
    mid: list[float | None] = []
    upper: list[float | None] = []
    lower: list[float | None] = []
    for i in range(len(values)):
        if i < period - 1:
            mid.append(None), upper.append(None), lower.append(None)
            continue
        window = values[i - period + 1 : i + 1]
        mean = sum(window) / period
        std = math.sqrt(sum((x - mean) ** 2 for x in window) / period)
        mid.append(mean)
        upper.append(mean + k * std)
        lower.append(mean - k * std)
    return mid, upper, lower
