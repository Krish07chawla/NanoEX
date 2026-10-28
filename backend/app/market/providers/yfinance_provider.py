"""Optional delayed real-data provider via yfinance (Adapter).

Uses Yahoo tickers RELIANCE.NS (NSE) and RELIANCE.BO (BSE). Data is delayed
(~15 min) and polled, so it is for demonstration only. yfinance is an optional
dependency: install requirements-dev.txt to use it.
"""

import asyncio
import time
from decimal import Decimal

from app.core.constants import SYMBOL_UNIVERSE, TICK_SIZE, Exchange
from app.core.exceptions import MarketUnavailable
from app.market.providers.base import MarketDataProvider, Quote

SUFFIX = {Exchange.NSE: ".NS", Exchange.BSE: ".BO"}
POLL_SECONDS = 15


class YFinanceProvider(MarketDataProvider):
    name = "yfinance"

    def __init__(self, symbols: list[str] | None = None):
        try:
            import yfinance  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise MarketUnavailable("yfinance not installed; pip install yfinance") from exc
        self._symbols = symbols or list(SYMBOL_UNIVERSE)
        self._cache: list[Quote] = []
        self._fetched_at = 0.0

    def symbols(self) -> list[str]:
        return self._symbols

    async def next_quotes(self) -> list[Quote]:
        if time.time() - self._fetched_at >= POLL_SECONDS or not self._cache:
            self._cache = await asyncio.to_thread(self._fetch)
            self._fetched_at = time.time()
        return self._cache

    def _fetch(self) -> list[Quote]:
        import yfinance as yf

        tickers = [s + SUFFIX[e] for s in self._symbols for e in Exchange]
        data = yf.download(tickers, period="1d", interval="1m", progress=False, group_by="ticker")
        now = time.time()
        quotes = []
        for symbol in self._symbols:
            for exchange in Exchange:
                try:
                    frame = data[symbol + SUFFIX[exchange]].dropna()
                    last = Decimal(str(round(float(frame["Close"].iloc[-1]), 2)))
                    volume = int(frame["Volume"].sum())
                except (KeyError, IndexError):
                    continue
                quotes.append(Quote(symbol, exchange.value, last - TICK_SIZE, last + TICK_SIZE, last, volume, now))
        return quotes
