"""Normalized signal datasets."""
from __future__ import annotations

import pandas as pd

from quant_assistant.data.providers.base import ProviderResult


class SignalDataset:
    """Signal data facade over event and signal providers."""

    def __init__(self, eastmoney):
        self.eastmoney = eastmoney

    def limit_up_pool(self, trade_date: str) -> pd.DataFrame:
        """Return normalized limit-up pool data."""
        return _with_metadata(self.eastmoney.limit_up_pool(trade_date))

    def broken_limit_pool(self, trade_date: str) -> pd.DataFrame:
        """Return normalized broken limit-up pool data."""
        return _with_metadata(self.eastmoney.broken_limit_pool(trade_date))

    def limit_down_pool(self, trade_date: str) -> pd.DataFrame:
        """Return normalized limit-down pool data."""
        return _with_metadata(self.eastmoney.limit_down_pool(trade_date))

    def industry_rank(self, trade_date: str | None = None) -> pd.DataFrame:
        """Return normalized industry ranking data."""
        return _with_metadata(self.eastmoney.industry_rank(trade_date=trade_date))


def _with_metadata(result: ProviderResult) -> pd.DataFrame:
    frame = result.data.copy() if isinstance(result.data, pd.DataFrame) else pd.DataFrame(result.data)
    frame["source"] = result.source
    frame["endpoint"] = result.endpoint
    frame["fetch_time"] = result.fetched_at
    return frame
