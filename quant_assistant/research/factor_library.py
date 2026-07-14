"""Unified price/volume factor library.

Chains the three research stages into one directly callable pipeline:

    time-series compute (FactorCalculator)
        -> cross-sectional processing (CrossSectionProcessor)
        -> direction alignment + weighted composite scoring
        -> effectiveness validation (FactorAnalyzer)

This is the single entry point for "call factors, combine into a strategy,
compute a score" without re-implementing standardization at every call site.

Honest boundaries:
- Factor "effectiveness" is empirical and time-varying. ``screen_effective``
  uses heuristic IC / ICIR thresholds and is NOT a promise of future returns.
- Size neutralization uses ``amount`` as a market-cap proxy (see cross_section).
- Anomaly directions (reversal / low-vol / lottery) reflect A-share history and
  can decay as market structure changes, so ``validate`` on your own sample.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from .cross_section import CrossSectionProcessor
from .factor_analysis import FactorAnalyzer
from .factors import FactorCalculator, FactorDefinition, builtin_factor_definitions


class FactorLibrary:
    """Facade over factor computation, processing, scoring, and validation."""

    def __init__(
        self,
        definitions: Optional[Dict[str, FactorDefinition]] = None,
        processor: Optional[CrossSectionProcessor] = None,
    ):
        self.calculator = FactorCalculator(definitions or builtin_factor_definitions())
        self.processor = processor or CrossSectionProcessor()

    def list_factors(self) -> pd.DataFrame:
        """Return a catalog of available factors (name/direction/deps/desc)."""
        rows = [
            {
                "name": definition.name,
                "direction": definition.direction,
                "min_periods": definition.min_periods,
                "dependencies": ",".join(definition.dependencies),
                "description": definition.description,
            }
            for definition in self.calculator.definitions.values()
        ]
        return pd.DataFrame(rows).sort_values("name").reset_index(drop=True)

    def compute_raw(self, panel: pd.DataFrame, names: Iterable[str]) -> pd.DataFrame:
        """Compute raw per-symbol factor values (no cross-sectional step)."""
        return self.calculator.calculate(panel, list(names))

    def compute_processed(
        self,
        panel: pd.DataFrame,
        names: Iterable[str],
        industry_col: Optional[str] = None,
        size_col: Optional[str] = "amount",
        align_direction: bool = True,
    ) -> pd.DataFrame:
        """Compute factors then apply cross-sectional processing.

        When ``align_direction`` is True, factors whose ``direction`` is
        "negative" are multiplied by -1 after standardization so that a higher
        processed value always means "better", letting ``composite_score`` use
        plain positive weights.
        """
        names = list(names)
        raw = self.compute_raw(panel, names)
        merged = self._attach_context(panel, raw, names, industry_col, size_col)
        processed = self.processor.process(
            merged, names, industry_col=industry_col, size_col=size_col
        )
        if align_direction:
            for name in names:
                if self.calculator.get_definition(name).direction == "negative":
                    processed[name] = -processed[name]
        return processed[["symbol", "trade_date", *names]]

    def composite_score(
        self,
        panel: pd.DataFrame,
        weights: Dict[str, float],
        industry_col: Optional[str] = None,
        size_col: Optional[str] = "amount",
    ) -> pd.DataFrame:
        """Weighted composite of direction-aligned processed factors.

        Weights are on the "higher=better" scale (all positive for a long
        book). Returns symbol/trade_date/score with the per-name components.
        """
        if not weights:
            raise ValueError("weights 不能为空")
        names = list(weights)
        processed = self.compute_processed(
            panel, names, industry_col=industry_col, size_col=size_col, align_direction=True
        )
        denominator = sum(abs(w) for w in weights.values()) or 1.0
        weighted = processed[["symbol", "trade_date"]].copy()
        for name, weight in weights.items():
            weighted[name] = processed[name] * weight
        weighted["score"] = weighted[names].sum(axis=1, skipna=True) / denominator
        return weighted

    def validate(
        self,
        panel: pd.DataFrame,
        names: Iterable[str],
        forward_returns: Iterable[int] = (1, 5, 20),
        quantiles: int = 5,
        rebalance: str = "M",
    ) -> pd.DataFrame:
        """Return the IC/ICIR summary table via FactorAnalyzer."""
        analyzer = FactorAnalyzer(self.calculator.definitions)
        result = analyzer.analyze(
            panel,
            list(names),
            forward_returns=list(forward_returns),
            quantiles=quantiles,
            rebalance=rebalance,
        )
        return result.summary_table

    def screen_effective(
        self,
        panel: pd.DataFrame,
        names: Iterable[str],
        forward_returns: Iterable[int] = (1, 5, 20),
        ic_threshold: float = 0.02,
        icir_threshold: float = 0.3,
        rebalance: str = "M",
    ) -> List[str]:
        """Return factors clearing heuristic |IC| and |ICIR| thresholds.

        Thresholds are heuristic and direction-agnostic (uses absolute values),
        NOT a guarantee of future performance.
        """
        summary = self.validate(
            panel, names, forward_returns=forward_returns, rebalance=rebalance
        )
        if summary.empty:
            return []
        effective = []
        for name in names:
            if name not in summary.index:
                continue
            row = summary.loc[name]
            ic_mean = row.get("rank_ic_mean", np.nan)
            icir = row.get("icir", np.nan)
            if pd.isna(ic_mean) or pd.isna(icir):
                continue
            if abs(ic_mean) >= ic_threshold and abs(icir) >= icir_threshold:
                effective.append(name)
        return effective

    def _attach_context(
        self,
        panel: pd.DataFrame,
        raw: pd.DataFrame,
        names: List[str],
        industry_col: Optional[str],
        size_col: Optional[str],
    ) -> pd.DataFrame:
        """Merge industry/size context columns onto the raw factor frame."""
        context_cols = [
            col
            for col in {industry_col, size_col}
            if col and col in panel.columns and col not in raw.columns
        ]
        if not context_cols:
            return raw
        keys = panel[["symbol", "trade_date", *context_cols]].copy()
        keys["trade_date"] = pd.to_datetime(keys["trade_date"])
        merged = raw.copy()
        merged["trade_date"] = pd.to_datetime(merged["trade_date"])
        return merged.merge(keys, on=["symbol", "trade_date"], how="left")
