"""Evaluation metrics for stock-pool selection research."""
from typing import Dict

import numpy as np
import pandas as pd


class SelectionEvaluator:
    """Calculate performance and factor evaluation metrics."""

    def evaluate(self, daily_returns: pd.DataFrame) -> Dict[str, float]:
        """Calculate core portfolio metrics."""
        if daily_returns.empty:
            return {}
        returns = daily_returns["daily_return"].fillna(0.0)
        values = daily_returns["portfolio_value"]
        total_return = values.iloc[-1] / values.iloc[0] - 1 if values.iloc[0] else 0.0
        annual_return = (1 + total_return) ** (252 / len(values)) - 1 if len(values) else 0.0
        volatility = returns.std() * np.sqrt(252)
        sharpe = annual_return / volatility if volatility > 0 else 0.0
        drawdown = values / values.cummax() - 1
        max_drawdown = drawdown.min()
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        win_rate = (returns > 0).mean() if len(returns) else 0.0
        return {
            "total_return": float(total_return),
            "annual_return": float(annual_return),
            "volatility": float(volatility),
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "calmar_ratio": float(calmar),
            "win_rate": float(win_rate),
        }

    def factor_ic(self, factor_scores: pd.DataFrame, forward_returns: pd.DataFrame, factor_names: list[str]) -> Dict[str, float]:
        """Calculate simple average Spearman IC per factor."""
        if factor_scores.empty or forward_returns.empty:
            return {name: np.nan for name in factor_names}
        merged = factor_scores.merge(forward_returns, on=["trade_date", "symbol"], how="inner")
        result = {}
        for name in factor_names:
            if name not in merged.columns:
                result[name] = np.nan
                continue
            ics = []
            for _, group in merged.groupby("trade_date"):
                if group[name].notna().sum() >= 2 and group["forward_return"].notna().sum() >= 2:
                    ics.append(group[name].corr(group["forward_return"], method="spearman"))
            result[name] = float(pd.Series(ics).mean()) if ics else np.nan
        return result
