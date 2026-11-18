"""TickFlow SDK adapter for historical research and account-scoped market data.

``free`` uses the anonymous historical service. ``authenticated`` uses the API
key's actual permissions; having a key does not imply a paid subscription.
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import re

import pandas as pd
from dotenv import load_dotenv
from tickflow import TickFlow

from quant_assistant.core.exceptions import DataFetchException
from quant_assistant.data.fetcher.base_fetcher import BaseDataFetcher
from quant_assistant.data.providers.rate_limiter import SerialRateLimiter
from quant_assistant.data.providers.symbol import normalize_symbol


class TickFlowFetcher(BaseDataFetcher):
    FREE_API_BASE = "https://free-api.tickflow.org"
    PAID_API_BASE = "https://api.tickflow.org"
    ADJUSTMENTS = {
        "qfq": "forward_additive",
        "hfq": "backward_additive",
        "": "none",
        "none": "none",
        "forward": "forward",
        "backward": "backward",
        "forward_additive": "forward_additive",
        "backward_additive": "backward_additive",
    }
    DAILY_COLUMNS = ["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"]
    PAGE_SIZE = 10000

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_paid: Optional[bool] = None,
        *,
        mode: Optional[str] = None,
        client=None,
        timeout: float = 15.0,
        max_retries: int = 2,
        min_interval: float = 1.1,
    ):
        load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
        self.name = "TickFlow"
        self.api_key = api_key if api_key is not None else os.getenv("TICKFLOW_API_KEY", "")
        self.mode = mode or (
            ("authenticated" if use_paid else "free")
            if use_paid is not None
            else os.getenv("TICKFLOW_MODE") or ("authenticated" if self.api_key else "free")
        )
        if self.mode not in {"free", "authenticated"}:
            raise ValueError("TICKFLOW_MODE 必须是 free 或 authenticated")
        if self.mode == "authenticated" and not self.api_key and client is None:
            raise ValueError("TickFlow 认证模式需要 TICKFLOW_API_KEY")
        self.use_paid = self.mode == "authenticated"  # Legacy constructor compatibility only.
        self.base_url = self.PAID_API_BASE if self.use_paid else self.FREE_API_BASE
        self._limiter = SerialRateLimiter(min_interval=min_interval)
        # An explicit empty key prevents the SDK reading credentials in anonymous mode.
        self._client = (
            client
            if client is not None
            else TickFlow(
                api_key=self.api_key if self.use_paid else "",
                base_url=self.base_url,
                timeout=timeout,
                max_retries=max_retries,
            )
        )

    def _call(self, endpoint: str, method, *args, **kwargs):
        self._limiter.wait()
        try:
            return method(*args, **kwargs)
        except Exception as error:
            status = getattr(error, "status_code", None)
            message = str(error)
            if self.api_key:
                message = message.replace(self.api_key, "[REDACTED]")
            raise DataFetchException(
                f"TickFlow {endpoint} 请求失败"
                + (f" (HTTP {status})" if status else "")
                + f": {message}",
                details={
                    "source": "tickflow",
                    "mode": self.mode,
                    "endpoint": endpoint,
                    "status_code": status,
                    "api_code": getattr(error, "code", None),
                },
            ) from None

    def _require_authenticated(self, capability: str):
        if self.mode == "free":
            raise DataFetchException(
                f"TickFlow 匿名免费服务不支持{capability}；可选择 authenticated 模式测试 Key 的实际权限",
                details={"source": "tickflow", "mode": self.mode, "capability": capability},
            )

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        value = normalize_symbol(symbol)
        if "." not in value and re.fullmatch(r"\d{6}", value):
            if value.startswith(("5", "6", "9")):
                value += ".SH"
            elif value.startswith(("0", "1", "2", "3")):
                value += ".SZ"
            elif value.startswith(("4", "8")):
                value += ".BJ"
        if not re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", value):
            raise ValueError(f"不支持的 A 股标的代码: {symbol}")
        return value

    def _metadata(self, endpoint: str, **extra) -> dict:
        return {
            "source": "tickflow",
            "mode": self.mode,
            "endpoint": endpoint,
            "fetch_time": pd.Timestamp.now(tz="Asia/Shanghai").isoformat(),
            **extra,
        }

    def get_exchanges(self) -> pd.DataFrame:
        frame = pd.DataFrame(self._call("exchanges", self._client.exchanges.list))
        frame.attrs = self._metadata("exchanges")
        return frame

    def get_stock_list(self, exchange: Optional[str] = None) -> pd.DataFrame:
        exchanges = [exchange.upper()] if exchange else ["SH", "SZ", "BJ"]
        if any(ex not in {"SH", "SZ", "BJ"} for ex in exchanges):
            raise ValueError("交易所必须是 SH、SZ 或 BJ")
        instruments = []
        for ex in exchanges:
            # Never return a partial exchange list as though it were the whole market.
            instruments.extend(
                self._call(
                    f"exchanges/{ex}/instruments",
                    self._client.exchanges.get_instruments,
                    ex,
                    instrument_type="stock",
                )
            )
        frame = pd.DataFrame(instruments)
        if frame.empty:
            frame = pd.DataFrame(columns=["symbol", "name", "exchange"])
        else:
            frame = frame[
                frame["symbol"].str.match(
                    r"^(?:(?:600|601|603|605|688|689)\d{3}\.SH|(?:000|001|002|003|300|301)\d{3}\.SZ|(?:43|83|87|88|92)\d{4}\.BJ)$"
                )
            ].copy()
            frame["symbol"] = frame["symbol"].str.split(".", regex=False).str[0]
            frame = frame.drop_duplicates("symbol").reset_index(drop=True)
        frame.attrs = self._metadata("exchanges/instruments")
        return frame

    @staticmethod
    def _bound(value, *, end=False):
        if value is None:
            return None
        stamp = pd.Timestamp(value)
        stamp = (
            stamp.tz_localize("Asia/Shanghai")
            if stamp.tzinfo is None
            else stamp.tz_convert("Asia/Shanghai")
        )
        if end:
            stamp = stamp.normalize() + pd.DateOffset(days=1) - pd.Timedelta(milliseconds=1)
        return int(stamp.timestamp() * 1000)

    def _klines(self, symbol, period, start_date, end_date, adjust):
        symbol = self._convert_symbol(symbol)
        if adjust not in self.ADJUSTMENTS:
            raise ValueError(f"不支持的复权方式: {adjust}")
        adjustment = self.ADJUSTMENTS[adjust]
        start, end = self._bound(start_date), self._bound(end_date, end=True)
        if start is not None and end is not None and start > end:
            raise ValueError("开始日期不能晚于结束日期")
        params = {"period": period, "count": self.PAGE_SIZE, "adjust": adjustment}
        if start is not None:
            params["start_time"] = start
        if end is not None:
            params["end_time"] = end
        pages = []
        previous_first = None
        while True:
            raw = self._call("klines", self._client.klines.get, symbol, **params)
            if not isinstance(raw, dict) or "timestamp" not in raw:
                raise DataFetchException("TickFlow K线返回格式错误，缺少 timestamp")
            if not raw["timestamp"]:
                break
            required = ["timestamp", "open", "high", "low", "close", "volume", "amount"]
            if any(key not in raw or len(raw[key]) != len(raw["timestamp"]) for key in required):
                raise DataFetchException("TickFlow K线字段缺失或数组长度不一致")
            page = pd.DataFrame({key: raw[key] for key in required})
            first = int(page.timestamp.min())
            if previous_first is not None and first >= previous_first:
                raise DataFetchException("TickFlow K线分页未向前推进，拒绝返回截断历史数据")
            pages.append(page)
            if len(page) < self.PAGE_SIZE or (start is not None and first <= start):
                break
            previous_first = first
            params["end_time"] = first - 1
        if not pages:
            frame = pd.DataFrame(
                columns=self.DAILY_COLUMNS + (["datetime"] if period.endswith("m") else [])
            )
        else:
            frame = pd.concat(pages, ignore_index=True)
            if start is not None:
                frame = frame[frame.timestamp >= start]
            if end is not None:
                frame = frame[frame.timestamp <= end]
            frame = frame.sort_values("timestamp").drop_duplicates("timestamp", keep="last")
            local_time = (
                pd.to_datetime(frame.timestamp, unit="ms", utc=True)
                .dt.tz_convert("Asia/Shanghai")
                .dt.tz_localize(None)
            )
            frame["trade_date"] = local_time.dt.normalize()
            if period.endswith("m"):
                frame["datetime"] = local_time
            frame["symbol"] = symbol.split(".")[0]
            for column in ["open", "high", "low", "close", "volume", "amount"]:
                frame[column] = pd.to_numeric(frame[column], errors="raise")
            frame = frame.drop(columns="timestamp").reset_index(drop=True)
        frame.attrs = self._metadata(
            "klines", adjust=adjustment, period=period, volume_unit="lot", amount_unit="CNY"
        )
        return frame

    def get_daily_quotes(
        self, symbol: str, start_date=None, end_date=None, adjust="qfq"
    ) -> pd.DataFrame:
        return self._klines(symbol, "1d", start_date, end_date, adjust)

    def get_daily_quotes_incremental(
        self, symbol: str, last_date: Optional[date] = None, end_date=None, adjust="qfq"
    ):
        start = (last_date + timedelta(days=1)).isoformat() if last_date else None
        end_date = end_date or (date.today() - timedelta(days=1)).isoformat()
        if start and pd.Timestamp(start) > pd.Timestamp(end_date):
            return pd.DataFrame(columns=self.DAILY_COLUMNS)
        return self.get_daily_quotes(symbol, start, end_date, adjust)

    def get_minute_quotes(
        self, symbol: str, period="5m", start_date=None, end_date=None
    ) -> pd.DataFrame:
        self._require_authenticated("分钟K线")
        if period not in {"1m", "5m", "15m", "30m", "60m"}:
            raise ValueError(f"不支持的分钟周期: {period}")
        return self._klines(symbol, period, start_date, end_date, "none")

    def get_realtime_quotes(self, symbols: List[str]) -> pd.DataFrame:
        self._require_authenticated("实时行情")
        symbols = [self._convert_symbol(symbol) for symbol in symbols]
        records = self._call("quotes", self._client.quotes.get, symbols=symbols) if symbols else []
        frame = pd.json_normalize(records)
        returned = set(frame["symbol"]) if "symbol" in frame else set()
        missing = set(symbols) - returned
        if missing:
            raise DataFetchException(
                f"TickFlow 实时行情返回不完整，缺少: {', '.join(sorted(missing))}",
                details={"source": "tickflow", "missing_symbols": sorted(missing)},
            )
        if not frame.empty:
            frame = frame.rename(columns={"last_price": "price"})
        frame.attrs = self._metadata("quotes")
        return frame

    def _financial(self, symbol, statement):
        self._require_authenticated("财务数据")
        symbol = self._convert_symbol(symbol)
        data = self._call(
            f"financials/{statement}", getattr(self._client.financials, statement), [symbol]
        )
        frame = pd.DataFrame(data.get(symbol, []))
        frame["symbol"] = symbol.split(".")[0]
        frame.attrs = self._metadata(f"financials/{statement}")
        return frame

    def get_financial_indicators(self, symbol: str) -> pd.DataFrame:
        return self._financial(symbol, "metrics")

    def get_income_statement(self, symbol: str) -> pd.DataFrame:
        return self._financial(symbol, "income")

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        return self._financial(symbol, "balance_sheet")

    def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        return self._financial(symbol, "cash_flow")

    def get_instrument_info(self, symbol: str) -> Dict[str, Any]:
        return self._call("instruments", self._client.instruments.get, self._convert_symbol(symbol))

    def is_available(self) -> bool:
        try:
            return bool(self.get_instrument_info("600000.SH"))
        except DataFetchException:
            return False

    def close(self):
        self._client.close()

    def __repr__(self):
        return f"TickFlowFetcher(mode={self.mode!r}, api_key={'set' if self.api_key else 'unset'})"
