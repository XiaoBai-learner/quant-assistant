"""Factor effectiveness diagnostics for stock-pool research."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from .factors import FactorCalculator, FactorDefinition


@dataclass
class FactorAnalysisResult:
    """Container for factor diagnostics."""

    factor_values: pd.DataFrame = field(default_factory=pd.DataFrame)
    forward_return_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    ic_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    summary_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    group_returns: pd.DataFrame = field(default_factory=pd.DataFrame)
    correlation_matrix: pd.DataFrame = field(default_factory=pd.DataFrame)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        """Return a compact serializable summary."""
        return {
            "factors": list(self.summary_table.index.astype(str)) if not self.summary_table.empty else [],
            "summary_table": self.summary_table.to_dict(orient="index") if not self.summary_table.empty else {},
            "ic_rows": int(len(self.ic_table)),
            "group_return_rows": int(len(self.group_returns)),
            "warnings": list(self.warnings),
        }

    def export_csv(self, output_dir: str) -> None:
        """Export non-empty analysis tables to CSV."""
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        tables = {
            "factor_values": self.factor_values,
            "forward_return_table": self.forward_return_table,
            "ic_table": self.ic_table,
            "summary_table": self.summary_table.reset_index().rename(columns={"index": "factor"}),
            "group_returns": self.group_returns,
            "correlation_matrix": self.correlation_matrix,
        }
        for name, table in tables.items():
            if not table.empty:
                table.to_csv(path / f"{name}.csv", index=name == "correlation_matrix")


class FactorAnalyzer:
    """Evaluate factor effectiveness on a multi-stock panel."""

    def __init__(self, factor_definitions: Optional[Dict[str, FactorDefinition]] = None):
        self.factor_calculator = FactorCalculator(factor_definitions)

    def analyze(
        self,
        data: pd.DataFrame,
        factors: Iterable[str],
        forward_returns: Iterable[int],
        quantiles: int = 5,
        rebalance: str = "M",
    ) -> FactorAnalysisResult:
        """Analyze factor IC, group returns, and correlations."""
        factor_names = list(factors)
        windows = list(forward_returns)
        if not factor_names:
            raise ValueError("factors 不能为空")
        if not windows:
            raise ValueError("forward_returns 不能为空")

        panel = self._prepare_panel(data)
        factor_values = self.factor_calculator.calculate(panel, factor_names)
        rebalance_factors = self._rebalance_rows(factor_values, rebalance)
        forward_table = self._forward_returns(panel, windows)
        analysis_data = rebalance_factors.merge(forward_table, on=["symbol", "trade_date"], how="left")
        ic_table = self._rank_ic_table(analysis_data, factor_names, windows)
        group_returns, top_bottom = self._group_returns(analysis_data, factor_names, windows, quantiles)
        summary_table = self._summary_table(ic_table, factor_names, top_bottom, rebalance_factors)
        correlation_matrix = self._correlation_matrix(rebalance_factors, factor_names)

        return FactorAnalysisResult(
            factor_values=rebalance_factors,
            forward_return_table=forward_table,
            ic_table=ic_table,
            summary_table=summary_table,
            group_returns=group_returns,
            correlation_matrix=correlation_matrix,
        )

    @staticmethod
    def _prepare_panel(data: pd.DataFrame) -> pd.DataFrame:
        panel = data.copy()
        required = {"symbol", "trade_date", "close"}
        missing = required - set(panel.columns)
        if missing:
            raise ValueError(f"行情面板缺少必要字段: {', '.join(sorted(missing))}")
        panel["trade_date"] = pd.to_datetime(panel["trade_date"])
        return panel.sort_values(["symbol", "trade_date"]).reset_index(drop=True)

    @staticmethod
    def _rebalance_rows(factor_values: pd.DataFrame, rebalance: str) -> pd.DataFrame:
        data = factor_values.copy()
        data["trade_date"] = pd.to_datetime(data["trade_date"])
        period = data["trade_date"].dt.to_period(rebalance)
        last_dates = data.groupby(period)["trade_date"].transform("max")
        return data[data["trade_date"] == last_dates].copy().reset_index(drop=True)

    @staticmethod
    def _forward_returns(panel: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        parts = []
        for _, group in panel.groupby("symbol", sort=False):
            data = group[["symbol", "trade_date", "close"]].copy()
            for window in windows:
                data[f"forward_return_{window}"] = data["close"].shift(-window) / data["close"] - 1
            parts.append(data.drop(columns=["close"]))
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    @staticmethod
    def _rank_ic_table(data: pd.DataFrame, factors: List[str], windows: List[int]) -> pd.DataFrame:
        rows = []
        for factor in factors:
            for window in windows:
                return_col = f"forward_return_{window}"
                for trade_date, group in data.groupby("trade_date", sort=True):
                    sample = group[[factor, return_col]].dropna()
                    if len(sample) < 2:
                        continue
                    rank_ic = sample[factor].rank().corr(sample[return_col].rank())
                    if pd.isna(rank_ic):
                        continue
                    rows.append({
                        "trade_date": trade_date,
                        "factor": factor,
                        "window": window,
                        "rank_ic": float(rank_ic),
                        "sample_size": int(len(sample)),
                    })
        return pd.DataFrame(rows)

    @staticmethod
    def _group_returns(
        data: pd.DataFrame,
        factors: List[str],
        windows: List[int],
        quantiles: int,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        group_rows = []
        spread_rows = []
        for factor in factors:
            for window in windows:
                return_col = f"forward_return_{window}"
                for trade_date, group in data.groupby("trade_date", sort=True):
                    sample = group[["symbol", factor, return_col]].dropna().copy()
                    if len(sample) < 2:
                        continue
                    factor_rank = sample[factor].rank(method="first")
                    try:
                        sample["quantile"] = pd.qcut(
                            factor_rank,
                            q=min(quantiles, len(sample)),
                            labels=False,
                            duplicates="drop",
                        ) + 1
                    except ValueError:
                        continue
                    grouped = sample.groupby("quantile", sort=True)[return_col].mean()
                    for quantile, value in grouped.items():
                        group_rows.append({
                            "trade_date": trade_date,
                            "factor": factor,
                            "window": window,
                            "quantile": int(quantile),
                            "mean_forward_return": float(value),
                            "sample_size": int((sample["quantile"] == quantile).sum()),
                        })
                    if len(grouped) >= 2:
                        spread_rows.append({
                            "trade_date": trade_date,
                            "factor": factor,
                            "window": window,
                            "top_bottom": float(grouped.iloc[-1] - grouped.iloc[0]),
                        })
        return pd.DataFrame(group_rows), pd.DataFrame(spread_rows)

    @staticmethod
    def _summary_table(
        ic_table: pd.DataFrame,
        factors: List[str],
        top_bottom: pd.DataFrame,
        factor_values: pd.DataFrame,
    ) -> pd.DataFrame:
        rows = {}
        for factor in factors:
            factor_ic = ic_table[ic_table["factor"] == factor]["rank_ic"] if not ic_table.empty else pd.Series(dtype=float)
            values = factor_values[factor] if factor in factor_values.columns else pd.Series(dtype=float)
            valid_values = values.dropna()
            ic_mean = float(factor_ic.mean()) if len(factor_ic) else np.nan
            ic_std = float(factor_ic.std()) if len(factor_ic) else np.nan
            rows[factor] = {
                "factor_coverage": float(values.notna().mean()) if len(values) else 0.0,
                "factor_observations": int(len(valid_values)),
                "factor_mean": float(valid_values.mean()) if len(valid_values) else np.nan,
                "factor_std": float(valid_values.std()) if len(valid_values) else np.nan,
                "rank_ic_mean": ic_mean,
                "rank_ic_std": ic_std,
                "icir": float(ic_mean / ic_std) if ic_std and not pd.isna(ic_std) else np.nan,
                "ic_win_rate": float((factor_ic > 0).mean()) if len(factor_ic) else np.nan,
                "ic_count": int(len(factor_ic)),
                "top_bottom_mean": FactorAnalyzer._top_bottom_mean(top_bottom, factor),
            }
        return pd.DataFrame.from_dict(rows, orient="index")

    @staticmethod
    def _top_bottom_mean(top_bottom: pd.DataFrame, factor: str) -> float:
        if top_bottom.empty:
            return np.nan
        values = top_bottom[top_bottom["factor"] == factor]["top_bottom"]
        return float(values.mean()) if len(values) else np.nan

    @staticmethod
    def _correlation_matrix(rebalance_factors: pd.DataFrame, factors: List[str]) -> pd.DataFrame:
        available = [factor for factor in factors if factor in rebalance_factors.columns]
        if not available:
            return pd.DataFrame()
        return rebalance_factors[available].corr(method="spearman")
