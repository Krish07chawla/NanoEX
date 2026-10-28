from app.indicators import rsi
from app.strategies.base import Action, BaseStrategy, Param, Signal
from app.strategies.factory import register


@register
class RSIReversalStrategy(BaseStrategy):
    key = "rsi_reversal"
    display_name = "RSI Reversal"
    description = "Buy when RSI is oversold; sell when RSI is overbought."
    params = {
        "period": Param(14, 2, 100, "RSI period"),
        "oversold": Param(30, 1, 50, "Buy below this RSI"),
        "overbought": Param(70, 50, 99, "Sell above this RSI"),
    }

    def validate(self) -> None:
        if self.p["oversold"] >= self.p["overbought"]:
            raise ValueError("oversold must be below overbought")

    def warmup(self) -> int:
        return int(self.p["period"]) + 1

    def evaluate(self, prices: list[float]) -> Signal:
        value = rsi(prices, int(self.p["period"]))[-1]
        if value is None:
            return Signal.hold()
        if value < self.p["oversold"]:
            return Signal(Action.BUY, f"RSI {value:.1f} < {self.p['oversold']} (oversold)")
        if value > self.p["overbought"]:
            return Signal(Action.SELL, f"RSI {value:.1f} > {self.p['overbought']} (overbought)")
        return Signal.hold()
