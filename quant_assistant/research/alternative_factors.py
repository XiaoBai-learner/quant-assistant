"""Alternative data factors for stock-pool research."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_limit_board_features(limit_up_events: pd.DataFrame) -> pd.DataFrame:
    """Build daily limit-board features by symbol."""
    if limit_up_events.empty:
        return pd.DataFrame(columns=["trade_date", "symbol", "limit_up_score"])

    data = limit_up_events.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"])
    data["consecutive_boards"] = pd.to_numeric(
        data.get("consecutive_boards", 0),
        errors="coerce",
    ).fillna(0)
    data["sealed_amount"] = pd.to_numeric(
        data.get("sealed_amount", 0),
        errors="coerce",
    ).fillna(0)
    data["limit_up_score"] = data["consecutive_boards"] + np.log1p(data["sealed_amount"]) / 20
    return data[["trade_date", "symbol", "limit_up_score"]]
