import pandas as pd

from quant_assistant.research.daily_features import DailyFeatureWideBuilder, daily_feature_definitions


def make_market_panel():
    dates = pd.date_range("2024-01-01", periods=25, freq="B")
    rows = []
    for symbol, base in [("000001", 10.0), ("600000", 20.0), ("688001", 30.0)]:
        for i, trade_date in enumerate(dates):
            close = base + i * 0.2
            high = close + 0.3
            low = close - 0.2
            if symbol == "600000" and i == 24:
                high = low = close
            rows.append({
                "symbol": symbol,
                "trade_date": trade_date,
                "open": close - 0.1,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000 + i,
                "amount": close * (1000 + i),
            })
    return pd.DataFrame(rows)


def test_daily_feature_builder_creates_daily_ohlcv_and_tradability_features():
    features = DailyFeatureWideBuilder().build(make_market_panel())
    latest = features[features["trade_date"] == features["trade_date"].max()]

    assert {"return_1d", "momentum_5", "volatility_20", "atr_ratio_14", "amount_ma_20"}.issubset(features.columns)
    assert latest.loc[latest["symbol"] == "000001", "is_tradable_next_day"].item() is True
    assert latest.loc[latest["symbol"] == "600000", "is_tradable_next_day"].item() is False
    assert latest.loc[latest["symbol"] == "688001", "is_allowed_universe"].item() is False


def test_daily_feature_builder_merges_optional_external_daily_datasets():
    trade_date = pd.Timestamp("2024-02-02")
    industry = pd.DataFrame({
        "trade_date": [trade_date],
        "symbol": ["000001"],
        "industry_pct_change": [2.5],
        "industry_rank_score": [0.8],
    })
    fund_flow = pd.DataFrame({
        "trade_date": [trade_date],
        "symbol": ["000001"],
        "main_net_inflow": [1000000.0],
        "fund_flow_score": [1.2],
    })
    events = pd.DataFrame({
        "trade_date": [trade_date],
        "symbol": ["000001"],
        "limit_up_score": [2.0],
        "dragon_tiger_score": [0.5],
    })
    margin = pd.DataFrame({
        "trade_date": [trade_date],
        "symbol": ["000001"],
        "margin_balance_change": [0.03],
    })
    shareholders = pd.DataFrame({
        "trade_date": [trade_date],
        "symbol": ["000001"],
        "holder_count_change": [-0.05],
    })
    sentiment = pd.DataFrame({
        "trade_date": [trade_date],
        "symbol": ["000001"],
        "sentiment_rank_score": [0.7],
    })

    features = DailyFeatureWideBuilder().build(
        make_market_panel(),
        industry=industry,
        fund_flow=fund_flow,
        events=events,
        margin=margin,
        shareholders=shareholders,
        sentiment=sentiment,
    )

    row = features[(features["trade_date"] == trade_date) & (features["symbol"] == "000001")].iloc[0]
    assert row["industry_rank_score"] == 0.8
    assert row["fund_flow_score"] == 1.2
    assert row["limit_up_score"] == 2.0
    assert row["margin_balance_change"] == 0.03
    assert row["holder_count_change"] == -0.05
    assert row["sentiment_rank_score"] == 0.7


def test_daily_feature_definitions_include_groups_and_directions():
    definitions = daily_feature_definitions()

    assert definitions["momentum_20"].group == "daily"
    assert definitions["volatility_20"].direction == "negative"
    assert definitions["industry_rank_score"].group == "sector"
    assert definitions["main_net_inflow"].group == "capital"
    assert definitions["sentiment_rank_score"].group == "sentiment"
