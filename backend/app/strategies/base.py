"""BaseStrategy: the shared interface every trading strategy implements (Strategy pattern).

A strategy receives prices one at a time via `update(price)` and returns a
Signal (BUY / SELL / HOLD) with a human-readable reason. It knows nothing about
orders, money or risk; StrategyTrader and the risk manager handle those.
"""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar

WINDOW_MULTIPLIER = 3  # keep a few times the longest lookback so EMAs settle


class Action(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Signal:
    action: Action
    reason: str = ""

    @classmethod
    def hold(cls, reason: str = "") -> "Signal":
        return cls(Action.HOLD, reason)


@dataclass(frozen=True)
class Param:
    default: float
    minimum: float
    maximum: float
    description: str
    integer: bool = True

    def coerce(self, name: str, value: Any) -> float | int:
        number = float(value)
        if not self.minimum <= number <= self.maximum:
            raise ValueError(f"{name} must be between {self.minimum} and {self.maximum}")
        return int(number) if self.integer else number

    def to_dict(self) -> dict:
        return {
            "default": self.default,
            "min": self.minimum,
            "max": self.maximum,
            "description": self.description,
            "type": "int" if self.integer else "float",
        }


class BaseStrategy(ABC):
    key: ClassVar[str]
    display_name: ClassVar[str]
    description: ClassVar[str]
    params: ClassVar[dict[str, Param]] = {}

    def __init__(self, **overrides: Any):
        unknown = set(overrides) - set(self.params)
        if unknown:
            raise ValueError(f"Unknown parameters for {self.key}: {sorted(unknown)}")
        self.p: dict[str, float | int] = {
            name: spec.coerce(name, overrides.get(name, spec.default)) for name, spec in self.params.items()
        }
        self.validate()
        self.prices: deque[float] = deque(maxlen=max(self.warmup() * WINDOW_MULTIPLIER, 10))

    def validate(self) -> None:  # noqa: B027 - optional hook, intentionally empty
        """Hook for cross-parameter checks (e.g. fast < slow)."""

    @abstractmethod
    def warmup(self) -> int:
        """Number of prices needed before the first signal."""

    @abstractmethod
    def evaluate(self, prices: list[float]) -> Signal:
        """Decide on the latest price given the recent window."""

    def update(self, price: float) -> Signal:
        self.prices.append(float(price))
        if len(self.prices) < self.warmup():
            return Signal.hold("warming up")
        return self.evaluate(list(self.prices))

    @classmethod
    def describe(cls) -> dict:
        return {
            "key": cls.key,
            "name": cls.display_name,
            "description": cls.description,
            "params": {k: v.to_dict() for k, v in cls.params.items()},
        }


def crossed_above(a_prev: float | None, a: float | None, b_prev: float | None, b: float | None) -> bool:
    return None not in (a_prev, a, b_prev, b) and a_prev <= b_prev and a > b  # type: ignore[operator]


def crossed_below(a_prev: float | None, a: float | None, b_prev: float | None, b: float | None) -> bool:
    return None not in (a_prev, a, b_prev, b) and a_prev >= b_prev and a < b  # type: ignore[operator]
