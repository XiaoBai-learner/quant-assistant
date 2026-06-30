"""End-to-end stock-pool factor selection research workflow."""
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from .backtest import SelectionBacktester
from .config import SelectionResearchConfig
from .evaluation import SelectionEvaluator
from .factors import FactorCalculator, FactorDefinition
from .panel import DataBundle
from .portfolio import PortfolioConstructor
from .preprocessing import FactorPreprocessor
from .result import SelectionResearchResult
from .scoring import FactorScorer
from .selector import StockPoolSelector


class SelectionResearch:
    """Orchestrate multi-stock factor ranking, selection, and portfolio backtest."""

    def __init__(
        self,
        universe: List[str],
        start: str,
        end: str,
        factors: Dict[str, float],
        top_n: int = 10,
        rebalance: str = "M",
        data: Optional[pd.DataFrame] = None,
        factor_definitions: Optional[Dict[str, FactorDefinition]] = None,
        data_loader: Optional[Callable[[List[str], str, str], pd.DataFrame]] = None,
        max_weight: float = 0.2,
        initial_cash: float = 100000.0,
        data_quality: Optional[Dict[str, Any]] = None,
    ):
        self.config = SelectionResearchConfig(
            universe=universe,
            start=start,
            end=end,
            factors=factors,
            top_n=top_n,
            rebalance=rebalance,
            max_weight=max_weight,
        )
        self.data = data
        self.data_loader = data_loader
        self.factor_calculator = FactorCalculator(factor_definitions)
        self.initial_cash = initial_cash
        self.data_quality = data_quality

    @classmethod
    def from_bundle(
        cls,
        bundle: DataBundle,
        factors: Dict[str, float],
        top_n: int = 10,
        rebalance: str = "M",
        factor_definitions: Optional[Dict[str, FactorDefinition]] = None,
        max_weight: float = 0.2,
        initial_cash: float = 100000.0,
    ) -> "SelectionResearch":
        """Create a research workflow directly from a DataBundle."""
        return cls(
            universe=bundle.symbols,
            start=bundle.start,
            end=bundle.end,
            factors=factors,
            top_n=top_n,
            rebalance=rebalance,
            data=bundle.panel,
            factor_definitions=factor_definitions,
            max_weight=max_weight,
            initial_cash=initial_cash,
            data_quality=bundle.quality.summary() if bundle.quality is not None else None,
        )

    def register_factor(self, definition: FactorDefinition) -> None:
        """Register a user-defined factor for this research workflow."""
        self.factor_calculator.register_factor(definition)

    def run(self) -> SelectionResearchResult:
        """Run the complete selection research workflow."""
        warnings: List[str] = []
        panel = self._load_panel()
        panel, data_quality = self._prepare_panel(panel)
        if panel.empty:
            raise ValueError("股票池没有可用行情数据")

        factor_names = list(self.config.factor_weights)
        factor_values = self.factor_calculator.calculate(panel, factor_names)
        rebalance_factors = self._rebalance_rows(factor_values)
        definitions = self.factor_calculator.selected_definitions(factor_names)
        preprocessor = FactorPreprocessor(definitions)
        processed = preprocessor.transform(rebalance_factors, factor_names)
        for date_value, disabled in preprocessor.disabled_factors.items():
            warnings.append(f"{date_value.date()} 因子有效样本不足，已禁用: {', '.join(disabled)}")

        factor_scores = FactorScorer(self.config.factor_weights).score(processed)
        selections = StockPoolSelector(top_n=self.config.top_n).select(factor_scores)
        holdings = PortfolioConstructor(max_weight=self.config.max_weight).construct(selections)
        backtest_result = SelectionBacktester(initial_cash=self.initial_cash).run(panel, holdings)
        daily_returns = backtest_result["daily_returns"]
        metrics = SelectionEvaluator().evaluate(daily_returns)

        return SelectionResearchResult(
            metrics=metrics,
            daily_returns=daily_returns,
            equity_curve=daily_returns[["trade_date", "portfolio_value"]].copy() if not daily_returns.empty else pd.DataFrame(),
            selections=selections,
            holdings=holdings,
            rebalance_trades=backtest_result["rebalance_trades"],
            factor_values=factor_values,
            factor_scores=factor_scores,
            factor_contributions=self._contributions(factor_scores),
            data_quality=self.data_quality or data_quality,
            warnings=warnings,
        )

    def _load_panel(self) -> pd.DataFrame:
        if self.data is not None:
            return self.data.copy()
        if self.data_loader is not None:
            return self.data_loader(self.config.universe, self.config.start, self.config.end)
        raise ValueError("SelectionResearch 需要 data 或 data_loader")

    def _prepare_panel(self, panel: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, dict]]:
        data = panel.copy()
        required = {"symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"}
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"行情数据缺少必要字段: {', '.join(sorted(missing))}")
        data["trade_date"] = pd.to_datetime(data["trade_date"])
        start = pd.Timestamp(self.config.start)
        end = pd.Timestamp(self.config.end)
        data = data[(data["symbol"].isin(self.config.universe)) & (data["trade_date"] >= start) & (data["trade_date"] <= end)]
        data = data.sort_values(["symbol", "trade_date"]).drop_duplicates(["symbol", "trade_date"], keep="last")
        quality = {}
        for symbol in self.config.universe:
            group = data[data["symbol"] == symbol]
            quality[symbol] = {
                "rows": int(len(group)),
                "start": str(group["trade_date"].min().date()) if not group.empty else None,
                "end": str(group["trade_date"].max().date()) if not group.empty else None,
                "missing_ohlcv": int(group[["open", "high", "low", "close", "volume", "amount"]].isna().sum().sum()) if not group.empty else 0,
            }
        return data, quality

    def _rebalance_rows(self, factor_values: pd.DataFrame) -> pd.DataFrame:
        data = factor_values.copy()
        data["trade_date"] = pd.to_datetime(data["trade_date"])
        period = data["trade_date"].dt.to_period(self.config.rebalance)
        last_dates = data.groupby(period)["trade_date"].transform("max")
        return data[data["trade_date"] == last_dates].copy()

    @staticmethod
    def _contributions(factor_scores: pd.DataFrame) -> pd.DataFrame:
        columns = ["trade_date", "symbol", *[c for c in factor_scores.columns if c.endswith("_contribution")]]
        return factor_scores[[c for c in columns if c in factor_scores.columns]].copy()
