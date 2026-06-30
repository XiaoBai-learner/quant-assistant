"""Experiment metadata records for stock-pool research."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, Optional

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
