"""Arbitrage queries and stats for the P&L dashboard."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ArbStatus
from app.repositories.arbitrage_repo import ArbitrageTradeRepository


class ArbitrageStatsService:
    def __init__(self, session: AsyncSession):
        self.repo = ArbitrageTradeRepository(session)

    async def stats(self, user_id: str) -> dict:
        trades = await self.repo.all_for_user(user_id)
        executed = [t for t in trades if t.status != ArbStatus.FAILED]
        completed = [t for t in trades if t.status == ArbStatus.COMPLETED]
        winners = [t for t in executed if t.net_pnl > 0]
        cum, curve = Decimal("0"), []
        for t in trades:
            cum += t.net_pnl
            curve.append({"t": t.created_at.isoformat(), "cumulative_pnl": float(cum)})
        status_counts: dict[str, int] = {}
        for t in trades:
            status_counts[t.status] = status_counts.get(t.status, 0) + 1
        return {
            "attempts": len(trades),
            "executed": len(executed),
            "completed": len(completed),
            "hit_rate_pct": round(100 * len(winners) / len(executed), 2) if executed else 0.0,
            "cumulative_net_pnl": float(cum),
            "total_costs": float(sum((t.total_costs for t in trades), Decimal("0"))),
            "avg_spread_captured": (
                round(sum(float(t.captured_spread) for t in completed) / len(completed), 4) if completed else 0.0
            ),
            "avg_latency_ms": round(sum(t.latency_ms for t in trades) / len(trades), 1) if trades else 0.0,
            "status_counts": status_counts,
            "curve": curve,
        }
