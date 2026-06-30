"""Data quality diagnostics for stock-pool panels."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .universe import Universe


@dataclass
class SymbolDataQuality:
    """Quality diagnostics for one symbol."""

    symbol: str
    rows: int
    start: Optional[str]
    end: Optional[str]
    coverage: float
    missing_ohlcv: int
    duplicate_rows: int
    invalid_price_rows: int
    zero_volume_rows: int
    status: str
    reason: str = ""

    def summary(self) -> Dict[str, Any]:
        """Return a serializable summary."""
        return {
            "symbol": self.symbol,
            "rows": self.rows,
            "start": self.start,
            "end": self.end,
            "coverage": self.coverage,
            "missing_ohlcv": self.missing_ohlcv,
            "duplicate_rows": self.duplicate_rows,
            "invalid_price_rows": self.invalid_price_rows,
            "zero_volume_rows": self.zero_volume_rows,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass
class DataQualityReport:
    """Aggregated quality report for a stock-pool panel."""

    by_symbol: Dict[str, SymbolDataQuality]
    warnings: List[str] = field(default_factory=list)

    @property
    def failed_symbols(self) -> List[str]:
        """Return symbols without usable data."""
        return [symbol for symbol, item in self.by_symbol.items() if item.status == "failed"]

    @property
    def available_symbols(self) -> List[str]:
        """Return symbols with at least one usable row."""
        return [symbol for symbol, item in self.by_symbol.items() if item.status in {"ok", "warning"}]

    @classmethod
    def from_panel(
        cls,
        universe: Universe,
        panel: pd.DataFrame,
        start: str,
        end: str,
        min_coverage: float = 0.8,
        fetch_log: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> "DataQualityReport":
        """Build a quality report from a standard stock-pool panel."""
        data = panel.copy() if panel is not None else pd.DataFrame()
        if not data.empty and "trade_date" in data.columns:
            data["trade_date"] = pd.to_datetime(data["trade_date"])

        expected_days = max(len(pd.bdate_range(start=start, end=end)), 1)
        by_symbol: Dict[str, SymbolDataQuality] = {}
        warnings: List[str] = []
        logs = fetch_log or {}

        for symbol in universe.symbols:
            group = data[data["symbol"] == symbol].copy() if "symbol" in data.columns else pd.DataFrame()
            quality = cls._symbol_quality(symbol, group, expected_days, min_coverage, logs.get(symbol))
            by_symbol[symbol] = quality
            if quality.status != "ok":
                warnings.append(f"{symbol}: {quality.reason}")

        return cls(by_symbol=by_symbol, warnings=warnings)

    @staticmethod
    def _symbol_quality(
        symbol: str,
        group: pd.DataFrame,
        expected_days: int,
        min_coverage: float,
        fetch_log: Optional[Dict[str, Any]],
    ) -> SymbolDataQuality:
        if group.empty:
            reason = "无可用行情数据"
            if fetch_log and fetch_log.get("message"):
                reason = str(fetch_log["message"])
            return SymbolDataQuality(
                symbol=symbol,
                rows=0,
                start=None,
                end=None,
                coverage=0.0,
                missing_ohlcv=0,
                duplicate_rows=0,
                invalid_price_rows=0,
                zero_volume_rows=0,
                status="failed",
                reason=reason,
            )

        duplicate_rows = int(group.duplicated(["trade_date"]).sum()) if "trade_date" in group.columns else 0
        ohlcv_columns = [col for col in ["open", "high", "low", "close", "volume", "amount"] if col in group.columns]
        missing_ohlcv = int(group[ohlcv_columns].isna().sum().sum()) if ohlcv_columns else 0
        invalid_price_rows = int(
            (
                (group.get("high", pd.Series(index=group.index, dtype=float)) < group.get("low", pd.Series(index=group.index, dtype=float)))
                | (group.get("close", pd.Series(index=group.index, dtype=float)) <= 0)
            ).sum()
        )
        zero_volume_rows = int((group.get("volume", pd.Series(index=group.index, dtype=float)) <= 0).sum())
        unique_days = int(group["trade_date"].nunique()) if "trade_date" in group.columns else 0
        coverage = float(unique_days / expected_days) if expected_days else 0.0

        issues = []
        if coverage < min_coverage:
            issues.append(f"覆盖率低于阈值 {min_coverage:.0%}")
        if duplicate_rows:
            issues.append("存在重复日期")
        if missing_ohlcv:
            issues.append("存在 OHLCV 缺失")
        if invalid_price_rows:
            issues.append("存在异常价格")
        if zero_volume_rows:
            issues.append("存在零成交量")

        status = "warning" if issues else "ok"
        return SymbolDataQuality(
            symbol=symbol,
            rows=int(len(group)),
            start=str(group["trade_date"].min().date()) if "trade_date" in group.columns else None,
            end=str(group["trade_date"].max().date()) if "trade_date" in group.columns else None,
            coverage=coverage,
            missing_ohlcv=missing_ohlcv,
            duplicate_rows=duplicate_rows,
            invalid_price_rows=invalid_price_rows,
            zero_volume_rows=zero_volume_rows,
            status=status,
            reason="; ".join(issues),
        )

    def summary(self) -> Dict[str, Any]:
        """Return aggregate quality statistics."""
        total = len(self.by_symbol)
        available = len(self.available_symbols)
        failed = len(self.failed_symbols)
        coverages = [item.coverage for item in self.by_symbol.values() if item.rows > 0]
        return {
            "total_symbols": total,
            "available_symbols": available,
            "failed_symbols": failed,
            "average_coverage": float(sum(coverages) / len(coverages)) if coverages else 0.0,
            "failed_symbol_list": self.failed_symbols,
            "warnings": list(self.warnings),
        }

    def to_frame(self) -> pd.DataFrame:
        """Return symbol-level quality rows as a DataFrame."""
        return pd.DataFrame([item.summary() for item in self.by_symbol.values()])

    def export_csv(self, output_path: str) -> None:
        """Export symbol-level quality rows to a CSV file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.to_frame().to_csv(path, index=False)
