"""Local Parquet cache for A-share daily market data."""
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pandas as pd


class AshareDailyCache:
    """Store A-share daily bars as one Parquet file per symbol."""

    required_columns = ["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"]

    def __init__(self, cache_dir: Optional[str] = None):
        root = cache_dir or "~/.quant_assistant/cache/ashare_daily"
        self.cache_dir = Path(root).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def symbol_path(self, symbol: str) -> Path:
        """Return the Parquet file path for one symbol."""
        return self.cache_dir / f"{self._normalize_symbol(symbol)}.parquet"

    def read_symbol(self, symbol: str) -> pd.DataFrame:
        """Read cached data for one symbol."""
        path = self.symbol_path(symbol)
        if not path.exists():
            return pd.DataFrame(columns=self.required_columns)
        data = pd.read_parquet(path)
        if "trade_date" in data.columns:
            data["trade_date"] = pd.to_datetime(data["trade_date"])
        return data.sort_values("trade_date").reset_index(drop=True)

    def append_symbol(self, symbol: str, data: pd.DataFrame) -> pd.DataFrame:
        """Append rows for one symbol, deduplicate by trade date, and save."""
        normalized = self._standardize(data, symbol)
        existing = self.read_symbol(symbol)
        combined = pd.concat([existing, normalized], ignore_index=True)
        combined = (
            combined.sort_values(["trade_date"])
            .drop_duplicates(["trade_date"], keep="last")
            .reset_index(drop=True)
        )
        combined.to_parquet(self.symbol_path(symbol), index=False)
        return combined

    def stats(self) -> Dict[str, Any]:
        """Return cache-level statistics."""
        files = sorted(self.cache_dir.glob("*.parquet"))
        rows = 0
        min_date = None
        max_date = None
        for path in files:
            data = pd.read_parquet(path, columns=["trade_date"])
            if data.empty:
                continue
            dates = pd.to_datetime(data["trade_date"])
            rows += int(len(dates))
            current_min = dates.min()
            current_max = dates.max()
            min_date = current_min if min_date is None or current_min < min_date else min_date
            max_date = current_max if max_date is None or current_max > max_date else max_date
        return {
            "cache_dir": str(self.cache_dir),
            "symbol_count": len(files),
            "rows": rows,
            "start": str(min_date.date()) if min_date is not None else None,
            "end": str(max_date.date()) if max_date is not None else None,
        }

    def _standardize(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        frame = data.copy()
        frame = frame.rename(columns={
            "date": "trade_date",
            "datetime": "trade_date",
        })
        if "symbol" not in frame.columns:
            frame["symbol"] = symbol
        missing = [column for column in self.required_columns if column not in frame.columns]
        if missing:
            raise ValueError(f"行情数据缺少必要字段: {', '.join(missing)}")
        frame = frame[self.required_columns].copy()
        frame["symbol"] = self._normalize_symbol(symbol)
        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        for column in ["open", "high", "low", "close", "volume", "amount"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return str(symbol).strip()


class AshareCacheUpdater:
    """Fetch A-share daily data and append it to local Parquet cache."""

    def __init__(
        self,
        data_api: Optional[Any] = None,
        stock_list_api: Optional[Any] = None,
        cache: Optional[AshareDailyCache] = None,
    ):
        if data_api is None:
            from quant_assistant.api import QuantAPI

            data_api = QuantAPI().data
        self.data_api = data_api
        self.stock_list_api = stock_list_api or data_api
        self.cache = cache or AshareDailyCache()

    def initialize_one_year(
        self,
        end: Optional[str] = None,
        market: str = "all",
        adjust: str = "qfq",
        limit: Optional[int] = None,
        symbols: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Initialize cache with the latest one year of A-share daily data."""
        end_date = pd.Timestamp(end or pd.Timestamp.today().date())
        start_date = end_date - pd.DateOffset(years=1)
        return self.update_range(
            start=start_date.date().isoformat(),
            end=end_date.date().isoformat(),
            market=market,
            adjust=adjust,
            limit=limit,
            symbols=symbols,
        )

    def initialize_years(
        self,
        end: Optional[str] = None,
        years: int = 2,
        market: str = "all",
        adjust: str = "qfq",
        limit: Optional[int] = None,
        symbols: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Initialize cache with a configurable latest-year window."""
        if years <= 0:
            raise ValueError("years 必须大于 0")
        end_date = pd.Timestamp(end or pd.Timestamp.today().date())
        start_date = end_date - pd.DateOffset(years=years)
        return self.update_range(
            start=start_date.date().isoformat(),
            end=end_date.date().isoformat(),
            market=market,
            adjust=adjust,
            limit=limit,
            symbols=symbols,
        )

    def update_latest(
        self,
        run_date: Optional[str] = None,
        market: str = "all",
        adjust: str = "qfq",
        limit: Optional[int] = None,
        symbols: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Update cache for the previous business day."""
        target_date = self.previous_business_day(run_date)
        report = self.update_range(
            start=target_date,
            end=target_date,
            market=market,
            adjust=adjust,
            limit=limit,
            symbols=symbols,
        )
        report["date_rule"] = "previous_business_day"
        return report

    def update_range(
        self,
        start: str,
        end: str,
        market: str = "all",
        adjust: str = "qfq",
        limit: Optional[int] = None,
        symbols: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch a date range for all selected A-share symbols."""
        symbols = self._canonical_symbols(symbols) if symbols is not None else self.stock_symbols(market=market)
        if limit is not None:
            symbols = symbols[:limit]

        report = {
            "start": start,
            "end": end,
            "market": market,
            "adjust": adjust,
            "total_symbols": len(symbols),
            "success_count": 0,
            "failed_count": 0,
            "empty_count": 0,
            "symbols": {},
            "cache": {},
        }

        for symbol in symbols:
            try:
                data = self.data_api.get_stock_data(symbol, start=start, end=end, adjust=adjust)
                if data is None or data.empty:
                    report["empty_count"] += 1
                    report["symbols"][symbol] = {"status": "empty", "rows": 0, "message": "数据源返回空结果"}
                    continue
                cached = self.cache.append_symbol(symbol, data)
                report["success_count"] += 1
                report["symbols"][symbol] = {"status": "ok", "rows": int(len(data)), "cached_rows": int(len(cached))}
            except Exception as exc:  # noqa: BLE001 - third-party data sources raise heterogeneous errors
                report["failed_count"] += 1
                report["symbols"][symbol] = {"status": "failed", "rows": 0, "message": str(exc)}

        report["cache"] = self.cache.stats()
        return report

    def stock_symbols(self, market: str = "all") -> list[str]:
        """Return normalized A-share symbols from the configured stock-list API."""
        stocks = self.stock_list_api.get_stock_list(market=market)
        if stocks is None or stocks.empty:
            return []
        symbol_col = self._symbol_column(stocks.columns)
        values: Iterable[Any] = stocks[symbol_col].dropna()
        symbols = []
        seen = set()
        for value in values:
            symbol = self._canonical_a_share_symbol(value)
            if symbol and symbol not in seen:
                seen.add(symbol)
                symbols.append(symbol)
        return symbols

    def _canonical_symbols(self, symbols: Iterable[str]) -> list[str]:
        """Return canonical A-share symbols and drop unsupported instruments."""
        normalized = []
        seen = set()
        for value in symbols:
            symbol = self._canonical_a_share_symbol(value)
            if symbol and symbol not in seen:
                seen.add(symbol)
                normalized.append(symbol)
        return normalized

    @staticmethod
    def previous_business_day(run_date: Optional[str] = None) -> str:
        """Return previous business day for a run date."""
        date_value = pd.Timestamp(run_date or pd.Timestamp.today().date())
        previous = date_value - pd.offsets.BDay(1)
        return previous.date().isoformat()

    @staticmethod
    def _symbol_column(columns: Iterable[str]) -> str:
        for candidate in ["symbol", "code", "股票代码"]:
            if candidate in columns:
                return candidate
        raise ValueError("股票列表缺少 symbol/code 字段")

    @staticmethod
    def _is_a_share_stock_symbol(symbol: str) -> bool:
        return AshareCacheUpdater._canonical_a_share_symbol(symbol) is not None

    @staticmethod
    def _canonical_a_share_symbol(symbol: Any) -> Optional[str]:
        code = str(symbol).strip().split(".")[0].lower()
        if code.startswith(("sh", "sz", "bj")):
            code = code[2:]
        if len(code) != 6 or not code.isdigit():
            return None
        if code.startswith(("000", "001", "002", "003", "300", "301")):
            return f"{code}.SZ"
        if code.startswith(("600", "601", "603", "605", "688", "689")):
            return f"{code}.SH"
        if code.startswith(("43", "83", "87", "88", "92")):
            return f"{code}.BJ"
        return None
