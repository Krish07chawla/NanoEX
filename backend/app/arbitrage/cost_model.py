"""Indian equity (intraday) transaction cost model.

Rates are illustrative values close to typical discount-broker intraday charges
and are all configurable through ChargeSchedule. Used for every simulated
trade, for the backtester and for arbitrage profit estimates.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.constants import PAISE, Exchange, Side

BPS = Decimal("0.0001")


@dataclass(frozen=True)
class ChargeSchedule:
    brokerage_flat: Decimal = Decimal("20")  # Rs per executed order, capped ...
    brokerage_pct: Decimal = Decimal("0.0003")  # ... at 0.03% of turnover, whichever is lower
    stt_sell_pct: Decimal = Decimal("0.00025")  # STT intraday: 0.025% on the sell side
    exchange_txn_pct: dict[str, Decimal] = field(
        default_factory=lambda: {
            Exchange.NSE.value: Decimal("0.0000297"),  # NSE transaction charge
            Exchange.BSE.value: Decimal("0.0000375"),  # BSE transaction charge
        }
    )
    sebi_pct: Decimal = Decimal("0.000001")  # Rs 10 per crore
    gst_pct: Decimal = Decimal("0.18")  # on brokerage + exchange + SEBI
    stamp_buy_pct: Decimal = Decimal("0.00003")  # stamp duty intraday: 0.003% on buy side
    slippage_bps: Decimal = Decimal("1")  # estimate only; real fills slip naturally


@dataclass(frozen=True)
class CostBreakdown:
    brokerage: Decimal
    stt: Decimal
    exchange_txn: Decimal
    sebi: Decimal
    gst: Decimal
    stamp: Decimal
    slippage: Decimal = Decimal("0")

    @property
    def charges(self) -> Decimal:
        """Statutory + broker charges (what actually gets debited as fees)."""
        return self.brokerage + self.stt + self.exchange_txn + self.sebi + self.gst + self.stamp

    @property
    def total(self) -> Decimal:
        return self.charges + self.slippage

    def __add__(self, other: "CostBreakdown") -> "CostBreakdown":
        return CostBreakdown(
            *(
                getattr(self, f) + getattr(other, f)
                for f in ("brokerage", "stt", "exchange_txn", "sebi", "gst", "stamp", "slippage")
            )
        )

    def to_dict(self) -> dict[str, float]:
        d = {
            k: float(getattr(self, k)) for k in ("brokerage", "stt", "exchange_txn", "sebi", "gst", "stamp", "slippage")
        }
        d["total"] = float(self.total)
        return d


ZERO_COST = CostBreakdown(*(Decimal("0"),) * 7)


class CostModel:
    def __init__(self, schedule: ChargeSchedule | None = None):
        self.schedule = schedule or ChargeSchedule()

    def leg_costs(
        self, side: Side | str, exchange: Exchange | str, price: Decimal, quantity: int, include_slippage: bool = False
    ) -> CostBreakdown:
        """Charges for one executed order (one leg)."""
        if quantity <= 0 or price <= 0:
            return ZERO_COST
        s = self.schedule
        side = Side(side)
        turnover = Decimal(price) * quantity
        brokerage = min(s.brokerage_flat, turnover * s.brokerage_pct)
        stt = turnover * s.stt_sell_pct if side is Side.SELL else Decimal("0")
        exch = turnover * s.exchange_txn_pct[Exchange(exchange).value]
        sebi = turnover * s.sebi_pct
        gst = (brokerage + exch + sebi) * s.gst_pct
        stamp = turnover * s.stamp_buy_pct if side is Side.BUY else Decimal("0")
        slippage = turnover * s.slippage_bps * BPS if include_slippage else Decimal("0")
        q = lambda v: v.quantize(PAISE)  # noqa: E731
        return CostBreakdown(q(brokerage), q(stt), q(exch), q(sebi), q(gst), q(stamp), q(slippage))

    def round_trip(
        self,
        buy_exchange: str,
        buy_price: Decimal,
        sell_exchange: str,
        sell_price: Decimal,
        quantity: int,
        include_slippage: bool = True,
    ) -> CostBreakdown:
        """Both legs of an arbitrage (or a buy-then-sell round trip)."""
        return self.leg_costs(Side.BUY, buy_exchange, buy_price, quantity, include_slippage) + self.leg_costs(
            Side.SELL, sell_exchange, sell_price, quantity, include_slippage
        )
