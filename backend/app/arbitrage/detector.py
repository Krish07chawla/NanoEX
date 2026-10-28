"""NSE-BSE arbitrage detector.

For a symbol it asks: if I BUY `quantity` on one exchange and SELL the same
quantity on the other right now, walking real book depth, what is the net
profit after every charge? It checks both directions and returns the better one.

    net_profit = (sell_vwap - buy_vwap) * quantity - total_costs
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.arbitrage.cost_model import CostBreakdown, CostModel
from app.core.constants import PAISE, Exchange, Side
from app.market.providers.base import Quote

PCT = Decimal("100")


class Liquidity(Protocol):
    """Anything that can price a sweep of the book (OrderBook implements this)."""

    def sweep_vwap(self, side: Side, quantity: int) -> tuple[Decimal | None, int]: ...


class Confidence:
    HIGH = "HIGH"  # liquid and net profit at least covers costs again
    MEDIUM = "MEDIUM"  # liquid and profitable after costs
    LOW = "LOW"  # not liquid enough or not profitable


@dataclass(frozen=True)
class Opportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: Decimal
    sell_price: Decimal
    quantity: int
    max_qty: int
    costs: CostBreakdown
    liquidity_ok: bool

    @property
    def spread_abs(self) -> Decimal:
        return self.sell_price - self.buy_price

    @property
    def spread_pct(self) -> Decimal:
        return self.spread_abs / self.buy_price * PCT if self.buy_price else Decimal("0")

    @property
    def gross_profit(self) -> Decimal:
        return (self.spread_abs * self.quantity).quantize(PAISE)

    @property
    def net_profit(self) -> Decimal:
        return (self.gross_profit - self.costs.total).quantize(PAISE)

    @property
    def confidence(self) -> str:
        if not self.liquidity_ok or self.net_profit <= 0:
            return Confidence.LOW
        return Confidence.HIGH if self.net_profit >= self.costs.total else Confidence.MEDIUM

    def is_actionable(self, min_profit: Decimal) -> bool:
        return self.liquidity_ok and self.net_profit > max(min_profit, Decimal("0"))

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "buy_exchange": self.buy_exchange,
            "sell_exchange": self.sell_exchange,
            "buy_price": float(round(self.buy_price, 2)),
            "sell_price": float(round(self.sell_price, 2)),
            "spread_abs": float(round(self.spread_abs, 4)),
            "spread_pct": float(round(self.spread_pct, 4)),
            "quantity": self.quantity,
            "max_qty": self.max_qty,
            "gross_profit": float(self.gross_profit),
            "est_costs": float(self.costs.total),
            "cost_breakdown": self.costs.to_dict(),
            "est_net_profit": float(self.net_profit),
            "liquidity_ok": self.liquidity_ok,
            "confidence": self.confidence,
        }


def quote_spread(nse: Quote, bse: Quote) -> dict:
    """Display spread: price_BSE - price_NSE (absolute and %), from last prices."""
    spread = bse.last - nse.last
    return {
        "symbol": nse.symbol,
        "nse_last": float(nse.last),
        "bse_last": float(bse.last),
        "nse_bid": float(nse.bid),
        "nse_ask": float(nse.ask),
        "bse_bid": float(bse.bid),
        "bse_ask": float(bse.ask),
        "spread_abs": float(spread),
        "spread_pct": float(round(spread / nse.last * PCT, 4)) if nse.last else 0.0,
        "timestamp": max(nse.timestamp, bse.timestamp),
    }


class ArbitrageDetector:
    def __init__(self, cost_model: CostModel):
        self.cost_model = cost_model

    def evaluate(self, symbol: str, books: dict[str, Liquidity], quantity: int) -> Opportunity | None:
        """Best of (buy NSE / sell BSE) and (buy BSE / sell NSE). None if either book is empty."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        candidates = []
        for buy_ex, sell_ex in ((Exchange.NSE.value, Exchange.BSE.value), (Exchange.BSE.value, Exchange.NSE.value)):
            opp = self._direction(symbol, books[buy_ex], buy_ex, books[sell_ex], sell_ex, quantity)
            if opp is not None:
                candidates.append(opp)
        return max(candidates, key=lambda o: o.net_profit, default=None)

    def _direction(
        self, symbol: str, buy_book: Liquidity, buy_ex: str, sell_book: Liquidity, sell_ex: str, quantity: int
    ) -> Opportunity | None:
        buy_vwap, buy_fillable = buy_book.sweep_vwap(Side.BUY, quantity)
        sell_vwap, sell_fillable = sell_book.sweep_vwap(Side.SELL, quantity)
        if buy_vwap is None or sell_vwap is None:
            return None
        max_qty = min(buy_fillable, sell_fillable)
        costs = self.cost_model.round_trip(buy_ex, buy_vwap, sell_ex, sell_vwap, quantity)
        return Opportunity(
            symbol, buy_ex, sell_ex, buy_vwap, sell_vwap, quantity, max_qty, costs, liquidity_ok=max_qty >= quantity
        )
