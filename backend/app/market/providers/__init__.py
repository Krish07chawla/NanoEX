"""Provider factory: choose the data source by config."""

from app.core.config import Settings
from app.market.providers.base import MarketDataProvider, Quote
from app.market.providers.synthetic import SyntheticProvider


def build_provider(settings: Settings) -> MarketDataProvider:
    if settings.market_provider == "yfinance":
        from app.market.providers.yfinance_provider import YFinanceProvider

        return YFinanceProvider()
    return SyntheticProvider(seed=settings.sim_seed, step_seconds=settings.tick_interval_ms / 1000)


__all__ = ["MarketDataProvider", "Quote", "SyntheticProvider", "build_provider"]
