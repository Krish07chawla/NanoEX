from app.indicators import zscore
from app.strategies.base import Action, BaseStrategy, Param, Signal
from app.strategies.factory import register


@register
class ZScoreStrategy(BaseStrategy):
    key = "zscore"
    display_name = "Z-Score"
    description = "Buy when price is unusually low versus its rolling mean (z < -entry); sell when unusually high."
    params = {
        "period": Param(20, 3, 500, "Rolling window"),
        "entry_z": Param(2.0, 0.5, 5, "Z-score threshold", integer=False),
    }

    def warmup(self) -> int:
        return int(self.p["period"])

    def evaluate(self, prices: list[float]) -> Signal:
        z = zscore(prices, int(self.p["period"]))[-1]
        if z is None:
            return Signal.hold()
        if z <= -self.p["entry_z"]:
            return Signal(Action.BUY, f"Z-score {z:.2f} <= -{self.p['entry_z']}")
        if z >= self.p["entry_z"]:
            return Signal(Action.SELL, f"Z-score {z:.2f} >= {self.p['entry_z']}")
        return Signal.hold()
