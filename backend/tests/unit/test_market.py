from decimal import Decimal as D

from app.core.constants import TICK_SIZE
from app.core.event_bus import EventBus
from app.market.providers.synthetic import SyntheticProvider, round_to_tick


def test_round_to_tick():
    assert round_to_tick(100.02) == D("100.00")
    assert round_to_tick(100.03) == D("100.05")
    assert round_to_tick(0.0001) == TICK_SIZE


def test_synthetic_is_reproducible_and_on_ticks():
    a, b = SyntheticProvider(seed=9), SyntheticProvider(seed=9)
    qa, qb = a.step(), b.step()
    assert [q.last for q in qa] == [q.last for q in qb]
    for q in qa:
        assert q.last % TICK_SIZE == 0 and q.bid < q.ask


def test_nse_and_bse_stay_close():
    p = SyntheticProvider(seed=1, dislocation_prob=0)
    for _ in range(200):
        quotes = p.step()
    by = {(q.symbol, q.exchange): q.last for q in quotes}
    for symbol in p.symbols():
        nse, bse = by[(symbol, "NSE")], by[(symbol, "BSE")]
        assert abs(bse - nse) / nse < D("0.002")  # within 20 bps without dislocations


def test_event_bus_fan_out_and_drop_oldest():
    bus = EventBus()
    q1, q2 = bus.subscribe("t"), bus.subscribe("t", "u")
    bus.publish("t", 1)
    bus.publish("u", 2)
    assert q1.qsize() == 1 and q2.qsize() == 2
    bus.unsubscribe(q1)
    assert bus.subscriber_count("t") == 1


def test_production_requires_strong_jwt_secret():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret_key="short", _env_file=None)
    assert Settings(environment="production", jwt_secret_key="x" * 40, _env_file=None).jwt_secret_key == "x" * 40
