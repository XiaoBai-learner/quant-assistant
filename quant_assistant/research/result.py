"""Result object for stock-pool factor research."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


@dataclass
class SelectionResearchResult:
    """Container for research outputs and diagnostics."""

    metrics: Dict[str, Any] = field(default_factory=dict)
    daily_returns: pd.DataFrame = field(default_factory=pd.DataFrame)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    selections: pd.DataFrame = field(default_factory=pd.DataFrame)
    holdings: pd.DataFrame = field(default_factory=pd.DataFrame)
    rebalance_trades: pd.DataFrame = field(default_factory=pd.DataFrame)
    factor_values: pd.DataFrame = field(default_factory=pd.DataFrame)
    factor_scores: pd.DataFrame = field(default_factory=pd.DataFrame)
    factor_contributions: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_quality: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def latest_selection(self) -> pd.DataFrame:
        """Return the latest rebalance selection."""
        if self.selections.empty:
            return pd.DataFrame()
        date_col = "rebalance_date" if "rebalance_date" in self.selections.columns else "trade_date"
        latest_date = self.selections[date_col].max()
        return self.selections[self.selections[date_col] == latest_date].copy()

    def summary(self) -> Dict[str, Any]:
        """Return a compact serializable summary."""
        return {
            "metrics": dict(self.metrics),
            "warnings": list(self.warnings),
            "selection_count": int(len(self.selections)),
            "holding_count": int(len(self.holdings)),
        }

    def export_csv(self, output_dir: str) -> None:
        """Export non-empty result tables to CSV files."""
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        tables = {
            "daily_returns": self.daily_returns,
            "equity_curve": self.equity_curve,
            "selections": self.selections,
            "holdings": self.holdings,
            "rebalance_trades": self.rebalance_trades,
            "factor_values": self.factor_values,
            "factor_scores": self.factor_scores,
            "factor_contributions": self.factor_contributions,
        }
        for name, table in tables.items():
            if not table.empty:
                table.to_csv(path / f"{name}.csv", index=False)
