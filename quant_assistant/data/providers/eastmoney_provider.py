"""EastMoney provider.

Endpoint references are derived from simonlin1212/a-stock-data (Apache 2.0).
Implementation is adapted for quant-assistant provider interfaces, caching,
rate limiting, and schema normalization.
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from quant_assistant.data.providers.base import ProviderResult
from quant_assistant.data.providers.http_client import HTTPClient
from quant_assistant.data.providers.rate_limiter import SerialRateLimiter
from quant_assistant.data.providers.symbol import eastmoney_secid, normalize_symbol


class EastMoneyProvider:
    """Fetch EastMoney-only A-share signal and event datasets."""

    source = "eastmoney"
    push2ex_url = "https://push2ex.eastmoney.com/getTopicZTPool"
    push2_url = "https://push2.eastmoney.com/api/qt/clist/get"
    push2his_url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"

    def __init__(self, client: Optional[HTTPClient] = None):
        self.client = client or HTTPClient(
            headers={
                "User-Agent": "Mozilla/5.0 quant-assistant/1.0",
                "Referer": "https://quote.eastmoney.com/",
            },
            limiter=SerialRateLimiter(min_interval=1.2, jitter=(0.2, 0.8)),
        )

    def limit_up_pool(self, trade_date: str) -> ProviderResult:
        """Fetch EastMoney limit-up pool for a trade date."""
        params = self._limit_pool_params(trade_date, "zt")
        payload = self.client.get_json(self.push2ex_url, params=params)
        return ProviderResult(
            data=self.parse_limit_up_pool(payload, trade_date),
            source=self.source,
            endpoint="limit_up_pool",
            params=params,
        )

    def broken_limit_pool(self, trade_date: str) -> ProviderResult:
        """Fetch EastMoney broken limit-up pool for a trade date."""
        params = self._limit_pool_params(trade_date, "zbgc")
        payload = self.client.get_json(self.push2ex_url, params=params)
        return ProviderResult(
            data=self.parse_limit_up_pool(payload, trade_date),
            source=self.source,
            endpoint="broken_limit_pool",
            params=params,
        )

    def limit_down_pool(self, trade_date: str) -> ProviderResult:
        """Fetch EastMoney limit-down pool for a trade date."""
        params = self._limit_pool_params(trade_date, "dtgc")
        payload = self.client.get_json(self.push2ex_url, params=params)
        return ProviderResult(
            data=self.parse_limit_up_pool(payload, trade_date),
            source=self.source,
            endpoint="limit_down_pool",
            params=params,
        )

    def industry_rank(self, trade_date: Optional[str] = None) -> ProviderResult:
        """Fetch EastMoney industry ranking snapshot."""
        params = {
            "pn": 1,
            "pz": 200,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fid": "f3",
            "fs": "m:90+t:2",
            "fields": "f12,f14,f3,f104,f105",
        }
        payload = self.client.get_json(self.push2_url, params=params)
        return ProviderResult(
            data=self.parse_industry_rank(payload, trade_date=trade_date),
            source=self.source,
            endpoint="industry_rank",
            params=params,
        )

    def concept_blocks(self, symbol: str) -> ProviderResult:
        """Fetch EastMoney concept and block membership for one symbol."""
        normalized = normalize_symbol(symbol)
        params = {
            "pn": 1,
            "pz": 200,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fid": "f3",
            "fs": f"b:{normalized.split('.')[0]}",
            "fields": "f12,f14,f3,f128",
        }
        payload = self.client.get_json(self.push2_url, params=params)
        return ProviderResult(
            data=self.parse_concept_blocks(payload, symbol=normalized),
            source=self.source,
            endpoint="concept_blocks",
            params=params,
        )

    def stock_fund_flow_120d(self, symbol: str) -> ProviderResult:
        """Fetch daily capital flow history for one stock."""
        normalized = normalize_symbol(symbol)
        params = {
            "lmt": 120,
            "klt": 101,
            "secid": eastmoney_secid(normalized),
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
        }
        payload = self.client.get_json(self.push2his_url, params=params)
        frame = self.parse_stock_fund_flow_120d(payload, symbol=normalized)
        return ProviderResult(
            data=frame,
            source=self.source,
            endpoint="stock_fund_flow_120d",
            params=params,
        )

    def parse_limit_up_pool(self, payload: dict[str, Any], trade_date: str) -> pd.DataFrame:
        """Normalize EastMoney limit-board pool payload."""
        rows = []
        for item in _records(payload):
            code = str(item.get("c") or item.get("f12") or "")
            rows.append({
                "trade_date": trade_date,
                "symbol": normalize_symbol(code),
                "name": item.get("n") or item.get("f14") or "",
                "consecutive_boards": _to_int(item.get("lbc") or item.get("f20")),
                "sealed_amount": _to_float(item.get("fund") or item.get("f8")),
                "first_limit_time": _format_time(item.get("fbt") or item.get("f9")),
                "last_limit_time": _format_time(item.get("lbt") or item.get("f10")),
                "open_count": _to_int(item.get("zbc") or item.get("f11")),
                "source": self.source,
            })
        return pd.DataFrame(rows)

    def parse_industry_rank(
        self,
        payload: dict[str, Any],
        trade_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Normalize EastMoney industry ranking payload."""
        rows = []
        for item in _records(payload):
            rows.append({
                "trade_date": trade_date,
                "industry_code": item.get("f12") or item.get("code"),
                "industry": item.get("f14") or item.get("name"),
                "pct_change": _to_float(item.get("f3") or item.get("pct_change")),
                "rising_count": _to_int(item.get("f104") or item.get("rising_count")),
                "falling_count": _to_int(item.get("f105") or item.get("falling_count")),
                "source": self.source,
            })
        return pd.DataFrame(rows)

    def parse_concept_blocks(self, payload: dict[str, Any], symbol: str) -> pd.DataFrame:
        """Normalize EastMoney concept block membership payload."""
        rows = []
        normalized = normalize_symbol(symbol)
        for item in _records(payload):
            rows.append({
                "symbol": normalized,
                "block_code": item.get("f12") or item.get("code"),
                "block_name": item.get("f14") or item.get("name"),
                "pct_change": _to_float(item.get("f3") or item.get("pct_change")),
                "leader": item.get("f128") or item.get("leader"),
                "source": self.source,
            })
        return pd.DataFrame(rows)

    def parse_stock_fund_flow_120d(self, payload: dict[str, Any], symbol: str) -> pd.DataFrame:
        """Normalize EastMoney 120-day stock fund-flow payload."""
        klines = payload.get("data", {}).get("klines") or []
        rows = []
        normalized = normalize_symbol(symbol)
        for row in klines:
            fields = str(row).split(",")
            rows.append({
                "trade_date": fields[0] if len(fields) > 0 else None,
                "symbol": normalized,
                "main_net_inflow": _to_float(fields[1] if len(fields) > 1 else None),
                "small_net_inflow": _to_float(fields[2] if len(fields) > 2 else None),
                "medium_net_inflow": _to_float(fields[3] if len(fields) > 3 else None),
                "large_net_inflow": _to_float(fields[4] if len(fields) > 4 else None),
                "super_large_net_inflow": _to_float(fields[5] if len(fields) > 5 else None),
                "source": self.source,
            })
        return pd.DataFrame(rows)

    @staticmethod
    def _limit_pool_params(trade_date: str, pool_type: str) -> dict[str, Any]:
        return {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": 0,
            "pagesize": 5000,
            "sort": "fbt:asc",
            "date": trade_date.replace("-", ""),
            "type": pool_type,
        }


def _records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    if isinstance(data, dict):
        records = data.get("pool") or data.get("diff") or data.get("list") or []
        return records if isinstance(records, list) else []
    return data if isinstance(data, list) else []


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _format_time(value) -> str:
    if value is None:
        return ""
    text = str(value).zfill(6)
    if len(text) == 6:
        return f"{text[:2]}:{text[2:4]}:{text[4:]}"
    return str(value)
