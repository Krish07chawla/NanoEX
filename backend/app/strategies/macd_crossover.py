from app.indicators import macd
from app.strategies.base import Action, BaseStrategy, Param, Signal, crossed_above, crossed_below
from app.strategies.factory import register


@register
class MACDCrossoverStrategy(BaseStrategy):
    key = "macd_crossover"
    display_name = "MACD Crossover"
    description = "Buy when MACD crosses above its signal line; sell when it crosses below."
    params = {
        "fast": Param(12, 2, 100, "Fast EMA"),
        "slow": Param(26, 3, 200, "Slow EMA"),
        "signal": Param(9, 2, 100, "Signal EMA"),
    }

    def validate(self) -> None:
        if self.p["fast"] >= self.p["slow"]:
            raise ValueError("fast must be shorter than slow")

    def warmup(self) -> int:
        return int(self.p["slow"]) + int(self.p["signal"]) + 1

    def evaluate(self, prices: list[float]) -> Signal:
        line, sig, _ = macd(prices, int(self.p["fast"]), int(self.p["slow"]), int(self.p["signal"]))
        if crossed_above(line[-2], line[-1], sig[-2], sig[-1]):
            return Signal(Action.BUY, f"MACD {line[-1]:.3f} crossed above signal {sig[-1]:.3f}")
        if crossed_below(line[-2], line[-1], sig[-2], sig[-1]):
            return Signal(Action.SELL, f"MACD {line[-1]:.3f} crossed below signal {sig[-1]:.3f}")
        return Signal.hold()
