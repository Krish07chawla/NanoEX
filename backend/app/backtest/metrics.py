"""Performance metrics for an equity curve and a list of closed trades."""

import math
from collections.abc import Sequence


def returns(equity: Sequence[float]) -> list[float]:
    return [equity[i] / equity[i - 1] - 1 for i in range(1, len(equity)) if equity[i - 1] > 0]


def max_drawdown_pct(equity: Sequence[float]) -> float:
    peak, worst = -math.inf, 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1)
    return round(worst * 100, 4)


def sharpe(rets: Sequence[float], periods_per_year: int) -> float:
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    std = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))
    return round(mean / std * math.sqrt(periods_per_year), 4) if std > 0 else 0.0


def sortino(rets: Sequence[float], periods_per_year: int) -> float:
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    downside = [min(0.0, r) ** 2 for r in rets]
    dd = math.sqrt(sum(downside) / len(rets))
    return round(mean / dd * math.sqrt(periods_per_year), 4) if dd > 0 else 0.0


def profit_factor(pnls: Sequence[float]) -> float | None:
    """Gross profit / gross loss. None when there were no losing trades."""
    gains = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses == 0:
        return None
    return round(gains / losses, 4)


def win_rate_pct(pnls: Sequence[float]) -> float:
    return round(100 * sum(1 for p in pnls if p > 0) / len(pnls), 2) if pnls else 0.0
