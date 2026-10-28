import pytest

from app.indicators import bollinger, ema, macd, rsi, sma, zscore


def test_sma_basic():
    assert sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_sma_invalid_period():
    with pytest.raises(ValueError):
        sma([1, 2], 0)


def test_ema_seeded_with_sma():
    out = ema([1, 2, 3, 4], 3)
    assert out[:2] == [None, None]
    assert out[2] == pytest.approx(2.0)
    assert out[3] == pytest.approx(0.5 * 4 + 0.5 * 2.0)


def test_ema_skips_leading_none():
    assert ema([None, 1, 2, 3], 2)[2] == pytest.approx(1.5)


def test_rsi_all_gains_is_100_and_all_losses_is_0():
    assert rsi(list(range(1, 20)), 14)[-1] == 100.0
    assert rsi(list(range(20, 1, -1)), 14)[-1] == pytest.approx(0.0)


def test_rsi_flat_series_is_50():
    assert rsi([5.0] * 20, 14)[-1] == 50.0


def test_rsi_short_series_all_none():
    assert rsi([1, 2, 3], 14) == [None, None, None]


def test_rsi_known_value():
    prices = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
    assert rsi(prices, 14)[14] == pytest.approx(70.53, abs=0.1)  # Wilder's textbook example


def test_macd_lengths_and_sign():
    prices = [float(i) for i in range(1, 60)]
    line, sig, hist = macd(prices)
    assert len(line) == len(sig) == len(hist) == len(prices)
    assert line[-1] > 0 and sig[-1] is not None


def test_macd_fast_must_be_shorter():
    with pytest.raises(ValueError):
        macd([1.0] * 50, fast=26, slow=12)


def test_bollinger_flat_series_has_zero_width():
    mid, up, low = bollinger([10.0] * 25, 20, 2)
    assert mid[-1] == up[-1] == low[-1] == 10.0
    assert mid[0] is None


def test_bollinger_band_ordering():
    mid, up, low = bollinger([1, 3, 2, 5, 4, 6, 5, 8], 4, 2)
    assert low[-1] < mid[-1] < up[-1]


def test_zscore_values():
    z = zscore([1, 2, 3, 4, 5], 5)
    assert z[-1] == pytest.approx(1.4142, abs=1e-3)
    assert zscore([3.0] * 5, 5)[-1] == 0.0
