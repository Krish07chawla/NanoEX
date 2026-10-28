"""Synthetic NSE/BSE feed.

Each stock has ONE "fair value" that follows geometric Brownian motion (GBM).
Each exchange quotes fair value plus its own small mean-reverting basis
(Ornstein-Uhlenbeck), so NSE and BSE stay close like real markets, with
occasional short-lived dislocations that create arbitrage opportunities.
Seeded for reproducibility.
"""

import math
import random
import time
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.core.constants import SYMBOL_UNIVERSE, TICK_SIZE, Exchange
from app.market.providers.base import MarketDataProvider, Quote

TRADING_SECONDS_PER_YEAR = 252 * 6.25 * 3600
BASIS_SIGMA_BPS = 1.5  # typical NSE/BSE basis noise per step
BASIS_MEAN_REVERSION = 0.25  # how fast the basis decays back to 0 each step
DISLOCATION_PROB = 0.004  # chance per symbol per step of a price dislocation
DISLOCATION_BPS_RANGE = (8.0, 35.0)
MAX_SPREAD_TICKS = 3
BASE_VOLUME_RANGE = (100, 5000)


def round_to_tick(value: float) -> Decimal:
    ticks = (Decimal(str(value)) / TICK_SIZE).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(TICK_SIZE, ticks * TICK_SIZE)


@dataclass
class _SymbolState:
    fair: float
    vol: float
    basis_bps: dict[str, float] = field(default_factory=lambda: {e.value: 0.0 for e in Exchange})
    volume: dict[str, int] = field(default_factory=lambda: {e.value: 0 for e in Exchange})


class SyntheticProvider(MarketDataProvider):
    name = "synthetic"

    def __init__(
        self,
        seed: int | None = None,
        step_seconds: float = 0.5,
        universe: dict[str, tuple[float, float]] | None = None,
        dislocation_prob: float = DISLOCATION_PROB,
    ):
        self.rng = random.Random(seed)
        self.step_seconds = step_seconds
        self.dislocation_prob = dislocation_prob
        self._state = {s: _SymbolState(fair=p, vol=v) for s, (p, v) in (universe or SYMBOL_UNIVERSE).items()}

    def symbols(self) -> list[str]:
        return list(self._state)

    async def next_quotes(self) -> list[Quote]:
        return self.step()

    def step(self) -> list[Quote]:
        """Advance every symbol by one time step (synchronous; handy for tests/backtests)."""
        now = time.time()
        dt = self.step_seconds / TRADING_SECONDS_PER_YEAR
        quotes: list[Quote] = []
        for symbol, st in self._state.items():
            z = self.rng.gauss(0.0, 1.0)
            st.fair *= math.exp((-0.5 * st.vol**2) * dt + st.vol * math.sqrt(dt) * z)
            dislocated = self.rng.random() < self.dislocation_prob
            dislocated_ex = self.rng.choice(list(st.basis_bps)) if dislocated else None
            for exchange in st.basis_bps:
                basis = st.basis_bps[exchange]
                basis += -BASIS_MEAN_REVERSION * basis + self.rng.gauss(0.0, BASIS_SIGMA_BPS)
                if exchange == dislocated_ex:
                    basis += self.rng.choice((-1, 1)) * self.rng.uniform(*DISLOCATION_BPS_RANGE)
                st.basis_bps[exchange] = basis
                quotes.append(self._quote(symbol, exchange, st, basis, now))
        return quotes

    def _quote(self, symbol: str, exchange: str, st: _SymbolState, basis_bps: float, ts: float) -> Quote:
        last = round_to_tick(st.fair * (1 + basis_bps / 10_000))
        half_spread = TICK_SIZE * self.rng.randint(1, MAX_SPREAD_TICKS)
        st.volume[exchange] += self.rng.randint(*BASE_VOLUME_RANGE)
        return Quote(
            symbol=symbol,
            exchange=exchange,
            bid=max(TICK_SIZE, last - half_spread),
            ask=last + half_spread,
            last=last,
            volume=st.volume[exchange],
            timestamp=ts,
        )

    def generate_series(self, symbol: str, bars: int, bar_seconds: float = 86400 / 6.25) -> list[float]:
        """Close prices for backtesting: GBM with the symbol's volatility (one bar = one day by default)."""
        price, vol = SYMBOL_UNIVERSE.get(symbol, (1000.0, 0.25))
        dt = bar_seconds / TRADING_SECONDS_PER_YEAR
        drift = 0.08  # mild positive annual drift
        series = []
        for _ in range(bars):
            z = self.rng.gauss(0.0, 1.0)
            price *= math.exp((drift - 0.5 * vol**2) * dt + vol * math.sqrt(dt) * z)
            series.append(round(price, 2))
        return series
