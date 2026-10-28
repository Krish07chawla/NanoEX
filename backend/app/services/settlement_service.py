"""Turns engine fills into persisted trades, position changes and wallet entries.

Used both for immediate fills (OrderService) and fills that happen later when
the simulated market maker re-quotes against resting limit orders.
"""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.arbitrage.cost_model import CostModel
from app.core.constants import PAISE, PRICE_PRECISION, AuditAction, OrderStatus, OrderType, Side
from app.core.event_bus import Topics
from app.core.events import publish_user
from app.core.metrics import metrics
from app.engine.order import Fill
from app.models.order import Order
from app.models.trade import Trade
from app.repositories.order_repo import OrderRepository, TradeRepository
from app.repositories.position_repo import PositionRepository
from app.repositories.wallet_repo import WalletRepository
from app.schemas.order import OrderOut, TradeOut
from app.services.audit_service import AuditService
from app.services.position_math import apply_fill
from app.services.wallet_service import WalletService


class SettlementService:
    def __init__(self, session: AsyncSession, cost_model: CostModel):
        self.session = session
        self.cost_model = cost_model
        self.orders = OrderRepository(session)
        self.trades = TradeRepository(session)
        self.positions = PositionRepository(session)
        self.wallets = WalletRepository(session)
        self.wallet_service = WalletService(session)
        self.audit = AuditService(session)

    async def settle_fills(self, fills: list[Fill]) -> list[Trade]:
        trades: list[Trade] = []
        for fill in fills:
            if fill.taker_user_id:
                trades.append(await self._settle_side(fill.taker_order_id, fill.taker_side, fill))
            if fill.maker_user_id:
                trades.append(await self._settle_side(fill.maker_order_id, fill.taker_side.opposite, fill))
        return [t for t in trades if t is not None]

    async def _settle_side(self, order_id: str, side: Side, fill: Fill) -> Trade | None:
        order = await self.orders.get(order_id)
        if order is None:
            return None
        price, qty = fill.price, fill.quantity
        fees = self.cost_model.leg_costs(side, fill.exchange, price, qty).charges

        position = await self.positions.get_or_create(order.user_id, order.symbol)
        position.quantity, position.avg_price, realized = apply_fill(
            position.quantity, position.avg_price, side, price, qty
        )
        position.avg_price = position.avg_price.quantize(PRICE_PRECISION)
        realized = realized.quantize(PAISE)
        position.realized_pnl += realized

        trade = await self.trades.add(
            Trade(
                order_id=order.id,
                user_id=order.user_id,
                symbol=order.symbol,
                exchange=fill.exchange,
                side=side,
                price=price,
                quantity=qty,
                fees=fees,
                realized_pnl=realized,
                source=order.source,
                strategy_name=order.strategy_name,
                signal_reason=order.signal_reason,
            )
        )

        wallet = await self.wallets.get_by_user(order.user_id)
        assert wallet is not None
        remaining_before = order.quantity - order.filled_qty
        if order.blocked_amount > 0 and remaining_before > 0:
            release = (order.blocked_amount * qty / remaining_before).quantize(PAISE)
            if qty == remaining_before:
                release = order.blocked_amount
            order.blocked_amount -= release
            self.wallet_service.release(wallet, release)
        cash_delta = -(price * qty) if side is Side.BUY else price * qty
        await self.wallet_service.apply_trade(
            wallet, cash_delta.quantize(PAISE), fees, trade.id, f"{side} {qty} {order.symbol}@{price} {fill.exchange}"
        )

        self._update_order(order, price, qty)
        await self.audit.log(
            AuditAction.TRADE,
            user_id=order.user_id,
            entity="trade",
            entity_id=trade.id,
            details={"symbol": order.symbol, "side": side, "qty": qty, "price": str(price)},
        )
        metrics.trades_total += 1
        publish_user(Topics.TRADE, order.user_id, {"trade": TradeOut.model_validate(trade).model_dump(mode="json")})
        publish_user(
            Topics.ORDER_UPDATE, order.user_id, {"order": OrderOut.model_validate(order).model_dump(mode="json")}
        )
        return trade

    @staticmethod
    def _update_order(order: Order, price: Decimal, qty: int) -> None:
        prev_value = (order.avg_fill_price or Decimal("0")) * order.filled_qty
        order.filled_qty += qty
        order.avg_fill_price = ((prev_value + price * qty) / order.filled_qty).quantize(PRICE_PRECISION)
        if order.filled_qty >= order.quantity:
            order.status = OrderStatus.FILLED
        elif order.order_type is OrderType.LIMIT:
            order.status = OrderStatus.PARTIAL
