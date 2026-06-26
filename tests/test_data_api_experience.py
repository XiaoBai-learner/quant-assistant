import pandas as pd

from quant_assistant.data.fetcher.unified_fetcher import DataSourceType, UnifiedDataFetcher
from quant_assistant.data.query.data_query import DataQueryEngine


def test_unified_fetcher_accepts_efinance_primary_source_without_falling_back_to_default():
    fetcher = UnifiedDataFetcher.__new__(UnifiedDataFetcher)
    fetcher.name = "UnifiedDataFetcher"
    fetcher._init_fetchers = lambda *args, **kwargs: None

    UnifiedDataFetcher.__init__(fetcher, primary_source="efinance")

    assert fetcher.primary_source == DataSourceType.EFINANCE


class FakeStorage:
    def get_daily_quotes(self, symbol, start_date=None, end_date=None):
        return pd.DataFrame(
            {
                "symbol": [symbol],
                "trade_date": [pd.Timestamp("2024-01-02")],
                "close": [10.0],
                "pct_change": [1.0],
                "volume": [1000],
                "turnover": [0.5],
            }
        )


def test_data_query_engine_has_generic_query_for_daily_quotes():
    engine = DataQueryEngine.__new__(DataQueryEngine)
    engine.storage = FakeStorage()
    engine.cache = None
    engine._local_cache = {}

    data = engine.query("daily_quotes", symbol="000001", start="2024-01-01", end="2024-01-31")

    assert data.iloc[0]["symbol"] == "000001"
    assert data.iloc[0]["close"] == 10.0

class EmptyFetcher:
    def get_daily_quotes(self, *args, **kwargs):
        return pd.DataFrame()


class WorkingFetcher:
    def get_daily_quotes(self, *args, **kwargs):
        return pd.DataFrame({"close": [1.0]})


def test_unified_fetcher_falls_back_when_primary_returns_empty_dataframe():
    fetcher = UnifiedDataFetcher.__new__(UnifiedDataFetcher)
    fetcher.primary_source = DataSourceType.EFINANCE
    fetcher.fallback_enabled = True
    fetcher.efinance_fetcher = EmptyFetcher()
    fetcher.akshare_fetcher = WorkingFetcher()
    fetcher.tickflow_fetcher = None

    data = fetcher.get_daily_quotes("000001", "2024-01-01", "2024-01-02")

    assert len(data) == 1
    assert data.iloc[0]["close"] == 1.0

def test_data_api_filters_fetcher_result_to_requested_date_range():
    from quant_assistant import QuantAPI

    class WideFetcher:
        def get_daily_quotes(self, *args, **kwargs):
            return pd.DataFrame(
                {
                    "trade_date": pd.to_datetime(["2023-12-29", "2024-01-02", "2024-01-11"]),
                    "close": [9.0, 10.0, 11.0],
                }
            )

    api = QuantAPI()
    api.data.set_fetcher(WideFetcher())

    data = api.data.get_stock_data("000001", start="2024-01-01", end="2024-01-10")

    assert list(data["close"]) == [10.0]

import pytest


def test_data_api_raises_clear_error_when_requested_range_is_not_covered():
    from quant_assistant import QuantAPI

    class OutOfRangeFetcher:
        def get_daily_quotes(self, *args, **kwargs):
            return pd.DataFrame(
                {
                    "trade_date": pd.to_datetime(["2024-02-01"]),
                    "close": [10.0],
                }
            )

    api = QuantAPI()
    api.data.set_fetcher(OutOfRangeFetcher())

    with pytest.raises(ValueError, match="请求区间内无可用行情数据"):
        api.data.get_stock_data("000001", start="2024-01-01", end="2024-01-10")
