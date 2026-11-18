"""Normalized market datasets."""
from __future__ import annotations

import pandas as pd

from quant_assistant.data.providers.base import ProviderResult
from quant_assistant.data.providers.symbol import normalize_symbol


class MarketDataset:
    """Market data facade over market providers."""

    def __init__(self, tencent, market_fetcher=None, prefer_tencent=False):
        self.tencent = tencent
        self._fetcher = market_fetcher
        self._prefer_tencent = prefer_tencent

    def _market_fetcher(self):
        if self._fetcher is None:
            from quant_assistant.data.fetcher import UnifiedDataFetcher
            self._fetcher = UnifiedDataFetcher()
        return self._fetcher

    def daily(self, symbol, start=None, end=None, adjust="qfq") -> pd.DataFrame:
        """Use the shared TickFlow-first policy for historical daily candles."""
        return self._market_fetcher().get_daily_quotes(symbol, start, end, adjust=adjust)

    def realtime(self, symbols: list[str]) -> pd.DataFrame:
        """Return normalized realtime quote data."""
        if self._prefer_tencent:
            return _with_metadata(self.tencent.realtime_quote(symbols))
        frame = self._market_fetcher().get_realtime_quotes(symbols).copy()
        if "symbol" in frame:
            frame["symbol"] = frame["symbol"].map(normalize_symbol)
        if "price" not in frame and "close" in frame:
            frame["price"] = frame["close"]
        for source, target in (("ext.name", "name"), ("change_percent", "change_pct")):
            if source in frame and target not in frame:
                frame[target] = frame[source]
        if "ext.change_pct" in frame:
            frame["change_pct"] = frame["ext.change_pct"] * 100
        for key in ("source", "endpoint", "fetch_time"):
            if key in frame.attrs:
                frame[key] = frame.attrs[key]
        return frame

def _with_metadata(result: ProviderResult) -> pd.DataFrame:
    frame = result.data.copy() if isinstance(result.data, pd.DataFrame) else pd.DataFrame(result.data)
    frame["source"] = result.source
    frame["endpoint"] = result.endpoint
    frame["fetch_time"] = result.fetched_at
    return frame
