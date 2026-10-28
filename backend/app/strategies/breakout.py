from app.strategies.base import Action, BaseStrategy, Param, Signal
from app.strategies.factory import register


@register
class BreakoutStrategy(BaseStrategy):
    key = "breakout"
    display_name = "Breakout"
    description = "Buy when price breaks above the recent high; sell when it breaks below the recent low."
    params = {"lookback": Param(20, 2, 500, "Bars that define the range")}

    def warmup(self) -> int:
        return int(self.p["lookback"]) + 1

    def evaluate(self, prices: list[float]) -> Signal:
        window = prices[-int(self.p["lookback"]) - 1 : -1]
        high, low, price = max(window), min(window), prices[-1]
        if price > high:
            return Signal(Action.BUY, f"Breakout above {self.p['lookback']}-bar high {high:.2f}")
        if price < low:
            return Signal(Action.SELL, f"Breakdown below {self.p['lookback']}-bar low {low:.2f}")
        return Signal.hold()
