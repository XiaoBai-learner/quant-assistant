# Stock Pool Factor Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first-stage stock pool multi-factor selection research workflow with indicator calculation, factor scoring, Top N selection, equal-weight portfolio backtesting, and explainable outputs.

**Architecture:** Add a focused `quant_assistant.research` product line. Keep first-stage implementation deterministic and pandas-based, with built-in factor definitions plus extension points for user-supplied factor functions and user-defined factor weights.

**Tech Stack:** Python 3.10+, pandas, numpy, pytest.

---

## File Structure

- Create `quant_assistant/research/__init__.py`: public exports for the research product line.
- Create `quant_assistant/research/config.py`: `SelectionResearchConfig`, `CostConfig`, validation helpers.
- Create `quant_assistant/research/result.py`: `SelectionResearchResult` with summary/export helpers.
- Create `quant_assistant/research/factors.py`: factor metadata, built-in factor functions, `FactorCalculator`, and custom factor registration.
- Create `quant_assistant/research/preprocessing.py`: winsorization, z-score, direction adjustment, missing handling.
- Create `quant_assistant/research/scoring.py`: weighted factor contribution and total score.
- Create `quant_assistant/research/selector.py`: Top N selection and explainable selection rows.
- Create `quant_assistant/research/portfolio.py`: equal-weight target holdings.
- Create `quant_assistant/research/backtest.py`: rebalance portfolio backtest.
- Create `quant_assistant/research/evaluation.py`: performance metrics and IC metrics.
- Create `quant_assistant/research/workflow.py`: `SelectionResearch` orchestrator.
- Create `tests/test_research_factors.py`: factor calculation and custom factor tests.
- Create `tests/test_research_scoring_selection.py`: preprocessing, scoring, selection, portfolio tests.
- Create `tests/test_research_workflow.py`: end-to-end small stock pool workflow tests.
- Modify `README.md`: add first-stage research API example.

## Task 1: Config And Result Objects

**Files:**
- Create: `quant_assistant/research/config.py`
- Create: `quant_assistant/research/result.py`
- Create: `quant_assistant/research/__init__.py`
- Test: `tests/test_research_workflow.py`

- [ ] **Step 1: Write failing tests**

```python
from quant_assistant.research import SelectionResearchConfig, SelectionResearchResult


def test_selection_research_config_validates_core_inputs():
    config = SelectionResearchConfig(
        universe=["000001", "600000", "000001"],
        start="2024-01-01",
        end="2024-03-31",
        factors={"momentum_20": 1.0},
        top_n=2,
        rebalance="M",
    )

    assert config.universe == ["000001", "600000"]
    assert config.start == "2024-01-01"
    assert config.end == "2024-03-31"
    assert config.factor_weights == {"momentum_20": 1.0}


def test_selection_research_result_summary_exposes_key_tables():
    result = SelectionResearchResult(metrics={"total_return": 0.1}, warnings=["sample warning"])

    summary = result.summary()

    assert summary["metrics"]["total_return"] == 0.1
    assert summary["warnings"] == ["sample warning"]
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_research_workflow.py -q`
Expected: FAIL because `quant_assistant.research` does not exist.

- [ ] **Step 3: Implement config/result/export modules**

Implement dataclasses with minimal validation: non-empty universe, start <= end, non-empty factor weights, `top_n > 0`, `rebalance in {"W", "M"}`.

- [ ] **Step 4: Run passing tests**

Run: `python -m pytest tests/test_research_workflow.py -q`
Expected: PASS for config/result tests.

## Task 2: Factor Calculation With Extension Points

**Files:**
- Create: `quant_assistant/research/factors.py`
- Test: `tests/test_research_factors.py`

- [ ] **Step 1: Write failing tests**

```python
import pandas as pd
from quant_assistant.research.factors import FactorCalculator, FactorDefinition


def make_panel():
    dates = pd.date_range("2024-01-01", periods=70, freq="B")
    rows = []
    for symbol, base in [("000001", 10), ("600000", 20)]:
        for i, trade_date in enumerate(dates):
            close = base + i
            rows.append({
                "symbol": symbol,
                "trade_date": trade_date,
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 1000 + i,
                "amount": (1000 + i) * close,
            })
    return pd.DataFrame(rows)


def test_factor_calculator_computes_builtin_factors_without_future_data():
    calculator = FactorCalculator()
    factors = calculator.calculate(make_panel(), ["momentum_20", "volatility_20"])

    latest = factors[factors["trade_date"] == factors["trade_date"].max()]

    assert set(latest["symbol"]) == {"000001", "600000"}
    assert "momentum_20" in latest.columns
    assert "volatility_20" in latest.columns
    assert latest["momentum_20"].notna().all()


def test_factor_calculator_accepts_user_defined_factor_function():
    def close_to_open(df):
        return df["close"] / df["open"] - 1

    calculator = FactorCalculator()
    calculator.register_factor(FactorDefinition(
        name="close_to_open",
        direction="positive",
        min_periods=1,
        dependencies=["close", "open"],
        compute=close_to_open,
    ))

    factors = calculator.calculate(make_panel(), ["close_to_open"])

    assert "close_to_open" in factors.columns
    assert factors["close_to_open"].notna().all()
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_research_factors.py -q`
Expected: FAIL because factor module is missing.

- [ ] **Step 3: Implement factor module**

Implement `FactorDefinition`, built-ins for `momentum_20`, `momentum_60`, `ma_position_20`, `ma_position_60`, `volatility_20`, `turnover_amount_20`, `drawdown_20`, `atr_ratio_14`, and `FactorCalculator.register_factor()`.

- [ ] **Step 4: Run passing tests**

Run: `python -m pytest tests/test_research_factors.py -q`
Expected: PASS.

## Task 3: Preprocessing, Scoring, Selection, Portfolio

**Files:**
- Create: `quant_assistant/research/preprocessing.py`
- Create: `quant_assistant/research/scoring.py`
- Create: `quant_assistant/research/selector.py`
- Create: `quant_assistant/research/portfolio.py`
- Test: `tests/test_research_scoring_selection.py`

- [ ] **Step 1: Write failing tests**

```python
import pandas as pd
from quant_assistant.research.preprocessing import FactorPreprocessor
from quant_assistant.research.scoring import FactorScorer
from quant_assistant.research.selector import StockPoolSelector
from quant_assistant.research.portfolio import PortfolioConstructor
from quant_assistant.research.factors import FactorDefinition


def test_scoring_uses_direction_adjustment_and_factor_contributions():
    factor_data = pd.DataFrame({
        "trade_date": pd.to_datetime(["2024-01-31"] * 3),
        "symbol": ["A", "B", "C"],
        "momentum_20": [0.3, 0.1, -0.1],
        "volatility_20": [0.1, 0.2, 0.3],
    })
    definitions = {
        "momentum_20": FactorDefinition("momentum_20", "positive", 20, ["close"], lambda df: df["close"]),
        "volatility_20": FactorDefinition("volatility_20", "negative", 20, ["close"], lambda df: df["close"]),
    }

    processed = FactorPreprocessor(definitions).transform(factor_data, ["momentum_20", "volatility_20"])
    scored = FactorScorer({"momentum_20": 1.0, "volatility_20": 1.0}).score(processed)

    ranked = scored.sort_values("score", ascending=False)
    assert ranked.iloc[0]["symbol"] == "A"
    assert "momentum_20_contribution" in scored.columns
    assert "volatility_20_contribution" in scored.columns


def test_selector_and_portfolio_create_top_n_equal_weights():
    scored = pd.DataFrame({
        "trade_date": pd.to_datetime(["2024-01-31"] * 3),
        "symbol": ["A", "B", "C"],
        "score": [2.0, 1.0, -1.0],
    })

    selections = StockPoolSelector(top_n=2).select(scored)
    holdings = PortfolioConstructor(max_weight=0.6).construct(selections)

    assert list(selections["symbol"]) == ["A", "B"]
    assert holdings["target_weight"].sum() == 1.0
    assert set(holdings["symbol"]) == {"A", "B"}
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_research_scoring_selection.py -q`
Expected: FAIL because modules are missing.

- [ ] **Step 3: Implement preprocessing/scoring/selection/portfolio**

Implement per-date winsorization, z-score, direction adjustment, weighted contribution columns, Top N ranking, and equal-weight construction.

- [ ] **Step 4: Run passing tests**

Run: `python -m pytest tests/test_research_scoring_selection.py -q`
Expected: PASS.

## Task 4: Backtest And Evaluation

**Files:**
- Create: `quant_assistant/research/backtest.py`
- Create: `quant_assistant/research/evaluation.py`
- Test: `tests/test_research_workflow.py`

- [ ] **Step 1: Write failing tests**

```python
import pandas as pd
from quant_assistant.research.backtest import SelectionBacktester
from quant_assistant.research.evaluation import SelectionEvaluator


def test_selection_backtester_uses_next_period_returns_after_rebalance():
    prices = pd.DataFrame({
        "symbol": ["A", "A", "A", "B", "B", "B"],
        "trade_date": pd.to_datetime(["2024-01-31", "2024-02-01", "2024-02-02"] * 2),
        "close": [10, 11, 12, 20, 20, 22],
    })
    holdings = pd.DataFrame({
        "rebalance_date": pd.to_datetime(["2024-01-31", "2024-01-31"]),
        "symbol": ["A", "B"],
        "target_weight": [0.5, 0.5],
    })

    result = SelectionBacktester(initial_cash=100000).run(prices, holdings)

    assert result["daily_returns"]["portfolio_value"].iloc[0] == 100000
    assert result["daily_returns"]["portfolio_value"].iloc[-1] > 100000


def test_selection_evaluator_calculates_core_metrics():
    daily = pd.DataFrame({
        "trade_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        "daily_return": [0.0, 0.01, -0.005],
        "portfolio_value": [100000, 101000, 100495],
    })

    metrics = SelectionEvaluator().evaluate(daily)

    assert "total_return" in metrics
    assert "max_drawdown" in metrics
    assert metrics["total_return"] > 0
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_research_workflow.py -q`
Expected: FAIL for missing backtest/evaluation modules.

- [ ] **Step 3: Implement backtest/evaluation**

Implement simple next-day return portfolio value calculation and core metrics.

- [ ] **Step 4: Run passing tests**

Run: `python -m pytest tests/test_research_workflow.py -q`
Expected: PASS.

## Task 5: End-To-End SelectionResearch Workflow

**Files:**
- Create: `quant_assistant/research/workflow.py`
- Modify: `quant_assistant/research/__init__.py`
- Test: `tests/test_research_workflow.py`

- [ ] **Step 1: Write failing test**

```python
import pandas as pd
from quant_assistant.research import SelectionResearch


def make_research_panel():
    dates = pd.date_range("2024-01-01", periods=90, freq="B")
    rows = []
    for symbol, base, slope in [("A", 10, 0.2), ("B", 20, 0.05), ("C", 30, -0.02)]:
        for i, trade_date in enumerate(dates):
            close = base + i * slope
            rows.append({
                "symbol": symbol,
                "trade_date": trade_date,
                "open": close,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": 1000,
                "amount": 1000 * close,
            })
    return pd.DataFrame(rows)


def test_selection_research_runs_end_to_end_with_user_factor_weights():
    research = SelectionResearch(
        universe=["A", "B", "C"],
        start="2024-01-01",
        end="2024-05-01",
        factors={"momentum_20": 1.0, "volatility_20": -0.2},
        top_n=2,
        rebalance="M",
        data=make_research_panel(),
    )

    result = research.run()

    assert result.metrics["total_return"] >= 0
    assert not result.selections.empty
    assert not result.holdings.empty
    assert "momentum_20_contribution" in result.factor_scores.columns
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_research_workflow.py::test_selection_research_runs_end_to_end_with_user_factor_weights -q`
Expected: FAIL because `SelectionResearch` is missing.

- [ ] **Step 3: Implement workflow**

Implement orchestrator that accepts injected `data` for tests and later external data fetchers.

- [ ] **Step 4: Run full tests**

Run: `python -m pytest tests -q`
Expected: PASS.

## Task 6: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/PRODUCT_DESCRIPTION.md`

- [ ] **Step 1: Add research API usage example**

Add a concise `SelectionResearch` example showing user-defined factor weights.

- [ ] **Step 2: Run verification**

Run: `python -m pytest tests -q`
Expected: PASS.
