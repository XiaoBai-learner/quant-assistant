"""Daily stock feature wide table builder for next-day selection research."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DailyFeatureDefinition:
    """Metadata for one daily feature column."""

    name: str
    group: str
    direction: str
    description: str = ""

    def __post_init__(self) -> None:
        if self.direction not in {"positive", "negative", "neutral"}:
            raise ValueError("direction must be positive, negative, or neutral")


def daily_feature_definitions() -> dict[str, DailyFeatureDefinition]:
    """Return first-stage feature metadata grouped by research dimension."""
    items = [
        DailyFeatureDefinition("return_1d", "daily", "neutral", "one-day close return"),
        DailyFeatureDefinition("momentum_5", "daily", "positive", "5-day close momentum"),
        DailyFeatureDefinition("momentum_20", "daily", "positive", "20-day close momentum"),
        DailyFeatureDefinition("drawdown_20", "daily", "negative", "20-day close drawdown from rolling high"),
        DailyFeatureDefinition("volatility_20", "daily", "negative", "20-day return volatility"),
        DailyFeatureDefinition("atr_ratio_14", "daily", "negative", "ATR14 divided by close"),
        DailyFeatureDefinition("amount_ma_20", "daily", "positive", "20-day average turnover amount"),
        DailyFeatureDefinition("volume_ratio_5", "daily", "positive", "volume over 5-day average"),
        DailyFeatureDefinition("gap_open", "daily", "neutral", "open over previous close minus one"),
        DailyFeatureDefinition("upper_shadow_ratio", "daily", "negative", "upper shadow over close"),
        DailyFeatureDefinition("lower_shadow_ratio", "daily", "positive", "lower shadow over close"),
        DailyFeatureDefinition("intraday_return", "daily", "neutral", "close over open minus one"),
        DailyFeatureDefinition("industry_pct_change", "sector", "positive", "industry daily change"),
        DailyFeatureDefinition("industry_rank_score", "sector", "positive", "industry strength rank score"),
        DailyFeatureDefinition("concept_heat_score", "sector", "positive", "concept heat score"),
        DailyFeatureDefinition("main_net_inflow", "capital", "positive", "main capital net inflow"),
        DailyFeatureDefinition("fund_flow_score", "capital", "positive", "capital flow score"),
        DailyFeatureDefinition("limit_up_score", "event", "positive", "limit-board event score"),
        DailyFeatureDefinition("dragon_tiger_score", "event", "positive", "dragon tiger board score"),
        DailyFeatureDefinition("margin_balance_change", "margin", "neutral", "margin balance change"),
        DailyFeatureDefinition("holder_count_change", "shareholder", "negative", "holder count change"),
        DailyFeatureDefinition("sentiment_rank_score", "sentiment", "positive", "market attention score"),
    ]
    return {item.name: item for item in items}


class DailyFeatureWideBuilder:
    """Build a `trade_date + symbol` daily feature table from local datasets."""

    required_market_columns = ["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"]

    def build(
        self,
        market: pd.DataFrame,
        *,
        industry: Optional[pd.DataFrame] = None,
        fund_flow: Optional[pd.DataFrame] = None,
        events: Optional[pd.DataFrame] = None,
        margin: Optional[pd.DataFrame] = None,
        shareholders: Optional[pd.DataFrame] = None,
        sentiment: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """Create a daily feature wide table without using future market rows."""
        features = self._market_features(market)
        for extra in [industry, fund_flow, events, margin, shareholders, sentiment]:
            features = self._merge_optional(features, extra)
        return features.sort_values(["trade_date", "symbol"]).reset_index(drop=True)

    def _market_features(self, market: pd.DataFrame) -> pd.DataFrame:
        data = self._standardize_market(market)
        parts = []
        for _, group in data.groupby("symbol", sort=False):
            frame = group.copy().sort_values("trade_date").reset_index(drop=True)
            prev_close = frame["close"].shift(1)
            frame["return_1d"] = frame["close"].pct_change()
            frame["momentum_5"] = frame["close"] / frame["close"].shift(5) - 1
            frame["momentum_20"] = frame["close"] / frame["close"].shift(20) - 1
            rolling_high_20 = frame["close"].rolling(20, min_periods=20).max()
            frame["drawdown_20"] = frame["close"] / rolling_high_20 - 1
            frame["volatility_20"] = frame["return_1d"].rolling(20, min_periods=20).std()
            frame["amount_ma_20"] = frame["amount"].rolling(20, min_periods=20).mean()
            frame["volume_ratio_5"] = frame["volume"] / frame["volume"].rolling(5, min_periods=5).mean()
            frame["gap_open"] = frame["open"] / prev_close - 1
            frame["intraday_return"] = frame["close"] / frame["open"] - 1
            frame["upper_shadow_ratio"] = (frame["high"] - frame[["open", "close"]].max(axis=1)) / frame["close"]
            frame["lower_shadow_ratio"] = (frame[["open", "close"]].min(axis=1) - frame["low"]) / frame["close"]
            frame["atr_ratio_14"] = self._atr_ratio(frame, window=14)
            parts.append(frame)

        if not parts:
            return pd.DataFrame(columns=self.required_market_columns)

        features = pd.concat(parts, ignore_index=True)
        features["is_allowed_universe"] = ~features["symbol"].astype(str).str.startswith("688")
        features["is_price_stalled"] = features["high"].eq(features["low"])
        features["is_tradable_next_day"] = (
            features["is_allowed_universe"]
            & ~features["is_price_stalled"]
            & features[["open", "high", "low", "close"]].notna().all(axis=1)
            & features["volume"].fillna(0).gt(0)
        )
        return features

    def _standardize_market(self, market: pd.DataFrame) -> pd.DataFrame:
        data = market.copy().rename(columns={"date": "trade_date", "datetime": "trade_date"})
        missing = [column for column in self.required_market_columns if column not in data.columns]
        if missing:
            raise ValueError(f"行情宽表缺少必要字段: {', '.join(missing)}")
        data = data[self.required_market_columns].copy()
        data["symbol"] = data["symbol"].astype(str).str.strip()
        data["trade_date"] = pd.to_datetime(data["trade_date"])
        for column in ["open", "high", "low", "close", "volume", "amount"]:
            data[column] = pd.to_numeric(data[column], errors="coerce")
        return data.sort_values(["symbol", "trade_date"]).drop_duplicates(["symbol", "trade_date"], keep="last")

    @staticmethod
    def _atr_ratio(frame: pd.DataFrame, window: int) -> pd.Series:
        prev_close = frame["close"].shift(1)
        ranges = pd.concat(
            [
                frame["high"] - frame["low"],
                (frame["high"] - prev_close).abs(),
                (frame["low"] - prev_close).abs(),
            ],
            axis=1,
        )
        atr = ranges.max(axis=1).rolling(window, min_periods=window).mean()
        return atr / frame["close"].replace(0, np.nan)

    @staticmethod
    def _merge_optional(base: pd.DataFrame, extra: Optional[pd.DataFrame]) -> pd.DataFrame:
        if extra is None or extra.empty:
            return base
        data = extra.copy().rename(columns={"date": "trade_date", "datetime": "trade_date"})
        required = {"trade_date", "symbol"}
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"扩展指标数据缺少字段: {', '.join(sorted(missing))}")
        data["trade_date"] = pd.to_datetime(data["trade_date"])
        data["symbol"] = data["symbol"].astype(str).str.strip()
        value_columns = [column for column in data.columns if column not in {"trade_date", "symbol"}]
        data = data[["trade_date", "symbol", *value_columns]]
        data = _deduplicate_extra(data, value_columns)
        return base.merge(data, on=["trade_date", "symbol"], how="left")


def feature_quality_report(features: pd.DataFrame, feature_names: Optional[Iterable[str]] = None) -> dict:
    """Return coverage and tradability summary for a daily feature wide table."""
    names = list(feature_names or [name for name in daily_feature_definitions() if name in features.columns])
    coverage = {}
    for name in names:
        values = features[name] if name in features.columns else pd.Series(dtype=float)
        coverage[name] = float(values.notna().mean()) if len(values) else 0.0
    return {
        "rows": int(len(features)),
        "symbol_count": int(features["symbol"].nunique()) if "symbol" in features.columns else 0,
        "start": str(pd.to_datetime(features["trade_date"]).min().date()) if len(features) else None,
        "end": str(pd.to_datetime(features["trade_date"]).max().date()) if len(features) else None,
        "tradable_rows": int(features.get("is_tradable_next_day", pd.Series(dtype=bool)).sum()),
        "blocked_rows": int((~features.get("is_tradable_next_day", pd.Series(dtype=bool))).sum()) if len(features) else 0,
        "feature_coverage": coverage,
    }


def _deduplicate_extra(data: pd.DataFrame, value_columns: list[str]) -> pd.DataFrame:
    aggregations = {}
    for column in value_columns:
        if pd.api.types.is_numeric_dtype(data[column]):
            aggregations[column] = "mean"
        else:
            aggregations[column] = "last"
    return data.groupby(["trade_date", "symbol"], as_index=False).agg(aggregations)
