from app.indicators import sma
from app.strategies.base import Action, BaseStrategy, Param, Signal
from app.strategies.factory import register


@register
class MeanReversionStrategy(BaseStrategy):
    key = "mean_reversion"
    display_name = "Mean Reversion"
    description = "Buy when price is far below its moving average; sell when far above."
    params = {
        "period": Param(20, 2, 500, "Moving-average period"),
        "deviation_pct": Param(1.0, 0.05, 20, "Distance from the average (%) to act", integer=False),
    }

    def warmup(self) -> int:
        return int(self.p["period"])

    def evaluate(self, prices: list[float]) -> Signal:
        mean = sma(prices, int(self.p["period"]))[-1]
        assert mean is not None
        dev = (prices[-1] / mean - 1) * 100
        if dev <= -self.p["deviation_pct"]:
            return Signal(Action.BUY, f"Price {dev:.2f}% below SMA{self.p['period']}")
        if dev >= self.p["deviation_pct"]:
            return Signal(Action.SELL, f"Price +{dev:.2f}% above SMA{self.p['period']}")
        return Signal.hold()
