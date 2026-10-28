"""Order placement and cancellation. Every order passes the RiskManager before the engine."""

import time
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import start_of_trading_day
from app.core.constants import (
    PAISE,
    TICK_SIZE,
    AuditAction,
    OrderSource,
    OrderStatus,
    OrderType,
    Side,
)
from app.core.event_bus import Topics
from app.core.events import publish_user
from app.core.exceptions import Conflict, DomainError, NotFound, ValidationFailed
from app.core.metrics import metrics
from app.engine.order import BookOrder
from app.engine.risk import RiskContext
from app.models.order import Order
from app.models.user import User
from app.repositories.order_repo import OrderRepository, TradeRepository
from app.repositories.position_repo import PositionRepository
from app.repositories.risk_repo import RiskSettingsRepository
from app.repositories.wallet_repo import WalletRepository
from app.schemas.order import OrderOut, PlaceOrderRequest
from app.services.audit_service import AuditService
from app.services.settlement_service import SettlementService
from app.services.wallet_service import WalletService

if TYPE_CHECKING:
    from app.container import Container

MARKET_BUY_BUFFER = Decimal("1.01")  # block 1% extra for market buys to cover price moves
LIMIT_PRICE_BAND = Decimal("0.20")  # limit price must be within +/-20% of last (circuit band)


@dataclass
class OrderContext:
    """Extra metadata for orders placed by bots."""

    source: OrderSource = OrderSource.MANUAL
    strategy_config_id: str | None = None
    strategy_name: str | None = None
    signal_reason: str | None = None
    arbitrage_trade_id: str | None = None


class OrderService:
    def __init__(self, session: AsyncSession, container: "Container"):
        self.session = session
        self.c = container
        self.orders = OrderRepository(session)
        self.wallets = WalletRepository(session)
        self.wallet_service = WalletService(session)
        self.audit = AuditService(session)

    async def place(self, user: User | str, req: PlaceOrderRequest, ctx: OrderContext | None = None) -> Order:
        """Validate, risk-check, persist, match and settle an order. Rejections are persisted too."""
        ctx = ctx or OrderContext()
        user_id = user if isinstance(user, str) else user.id
        started = time.perf_counter()
        quote = self.c.market.quote(req.symbol, req.exchange)
        ref_price = self._reference_price(req, quote)

        order = Order(
            user_id=user_id,
            symbol=req.symbol,
            exchange=req.exchange,
            side=req.side,
            order_type=req.order_type,
            price=req.price,
            quantity=req.quantity,
            source=ctx.source,
            strategy_config_id=ctx.strategy_config_id,
            strategy_name=ctx.strategy_name,
            signal_reason=ctx.signal_reason,
            arbitrage_trade_id=ctx.arbitrage_trade_id,
            status=OrderStatus.NEW,
            blocked_amount=Decimal("0"),
        )
        wallet = await self.wallets.get_by_user(user_id)
        if wallet is None:
            raise NotFound("Wallet not found")
        est_fees = self.c.cost_model.leg_costs(req.side, req.exchange, ref_price, req.quantity).charges
        try:
            await self._risk_check(user_id, req, ref_price, est_fees, wallet.available)
        except DomainError as exc:
            order.status = OrderStatus.REJECTED
            order.reject_reason = exc.message[:255]
            await self.orders.add(order)
            metrics.rejected_total += 1
            self._publish(order)
            raise

        if req.side is Side.BUY:
            buffer = MARKET_BUY_BUFFER if req.order_type is OrderType.MARKET else Decimal("1")
            order.blocked_amount = (ref_price * req.quantity * buffer + est_fees).quantize(PAISE)
            await self.wallet_service.block(wallet, order.blocked_amount)
        await self.orders.add(order)

        book_order = BookOrder(
            order.id, Side(req.side), OrderType(req.order_type), req.quantity, price=req.price, user_id=user_id
        )
        result = await self.c.engine.submit(req.symbol, req.exchange, book_order)
        await SettlementService(self.session, self.c.cost_model).settle_fills(result.fills)
        await self._cancel_stp_victims(result.cancelled_ids)

        if not result.resting and order.filled_qty < order.quantity:
            # Market orders are immediate-or-cancel: drop what the book could not fill.
            order.status = OrderStatus.CANCELLED
            order.reject_reason = (
                f"Filled {order.filled_qty}/{order.quantity}; " "unfilled remainder cancelled (not enough depth)"
            )
        if not result.resting:
            self._release_all(wallet, order)

        order.latency_us = int((time.perf_counter() - started) * 1_000_000)
        metrics.record_order(order.latency_us)
        await self.audit.log(
            AuditAction.ORDER,
            user_id=user_id,
            entity="order",
            entity_id=order.id,
            details={
                "symbol": req.symbol,
                "exchange": req.exchange,
                "side": req.side,
                "qty": req.quantity,
                "type": req.order_type,
                "source": ctx.source,
            },
        )
        await self.session.flush()
        self._publish(order)
        return order

    async def cancel(self, user: User, order_id: str) -> Order:
        order = await self.orders.get(order_id)
        if order is None or order.user_id != user.id:
            raise NotFound("Order not found")
        if order.status not in (OrderStatus.NEW, OrderStatus.PARTIAL):
            raise Conflict(f"Order is already {order.status}")
        removed = await self.c.engine.cancel(order.symbol, order.exchange, order.id)
        if removed is None:
            raise Conflict("Order is no longer in the book (it may have just filled)")
        await self._mark_cancelled(order, "Cancelled by user")
        await self.audit.log(AuditAction.ORDER_CANCEL, user_id=user.id, entity="order", entity_id=order.id)
        return order

    # ---------- helpers ----------
    @staticmethod
    def _reference_price(req: PlaceOrderRequest, quote) -> Decimal:
        if req.order_type is OrderType.LIMIT:
            assert req.price is not None
            if req.price % TICK_SIZE != 0:
                raise ValidationFailed(f"Price must be a multiple of the tick size ({TICK_SIZE})")
            low, high = quote.last * (1 - LIMIT_PRICE_BAND), quote.last * (1 + LIMIT_PRICE_BAND)
            if not low <= req.price <= high:
                raise ValidationFailed(f"Limit price outside the allowed band ({low:.2f} - {high:.2f})")
            return req.price
        return quote.ask if req.side is Side.BUY else quote.bid

    async def _risk_check(
        self, user_id: str, req: PlaceOrderRequest, ref_price: Decimal, est_fees: Decimal, available: Decimal
    ) -> None:
        limits = await RiskSettingsRepository(self.session).get_or_create(user_id)
        position = await PositionRepository(self.session).get_for(user_id, req.symbol)
        day_volume, day_pnl = await TradeRepository(self.session).day_stats(user_id, start_of_trading_day())
        ctx = RiskContext(
            side=Side(req.side),
            quantity=req.quantity,
            price=ref_price,
            est_fees=est_fees,
            available_funds=available,
            position_qty=position.quantity if position else 0,
            open_orders=await self.orders.count_open(user_id),
            day_volume=day_volume,
            day_pnl=day_pnl,
            kill_switch=limits.kill_switch,
            max_order_qty=limits.max_order_qty,
            max_order_notional=limits.max_order_notional,
            max_position_value=limits.max_position_value,
            daily_loss_limit=limits.daily_loss_limit,
            daily_volume_cap=limits.daily_volume_cap,
            max_open_orders=limits.max_open_orders,
        )
        self.c.risk_manager.check(ctx)

    def _release_all(self, wallet, order: Order) -> None:
        if order.blocked_amount > 0:
            self.wallet_service.release(wallet, order.blocked_amount)
            order.blocked_amount = Decimal("0")

    async def _mark_cancelled(self, order: Order, reason: str) -> None:
        wallet = await self.wallets.get_by_user(order.user_id)
        order.status = OrderStatus.CANCELLED
        order.reject_reason = reason
        if wallet:
            self._release_all(wallet, order)
        await self.session.flush()
        self._publish(order)

    async def _cancel_stp_victims(self, order_ids: list[str]) -> None:
        for oid in order_ids:
            victim = await self.orders.get(oid)
            if victim:
                await self._mark_cancelled(victim, "Cancelled by self-trade prevention")

    @staticmethod
    def _publish(order: Order) -> None:
        publish_user(
            Topics.ORDER_UPDATE, order.user_id, {"order": OrderOut.model_validate(order).model_dump(mode="json")}
        )
