"""Rolling z-score: how many standard deviations the price is from its rolling mean."""

import math
from collections.abc import Sequence

from app.indicators._validate import check_period


def zscore(values: Sequence[float], period: int = 20) -> list[float | None]:
    check_period(period)
    out: list[float | None] = []
    for i in range(len(values)):
        if i < period - 1:
            out.append(None)
            continue
        window = values[i - period + 1 : i + 1]
        mean = sum(window) / period
        std = math.sqrt(sum((x - mean) ** 2 for x in window) / period)
        out.append(0.0 if std == 0 else (values[i] - mean) / std)
    return out
