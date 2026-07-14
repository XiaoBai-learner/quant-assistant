"""Characterization tests locking strategy/factors/technical.py numeric output."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quant_assistant.strategy.factors.technical import (
    MAFactor, EMAFactor, MACDFactor, RSIFactor, BOLLFactor, KDJFactor,
    ATRFactor, OBVFactor,
)

GOLDEN = json.loads((Path(__file__).parent / "_golden_strategy_factors.json").read_text())


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


def _s(series) -> float:
    return round(float(np.nansum(pd.to_numeric(series, errors="coerce").values)), 6)


def _approx(actual, key):
    assert actual == pytest.approx(GOLDEN[key], rel=1e-9, abs=1e-6), (
        f"{key} drifted: got {actual}, expected {GOLDEN[key]}"
    )


def test_strategy_technical_factors_match_golden():
    df = make_ohlcv()

    _approx(_s(MAFactor(5).calculate(df).values), "MA5")
    _approx(_s(EMAFactor(12).calculate(df).values), "EMA12")

    macd = MACDFactor().calculate(df)
    _approx(_s(macd.values), "MACD")
    _approx(_s(macd.metadata["DIF"]), "MACD_DIF")
    _approx(_s(macd.metadata["DEA"]), "MACD_DEA")

    _approx(_s(RSIFactor(14).calculate(df).values), "RSI14")

    boll = BOLLFactor().calculate(df)
    _approx(_s(boll.values), "BOLL_band")
    _approx(_s(boll.metadata["upper"]), "BOLL_upper")
    _approx(_s(boll.metadata["lower"]), "BOLL_lower")

    kdj = KDJFactor().calculate(df)
    _approx(_s(kdj.values), "KDJ_J")
    _approx(_s(kdj.metadata["K"]), "KDJ_K")
    _approx(_s(kdj.metadata["D"]), "KDJ_D")

    _approx(_s(ATRFactor(14).calculate(df).values), "ATR14")
    _approx(_s(OBVFactor().calculate(df).values), "OBV")
