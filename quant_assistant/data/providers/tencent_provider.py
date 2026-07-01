"""Tencent Finance provider.

Endpoint references are derived from simonlin1212/a-stock-data (Apache 2.0).
Implementation is adapted for quant-assistant provider interfaces.
"""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd

from quant_assistant.data.providers.base import ProviderResult
from quant_assistant.data.providers.http_client import HTTPClient
from quant_assistant.data.providers.symbol import normalize_symbol, tencent_code


class TencentProvider:
    """Fetch realtime quote and valuation fields from Tencent Finance."""

    source = "tencent"
    quote_url = "https://qt.gtimg.cn/q="

    def __init__(self, client: Optional[HTTPClient] = None):
        self.client = client or HTTPClient(headers={"User-Agent": "Mozilla/5.0"})

    def realtime_quote(self, symbols: list[str]) -> ProviderResult:
        """Fetch realtime quotes for one or more A-share symbols."""
        codes = ",".join(tencent_code(symbol) for symbol in symbols)
        text = self.client.get_text(self.quote_url + codes)
        return ProviderResult(
            data=self.parse_quote_text(text),
            source=self.source,
            endpoint="realtime_quote",
            params={"symbols": symbols},
        )

    def parse_quote_text(self, text: str) -> pd.DataFrame:
        """Parse Tencent quote JavaScript payload into a DataFrame."""
        rows = []
        for match in re.finditer(r'v_([a-z]{2})(\d{6})="([^"]*)"', text):
            exchange, code, payload = match.groups()
            fields = payload.split("~")
            rows.append({
                "symbol": normalize_symbol(f"{code}.{exchange.upper()}"),
                "name": fields[1] if len(fields) > 1 else "",
                "price": _to_float(fields[3] if len(fields) > 3 else None),
                "prev_close": _to_float(fields[4] if len(fields) > 4 else None),
                "open": _to_float(fields[5] if len(fields) > 5 else None),
                "volume": _to_float(fields[6] if len(fields) > 6 else None),
                "amount": _to_float(fields[9] if len(fields) > 9 else None),
            })
        return pd.DataFrame(rows)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
