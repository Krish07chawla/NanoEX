from app.strategies.base import Action, BaseStrategy, Param, Signal
from app.strategies.factory import register

MEMBERS = ("rsi_reversal", "bollinger", "ema_crossover", "macd_crossover", "zscore")


@register
class EnsembleVoteStrategy(BaseStrategy):
    key = "ensemble"
    display_name = "Ensemble Vote"
    description = "Runs RSI, Bollinger, EMA, MACD and Z-score together and acts when enough of them agree."
    params = {"min_votes": Param(2, 1, len(MEMBERS), "Votes needed to act")}

    def __init__(self, **overrides):
        super().__init__(**overrides)
        from app.strategies.factory import StrategyFactory

        self.members = [StrategyFactory.create(key) for key in MEMBERS]

    def warmup(self) -> int:
        return 1  # each member handles its own warm-up

    def update(self, price: float) -> Signal:
        signals = [(m.display_name, m.update(price)) for m in self.members]
        return self._vote(signals)

    def evaluate(self, prices: list[float]) -> Signal:  # pragma: no cover - update() is overridden
        return Signal.hold()

    def _vote(self, signals: list[tuple[str, Signal]]) -> Signal:
        need = int(self.p["min_votes"])
        buys = [n for n, s in signals if s.action is Action.BUY]
        sells = [n for n, s in signals if s.action is Action.SELL]
        if len(buys) >= need and len(buys) > len(sells):
            return Signal(Action.BUY, f"{len(buys)}/{len(signals)} vote BUY: {', '.join(buys)}")
        if len(sells) >= need and len(sells) > len(buys):
            return Signal(Action.SELL, f"{len(sells)}/{len(signals)} vote SELL: {', '.join(sells)}")
        return Signal.hold()
