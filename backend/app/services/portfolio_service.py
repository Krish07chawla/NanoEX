"""Portfolio views: positions marked to market, P&L, equity curve and the profit dashboard.

Profit is always measured against capital added (opening balance + top-ups),
so adding virtual money never counts as profit.
"""

from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import IST
from app.core.constants import PAISE, Exchange
from app.core.exceptions import DomainError
from app.models.trade import Trade
from app.repositories.arbitrage_repo import ArbitrageTradeRepository
from app.repositories.order_repo import TradeRepository
from app.repositories.position_repo import PositionRepository
from app.services.wallet_service import WalletService

if TYPE_CHECKING:
    from app.container import Container

ZERO = Decimal("0")


def _f(v: Decimal | int) -> float:
    return float(Decimal(v).quantize(PAISE))


class PortfolioService:
    def __init__(self, session: AsyncSession, container: "Container"):
        self.session = session
        self.c = container
        self.positions = PositionRepository(session)
        self.trades = TradeRepository(session)

    def mark_price(self, symbol: str) -> Decimal | None:
        """Mark positions at the NSE mid price (falls back to BSE)."""
        for exchange in (Exchange.NSE.value, Exchange.BSE.value):
            try:
                return self.c.market.quote(symbol, exchange).mid
            except DomainError:
                continue
        return None

    async def positions_view(self, user_id: str, open_only: bool = True) -> list[dict]:
        rows = []
        for p in await self.positions.for_user(user_id, open_only=open_only):
            mark = self.mark_price(p.symbol) or p.avg_price
            unrealized = (mark - p.avg_price) * p.quantity if p.quantity else ZERO
            rows.append(
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "side": "LONG" if p.quantity > 0 else "SHORT",
                    "avg_price": float(p.avg_price),
                    "mark_price": float(round(mark, 2)),
                    "market_value": _f(mark * p.quantity),
                    "unrealized_pnl": _f(unrealized),
                    "unrealized_pct": (
                        float(round((mark / p.avg_price - 1) * 100 * (1 if p.quantity > 0 else -1), 3))
                        if p.avg_price
                        else 0.0
                    ),
                    "realized_pnl": _f(p.realized_pnl),
                }
            )
        return rows

    async def summary(self, user_id: str) -> dict:
        wallet = await WalletService(self.session).get(user_id)
        positions = await self.positions_view(user_id, open_only=True)
        trades = await self.trades.all_for_user(user_id)
        market_value = sum((Decimal(str(p["market_value"])) for p in positions), ZERO)
        unrealized = sum((Decimal(str(p["unrealized_pnl"])) for p in positions), ZERO)
        realized = sum((t.realized_pnl for t in trades), ZERO)
        fees = sum((t.fees for t in trades), ZERO)
        equity = wallet.balance + market_value
        total_pnl = equity - wallet.capital_added
        return {
            "cash": _f(wallet.balance),
            "blocked": _f(wallet.blocked_margin),
            "available": _f(wallet.available),
            "market_value": _f(market_value),
            "equity": _f(equity),
            "capital_added": _f(wallet.capital_added),
            "realized_pnl": _f(realized),
            "unrealized_pnl": _f(unrealized),
            "total_fees": _f(fees),
            "net_realized_pnl": _f(realized - fees),
            "total_pnl": _f(total_pnl),
            "total_return_pct": (
                float(round(total_pnl / wallet.capital_added * 100, 4)) if wallet.capital_added else 0.0
            ),
            "open_positions": len(positions),
            "trade_count": len(trades),
        }

    async def equity_curve(self, user_id: str) -> list[dict]:
        """Capital added + cumulative realized P&L (net of fees) after each trade, plus a live point."""
        wallet = await WalletService(self.session).get(user_id)
        base = wallet.capital_added
        points, cum = [], ZERO
        for t in await self.trades.all_for_user(user_id):
            cum += t.realized_pnl - t.fees
            points.append({"t": t.executed_at.isoformat(), "equity": _f(base + cum)})
        summary = await self.summary(user_id)
        from datetime import UTC, datetime

        points.append({"t": datetime.now(UTC).isoformat(), "equity": summary["equity"]})
        return points

    async def profit_dashboard(self, user_id: str) -> dict:
        """Everything the Profit & Portfolio page needs in one call."""
        summary = await self.summary(user_id)
        trades = await self.trades.all_for_user(user_id)
        by_source: dict[str, Decimal] = defaultdict(lambda: ZERO)
        by_strategy: dict[str, Decimal] = defaultdict(lambda: ZERO)
        by_symbol: dict[str, Decimal] = defaultdict(lambda: ZERO)
        by_day: dict[str, Decimal] = defaultdict(lambda: ZERO)
        closing: list[Decimal] = []
        for t in trades:
            net = t.realized_pnl - t.fees
            by_source[t.source] += net
            by_strategy[t.strategy_name or "Manual"] += net
            by_symbol[t.symbol] += net
            by_day[t.executed_at.astimezone(IST).date().isoformat()] += net
            if t.realized_pnl != 0:
                closing.append(t.realized_pnl - t.fees)
        arb_trades = await ArbitrageTradeRepository(self.session).all_for_user(user_id)
        wins = [x for x in closing if x > 0]
        return {
            "summary": summary,
            "by_source": [{"source": k, "pnl": _f(v)} for k, v in sorted(by_source.items())],
            "by_strategy": sorted(
                ({"name": k, "pnl": _f(v)} for k, v in by_strategy.items()), key=lambda r: r["pnl"], reverse=True
            ),
            "by_symbol": sorted(
                ({"symbol": k, "pnl": _f(v)} for k, v in by_symbol.items()), key=lambda r: r["pnl"], reverse=True
            ),
            "daily": [{"date": k, "pnl": _f(v)} for k, v in sorted(by_day.items())],
            "win_rate_pct": round(100 * len(wins) / len(closing), 2) if closing else 0.0,
            "closed_trades": len(closing),
            "best_trade": _f(max(closing)) if closing else 0.0,
            "worst_trade": _f(min(closing)) if closing else 0.0,
            "arbitrage_net_pnl": _f(sum((a.net_pnl for a in arb_trades), ZERO)),
            "positions": await self.positions_view(user_id),
            "equity_curve": await self.equity_curve(user_id),
        }


def trade_row(t: Trade) -> list:
    return [
        t.executed_at.isoformat(),
        t.symbol,
        t.exchange,
        t.side,
        t.quantity,
        f"{t.price:.2f}",
        f"{t.fees:.2f}",
        f"{t.realized_pnl:.2f}",
        t.source,
        t.strategy_name or "",
        t.signal_reason or "",
        t.order_id,
    ]


TRADE_CSV_HEADER = [
    "executed_at",
    "symbol",
    "exchange",
    "side",
    "quantity",
    "price",
    "fees",
    "realized_pnl",
    "source",
    "strategy",
    "signal_reason",
    "order_id",
]
