"""Price data for backtests: seeded synthetic GBM or (optional) yfinance daily history."""

from app.core.constants import SYMBOL_UNIVERSE
from app.core.exceptions import MarketUnavailable, ValidationFailed
from app.market.providers.synthetic import SyntheticProvider


def load_prices(symbol: str, bars: int, source: str = "synthetic", seed: int | None = None) -> list[float]:
    if symbol not in SYMBOL_UNIVERSE:
        raise ValidationFailed(f"Unknown symbol {symbol}")
    if source == "synthetic":
        return SyntheticProvider(seed=seed).generate_series(symbol, bars)
    if source == "yfinance":
        return _yfinance_daily(symbol, bars)
    raise ValidationFailed("data_source must be 'synthetic' or 'yfinance'")


def _yfinance_daily(symbol: str, bars: int) -> list[float]:  # pragma: no cover - network
    try:
        import yfinance as yf
    except ImportError as exc:
        raise MarketUnavailable("yfinance not installed") from exc
    years = max(1, bars // 250 + 1)
    frame = yf.Ticker(f"{symbol}.NS").history(period=f"{years}y", interval="1d")
    closes = [round(float(x), 2) for x in frame["Close"].dropna().tolist()]
    if len(closes) < 30:
        raise MarketUnavailable("Not enough historical data returned by yfinance")
    return closes[-bars:]
