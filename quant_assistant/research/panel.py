"""Data bundle utilities for stock-pool research."""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

import pandas as pd

from .data_quality import DataQualityReport
from .universe import Universe


@dataclass
class DataBundle:
    """Reusable multi-stock data package for selection research."""

    universe: Universe
    panel: pd.DataFrame
    start: str
    end: str
    quality: Optional[DataQualityReport] = None
    fetch_log: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def symbols(self) -> List[str]:
        """Return the configured universe symbols."""
        return list(self.universe.symbols)

    def summary(self) -> Dict[str, Any]:
        """Return a compact summary for logs and reports."""
        return {
            "universe": self.universe.name,
            "symbol_count": len(self.universe.symbols),
            "rows": int(len(self.panel)),
            "start": self.start,
            "end": self.end,
        }


DataLoader = Callable[[str, str, str, str], pd.DataFrame]


class DataBundleBuilder:
    """Build multi-stock data bundles with partial failure tolerance."""

    required_columns = ["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"]

    def __init__(self, data_api: Optional[Any] = None, loader: Optional[DataLoader] = None):
        self.data_api = data_api
        self.loader = loader

    def build(
        self,
        universe: Iterable[Optional[str]] | Universe,
        start: str,
        end: str,
        adjust: str = "qfq",
        min_coverage: float = 0.8,
    ) -> DataBundle:
        """Fetch and validate a stock-pool panel."""
        universe_obj = universe if isinstance(universe, Universe) else Universe.from_symbols(universe)
        frames: List[pd.DataFrame] = []
        fetch_log: Dict[str, Dict[str, Any]] = {}

        for symbol in universe_obj.symbols:
            try:
                raw = self._load_symbol(symbol, start, end, adjust)
                if raw is None or raw.empty:
                    fetch_log[symbol] = {"status": "empty", "rows": 0, "message": "数据源返回空结果"}
                    continue
                frame = self._standardize_symbol_frame(raw, symbol)
                frames.append(frame)
                fetch_log[symbol] = {"status": "ok", "rows": int(len(frame)), "message": ""}
            except Exception as exc:  # noqa: BLE001 - fetchers use heterogeneous exceptions
                fetch_log[symbol] = {"status": "failed", "rows": 0, "message": str(exc)}

        panel = self._combine_frames(frames)
        if panel.empty:
            quality = DataQualityReport.from_panel(universe_obj, panel, start, end, min_coverage, fetch_log)
            raise ValueError(f"股票池没有可用行情数据: {quality.failed_symbols}")

        quality = DataQualityReport.from_panel(universe_obj, panel, start, end, min_coverage, fetch_log)
        return DataBundle(
            universe=universe_obj,
            panel=panel,
            start=start,
            end=end,
            quality=quality,
            fetch_log=fetch_log,
        )

    def _load_symbol(self, symbol: str, start: str, end: str, adjust: str) -> pd.DataFrame:
        if self.loader is not None:
            return self.loader(symbol, start, end, adjust)
        if self.data_api is None:
            raise ValueError("DataBundleBuilder 需要 data_api 或 loader")
        return self.data_api.get_stock_data(symbol, start=start, end=end, adjust=adjust)

    def _standardize_symbol_frame(self, frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
        data = frame.copy()
        rename_map = {"date": "trade_date", "datetime": "trade_date"}
        data = data.rename(columns={old: new for old, new in rename_map.items() if old in data.columns})
        if "symbol" not in data.columns:
            data["symbol"] = symbol
        data["symbol"] = data["symbol"].fillna(symbol).astype(str)

        missing = [column for column in self.required_columns if column not in data.columns]
        if missing:
            raise ValueError(f"行情数据缺少必要字段: {', '.join(missing)}")

        data = data[self.required_columns].copy()
        data["trade_date"] = pd.to_datetime(data["trade_date"])
        for column in ["open", "high", "low", "close", "volume", "amount"]:
            data[column] = pd.to_numeric(data[column], errors="coerce")
        return data

    def _combine_frames(self, frames: List[pd.DataFrame]) -> pd.DataFrame:
        if not frames:
            return pd.DataFrame(columns=self.required_columns)
        panel = pd.concat(frames, ignore_index=True)
        return (
            panel.sort_values(["symbol", "trade_date"])
            .drop_duplicates(["symbol", "trade_date"], keep="last")
            .reset_index(drop=True)
        )
