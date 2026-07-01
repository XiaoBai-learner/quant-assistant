"""Daily feature-wide strategy candidates for stock-pool research."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

import pandas as pd


FilterFunction = Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class StrategyCandidate:
    """Declarative strategy candidate based on daily feature columns."""

    name: str
    description: str
    expected_regime: str
    factor_weights: dict[str, float]
    required_columns: list[str]
    top_n: int = 10
    min_score: Optional[float] = None
    hard_filters: list[FilterFunction] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.top_n <= 0:
            raise ValueError("top_n must be positive")
        if not self.factor_weights:
            raise ValueError("factor_weights cannot be empty")


class StrategyCandidateRunner:
    """Score and select stocks for one or more strategy candidates."""

    def __init__(self, candidates: Iterable[StrategyCandidate]):
        self.candidates = list(candidates)

    def run(self, feature_wide: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Return selected rows keyed by strategy name."""
        return {candidate.name: self.select(feature_wide, candidate) for candidate in self.candidates}

    def select(self, feature_wide: pd.DataFrame, candidate: StrategyCandidate) -> pd.DataFrame:
        """Score one strategy candidate on each trade date."""
        self._validate_columns(feature_wide, candidate)
        data = feature_wide.copy()
        data["trade_date"] = pd.to_datetime(data["trade_date"])
        mask = self._base_mask(data)
        for hard_filter in candidate.hard_filters:
            mask &= hard_filter(data).fillna(False)
        data = data[mask].copy()
        if data.empty:
            return _empty_selection(feature_wide)

        score_columns = []
        for column, weight in candidate.factor_weights.items():
            score_column = f"{column}_strategy_component"
            data[score_column] = _cross_sectional_score(data, column) * weight
            score_columns.append(score_column)
        denominator = sum(abs(weight) for weight in candidate.factor_weights.values()) or 1.0
        data["score"] = data[score_columns].sum(axis=1, skipna=True) / denominator

        selections = []
        for trade_date, group in data.groupby("trade_date", sort=True):
            ranked = group.dropna(subset=["score"]).sort_values(["score", "symbol"], ascending=[False, True])
            if candidate.min_score is not None:
                ranked = ranked[ranked["score"] >= candidate.min_score]
            selected = ranked.head(candidate.top_n).copy()
            selected["rank"] = range(1, len(selected) + 1)
            selected["selected"] = True
            selected["rebalance_date"] = pd.Timestamp(trade_date)
            selected["strategy_name"] = candidate.name
            selections.append(selected)

        if not selections:
            return _empty_selection(feature_wide)
        return pd.concat(selections, ignore_index=True)

    @staticmethod
    def _validate_columns(feature_wide: pd.DataFrame, candidate: StrategyCandidate) -> None:
        required = {"trade_date", "symbol", *candidate.required_columns, *candidate.factor_weights.keys()}
        missing = required - set(feature_wide.columns)
        if missing:
            raise ValueError(f"策略 {candidate.name} 缺少字段: {', '.join(sorted(missing))}")

    @staticmethod
    def _base_mask(data: pd.DataFrame) -> pd.Series:
        allowed = data.get("is_allowed_universe", True)
        tradable = data.get("is_tradable_next_day", True)
        return pd.Series(allowed, index=data.index).astype(bool) & pd.Series(tradable, index=data.index).astype(bool)


def default_strategy_candidates() -> dict[str, StrategyCandidate]:
    """Return first-stage candidates covering different market views."""
    candidates = [
        StrategyCandidate(
            name="trend_momentum",
            description="Strong price trend with acceptable volatility and attention.",
            expected_regime="strong_market",
            factor_weights={"momentum_20": 1.0, "volatility_20": -0.4, "sentiment_rank_score": 0.2},
            required_columns=["momentum_20", "volatility_20", "sentiment_rank_score"],
            top_n=10,
            hard_filters=[_positive("momentum_20")],
        ),
        StrategyCandidate(
            name="low_vol_reversal",
            description="Controlled volatility names recovering from moderate drawdown.",
            expected_regime="choppy_market",
            factor_weights={"drawdown_20": -0.8, "volatility_20": -1.0, "momentum_5": 0.3},
            required_columns=["drawdown_20", "volatility_20", "momentum_5"],
            top_n=10,
        ),
        StrategyCandidate(
            name="capital_flow",
            description="Capital inflow continuation with price confirmation.",
            expected_regime="liquidity_driven",
            factor_weights={"fund_flow_score": 1.0, "main_net_inflow": 0.4, "momentum_5": 0.3},
            required_columns=["fund_flow_score", "main_net_inflow", "momentum_5"],
            top_n=10,
            hard_filters=[_positive("fund_flow_score")],
        ),
        StrategyCandidate(
            name="sector_rotation",
            description="Pick liquid leaders from strong industry or concept buckets.",
            expected_regime="sector_rotation",
            factor_weights={"industry_rank_score": 1.0, "concept_heat_score": 0.5, "momentum_20": 0.4},
            required_columns=["industry_rank_score", "concept_heat_score", "momentum_20"],
            top_n=10,
        ),
        StrategyCandidate(
            name="event_enhanced",
            description="Event and attention enhanced continuation candidate.",
            expected_regime="event_driven",
            factor_weights={
                "limit_up_score": 0.8,
                "dragon_tiger_score": 0.6,
                "sentiment_rank_score": 0.4,
                "volatility_20": -0.3,
            },
            required_columns=["limit_up_score", "dragon_tiger_score", "sentiment_rank_score", "volatility_20"],
            top_n=10,
        ),
    ]
    return {candidate.name: candidate for candidate in candidates}


def _cross_sectional_score(data: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(data[column], errors="coerce")
    return values.groupby(data["trade_date"]).transform(_zscore)


def _zscore(values: pd.Series) -> pd.Series:
    mean = values.mean(skipna=True)
    std = values.std(skipna=True)
    if pd.isna(std) or std == 0:
        return values.where(values.isna(), 0.0)
    return (values - mean) / std


def _positive(column: str) -> FilterFunction:
    def apply(data: pd.DataFrame) -> pd.Series:
        return pd.to_numeric(data[column], errors="coerce") > 0

    return apply


def _empty_selection(feature_wide: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(columns=[*feature_wide.columns, "score", "rank", "selected", "rebalance_date", "strategy_name"])
