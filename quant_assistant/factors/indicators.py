"""Canonical technical-indicator math.

Single source of truth for the core indicators that were previously
re-implemented in ``factors/engine.py`` (V1), ``factors/engine_v2.py`` (V2)
and ``strategy/factors/technical.py``.

Every function is a pure ``pd.Series/pd.DataFrame -> ...`` transform and takes
an explicit ``min_periods`` where the historical call sites disagreed, so each
caller keeps its exact numeric behavior:

- V1 method-level, V2, strategy: ``min_periods=1`` (values emitted immediately)
- V1 ``compute_all_factors`` batch: ``min_periods=window`` for atr/volatility/
  cci/williams_r/mfi (NaN until the window fills)

MACD returns raw dif/dea/hist; the strategy layer applies its own ``2*(dif-dea)``
scaling on top.
"""
from typing import Dict, Optional

import numpy as np
import pandas as pd


def ma(series: pd.Series, window: int, min_periods: Optional[int] = 1) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=window, min_periods=min_periods).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """Exponential moving average (adjust=False, matching all legacy callers)."""
    return series.ewm(span=window, adjust=False).mean()


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Dict[str, pd.Series]:
    """MACD components. Returns dif (macd line), dea (signal), hist."""
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    hist = dif - dea
    return {"macd": dif, "signal": dea, "histogram": hist}


def rsi(series: pd.Series, window: int, min_periods: Optional[int] = 1) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=window, min_periods=min_periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=min_periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def kdj(
    data: pd.DataFrame,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
    min_periods: Optional[int] = 1,
) -> Dict[str, pd.Series]:
    """KDJ stochastic. K=EMA(RSV, alpha=1/m1), D=EMA(K, alpha=1/m2), J=3K-2D.

    ``ewm(alpha=1/m)`` equals the legacy ``ewm(com=m-1)`` forms.
    """
    low_list = data["low"].rolling(window=n, min_periods=min_periods).min()
    high_list = data["high"].rolling(window=n, min_periods=min_periods).max()
    rsv = (data["close"] - low_list) / (high_list - low_list) * 100
    k = rsv.ewm(alpha=1 / m1, adjust=False).mean()
    d = k.ewm(alpha=1 / m2, adjust=False).mean()
    j = 3 * k - 2 * d
    return {"k": k, "d": d, "j": j}


def bollinger(
    series: pd.Series,
    window: int = 20,
    std: float = 2.0,
    min_periods: Optional[int] = 1,
) -> Dict[str, pd.Series]:
    """Bollinger Bands."""
    middle = series.rolling(window=window, min_periods=min_periods).mean()
    rolling_std = series.rolling(window=window, min_periods=min_periods).std()
    upper = middle + rolling_std * std
    lower = middle - rolling_std * std
    return {"upper": upper, "middle": middle, "lower": lower}


def true_range(data: pd.DataFrame) -> pd.Series:
    """True Range: max(high-low, |high-prev_close|, |low-prev_close|)."""
    high_low = data["high"] - data["low"]
    high_close = np.abs(data["high"] - data["close"].shift())
    low_close = np.abs(data["low"] - data["close"].shift())
    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)


def atr(data: pd.DataFrame, window: int = 14, min_periods: Optional[int] = None) -> pd.Series:
    """Average True Range. ``min_periods`` defaults to ``window`` (V1 batch)."""
    return true_range(data).rolling(window=window, min_periods=min_periods).mean()


def cci(data: pd.DataFrame, window: int = 20, min_periods: Optional[int] = None) -> pd.Series:
    """Commodity Channel Index."""
    tp = (data["high"] + data["low"] + data["close"]) / 3
    ma_tp = tp.rolling(window=window, min_periods=min_periods).mean()
    md_tp = tp.rolling(window=window, min_periods=min_periods).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    return (tp - ma_tp) / (0.015 * md_tp)


def williams_r(data: pd.DataFrame, window: int = 14, min_periods: Optional[int] = None) -> pd.Series:
    """Williams %R."""
    highest_high = data["high"].rolling(window=window, min_periods=min_periods).max()
    lowest_low = data["low"].rolling(window=window, min_periods=min_periods).min()
    return -100 * (highest_high - data["close"]) / (highest_high - lowest_low)


def mfi(
    data: pd.DataFrame,
    window: int = 14,
    min_periods: Optional[int] = None,
    eps: float = 0.0,
) -> pd.Series:
    """Money Flow Index. ``eps`` guards divide-by-zero (V2 uses 1e-10)."""
    typical_price = (data["high"] + data["low"] + data["close"]) / 3
    raw_money_flow = typical_price * data["volume"]
    money_flow = raw_money_flow.where(typical_price > typical_price.shift(), -raw_money_flow)
    positive_flow = money_flow.where(money_flow > 0, 0).rolling(window=window, min_periods=min_periods).sum()
    negative_flow = np.abs(money_flow.where(money_flow < 0, 0)).rolling(window=window, min_periods=min_periods).sum()
    money_ratio = positive_flow / (negative_flow + eps)
    return 100 - (100 / (1 + money_ratio))


def obv(data: pd.DataFrame) -> pd.Series:
    """On-Balance Volume (vectorized). First bar contributes 0."""
    return (np.sign(data["close"].diff()) * data["volume"]).cumsum()
