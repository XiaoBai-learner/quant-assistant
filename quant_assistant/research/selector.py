"""Top-N stock pool selection."""
import pandas as pd


class StockPoolSelector:
    """Select top ranked stocks on each rebalance date."""

    def __init__(self, top_n: int = 10, min_score: float | None = None):
        if top_n <= 0:
            raise ValueError("top_n 必须大于 0")
        self.top_n = top_n
        self.min_score = min_score

    def select(self, scored: pd.DataFrame) -> pd.DataFrame:
        """Return selected rows with rank and rebalance_date."""
        selections = []
        data = scored.copy()
        data["trade_date"] = pd.to_datetime(data["trade_date"])
        for trade_date, group in data.groupby("trade_date", sort=True):
            candidates = group.dropna(subset=["score"]).sort_values("score", ascending=False)
            if self.min_score is not None:
                candidates = candidates[candidates["score"] >= self.min_score]
            selected = candidates.head(self.top_n).copy()
            selected["rank"] = range(1, len(selected) + 1)
            selected["selected"] = True
            selected["rebalance_date"] = pd.Timestamp(trade_date)
            selections.append(selected)
        if not selections:
            return pd.DataFrame(columns=[*scored.columns, "rank", "selected", "rebalance_date"])
        return pd.concat(selections, ignore_index=True)
