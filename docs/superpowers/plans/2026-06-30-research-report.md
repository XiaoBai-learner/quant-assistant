# Research Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add Markdown research report generation that combines data quality, factor diagnostics, selection backtest metrics, latest picks, and warnings into one reproducible artifact.

**Architecture:** Add `quant_assistant.research.report` as a formatting-only module. It consumes existing `SelectionResearchResult`, optional `FactorAnalysisResult`, and optional data bundle/metadata summaries; it does not recompute data, factors, or backtests.

**Tech Stack:** Python 3.10+, dataclasses, pandas, pytest, Markdown text output.

---

## File Structure

- Create `quant_assistant/research/report.py`: `ResearchReport` Markdown renderer.
- Modify `quant_assistant/research/__init__.py`: export `ResearchReport`.
- Create `tests/test_research_report.py`: report rendering tests with small synthetic result objects.
- Modify `README.md`: add `ResearchReport().write_markdown(...)` example.

## Task 1: Basic Markdown Report

**Files:**
- Create: `quant_assistant/research/report.py`
- Modify: `quant_assistant/research/__init__.py`
- Test: `tests/test_research_report.py`

- [x] **Step 1: Write failing test**

```python
import pandas as pd

from quant_assistant.research import ResearchReport, SelectionResearchResult


def make_selection_result():
    return SelectionResearchResult(
        metrics={"total_return": 0.12, "max_drawdown": -0.08},
        selections=pd.DataFrame({
            "rebalance_date": pd.to_datetime(["2024-03-29", "2024-03-29"]),
            "symbol": ["000001", "600000"],
            "rank": [1, 2],
            "score": [1.2, 0.8],
        }),
        factor_contributions=pd.DataFrame({
            "trade_date": pd.to_datetime(["2024-03-29"]),
            "symbol": ["000001"],
            "momentum_20_contribution": [0.7],
        }),
        warnings=["sample warning"],
    )


def test_research_report_renders_core_markdown_sections(tmp_path):
    output = tmp_path / "report.md"

    ResearchReport().write_markdown(make_selection_result(), output_path=str(output))

    text = output.read_text()
    assert "# 股票池多因子研究报告" in text
    assert "## 研究配置" in text
    assert "## 回测绩效摘要" in text
    assert "## 最新一期选股" in text
    assert "sample warning" in text
```

- [x] **Step 2: Run test and verify RED**

Run: `python -m pytest tests/test_research_report.py::test_research_report_renders_core_markdown_sections -q`

Expected: FAIL because `ResearchReport` is not exported.

- [x] **Step 3: Implement minimal report**

Implement `ResearchReport.write_markdown(selection_result, factor_analysis=None, output_path="research_report.md", metadata=None)` that writes:

- Title.
- Research config section from metadata.
- Backtest metrics table.
- Latest selection table.
- Warnings section.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_report.py -q`

Expected: PASS.

## Task 2: Data Quality And Factor Analysis Sections

**Files:**
- Modify: `quant_assistant/research/report.py`
- Test: `tests/test_research_report.py`

- [x] **Step 1: Write failing test**

```python
from quant_assistant.research import FactorAnalysisResult


def test_research_report_includes_data_quality_and_factor_analysis(tmp_path):
    output = tmp_path / "report.md"
    factor_analysis = FactorAnalysisResult(
        summary_table=pd.DataFrame({
            "rank_ic_mean": [0.05],
            "icir": [0.8],
            "top_bottom_mean": [0.02],
            "factor_coverage": [0.95],
        }, index=["momentum_20"]),
        correlation_matrix=pd.DataFrame([[1.0]], index=["momentum_20"], columns=["momentum_20"]),
    )
    result = make_selection_result()
    result.data_quality = {
        "total_symbols": 10,
        "available_symbols": 8,
        "failed_symbols": 2,
        "warnings": ["600000: source unavailable"],
    }

    ResearchReport().write_markdown(result, factor_analysis=factor_analysis, output_path=str(output))

    text = output.read_text()
    assert "## 数据质量摘要" in text
    assert "available_symbols" in text
    assert "## 因子有效性摘要" in text
    assert "momentum_20" in text
    assert "## 因子相关性摘要" in text
```

- [x] **Step 2: Run test and verify RED**

Run: `python -m pytest tests/test_research_report.py::test_research_report_includes_data_quality_and_factor_analysis -q`

Expected: FAIL because factor/data quality sections are missing.

- [x] **Step 3: Implement sections**

Add:

- Data quality table from `selection_result.data_quality` dict.
- Factor summary table from `factor_analysis.summary_table`.
- Correlation matrix table from `factor_analysis.correlation_matrix`.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_report.py -q`

Expected: PASS.

## Task 3: Export Helpers And README

**Files:**
- Modify: `quant_assistant/research/report.py`
- Modify: `README.md`
- Test: `tests/test_research_report.py`

- [x] **Step 1: Write failing test**

```python
def test_research_report_render_markdown_returns_text_without_writing():
    text = ResearchReport().render_markdown(make_selection_result(), metadata={"name": "demo"})

    assert "# 股票池多因子研究报告" in text
    assert "demo" in text
```

- [x] **Step 2: Run test and verify RED**

Run: `python -m pytest tests/test_research_report.py::test_research_report_render_markdown_returns_text_without_writing -q`

Expected: FAIL because `render_markdown()` is missing.

- [x] **Step 3: Implement render helper and README example**

Implement `render_markdown()` and make `write_markdown()` call it. Add README snippet:

```python
from quant_assistant.research import ResearchReport

ResearchReport().write_markdown(
    result,
    factor_analysis=factor_analysis,
    output_path="reports/stock_pool_research.md",
)
```

- [x] **Step 4: Run full tests**

Run: `python -m pytest tests -q`

Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add quant_assistant/research/report.py \
        quant_assistant/research/__init__.py \
        tests/test_research_report.py \
        README.md \
        docs/superpowers/plans/2026-06-30-research-report.md
git commit -m "feat: add markdown research reports"
```

