# Factor Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a factor effectiveness analyzer that evaluates stock-pool factors with forward returns, Rank IC, ICIR, group returns, Top-Bottom spread, and factor correlation.

**Architecture:** Add `quant_assistant.research.factor_analysis` as a read-only analysis module. It reuses existing `FactorCalculator` definitions, calculates factor values on a standard panel, evaluates factors only on rebalance dates, and returns a `FactorAnalysisResult` object with tabular outputs.

**Tech Stack:** Python 3.10+, dataclasses, pandas, numpy, pytest.

---

## File Structure

- Create `quant_assistant/research/factor_analysis.py`: `FactorAnalyzer`, `FactorAnalysisResult`, forward return and IC logic.
- Modify `quant_assistant/research/__init__.py`: export `FactorAnalyzer` and `FactorAnalysisResult`.
- Create `tests/test_research_factor_analysis.py`: unit tests using deterministic synthetic stock-pool panel.
- Modify `README.md`: add a short factor analysis snippet before running `SelectionResearch`.

## Task 1: Forward Returns And Rank IC

**Files:**
- Create: `quant_assistant/research/factor_analysis.py`
- Modify: `quant_assistant/research/__init__.py`
- Test: `tests/test_research_factor_analysis.py`

- [x] **Step 1: Write failing tests**

```python
import pandas as pd

from quant_assistant.research import FactorAnalyzer, FactorDefinition


def make_factor_panel():
    dates = pd.date_range("2024-01-01", periods=70, freq="B")
    rows = []
    for symbol, base, slope in [("A", 10.0, 0.05), ("B", 10.0, 0.10), ("C", 10.0, 0.20)]:
        for i, trade_date in enumerate(dates):
            close = base + slope * i
            rows.append({
                "symbol": symbol,
                "trade_date": trade_date,
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": 1000 + i,
                "amount": (1000 + i) * close,
            })
    return pd.DataFrame(rows)


def test_factor_analyzer_calculates_rank_ic_and_ic_summary():
    def slope_factor(df):
        return df["close"].pct_change(20)

    analyzer = FactorAnalyzer(factor_definitions={
        "slope_20": FactorDefinition("slope_20", "positive", 20, ["close"], slope_factor),
    })

    result = analyzer.analyze(
        data=make_factor_panel(),
        factors=["slope_20"],
        forward_returns=[5],
        rebalance="M",
    )

    assert not result.ic_table.empty
    assert result.ic_table["factor"].unique().tolist() == ["slope_20"]
    assert result.summary_table.loc["slope_20", "ic_count"] > 0
    assert result.summary_table.loc["slope_20", "rank_ic_mean"] > 0
```

- [x] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_research_factor_analysis.py::test_factor_analyzer_calculates_rank_ic_and_ic_summary -q`

Expected: FAIL because `FactorAnalyzer` is not exported.

- [x] **Step 3: Implement minimal analyzer**

Implement:

- `FactorAnalysisResult` dataclass with `factor_values`, `forward_return_table`, `ic_table`, `summary_table`, `group_returns`, `correlation_matrix`.
- `FactorAnalyzer.analyze(data, factors, forward_returns, quantiles=5, rebalance="M")`.
- Factor calculation via `FactorCalculator`.
- Rebalance date selection by last trading date in each `trade_date.dt.to_period(rebalance)`.
- Forward return per symbol as `close.shift(-window) / close - 1`.
- Rank IC as Spearman correlation using `Series.rank().corr()`.
- Summary table columns: `rank_ic_mean`, `rank_ic_std`, `icir`, `ic_win_rate`, `ic_count`.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_factor_analysis.py -q`

Expected: PASS.

## Task 2: Group Returns And Top-Bottom Spread

**Files:**
- Modify: `quant_assistant/research/factor_analysis.py`
- Test: `tests/test_research_factor_analysis.py`

- [x] **Step 1: Write failing tests**

```python
def test_factor_analyzer_calculates_group_returns_and_top_bottom_spread():
    def slope_factor(df):
        return df["close"].pct_change(20)

    analyzer = FactorAnalyzer(factor_definitions={
        "slope_20": FactorDefinition("slope_20", "positive", 20, ["close"], slope_factor),
    })

    result = analyzer.analyze(
        data=make_factor_panel(),
        factors=["slope_20"],
        forward_returns=[5],
        quantiles=3,
        rebalance="M",
    )

    groups = result.group_returns

    assert not groups.empty
    assert {"factor", "window", "quantile", "mean_forward_return"}.issubset(groups.columns)
    assert result.summary_table.loc["slope_20", "top_bottom_mean"] > 0
```

- [x] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_research_factor_analysis.py::test_factor_analyzer_calculates_group_returns_and_top_bottom_spread -q`

Expected: FAIL because `group_returns` is empty or summary lacks `top_bottom_mean`.

- [x] **Step 3: Implement group returns**

For each factor/date/window:

- Drop rows with missing factor or forward return.
- Assign quantile using `pd.qcut(factor_rank, q=quantiles, labels=False, duplicates="drop") + 1`.
- Compute mean forward return by quantile.
- Compute Top-Bottom as highest quantile mean minus lowest quantile mean per date/window.
- Add `top_bottom_mean` to summary table.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_factor_analysis.py -q`

Expected: PASS.

## Task 3: Factor Correlation And Exports

**Files:**
- Modify: `quant_assistant/research/factor_analysis.py`
- Test: `tests/test_research_factor_analysis.py`

- [x] **Step 1: Write failing tests**

```python
def test_factor_analysis_result_summary_and_csv_export(tmp_path):
    analyzer = FactorAnalyzer()
    result = analyzer.analyze(
        data=make_factor_panel(),
        factors=["momentum_20", "momentum_60"],
        forward_returns=[5],
        quantiles=3,
        rebalance="M",
    )

    summary = result.summary()
    output_dir = tmp_path / "factor_analysis"
    result.export_csv(str(output_dir))

    assert "summary_table" in summary
    assert not result.correlation_matrix.empty
    assert (output_dir / "summary_table.csv").exists()
    assert (output_dir / "ic_table.csv").exists()
    assert (output_dir / "group_returns.csv").exists()
```

- [x] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_research_factor_analysis.py::test_factor_analysis_result_summary_and_csv_export -q`

Expected: FAIL because `summary()` or `export_csv()` is missing.

- [x] **Step 3: Implement correlation and exports**

Implement:

- Factor correlation on rebalance factor rows, using selected factor columns and pandas `corr(method="spearman")`.
- `FactorAnalysisResult.summary()` returning serializable dictionaries for summary table shape, factors, windows, and warnings.
- `FactorAnalysisResult.export_csv(output_dir)` writing non-empty tables to CSV.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_factor_analysis.py -q`

Expected: PASS.

## Task 4: README And Full Verification

**Files:**
- Modify: `README.md`
- Test: all tests

- [x] **Step 1: Update README**

Add a factor analysis snippet:

```python
from quant_assistant.research import FactorAnalyzer

factor_analysis = FactorAnalyzer().analyze(
    data=bundle.panel,
    factors=["momentum_20", "momentum_60", "volatility_20"],
    forward_returns=[5, 20],
    rebalance="M",
)

print(factor_analysis.summary_table)
```

- [x] **Step 2: Run full tests**

Run: `python -m pytest tests -q`

Expected: all tests pass.

- [x] **Step 3: Inspect git diff**

Run: `git diff --stat`

Expected: changes are limited to factor analysis module, exports, tests, README, and this plan.

- [x] **Step 4: Commit**

```bash
git add quant_assistant/research/factor_analysis.py \
        quant_assistant/research/__init__.py \
        tests/test_research_factor_analysis.py \
        README.md \
        docs/superpowers/plans/2026-06-30-factor-analyzer.md
git commit -m "feat: add factor analysis diagnostics"
```

