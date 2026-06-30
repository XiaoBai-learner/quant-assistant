"""Experiment metadata records for stock-pool research."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from .factor_analysis import FactorAnalysisResult
from .panel import DataBundle
from .result import SelectionResearchResult


@dataclass
class ExperimentRecord:
    """Serializable metadata for one research experiment."""

    name: str
    universe: Dict[str, Any]
    period: Dict[str, Any]
    strategy: Dict[str, Any]
    data_quality: Dict[str, Any] = field(default_factory=dict)
    factor_summary: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    git_commit: Optional[str] = None
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable payload."""
        return {
            "name": self.name,
            "created_at": self.created_at,
            "universe": self.universe,
            "period": self.period,
            "strategy": self.strategy,
            "data_quality": self.data_quality,
            "factor_summary": self.factor_summary,
            "metrics": self.metrics,
            "git_commit": self.git_commit,
            "notes": self.notes,
        }

    def export_json(self, output_path: str) -> None:
        """Write the experiment record to a pretty JSON file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    @classmethod
    def from_research(
        cls,
        name: str,
        bundle: DataBundle,
        factors: Dict[str, float],
        top_n: int,
        rebalance: str,
        result: SelectionResearchResult,
        factor_analysis: Optional[FactorAnalysisResult] = None,
        git_commit: Optional[str] = None,
        notes: str = "",
    ) -> "ExperimentRecord":
        """Create a record from a completed stock-pool research run."""
        universe = {
            "name": bundle.universe.name,
            "source": bundle.universe.source,
            "symbols": bundle.symbols,
            "symbol_count": len(bundle.symbols),
        }
        strategy = {
            "factors": dict(factors),
            "top_n": top_n,
            "rebalance": rebalance,
        }
        factor_summary = (
            factor_analysis.summary_table.to_dict(orient="index")
            if factor_analysis is not None and not factor_analysis.summary_table.empty
            else {}
        )
        return cls(
            name=name,
            universe=universe,
            period={"start": bundle.start, "end": bundle.end},
            strategy=strategy,
            data_quality=dict(result.data_quality),
            factor_summary=factor_summary,
            metrics=dict(result.metrics),
            git_commit=git_commit or cls.current_git_commit(),
            notes=notes,
        )

    @staticmethod
    def current_git_commit() -> Optional[str]:
        """Return the current short git commit hash when available."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        return result.stdout.strip() or None


class ExperimentComparison:
    """Compare multiple exported experiment records."""

    def __init__(self, records: Iterable[Dict[str, Any]]):
        self.records = list(records)

    @classmethod
    def from_json_files(cls, paths: Iterable[str]) -> "ExperimentComparison":
        """Load experiment records from JSON files."""
        records = []
        for path in paths:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            records.append(payload)
        return cls(records)

    @classmethod
    def from_directory(cls, directory: str, pattern: str = "*.json") -> "ExperimentComparison":
        """Load experiment records from a directory."""
        paths = sorted(str(path) for path in Path(directory).glob(pattern))
        return cls.from_json_files(paths)

    def to_frame(self, sort_by: str = "total_return", ascending: bool = False) -> pd.DataFrame:
        """Return a flattened comparison table."""
        rows = [self._flatten_record(record) for record in self.records]
        table = pd.DataFrame(rows)
        if sort_by in table.columns:
            table = table.sort_values(sort_by, ascending=ascending, na_position="last")
        return table.reset_index(drop=True)

    def export_csv(self, output_path: str, sort_by: str = "total_return", ascending: bool = False) -> None:
        """Export the comparison table to CSV."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.to_frame(sort_by=sort_by, ascending=ascending).to_csv(path, index=False)

    @staticmethod
    def _flatten_record(record: Dict[str, Any]) -> Dict[str, Any]:
        universe = record.get("universe", {}) or {}
        period = record.get("period", {}) or {}
        strategy = record.get("strategy", {}) or {}
        data_quality = record.get("data_quality", {}) or {}
        metrics = record.get("metrics", {}) or {}
        factor_summary = record.get("factor_summary", {}) or {}
        factors = strategy.get("factors", {}) or {}
        return {
            "name": record.get("name"),
            "created_at": record.get("created_at"),
            "start": period.get("start"),
            "end": period.get("end"),
            "symbol_count": universe.get("symbol_count"),
            "available_symbols": data_quality.get("available_symbols"),
            "top_n": strategy.get("top_n"),
            "rebalance": strategy.get("rebalance"),
            "factor_count": len(factors),
            "total_return": metrics.get("total_return"),
            "max_drawdown": metrics.get("max_drawdown"),
            "mean_rank_ic": ExperimentComparison._mean_factor_value(factor_summary, "rank_ic_mean"),
            "mean_top_bottom": ExperimentComparison._mean_factor_value(factor_summary, "top_bottom_mean"),
            "git_commit": record.get("git_commit"),
            "notes": record.get("notes"),
        }

    @staticmethod
    def _mean_factor_value(factor_summary: Dict[str, Any], key: str) -> Optional[float]:
        values: List[float] = []
        for item in factor_summary.values():
            value = item.get(key) if isinstance(item, dict) else None
            if value is not None:
                values.append(float(value))
        if not values:
            return None
        return float(sum(values) / len(values))
