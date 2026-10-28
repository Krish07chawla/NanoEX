"""Helpers to publish user-scoped events on the global bus without importing the container."""

from typing import Any

from app.core.event_bus import EventBus, Topics

_bus: EventBus | None = None


def set_bus(bus: EventBus) -> None:
    global _bus
    _bus = bus


def get_bus() -> EventBus | None:
    return _bus


def publish_user(topic: str, user_id: str, data: Any) -> None:
    if _bus is not None:
        _bus.publish(topic, {"user_id": user_id, **({"payload": data} if not isinstance(data, dict) else data)})


def publish_wallet(user_id: str, wallet: dict) -> None:
    publish_user(Topics.WALLET, user_id, {"wallet": wallet})
