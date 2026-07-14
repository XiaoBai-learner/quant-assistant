"""Tests for research/cross_section.py cross-sectional processing."""
import numpy as np
import pandas as pd
import pytest

from quant_assistant.research.cross_section import (
    CrossSectionProcessor,
    neutralize,
    rank_normalize,
    winsorize,
    zscore,
)


def make_panel(days=3, per_day=30, seed=0):
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2024-01-01", periods=days, freq="B")
    rows = []
    for d in dates:
        for i in range(per_day):
            rows.append({
                "trade_date": d,
                "symbol": f"{i:06d}",
                "f1": rng.normal(3, 5),
                "amount": rng.uniform(1e6, 1e8),
                "industry": ["A", "B", "C"][i % 3],
            })
    return pd.DataFrame(rows)


def test_winsorize_quantile_clips_extremes():
    s = pd.Series([-100.0, 1, 2, 3, 4, 5, 6, 7, 8, 100.0])
    out = winsorize(s, lower=0.1, upper=0.9)
    assert out.min() > -100
    assert out.max() < 100


def test_zscore_produces_zero_mean_unit_std():
    s = pd.Series(np.arange(1, 51, dtype=float))
    out = zscore(s)
    assert abs(out.mean()) < 1e-9
    assert abs(out.std() - 1.0) < 1e-9


def test_zscore_zero_variance_returns_zeros():
    s = pd.Series([5.0, 5.0, 5.0])
    out = zscore(s)
    assert (out == 0.0).all()


def test_rank_normalize_bounds():
    s = pd.Series([10.0, 20.0, 30.0, 40.0])
    out = rank_normalize(s, feature_range=(-1.0, 1.0))
    assert np.isclose(out.min(), -1.0)
    assert np.isclose(out.max(), 1.0)


def test_neutralize_industry_removes_group_mean():
    s = pd.Series([1.0, 2.0, 3.0, 11.0, 12.0, 13.0])
    groups = pd.Series(["A", "A", "A", "B", "B", "B"])
    out = neutralize(s, groups=groups)
    for g in ["A", "B"]:
        assert abs(out[groups == g].mean()) < 1e-9


def test_neutralize_size_removes_log_size_correlation():
    rng = np.random.RandomState(3)
    size = pd.Series(rng.uniform(1e6, 1e8, 50))
    log_size = np.log(size)
    factor = 2.0 * log_size + rng.normal(0, 0.1, 50)  # strongly size-driven
    out = neutralize(factor, size=size)
    corr = np.corrcoef(out, log_size)[0, 1]
    assert abs(corr) < 1e-6


def test_processor_zscore_per_day():
    panel = make_panel()
    out = CrossSectionProcessor().process(panel, ["f1"])
    grouped = out.groupby("trade_date")["f1"]
    assert (grouped.mean().abs() < 1e-9).all()
    assert (grouped.std().round(6) == 1.0).all()


def test_processor_too_few_samples_returns_nan():
    panel = make_panel(days=1, per_day=3)
    out = CrossSectionProcessor(min_samples=5).process(panel, ["f1"])
    assert out["f1"].isna().all()


def test_processor_is_order_independent_across_days():
    panel = make_panel()
    baseline = CrossSectionProcessor().process(panel, ["f1"]).sort_values(["trade_date", "symbol"]).reset_index(drop=True)
    shuffled_panel = panel.sample(frac=1.0, random_state=42).reset_index(drop=True)
    shuffled = CrossSectionProcessor().process(shuffled_panel, ["f1"]).sort_values(["trade_date", "symbol"]).reset_index(drop=True)
    pd.testing.assert_series_equal(baseline["f1"], shuffled["f1"], check_names=False)


def test_processor_missing_industry_warns_and_skips():
    panel = make_panel().drop(columns=["industry"])
    proc = CrossSectionProcessor(neutralize=True)
    with pytest.warns(UserWarning, match="行业列"):
        out = proc.process(panel, ["f1"], industry_col="industry", size_col="amount")
    # still standardized despite skipped industry neutralization
    assert (out.groupby("trade_date")["f1"].std().round(6) == 1.0).all()
