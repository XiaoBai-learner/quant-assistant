import pandas as pd

from quant_assistant.research.strategy_candidates import (
    StrategyCandidate,
    StrategyCandidateRunner,
    default_strategy_candidates,
)


def make_feature_wide():
    return pd.DataFrame({
        "trade_date": pd.to_datetime(["2024-01-31"] * 4),
        "symbol": ["000001", "600000", "000002", "688001"],
        "momentum_20": [0.20, 0.05, -0.02, 0.50],
        "volatility_20": [0.02, 0.01, 0.03, 0.01],
        "drawdown_20": [-0.02, -0.12, -0.04, -0.01],
        "main_net_inflow": [2_000_000, -100_000, 300_000, 5_000_000],
        "fund_flow_score": [1.5, -0.2, 0.3, 2.0],
        "industry_rank_score": [0.8, 0.1, 0.4, 0.9],
        "limit_up_score": [0.0, 1.0, 0.0, 2.0],
        "dragon_tiger_score": [0.0, 0.2, 0.0, 1.0],
        "sentiment_rank_score": [0.7, 0.1, 0.2, 0.9],
        "is_allowed_universe": [True, True, True, False],
        "is_tradable_next_day": [True, True, True, False],
    })


def test_default_strategy_candidates_cover_multiple_market_views():
    candidates = default_strategy_candidates()

    assert {"trend_momentum", "low_vol_reversal", "capital_flow", "sector_rotation", "event_enhanced"}.issubset(candidates)
    assert candidates["trend_momentum"].expected_regime == "strong_market"
    assert candidates["capital_flow"].factor_weights["fund_flow_score"] > 0


def test_strategy_candidate_runner_scores_and_filters_feature_wide_table():
    candidate = StrategyCandidate(
        name="sample",
        description="sample candidate",
        expected_regime="test",
        factor_weights={"momentum_20": 1.0, "volatility_20": -0.5, "fund_flow_score": 0.5},
        required_columns=["momentum_20", "volatility_20", "fund_flow_score"],
        top_n=2,
        min_score=None,
    )

    result = StrategyCandidateRunner([candidate]).run(make_feature_wide())
    selections = result["sample"]

    assert selections["symbol"].iloc[0] == "000001"
    assert "688001" not in set(selections["symbol"])
    assert len(selections) == 2
    assert selections["rank"].tolist() == [1, 2]
    assert selections["strategy_name"].unique().tolist() == ["sample"]
    assert "score" in selections.columns
