from app.strategies.base import Action, BaseStrategy, Param, Signal
from app.strategies.factory import register


@register
class MomentumStrategy(BaseStrategy):
    key = "momentum"
    display_name = "Momentum"
    description = "Buy when the return over the lookback beats a threshold; sell when it falls below -threshold."
    params = {
        "lookback": Param(20, 2, 500, "Bars used to measure the return"),
        "threshold_pct": Param(0.5, 0.01, 20, "Return (%) needed to trigger", integer=False),
    }

    def warmup(self) -> int:
        return int(self.p["lookback"]) + 1

    def evaluate(self, prices: list[float]) -> Signal:
        past = prices[-int(self.p["lookback"]) - 1]
        change = (prices[-1] / past - 1) * 100
        if change >= self.p["threshold_pct"]:
            return Signal(Action.BUY, f"Momentum +{change:.2f}% over {self.p['lookback']} bars")
        if change <= -self.p["threshold_pct"]:
            return Signal(Action.SELL, f"Momentum {change:.2f}% over {self.p['lookback']} bars")
        return Signal.hold()
