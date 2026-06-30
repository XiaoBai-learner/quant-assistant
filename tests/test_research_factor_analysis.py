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


def test_factor_analysis_export_preserves_correlation_factor_names(tmp_path):
    analyzer = FactorAnalyzer()
    result = analyzer.analyze(
        data=make_factor_panel(),
        factors=["momentum_20", "momentum_60"],
        forward_returns=[5],
        quantiles=3,
        rebalance="M",
    )

    output_dir = tmp_path / "factor_analysis"
    result.export_csv(str(output_dir))

    exported = pd.read_csv(output_dir / "correlation_matrix.csv", index_col=0)
    assert "momentum_20" in exported.index
    assert "momentum_60" in exported.columns


def test_factor_analyzer_reports_factor_coverage_and_distribution():
    analyzer = FactorAnalyzer()

    result = analyzer.analyze(
        data=make_factor_panel(),
        factors=["momentum_20"],
        forward_returns=[5],
        rebalance="M",
    )

    row = result.summary_table.loc["momentum_20"]
    assert row["factor_coverage"] > 0
    assert row["factor_observations"] > 0
    assert pd.notna(row["factor_mean"])
    assert pd.notna(row["factor_std"])
