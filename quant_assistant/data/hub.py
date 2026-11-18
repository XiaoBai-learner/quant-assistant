"""Unified DataHub facade for normalized external datasets."""
from __future__ import annotations

from typing import Optional

from quant_assistant.data.datasets import MarketDataset, SignalDataset
from quant_assistant.data.providers.eastmoney_provider import EastMoneyProvider
from quant_assistant.data.providers.tencent_provider import TencentProvider


class DataHub:
    """High-level entry point for provider-backed normalized datasets."""

    def __init__(
        self,
        tencent: Optional[TencentProvider] = None,
        eastmoney: Optional[EastMoneyProvider] = None,
        market_fetcher=None,
    ):
        self.tencent = tencent or TencentProvider()
        self.eastmoney = eastmoney or EastMoneyProvider()
        self.market = MarketDataset(self.tencent, market_fetcher=market_fetcher,
                                    prefer_tencent=tencent is not None and market_fetcher is None)
        self.signals = SignalDataset(self.eastmoney)
