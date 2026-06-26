from datetime import date

import pandas as pd
import pytest

from quant_assistant import QuantAPI
from quant_assistant.strategy.examples import MAStrategy, get_strategy


def sample_ohlcv(rows=40):
    dates = pd.date_range("2024-01-01", periods=rows, freq="B")
    close = list(range(10, 10 + rows))
    return pd.DataFrame(
        {
            "trade_date": dates,
            "open": close,
            "high": [v + 1 for v in close],
            "low": [v - 1 for v in close],
            "close": close,
            "volume": [1000] * rows,
            "amount": [10000] * rows,
            "symbol": ["000001"] * rows,
        }
    )


class FakeFetcher:
    def __init__(self):
        self.calls = []

    def get_daily_quotes(self, symbol, start_date=None, end_date=None, adjust="qfq"):
        self.calls.append((symbol, start_date, end_date, adjust))
        return sample_ohlcv(5)

    def get_stock_list(self, exchange=None):
        return pd.DataFrame({"symbol": ["000001"], "name": ["平安银行"], "exchange": ["SZ"]})


class FakeQuery:
    def query(self, **kwargs):
        return pd.DataFrame({"symbol": [kwargs["symbol"]]})


def test_strategy_examples_registry_creates_ma_cross():
    strategy = get_strategy("ma_cross", fast_period=3, slow_period=5)

    assert isinstance(strategy, MAStrategy)
    assert strategy.get_param("fast_period") == 3
    assert strategy.get_param("slow_period") == 5


def test_data_api_uses_injected_fetcher_and_standard_dates():
    api = QuantAPI()
    fetcher = FakeFetcher()
    api.data.set_fetcher(fetcher)

    data = api.data.get_stock_data("000001", start="2024-01-01", end=date(2024, 1, 5))

    assert fetcher.calls == [("000001", "2024-01-01", "2024-01-05", "qfq")]
    assert "trade_date" in data.columns
    assert list(data["symbol"].unique()) == ["000001"]


def test_data_api_query_delegates_to_query_engine():
    api = QuantAPI()
    api.data.set_query(FakeQuery())

    data = api.data.query("daily_quotes", symbol="000001", start="2024-01-01")

    assert data.iloc[0]["symbol"] == "000001"


def test_quantapi_can_create_strategy_and_run_backtest_on_dataframe():
    api = QuantAPI()
    strategy = api.strategy.create("ma_cross", fast_period=2, slow_period=3)

    result = api.backtest.run(strategy, sample_ohlcv(8), initial_capital=100000)
    analysis = api.backtest.analyze(result)

    assert "daily_records" in result
    assert "metrics" in result
    assert "total_return" in analysis
