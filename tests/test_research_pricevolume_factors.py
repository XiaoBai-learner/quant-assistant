"""Tests for the price/volume factor catalog in research/factors.py."""
import numpy as np
import pandas as pd
import pytest

from quant_assistant.research.factors import (
    FactorCalculator,
    pricevolume_factor_definitions,
)


def make_panel(n: int = 200, symbols=("000001", "600000")):
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    rng = np.random.RandomState(7)
    rows = []
    for symbol in symbols:
        price = 100.0
        for i, trade_date in enumerate(dates):
            price *= 1 + rng.normal(0, 0.02)
            rows.append({
                "symbol": symbol,
                "trade_date": trade_date,
                "open": price * 0.99,
                "high": price * 1.02,
                "low": price * 0.98,
                "close": price,
                "volume": 1_000 + i,
                "amount": price * (1_000 + i),
            })
    return pd.DataFrame(rows)


def test_pricevolume_definitions_expose_expected_factors():
    definitions = pricevolume_factor_definitions()
    assert set(definitions) == {
        "reversal_5", "reversal_10", "momentum_120_skip20", "max_ret_20",
        "ret_skew_20", "amihud_illiq_20", "turnover_mean_20", "turnover_cv_20",
        "high_proximity_120", "vol_120",
    }
    for name, definition in definitions.items():
        assert definition.direction in {"positive", "negative"}
        assert definition.min_periods > 0


def test_pricevolume_factors_compute_on_panel():
    calc = FactorCalculator(pricevolume_factor_definitions())
    names = list(pricevolume_factor_definitions())
    out = calc.calculate(make_panel(), names)
    latest = out[out["trade_date"] == out["trade_date"].max()]
    assert set(latest["symbol"]) == {"000001", "600000"}
    for name in names:
        assert latest[name].notna().all(), f"{name} should be defined at the tail"


@pytest.mark.parametrize("name", list(pricevolume_factor_definitions()))
def test_pricevolume_factors_have_no_future_data(name):
    """Value at row k must not change when future rows are removed."""
    panel = make_panel(symbols=("000001",))
    definition = pricevolume_factor_definitions()[name]
    calc = FactorCalculator(pricevolume_factor_definitions())

    full = calc.calculate(panel, [name]).reset_index(drop=True)
    # pick a checkpoint deep enough to have a defined value
    k = 150
    truncated = calc.calculate(panel.iloc[: k + 1], [name]).reset_index(drop=True)

    full_val = full.loc[k, name]
    trunc_val = truncated.loc[k, name]
    assert np.isclose(full_val, trunc_val, equal_nan=True), (
        f"{name} leaks future data at row {k}: {full_val} vs {trunc_val}"
    )


def test_reversal_direction_is_negative_on_rising_series():
    """reversal_5 rises with recent gains but is tagged negative (low = good)."""
    dates = pd.date_range("2023-01-01", periods=30, freq="B")
    rising = pd.DataFrame({
        "symbol": "000001",
        "trade_date": dates,
        "close": np.linspace(100, 130, 30),
        "amount": 1e7,
    })
    calc = FactorCalculator(pricevolume_factor_definitions())
    out = calc.calculate(rising, ["reversal_5"])
    assert out["reversal_5"].dropna().iloc[-1] > 0
    assert pricevolume_factor_definitions()["reversal_5"].direction == "negative"


def test_high_proximity_hits_one_at_new_high():
    dates = pd.date_range("2023-01-01", periods=200, freq="B")
    rising = pd.DataFrame({
        "symbol": "000001",
        "trade_date": dates,
        "close": np.linspace(100, 300, 200),
        "amount": 1e7,
    })
    calc = FactorCalculator(pricevolume_factor_definitions())
    out = calc.calculate(rising, ["high_proximity_120"])
    assert np.isclose(out["high_proximity_120"].dropna().iloc[-1], 1.0)


def test_turnover_prefers_real_turnover_column():
    dates = pd.date_range("2023-01-01", periods=40, freq="B")
    panel = pd.DataFrame({
        "symbol": "000001",
        "trade_date": dates,
        "close": 100.0,
        "amount": 1e7,
        "turnover": np.linspace(1.0, 4.0, 40),
    })
    calc = FactorCalculator(pricevolume_factor_definitions())
    out = calc.calculate(panel, ["turnover_mean_20"])
    # mean of a rising 1..4 sequence over last 20 obs is well above 0
    assert out["turnover_mean_20"].dropna().iloc[-1] > 1.0


def test_missing_dependency_raises():
    panel = pd.DataFrame({
        "symbol": ["000001"] * 30,
        "trade_date": pd.date_range("2023-01-01", periods=30, freq="B"),
        "close": np.linspace(100, 120, 30),
    })
    calc = FactorCalculator(pricevolume_factor_definitions())
    with pytest.raises(ValueError, match="缺少依赖字段"):
        calc.calculate(panel, ["amihud_illiq_20"])
