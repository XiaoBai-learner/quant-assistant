"""Characterization tests locking the numeric output of the factor engines.

These guard the indicators refactor: V1/V2 engines must keep producing the
exact same values after delegating their math to factors.indicators. Each
assertion compares the column-wise nansum against a frozen golden snapshot
captured before the refactor.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quant_assistant.factors.engine import FactorEngine
from quant_assistant.factors.engine_v2 import FactorEngineV2, TimeGranularity

GOLDEN = json.loads((Path(__file__).parent / "_golden_factors.json").read_text())


def make_ohlcv(n: int = 80) -> pd.DataFrame:
    rng = np.random.RandomState(42)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.1, 2, n)
    low = close - rng.uniform(0.1, 2, n)
    openp = close + rng.uniform(-1, 1, n)
    vol = rng.uniform(1e5, 1e6, n)
    return pd.DataFrame(
        {"open": openp, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


def _signature(frame: pd.DataFrame, base: set) -> dict:
    out = {}
    for col in frame.columns:
        if col in base:
            continue
        series = pd.to_numeric(frame[col], errors="coerce")
        out[col] = round(float(np.nansum(series.values)), 6)
    return out


def _assert_matches(actual: dict, expected: dict, label: str):
    assert set(actual) == set(expected), (
        f"{label}: column set changed. "
        f"missing={set(expected) - set(actual)} extra={set(actual) - set(expected)}"
    )
    for col, exp in expected.items():
        assert actual[col] == pytest.approx(exp, rel=1e-9, abs=1e-6), (
            f"{label}: column '{col}' drifted: got {actual[col]}, expected {exp}"
        )


def test_compute_all_matches_golden():
    df = make_ohlcv()
    base = set(df.columns)
    result = _signature(FactorEngine().compute_all(df), base)
    _assert_matches(result, GOLDEN["compute_all"], "compute_all")


def test_compute_all_factors_matches_golden():
    df = make_ohlcv()
    base = set(df.columns)
    result = _signature(FactorEngine().compute_all_factors(df), base)
    _assert_matches(result, GOLDEN["compute_all_factors"], "compute_all_factors")


def test_v2_daily_matches_golden():
    df = make_ohlcv()
    base = set(df.columns)
    result = _signature(
        FactorEngineV2().compute_factors(df, granularity=TimeGranularity.DAILY), base
    )
    _assert_matches(result, GOLDEN["v2_daily"], "v2_daily")
