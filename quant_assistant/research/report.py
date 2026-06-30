"""Markdown reporting for stock-pool factor research."""
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from .factor_analysis import FactorAnalysisResult
from .result import SelectionResearchResult


class ResearchReport:
    """Render stock-pool research outputs as Markdown."""

    def write_markdown(
        self,
        selection_result: SelectionResearchResult,
        factor_analysis: Optional[FactorAnalysisResult] = None,
        output_path: str = "research_report.md",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write a Markdown research report to disk."""
        text = self.render_markdown(selection_result, factor_analysis=factor_analysis, metadata=metadata)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def render_markdown(
        self,
        selection_result: SelectionResearchResult,
        factor_analysis: Optional[FactorAnalysisResult] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Return a Markdown research report."""
        sections = [
            "# 股票池多因子研究报告",
            self._metadata_section(metadata or {}),
            self._data_quality_section(selection_result.data_quality),
            self._factor_section(factor_analysis),
            self._metrics_section(selection_result.metrics),
            self._latest_selection_section(selection_result.latest_selection),
            self._factor_contribution_section(selection_result.factor_contributions),
            self._warnings_section(selection_result.warnings),
        ]
        return "\n\n".join(section for section in sections if section).rstrip() + "\n"

    def _metadata_section(self, metadata: Dict[str, Any]) -> str:
        lines = ["## 研究配置"]
        if not metadata:
            lines.append("暂无配置元数据。")
            return "\n".join(lines)
        rows = [{"key": key, "value": value} for key, value in metadata.items()]
        lines.append(self._table(pd.DataFrame(rows)))
        return "\n".join(lines)

    def _data_quality_section(self, data_quality: Dict[str, Any]) -> str:
        if not data_quality:
            return "## 数据质量摘要\n暂无数据质量摘要。"
        rows = [{"key": key, "value": value} for key, value in data_quality.items() if key != "warnings"]
        lines = ["## 数据质量摘要", self._table(pd.DataFrame(rows))]
        warnings = data_quality.get("warnings", [])
        if warnings:
            lines.append("\n".join(["", "数据质量提示:", *[f"- {item}" for item in warnings]]))
        return "\n".join(lines)

    def _factor_section(self, factor_analysis: Optional[FactorAnalysisResult]) -> str:
        if factor_analysis is None:
            return "## 因子有效性摘要\n暂无因子有效性分析。"
        lines = ["## 因子有效性摘要"]
        if factor_analysis.summary_table.empty:
            lines.append("暂无因子摘要。")
        else:
            lines.append(self._table(factor_analysis.summary_table.reset_index().rename(columns={"index": "factor"})))
        if not factor_analysis.correlation_matrix.empty:
            lines.append("")
            lines.append("## 因子相关性摘要")
            lines.append(self._table(factor_analysis.correlation_matrix.reset_index().rename(columns={"index": "factor"})))
        return "\n".join(lines)

    def _metrics_section(self, metrics: Dict[str, Any]) -> str:
        lines = ["## 回测绩效摘要"]
        if not metrics:
            lines.append("暂无回测绩效。")
            return "\n".join(lines)
        rows = [{"metric": key, "value": value} for key, value in metrics.items()]
        lines.append(self._table(pd.DataFrame(rows)))
        return "\n".join(lines)

    def _latest_selection_section(self, latest_selection: pd.DataFrame) -> str:
        lines = ["## 最新一期选股"]
        if latest_selection.empty:
            lines.append("暂无选股结果。")
        else:
            lines.append(self._table(latest_selection))
        return "\n".join(lines)

    def _factor_contribution_section(self, factor_contributions: pd.DataFrame) -> str:
        lines = ["## 因子贡献摘要"]
        if factor_contributions.empty:
            lines.append("暂无因子贡献。")
        else:
            lines.append(self._table(factor_contributions.tail(10)))
        return "\n".join(lines)

    def _warnings_section(self, warnings: list[str]) -> str:
        lines = ["## 风险提示和 Warnings"]
        if not warnings:
            lines.append("暂无 warning。")
        else:
            lines.extend(f"- {warning}" for warning in warnings)
        lines.append("- 本报告仅供研究复盘使用，不构成投资建议。")
        return "\n".join(lines)

    @staticmethod
    def _table(data: pd.DataFrame) -> str:
        if data.empty:
            return ""
        return data.to_markdown(index=False)
