"""Two-leg NSE-BSE arbitrage executor (paper trading).

1. Re-price the opportunity from current book depth.
2. Simulate each leg's network/exchange latency and a chance that a leg is
   rejected (leg risk). Legs reach the exchange in latency order, so prices can
   move in between, exactly the risk real arbitrage faces.
3. Each leg is a MARKET order through OrderService, so the risk manager checks it.
4. Reconcile: any unmatched quantity is flattened immediately at market, and the
   result is recorded honestly as COMPLETED, PARTIAL, HEDGED or FAILED.
"""

import asyncio
import random
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.arbitrage.detector import Opportunity
from app.core.constants import PAISE, PRICE_PRECISION, ArbMode, ArbStatus, AuditAction, OrderSource, OrderType, Side
from app.core.event_bus import Topics
from app.core.events import publish_user
from app.core.exceptions import Conflict, DomainError, InsufficientFunds
from app.db.base import new_id
from app.models.arbitrage import ArbitrageTrade
from app.models.trade import Trade
from app.repositories.wallet_repo import WalletRepository
from app.schemas.order import PlaceOrderRequest
from app.services.audit_service import AuditService
from app.services.order_service import MARKET_BUY_BUFFER, OrderContext, OrderService

if TYPE_CHECKING:
    from app.container import Container

STRATEGY_NAME = "NSE-BSE Arbitrage"
MS = 1000


@dataclass
class LegPlan:
    side: Side
    exchange: str
    latency_ms: int
    fails: bool
    filled: int = 0
    order_id: str | None = None
    error: str | None = None


class ArbitrageExecutor:
    def __init__(self, container: "Container", rng: random.Random | None = None):
        self.c = container
        self.rng = rng or random.Random(container.settings.sim_seed)

    async def execute(
        self,
        session: AsyncSession,
        user_id: str,
        symbol: str,
        quantity: int,
        mode: ArbMode,
        min_profit: Decimal = Decimal("0"),
        opportunity_id: str | None = None,
    ) -> ArbitrageTrade:
        opp = self.c.arb_scanner.evaluate(symbol, quantity)
        if opp is None:
            raise Conflict("No prices available for this symbol yet", code="NO_OPPORTUNITY")
        if not opp.is_actionable(min_profit):
            raise Conflict(
                f"Not profitable right now: spread Rs {opp.spread_abs:.2f}/share, est. costs Rs {opp.costs.total:.2f}, "
                f"est. net Rs {opp.net_profit:.2f}" + ("" if opp.liquidity_ok else " (not enough depth)"),
                code="NO_OPPORTUNITY",
                details=opp.to_dict(),
            )

        await self._precheck_funds(session, user_id, opp)

        arb_id = new_id()
        started = time.perf_counter()
        orders = OrderService(session, self.c)
        legs = self._plan_legs(opp)
        for leg in sorted(legs, key=lambda lg: lg.latency_ms):
            await asyncio.sleep(max(0.0, leg.latency_ms / MS - (time.perf_counter() - started)))
            await self._send_leg(orders, user_id, symbol, quantity, leg, arb_id, opp)

        buy_leg = next(lg for lg in legs if lg.side is Side.BUY)
        sell_leg = next(lg for lg in legs if lg.side is Side.SELL)
        matched = min(buy_leg.filled, sell_leg.filled)
        flatten_note = await self._flatten(orders, user_id, symbol, buy_leg, sell_leg, arb_id)

        status = self._status(buy_leg.filled, sell_leg.filled, matched, quantity)
        record = ArbitrageTrade(
            id=arb_id,
            user_id=user_id,
            opportunity_id=opportunity_id,
            symbol=symbol,
            buy_exchange=opp.buy_exchange,
            sell_exchange=opp.sell_exchange,
            quantity=quantity,
            matched_qty=matched,
            mode=mode,
            buy_order_id=buy_leg.order_id,
            sell_order_id=sell_leg.order_id,
            expected_spread=opp.spread_abs.quantize(PRICE_PRECISION),
            status=status,
            latency_ms=int((time.perf_counter() - started) * MS),
            failure_reason=self._failure_text(buy_leg, sell_leg, flatten_note),
        )
        await self._fill_pnl(session, record)
        session.add(record)
        await session.flush()
        await AuditService(session).log(
            AuditAction.ARBITRAGE,
            user_id=user_id,
            entity="arbitrage_trade",
            entity_id=arb_id,
            details={"status": status, "net_pnl": str(record.net_pnl)},
        )
        publish_user(Topics.ARB_RESULT, user_id, {"arbitrage": arb_to_dict(record)})
        return record

    # ---------- steps ----------
    @staticmethod
    async def _precheck_funds(session: AsyncSession, user_id: str, opp: Opportunity) -> None:
        """Pre-trade check for the whole strategy, so we never send one leg we cannot pair."""
        wallet = await WalletRepository(session).get_by_user(user_id)
        need = opp.buy_price * opp.quantity * MARKET_BUY_BUFFER + opp.costs.total
        if wallet is None or wallet.available < need:
            available = wallet.available if wallet else Decimal("0")
            raise InsufficientFunds(f"Need about Rs {need:,.2f} for the buy leg, available Rs {available:,.2f}")

    def _plan_legs(self, opp: Opportunity) -> list[LegPlan]:
        s = self.c.settings
        return [
            LegPlan(
                side,
                ex,
                self.rng.randint(s.arb_min_latency_ms, s.arb_max_latency_ms),
                self.rng.random() < s.arb_leg_failure_prob,
            )
            for side, ex in ((Side.BUY, opp.buy_exchange), (Side.SELL, opp.sell_exchange))
        ]

    async def _send_leg(
        self, orders: OrderService, user_id: str, symbol: str, qty: int, leg: LegPlan, arb_id: str, opp: Opportunity
    ) -> None:
        if leg.fails:
            leg.error = f"{leg.side} leg on {leg.exchange} timed out after {leg.latency_ms} ms (simulated)"
            return
        reason = (
            f"Buy {opp.buy_exchange} @{opp.buy_price:.2f} / Sell {opp.sell_exchange} @{opp.sell_price:.2f}, "
            f"spread {opp.spread_abs:.2f}"
        )
        try:
            order = await orders.place(
                user_id,
                PlaceOrderRequest(
                    symbol=symbol,
                    exchange=leg.exchange,
                    side=leg.side,
                    order_type=OrderType.MARKET,
                    quantity=qty,
                ),
                OrderContext(
                    OrderSource.ARBITRAGE,
                    strategy_name=STRATEGY_NAME,
                    signal_reason=reason[:255],
                    arbitrage_trade_id=arb_id,
                ),
            )
            leg.order_id, leg.filled = order.id, order.filled_qty
        except DomainError as exc:
            leg.error = f"{leg.side} leg rejected: {exc.message}"

    async def _flatten(
        self, orders: OrderService, user_id: str, symbol: str, buy: LegPlan, sell: LegPlan, arb_id: str
    ) -> str | None:
        """Close any quantity bought but not sold (or sold but not bought) at market."""
        excess = buy.filled - sell.filled
        if excess == 0:
            return None
        side, exchange = (Side.SELL, buy.exchange) if excess > 0 else (Side.BUY, sell.exchange)
        try:
            order = await orders.place(
                user_id,
                PlaceOrderRequest(
                    symbol=symbol,
                    exchange=exchange,
                    side=side,
                    order_type=OrderType.MARKET,
                    quantity=abs(excess),
                ),
                OrderContext(
                    OrderSource.ARBITRAGE,
                    strategy_name=STRATEGY_NAME,
                    signal_reason="Flatten unmatched leg (leg risk)",
                    arbitrage_trade_id=arb_id,
                ),
            )
            return f"Flattened {order.filled_qty}/{abs(excess)} unmatched shares on {exchange}"
        except DomainError as exc:
            return f"Could not flatten {abs(excess)} shares: {exc.message}"

    @staticmethod
    def _status(bought: int, sold: int, matched: int, quantity: int) -> ArbStatus:
        if bought == 0 and sold == 0:
            return ArbStatus.FAILED
        if matched == quantity:
            return ArbStatus.COMPLETED
        if matched > 0:
            return ArbStatus.PARTIAL
        return ArbStatus.HEDGED

    @staticmethod
    def _failure_text(buy: LegPlan, sell: LegPlan, flatten_note: str | None) -> str | None:
        parts = [p for p in (buy.error, sell.error, flatten_note) if p]
        return "; ".join(parts)[:255] or None

    @staticmethod
    async def _fill_pnl(session: AsyncSession, record: ArbitrageTrade) -> None:
        """P&L from the actual fills of every order tagged with this arbitrage id."""
        from app.models.order import Order

        stmt = select(Trade).join(Order, Order.id == Trade.order_id).where(Order.arbitrage_trade_id == record.id)
        trades = list((await session.execute(stmt)).scalars().all())
        bought = sum((t.price * t.quantity for t in trades if t.side == Side.BUY), Decimal("0"))
        sold = sum((t.price * t.quantity for t in trades if t.side == Side.SELL), Decimal("0"))
        record.gross_pnl = (sold - bought).quantize(PAISE)
        record.total_costs = sum((t.fees for t in trades), Decimal("0")).quantize(PAISE)
        record.net_pnl = record.gross_pnl - record.total_costs
        if record.matched_qty:
            buy_q = sum(t.quantity for t in trades if t.side == Side.BUY and t.exchange == record.buy_exchange)
            sell_q = sum(t.quantity for t in trades if t.side == Side.SELL and t.exchange == record.sell_exchange)
            buy_avg = (
                sum(
                    (t.price * t.quantity for t in trades if t.side == Side.BUY and t.exchange == record.buy_exchange),
                    Decimal("0"),
                )
                / buy_q
            )
            sell_avg = (
                sum(
                    (
                        t.price * t.quantity
                        for t in trades
                        if t.side == Side.SELL and t.exchange == record.sell_exchange
                    ),
                    Decimal("0"),
                )
                / sell_q
            )
            record.captured_spread = (sell_avg - buy_avg).quantize(PRICE_PRECISION)


def arb_to_dict(t: ArbitrageTrade) -> dict:
    return {
        "id": t.id,
        "symbol": t.symbol,
        "buy_exchange": t.buy_exchange,
        "sell_exchange": t.sell_exchange,
        "quantity": t.quantity,
        "matched_qty": t.matched_qty,
        "mode": t.mode,
        "status": t.status,
        "expected_spread": float(t.expected_spread),
        "captured_spread": float(t.captured_spread or 0),
        "gross_pnl": float(t.gross_pnl),
        "total_costs": float(t.total_costs),
        "net_pnl": float(t.net_pnl),
        "latency_ms": t.latency_ms,
        "failure_reason": t.failure_reason,
        "buy_order_id": t.buy_order_id,
        "sell_order_id": t.sell_order_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
