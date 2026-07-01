import pandas as pd

from quant_assistant.research.backtest import SelectionBacktester


def make_prices():
    return pd.DataFrame({
        "symbol": ["A", "A", "A", "A", "B", "B", "B", "B"],
        "trade_date": pd.to_datetime([
            "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04",
            "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04",
        ]),
        "open": [10.0, 11.0, 12.0, 13.0, 20.0, 21.0, 22.0, 23.0],
        "high": [10.5, 11.5, 12.5, 13.5, 20.5, 21.0, 22.5, 23.5],
        "low": [9.8, 10.8, 11.8, 12.8, 19.8, 21.0, 21.8, 22.8],
        "close": [10.2, 11.2, 12.2, 13.2, 20.2, 21.2, 22.2, 23.2],
        "volume": [1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000],
    })


def test_selection_backtester_executes_rebalance_at_next_day_open_with_ledger():
    holdings = pd.DataFrame({
        "rebalance_date": pd.to_datetime(["2024-01-01"]),
        "symbol": ["A"],
        "target_weight": [1.0],
    })

    result = SelectionBacktester(initial_cash=11000, commission_rate=0.0, slippage=0.0).run(
        make_prices(),
        holdings,
        execution="next_open",
    )

    ledger = result["trade_ledger"]
    buy = ledger[ledger["action"] == "buy"].iloc[0]
    assert buy["trade_date"] == pd.Timestamp("2024-01-02")
    assert buy["symbol"] == "A"
    assert buy["price"] == 11.0
    assert buy["shares"] == 1000
    assert result["daily_returns"]["portfolio_value"].iloc[-1] > 11000


def test_selection_backtester_skips_non_tradable_execution_day_and_records_reason():
    holdings = pd.DataFrame({
        "rebalance_date": pd.to_datetime(["2024-01-01"]),
        "symbol": ["B"],
        "target_weight": [1.0],
    })

    result = SelectionBacktester(initial_cash=21000, commission_rate=0.0, slippage=0.0).run(
        make_prices(),
        holdings,
        execution="next_open",
    )

    ledger = result["trade_ledger"]
    skipped = ledger[ledger["status"] == "skipped"].iloc[0]
    assert skipped["trade_date"] == pd.Timestamp("2024-01-02")
    assert skipped["symbol"] == "B"
    assert skipped["reason"] == "non_tradable_high_equals_low"
    assert result["daily_returns"]["portfolio_value"].iloc[-1] == 21000


def test_selection_backtester_sells_removed_holdings_at_next_open():
    holdings = pd.DataFrame({
        "rebalance_date": pd.to_datetime(["2024-01-01", "2024-01-03"]),
        "symbol": ["A", "A"],
        "target_weight": [1.0, 0.0],
    })

    result = SelectionBacktester(initial_cash=11000, commission_rate=0.0, slippage=0.0).run(
        make_prices(),
        holdings,
        execution="next_open",
    )

    sells = result["trade_ledger"][result["trade_ledger"]["action"] == "sell"]
    assert sells.iloc[0]["trade_date"] == pd.Timestamp("2024-01-04")
    assert sells.iloc[0]["price"] == 13.0
