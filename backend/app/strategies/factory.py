"""StrategyFactory: a registry that creates strategies by key (Factory pattern).

New strategies register themselves with @register, so adding one never
requires editing this file (Open/Closed principle).
"""

from typing import Any

from app.strategies.base import BaseStrategy

_REGISTRY: dict[str, type[BaseStrategy]] = {}


def register(cls: type[BaseStrategy]) -> type[BaseStrategy]:
    if cls.key in _REGISTRY:
        raise ValueError(f"Strategy key '{cls.key}' registered twice")
    _REGISTRY[cls.key] = cls
    return cls


class StrategyFactory:
    @staticmethod
    def create(key: str, params: dict[str, Any] | None = None) -> BaseStrategy:
        _load_all()
        try:
            cls = _REGISTRY[key]
        except KeyError as exc:
            raise ValueError(f"Unknown strategy '{key}'. Available: {sorted(_REGISTRY)}") from exc
        return cls(**(params or {}))

    @staticmethod
    def available() -> list[dict]:
        _load_all()
        return [cls.describe() for cls in _REGISTRY.values()]

    @staticmethod
    def keys() -> list[str]:
        _load_all()
        return list(_REGISTRY)


def _load_all() -> None:
    """Import strategy modules so their @register decorators run."""
    from app.strategies import (  # noqa: F401
        bollinger,
        breakout,
        ema_crossover,
        ensemble,
        macd_crossover,
        mean_reversion,
        momentum,
        rsi_reversal,
        zscore,
    )
