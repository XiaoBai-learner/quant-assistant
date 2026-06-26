"""Portfolio construction for selection results."""
import pandas as pd


class PortfolioConstructor:
    """Construct target holdings from selected stocks."""

    def __init__(self, max_weight: float = 0.2):
        if max_weight <= 0 or max_weight > 1:
            raise ValueError("max_weight 必须在 (0, 1] 内")
        self.max_weight = max_weight

    def construct(self, selections: pd.DataFrame) -> pd.DataFrame:
        """Create equal-weight holdings for each rebalance date."""
        if selections.empty:
            return pd.DataFrame(columns=["rebalance_date", "symbol", "target_weight"])

        holdings = []
        date_col = "rebalance_date" if "rebalance_date" in selections.columns else "trade_date"
        for rebalance_date, group in selections.groupby(date_col, sort=True):
            count = len(group)
            if count == 0:
                continue
            weight = min(1.0 / count, self.max_weight)
            for _, row in group.iterrows():
                holdings.append({
                    "rebalance_date": pd.Timestamp(rebalance_date),
                    "symbol": row["symbol"],
                    "target_weight": weight,
                })
        return pd.DataFrame(holdings)
