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

from quant_assistant.research import DataBundle, DataQualityReport, SelectionResearch, Universe


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


def test_selection_research_from_bundle_uses_panel_and_quality_summary():
    panel = make_research_panel()
    universe = Universe.from_symbols(["A", "B", "C"])
    quality = DataQualityReport.from_panel(universe, panel, start="2024-01-01", end="2024-05-01")
    bundle = DataBundle(
        universe=universe,
        panel=panel,
        start="2024-01-01",
        end="2024-05-01",
        quality=quality,
    )

    research = SelectionResearch.from_bundle(
        bundle,
        factors={"momentum_20": 1.0, "volatility_20": -0.2},
        top_n=2,
        rebalance="M",
    )

    result = research.run()

    assert not result.selections.empty
    assert result.data_quality["total_symbols"] == 3
    assert result.data_quality["available_symbols"] == 3
