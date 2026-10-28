from app.indicators import ema
from app.strategies.base import Action, BaseStrategy, Param, Signal, crossed_above, crossed_below
from app.strategies.factory import register


@register
class EMACrossoverStrategy(BaseStrategy):
    key = "ema_crossover"
    display_name = "EMA Crossover"
    description = "Buy when the fast EMA crosses above the slow EMA; sell on the opposite cross."
    params = {
        "fast": Param(9, 2, 100, "Fast EMA period"),
        "slow": Param(21, 3, 300, "Slow EMA period"),
    }

    def validate(self) -> None:
        if self.p["fast"] >= self.p["slow"]:
            raise ValueError("fast must be shorter than slow")

    def warmup(self) -> int:
        return int(self.p["slow"]) + 1

    def evaluate(self, prices: list[float]) -> Signal:
        fast, slow = ema(prices, int(self.p["fast"])), ema(prices, int(self.p["slow"]))
        if crossed_above(fast[-2], fast[-1], slow[-2], slow[-1]):
            return Signal(Action.BUY, f"EMA{self.p['fast']} crossed above EMA{self.p['slow']}")
        if crossed_below(fast[-2], fast[-1], slow[-2], slow[-1]):
            return Signal(Action.SELL, f"EMA{self.p['fast']} crossed below EMA{self.p['slow']}")
        return Signal.hold()
