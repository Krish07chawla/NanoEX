from app.indicators import bollinger
from app.strategies.base import Action, BaseStrategy, Param, Signal
from app.strategies.factory import register


@register
class BollingerStrategy(BaseStrategy):
    key = "bollinger"
    display_name = "Bollinger Bands"
    description = "Buy on a close below the lower band; sell on a close above the upper band."
    params = {
        "period": Param(20, 2, 500, "Band period"),
        "std_dev": Param(2.0, 0.5, 5, "Band width in standard deviations", integer=False),
    }

    def warmup(self) -> int:
        return int(self.p["period"])

    def evaluate(self, prices: list[float]) -> Signal:
        _, upper, lower = bollinger(prices, int(self.p["period"]), float(self.p["std_dev"]))
        price = prices[-1]
        if lower[-1] is not None and price < lower[-1]:
            return Signal(Action.BUY, f"Close {price:.2f} below lower band {lower[-1]:.2f}")
        if upper[-1] is not None and price > upper[-1]:
            return Signal(Action.SELL, f"Close {price:.2f} above upper band {upper[-1]:.2f}")
        return Signal.hold()
