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
