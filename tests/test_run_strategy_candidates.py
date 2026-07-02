from argparse import Namespace

import pandas as pd

from scripts.run_strategy_candidates import run


def make_feature_wide(path):
    dates = pd.date_range("2024-01-01", periods=8, freq="B")
    rows = []
    for symbol, base, momentum, flow in [
        ("000001", 10.0, 0.20, 1.5),
        ("600000", 20.0, 0.05, 0.2),
        ("000002", 15.0, -0.02, -0.1),
    ]:
        for i, trade_date in enumerate(dates):
            close = base + i * (0.3 if symbol == "000001" else 0.1)
            rows.append({
                "trade_date": trade_date,
                "symbol": symbol,
                "open": close,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close + 0.1,
                "volume": 1000,
                "momentum_5": momentum / 2,
                "momentum_20": momentum,
                "volatility_20": 0.02 if symbol != "000002" else 0.04,
                "drawdown_20": -0.02 if symbol != "600000" else -0.08,
                "main_net_inflow": flow * 1_000_000,
                "fund_flow_score": flow,
                "industry_rank_score": 0.8 if symbol == "000001" else 0.2,
                "concept_heat_score": 0.6 if symbol == "000001" else 0.1,
                "limit_up_score": 0.0,
                "dragon_tiger_score": 0.0,
                "sentiment_rank_score": 0.7 if symbol == "000001" else 0.2,
                "is_allowed_universe": True,
                "is_tradable_next_day": True,
            })
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_run_strategy_candidates_writes_report_and_trade_ledgers(tmp_path):
    feature_path = tmp_path / "feature_wide.parquet"
    make_feature_wide(feature_path)

    report = run(Namespace(
        feature_wide=str(feature_path),
        daily_cache_dir="",
        extended_cache_dir="",
        start="2024-01-01",
        end="2024-01-10",
        output_dir=str(tmp_path / "strategy_runs"),
        initial_cash=300000.0,
        commission_rate=0.0,
        slippage=0.0,
        max_weight=0.5,
        rebalance_step=3,
        strategies="trend_momentum,capital_flow",
        dry_run=False,
    ))

    summary_path = tmp_path / "strategy_runs" / "strategy_summary.csv"
    ledger_path = tmp_path / "strategy_runs" / "trade_ledgers" / "trend_momentum.parquet"
    assert summary_path.exists()
    assert ledger_path.exists()
    assert set(report["strategies"].keys()) == {"trend_momentum", "capital_flow"}
    assert report["strategies"]["trend_momentum"]["selection_count"] > 0
    assert "max_drawdown" in report["strategies"]["trend_momentum"]["metrics"]


def test_run_strategy_candidates_dry_run_reports_selected_strategies(tmp_path):
    feature_path = tmp_path / "feature_wide.parquet"
    make_feature_wide(feature_path)

    report = run(Namespace(
        feature_wide=str(feature_path),
        daily_cache_dir="",
        extended_cache_dir="",
        start="2024-01-01",
        end="2024-01-10",
        output_dir=str(tmp_path / "strategy_runs"),
        initial_cash=300000.0,
        commission_rate=0.0,
        slippage=0.0,
        max_weight=0.5,
        rebalance_step=3,
        strategies="trend_momentum",
        dry_run=True,
    ))

    assert report["dry_run"] is True
    assert report["strategy_names"] == ["trend_momentum"]
    assert not (tmp_path / "strategy_runs").exists()


def test_run_strategy_candidates_skips_strategies_with_missing_columns(tmp_path):
    feature_path = tmp_path / "feature_wide.parquet"
    make_feature_wide(feature_path)
    data = pd.read_parquet(feature_path).drop(columns=["fund_flow_score", "main_net_inflow"])
    data.to_parquet(feature_path, index=False)

    report = run(Namespace(
        feature_wide=str(feature_path),
        daily_cache_dir="",
        extended_cache_dir="",
        start="2024-01-01",
        end="2024-01-10",
        output_dir=str(tmp_path / "strategy_runs"),
        initial_cash=300000.0,
        commission_rate=0.0,
        slippage=0.0,
        max_weight=0.5,
        rebalance_step=3,
        strategies="trend_momentum,capital_flow",
        dry_run=False,
    ))

    assert set(report["strategies"].keys()) == {"trend_momentum"}
    assert report["skipped_strategies"]["capital_flow"]["missing_columns"] == ["fund_flow_score", "main_net_inflow"]
