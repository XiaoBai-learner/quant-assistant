"""Factor definitions and calculation for stock-pool selection research."""
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List

import numpy as np
import pandas as pd

FactorFunction = Callable[[pd.DataFrame], pd.Series]


@dataclass
class FactorDefinition:
    """Metadata and compute function for one factor."""

    name: str
    direction: str
    min_periods: int
    dependencies: List[str]
    compute: FactorFunction
    description: str = ""

    def __post_init__(self) -> None:
        if self.direction not in {"positive", "negative"}:
            raise ValueError("direction 必须是 positive 或 negative")
        if self.min_periods <= 0:
            raise ValueError("min_periods 必须大于 0")


def _return_1d(df: pd.DataFrame) -> pd.Series:
    return df["close"].pct_change()


def _momentum(window: int) -> FactorFunction:
    def compute(df: pd.DataFrame) -> pd.Series:
        return df["close"] / df["close"].shift(window) - 1

    return compute


def _ma_position(window: int) -> FactorFunction:
    def compute(df: pd.DataFrame) -> pd.Series:
        ma = df["close"].rolling(window, min_periods=window).mean()
        return df["close"] / ma - 1

    return compute


def _volatility(window: int) -> FactorFunction:
    def compute(df: pd.DataFrame) -> pd.Series:
        return _return_1d(df).rolling(window, min_periods=window).std()

    return compute


def _turnover_amount(window: int) -> FactorFunction:
    def compute(df: pd.DataFrame) -> pd.Series:
        return df["amount"].rolling(window, min_periods=window).mean()

    return compute


def _drawdown(window: int) -> FactorFunction:
    def compute(df: pd.DataFrame) -> pd.Series:
        rolling_max = df["close"].rolling(window, min_periods=window).max()
        return df["close"] / rolling_max - 1

    return compute


def _atr_ratio(window: int) -> FactorFunction:
    def compute(df: pd.DataFrame) -> pd.Series:
        prev_close = df["close"].shift(1)
        ranges = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - prev_close).abs(),
                (df["low"] - prev_close).abs(),
            ],
            axis=1,
        )
        atr = ranges.max(axis=1).rolling(window, min_periods=window).mean()
        return atr / df["close"]

    return compute


# --- price/volume anomaly factors -------------------------------------------
# These are per-symbol time-series factors. Effectiveness is empirical and
# time-varying: the ``direction`` values below encode the historically observed
# A-share sign (e.g. short-term reversal, low-volatility, lottery/MAX effects),
# but they are NOT guarantees. Always re-check with FactorLibrary.validate on
# your own sample before trusting a factor.


def _reversal(window: int) -> FactorFunction:
    """Short-term reversal: recent ``window``-day return (direction negative)."""

    def compute(df: pd.DataFrame) -> pd.Series:
        return df["close"] / df["close"].shift(window) - 1

    return compute


def _momentum_skip(window: int, skip: int) -> FactorFunction:
    """Momentum over ``window`` days skipping the most recent ``skip`` days."""

    def compute(df: pd.DataFrame) -> pd.Series:
        return df["close"].shift(skip) / df["close"].shift(window) - 1

    return compute


def _max_return(window: int) -> FactorFunction:
    """MAX / lottery effect: largest single-day return in the window."""

    def compute(df: pd.DataFrame) -> pd.Series:
        return _return_1d(df).rolling(window, min_periods=window).max()

    return compute


def _return_skew(window: int) -> FactorFunction:
    """Rolling return skewness (positive skew ~ lottery names)."""

    def compute(df: pd.DataFrame) -> pd.Series:
        return _return_1d(df).rolling(window, min_periods=window).skew()

    return compute


def _amihud_illiq(window: int, scale: float = 1e9) -> FactorFunction:
    """Amihud illiquidity: mean(|ret| / amount) over the window, scaled."""

    def compute(df: pd.DataFrame) -> pd.Series:
        amount = df["amount"].replace(0, np.nan)
        daily = _return_1d(df).abs() / amount
        return daily.rolling(window, min_periods=window).mean() * scale

    return compute


def _turnover_series(df: pd.DataFrame) -> pd.Series:
    """Turnover proxy: real ``turnover`` column if present, else amount/close.

    Without float-share data a true turnover rate is unavailable; amount/close
    (approx traded shares) is used as a monotonic stand-in.
    """
    if "turnover" in df.columns:
        return pd.to_numeric(df["turnover"], errors="coerce")
    return df["amount"] / df["close"]


def _turnover_mean(window: int) -> FactorFunction:
    """Average turnover over the window (high attention ~ worse future)."""

    def compute(df: pd.DataFrame) -> pd.Series:
        return _turnover_series(df).rolling(window, min_periods=window).mean()

    return compute


def _turnover_cv(window: int) -> FactorFunction:
    """Turnover coefficient of variation (abnormal-attention proxy)."""

    def compute(df: pd.DataFrame) -> pd.Series:
        turnover = _turnover_series(df)
        mean = turnover.rolling(window, min_periods=window).mean()
        std = turnover.rolling(window, min_periods=window).std()
        return std / mean.replace(0, np.nan)

    return compute


def _high_proximity(window: int) -> FactorFunction:
    """Proximity to the rolling high (52-week-high effect proxy)."""

    def compute(df: pd.DataFrame) -> pd.Series:
        rolling_max = df["close"].rolling(window, min_periods=window).max()
        return df["close"] / rolling_max

    return compute


def builtin_factor_definitions() -> Dict[str, FactorDefinition]:
    """Return the full built-in factor catalog (original 8 + price/volume)."""
    definitions = _first_stage_factor_definitions()
    definitions.update(pricevolume_factor_definitions())
    return definitions


def _first_stage_factor_definitions() -> Dict[str, FactorDefinition]:
    """Return the original first-stage built-in factor definitions."""
    definitions = [
        FactorDefinition("momentum_20", "positive", 20, ["close"], _momentum(20), "20 day momentum"),
        FactorDefinition("momentum_60", "positive", 60, ["close"], _momentum(60), "60 day momentum"),
        FactorDefinition("ma_position_20", "positive", 20, ["close"], _ma_position(20), "close relative to MA20"),
        FactorDefinition("ma_position_60", "positive", 60, ["close"], _ma_position(60), "close relative to MA60"),
        FactorDefinition("volatility_20", "negative", 20, ["close"], _volatility(20), "20 day volatility"),
        FactorDefinition("turnover_amount_20", "positive", 20, ["amount"], _turnover_amount(20), "20 day average amount"),
        FactorDefinition("drawdown_20", "negative", 20, ["close"], _drawdown(20), "20 day drawdown"),
        FactorDefinition("atr_ratio_14", "negative", 14, ["high", "low", "close"], _atr_ratio(14), "ATR14 divided by close"),
    ]
    return {definition.name: definition for definition in definitions}


def pricevolume_factor_definitions() -> Dict[str, FactorDefinition]:
    """Return price/volume anomaly factors (per-symbol, no future data).

    Directions encode historically observed A-share signs and are heuristic,
    not guarantees; validate on your own sample before use.
    """
    definitions = [
        FactorDefinition("reversal_5", "negative", 5, ["close"], _reversal(5), "5 day return (short-term reversal)"),
        FactorDefinition("reversal_10", "negative", 10, ["close"], _reversal(10), "10 day return (short-term reversal)"),
        FactorDefinition("momentum_120_skip20", "positive", 120, ["close"], _momentum_skip(120, 20), "120 day momentum skipping last 20 days"),
        FactorDefinition("max_ret_20", "negative", 20, ["close"], _max_return(20), "max single-day return over 20 days (lottery effect)"),
        FactorDefinition("ret_skew_20", "negative", 20, ["close"], _return_skew(20), "20 day return skewness"),
        FactorDefinition("amihud_illiq_20", "positive", 20, ["close", "amount"], _amihud_illiq(20), "Amihud illiquidity over 20 days"),
        FactorDefinition("turnover_mean_20", "negative", 20, ["close", "amount"], _turnover_mean(20), "20 day average turnover proxy"),
        FactorDefinition("turnover_cv_20", "negative", 20, ["close", "amount"], _turnover_cv(20), "20 day turnover coefficient of variation"),
        FactorDefinition("high_proximity_120", "positive", 120, ["close"], _high_proximity(120), "close relative to 120 day high"),
        FactorDefinition("vol_120", "negative", 120, ["close"], _volatility(120), "120 day realized volatility (low-vol anomaly)"),
    ]
    return {definition.name: definition for definition in definitions}


class FactorCalculator:
    """Calculate built-in and user-registered factors on a multi-stock panel."""

    def __init__(self, definitions: Dict[str, FactorDefinition] | None = None):
        self.definitions = definitions or builtin_factor_definitions()

    def register_factor(self, definition: FactorDefinition) -> None:
        """Register or replace a factor definition."""
        self.definitions[definition.name] = definition

    def get_definition(self, name: str) -> FactorDefinition:
        """Return factor metadata by name."""
        try:
            return self.definitions[name]
        except KeyError as exc:
            raise ValueError(f"未知因子: {name}") from exc

    def selected_definitions(self, factor_names: Iterable[str]) -> Dict[str, FactorDefinition]:
        """Return selected factor metadata."""
        return {name: self.get_definition(name) for name in factor_names}

    def calculate(self, panel: pd.DataFrame, factor_names: List[str]) -> pd.DataFrame:
        """Calculate factors for each symbol without using future rows."""
        self._validate_panel(panel)
        names = list(factor_names)
        definitions = self.selected_definitions(names)
        output_parts = []

        for symbol, group in panel.sort_values(["symbol", "trade_date"]).groupby("symbol", sort=False):
            data = group.copy().reset_index(drop=True)
            result = data[["symbol", "trade_date"]].copy()
            for name, definition in definitions.items():
                missing = [col for col in definition.dependencies if col not in data.columns]
                if missing:
                    raise ValueError(f"因子 {name} 缺少依赖字段: {', '.join(missing)}")
                values = definition.compute(data)
                if len(values) != len(data):
                    raise ValueError(f"因子 {name} 返回长度与输入不一致")
                result[name] = values.astype(float)
            output_parts.append(result)

        if not output_parts:
            return pd.DataFrame(columns=["symbol", "trade_date", *names])
        return pd.concat(output_parts, ignore_index=True)

    def quality_report(self, factor_data: pd.DataFrame, factor_names: List[str]) -> Dict[str, Dict[str, float]]:
        """Return basic factor quality statistics."""
        report = {}
        for name in factor_names:
            values = factor_data[name]
            valid = values.dropna()
            report[name] = {
                "coverage": float(values.notna().mean()) if len(values) else 0.0,
                "count": float(valid.count()),
                "mean": float(valid.mean()) if len(valid) else np.nan,
                "std": float(valid.std()) if len(valid) else np.nan,
            }
        return report

    @staticmethod
    def _validate_panel(panel: pd.DataFrame) -> None:
        required = {"symbol", "trade_date", "close"}
        missing = required - set(panel.columns)
        if missing:
            raise ValueError(f"行情面板缺少必要字段: {', '.join(sorted(missing))}")
