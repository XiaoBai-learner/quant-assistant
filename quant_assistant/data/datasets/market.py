"""Normalized market datasets."""
from __future__ import annotations

import pandas as pd

from quant_assistant.data.providers.base import ProviderResult


class MarketDataset:
    """Market data facade over market providers."""

    def __init__(self, tencent):
        self.tencent = tencent

    def realtime(self, symbols: list[str]) -> pd.DataFrame:
        """Return normalized realtime quote data."""
        result = self.tencent.realtime_quote(symbols)
        return _with_metadata(result)


def _with_metadata(result: ProviderResult) -> pd.DataFrame:
    frame = result.data.copy() if isinstance(result.data, pd.DataFrame) else pd.DataFrame(result.data)
    frame["source"] = result.source
    frame["endpoint"] = result.endpoint
    frame["fetch_time"] = result.fetched_at
    return frame
