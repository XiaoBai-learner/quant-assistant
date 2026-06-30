import pandas as pd

from quant_assistant.data.local_cache import AshareCacheUpdater, AshareDailyCache


def test_ashare_daily_cache_writes_reads_and_deduplicates_parquet(tmp_path):
    cache = AshareDailyCache(cache_dir=str(tmp_path))
    first = pd.DataFrame({
        "symbol": ["000001", "000001"],
        "trade_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "open": [10.0, 10.5],
        "high": [11.0, 11.5],
        "low": [9.0, 9.5],
        "close": [10.5, 11.0],
        "volume": [1000.0, 1200.0],
        "amount": [10500.0, 13200.0],
    })
    second = pd.DataFrame({
        "symbol": ["000001", "000001"],
        "trade_date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "open": [10.6, 11.0],
        "high": [11.6, 12.0],
        "low": [9.6, 10.0],
        "close": [11.1, 11.5],
        "volume": [1300.0, 1400.0],
        "amount": [14430.0, 16100.0],
    })

    cache.append_symbol("000001", first)
    cache.append_symbol("000001", second)
    loaded = cache.read_symbol("000001")

    assert cache.symbol_path("000001").suffix == ".parquet"
    assert list(loaded["trade_date"].dt.strftime("%Y-%m-%d")) == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert loaded.loc[loaded["trade_date"] == pd.Timestamp("2024-01-02"), "close"].iloc[0] == 11.1


def test_ashare_daily_cache_reports_symbol_stats(tmp_path):
    cache = AshareDailyCache(cache_dir=str(tmp_path))
    cache.append_symbol("000001", pd.DataFrame({
        "symbol": ["000001"],
        "trade_date": pd.to_datetime(["2024-01-01"]),
        "open": [10.0],
        "high": [11.0],
        "low": [9.0],
        "close": [10.5],
        "volume": [1000.0],
        "amount": [10500.0],
    }))

    stats = cache.stats()

    assert stats["symbol_count"] == 1
    assert stats["rows"] == 1


class FakeDataAPI:
    def get_stock_list(self, market="all"):
        return pd.DataFrame({
            "symbol": ["000001", "600000", "300001"],
            "name": ["A", "B", "C"],
        })

    def get_stock_data(self, symbol, start=None, end=None, adjust="qfq"):
        if symbol == "600000":
            raise RuntimeError("source unavailable")
        return pd.DataFrame({
            "symbol": [symbol],
            "trade_date": pd.to_datetime([end or start]),
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.5],
            "volume": [1000.0],
            "amount": [10500.0],
        })


def test_ashare_cache_updater_updates_symbols_and_records_failures(tmp_path):
    cache = AshareDailyCache(cache_dir=str(tmp_path))
    updater = AshareCacheUpdater(data_api=FakeDataAPI(), cache=cache)

    report = updater.update_range(start="2024-01-01", end="2024-01-01", market="all")

    assert report["total_symbols"] == 3
    assert report["success_count"] == 2
    assert report["failed_count"] == 1
    assert report["symbols"]["600000"]["status"] == "failed"
    assert not cache.read_symbol("000001").empty


def test_ashare_cache_updater_uses_previous_business_day_for_latest(tmp_path):
    cache = AshareDailyCache(cache_dir=str(tmp_path))
    updater = AshareCacheUpdater(data_api=FakeDataAPI(), cache=cache)

    report = updater.update_latest(run_date="2024-01-08")

    assert report["start"] == "2024-01-05"
    assert report["end"] == "2024-01-05"
    assert report["date_rule"] == "previous_business_day"
