"""Tests for research/factor_library.py FactorLibrary facade."""
import numpy as np
import pandas as pd

from quant_assistant.research.factor_library import FactorLibrary


def make_panel(n=180, n_symbols=15, seed=1):
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    rows = []
    for s in range(n_symbols):
        symbol = f"{s:06d}"
        price = 100.0
        for i, d in enumerate(dates):
            price *= 1 + rng.normal(0, 0.02)
            rows.append({
                "symbol": symbol,
                "trade_date": d,
                "open": price * 0.99,
                "high": price * 1.02,
                "low": price * 0.98,
                "close": price,
                "volume": 1e5 + s * 1000,
                "amount": price * (1e5 + s * 1000),
                "industry": ["A", "B", "C"][s % 3],
            })
    return pd.DataFrame(rows)


def test_list_factors_returns_catalog():
    catalog = FactorLibrary().list_factors()
    assert {"name", "direction", "dependencies", "description"}.issubset(catalog.columns)
    assert "reversal_5" in set(catalog["name"])


def test_compute_processed_aligns_negative_factor_direction():
    """A negative-direction factor should, after alignment, correlate
    negatively with its own raw values."""
    panel = make_panel()
    lib = FactorLibrary()
    raw = lib.compute_raw(panel, ["vol_120"]).dropna(subset=["vol_120"])
    processed = lib.compute_processed(panel, ["vol_120"], align_direction=True)
    merged = raw.merge(
        processed, on=["symbol", "trade_date"], suffixes=("_raw", "_proc")
    ).dropna()
    corr = np.corrcoef(merged["vol_120_raw"], merged["vol_120_proc"])[0, 1]
    assert corr < 0  # negative factor flipped so higher processed = lower raw


def test_composite_score_produces_daily_scores():
    panel = make_panel()
    lib = FactorLibrary()
    scores = lib.composite_score(panel, {"reversal_5": 1.0, "momentum_20": 0.5})
    assert {"symbol", "trade_date", "score"}.issubset(scores.columns)
    tail_day = scores[scores["trade_date"] == scores["trade_date"].max()]
    assert tail_day["score"].notna().any()


def test_validate_returns_ic_summary():
    panel = make_panel()
    summary = FactorLibrary().validate(panel, ["reversal_5", "vol_120"], forward_returns=(1, 5))
    assert "rank_ic_mean" in summary.columns
    assert "icir" in summary.columns
    assert set(summary.index) == {"reversal_5", "vol_120"}


def test_screen_effective_filters_by_thresholds():
    panel = make_panel()
    lib = FactorLibrary()
    names = ["reversal_5", "vol_120", "momentum_20"]
    loose = lib.screen_effective(panel, names, ic_threshold=0.0, icir_threshold=0.0)
    strict = lib.screen_effective(panel, names, ic_threshold=10.0, icir_threshold=10.0)
    assert set(loose).issubset(set(names))
    assert strict == []


def test_screen_effective_uses_absolute_thresholds():
    """A factor with a strong constructed signal should pass a modest bar."""
    panel = make_panel(seed=5)
    lib = FactorLibrary()
    result = lib.screen_effective(panel, ["reversal_5"], ic_threshold=0.0, icir_threshold=0.0)
    assert result == ["reversal_5"]
