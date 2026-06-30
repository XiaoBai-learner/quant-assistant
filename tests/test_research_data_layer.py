import pandas as pd
import pytest

from quant_assistant.research import DataBundle, DataBundleBuilder, DataQualityReport, Universe


def test_universe_normalizes_symbols_and_records_metadata():
    universe = Universe.from_symbols(
        [" 000001 ", "600000", "000001", None, ""],
        name="core",
        source="manual",
    )

    assert universe.symbols == ["000001", "600000"]
    assert universe.name == "core"
    assert universe.source == "manual"
    assert universe.metadata["original_count"] == 5
    assert universe.metadata["dropped_count"] == 3


def test_data_bundle_exposes_basic_summary():
    universe = Universe.from_symbols(["000001", "600000"])
    panel = pd.DataFrame({
        "symbol": ["000001", "600000"],
        "trade_date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        "open": [10.0, 20.0],
        "high": [11.0, 21.0],
        "low": [9.0, 19.0],
        "close": [10.5, 20.5],
        "volume": [1000.0, 2000.0],
        "amount": [10500.0, 41000.0],
    })

    bundle = DataBundle(universe=universe, panel=panel, start="2024-01-01", end="2024-01-31")

    assert bundle.symbols == ["000001", "600000"]
    assert bundle.summary()["rows"] == 2


def test_data_quality_report_flags_missing_duplicates_and_invalid_prices():
    universe = Universe.from_symbols(["000001", "600000", "300001"])
    panel = pd.DataFrame({
        "symbol": ["000001", "000001", "000001", "600000"],
        "trade_date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-01"]),
        "open": [10.0, 10.1, None, 20.0],
        "high": [11.0, 11.1, 10.0, 18.0],
        "low": [9.0, 9.1, 10.5, 19.0],
        "close": [10.5, 10.6, -1.0, 20.5],
        "volume": [1000.0, 1100.0, 0.0, 2000.0],
        "amount": [10500.0, 11660.0, 0.0, 41000.0],
    })

    report = DataQualityReport.from_panel(universe, panel, start="2024-01-01", end="2024-01-03")
    summary = report.summary()

    assert summary["total_symbols"] == 3
    assert summary["available_symbols"] == 2
    assert summary["failed_symbols"] == 1
    assert report.by_symbol["000001"].duplicate_rows == 1
    assert report.by_symbol["000001"].missing_ohlcv == 1
    assert report.by_symbol["000001"].invalid_price_rows == 1
    assert report.by_symbol["000001"].zero_volume_rows == 1
    assert report.by_symbol["300001"].status == "failed"


def test_data_quality_report_exports_symbol_rows_to_csv(tmp_path):
    universe = Universe.from_symbols(["000001"])
    panel = pd.DataFrame({
        "symbol": ["000001"],
        "trade_date": pd.to_datetime(["2024-01-01"]),
        "open": [10.0],
        "high": [11.0],
        "low": [9.0],
        "close": [10.5],
        "volume": [1000.0],
        "amount": [10500.0],
    })
    report = DataQualityReport.from_panel(universe, panel, start="2024-01-01", end="2024-01-01")

    output_path = tmp_path / "quality.csv"
    report.export_csv(str(output_path))

    assert "000001" in output_path.read_text()
    exported = pd.read_csv(output_path, dtype={"symbol": str})
    assert exported.loc[0, "symbol"] == "000001"
    assert exported.loc[0, "rows"] == 1


class FakeDataAPI:
    def get_stock_data(self, symbol, start=None, end=None, adjust="qfq"):
        if symbol == "600000":
            raise RuntimeError("source unavailable")
        if symbol == "300001":
            return pd.DataFrame()
        return pd.DataFrame({
            "symbol": [symbol, symbol],
            "trade_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "open": [10.0, 10.5],
            "high": [11.0, 11.5],
            "low": [9.0, 9.5],
            "close": [10.5, 11.0],
            "volume": [1000.0, 1200.0],
            "amount": [10500.0, 13200.0],
        })


def test_data_bundle_builder_keeps_usable_symbols_when_some_fail():
    builder = DataBundleBuilder(data_api=FakeDataAPI())

    bundle = builder.build(
        universe=["000001", "600000", "300001"],
        start="2024-01-01",
        end="2024-01-31",
    )

    assert bundle.symbols == ["000001", "600000", "300001"]
    assert set(bundle.panel["symbol"]) == {"000001"}
    assert bundle.fetch_log["000001"]["status"] == "ok"
    assert bundle.fetch_log["600000"]["status"] == "failed"
    assert bundle.fetch_log["300001"]["status"] == "empty"
    assert bundle.quality.summary()["available_symbols"] == 1
    assert "600000" in bundle.quality.failed_symbols


def test_data_bundle_builder_raises_when_all_symbols_fail():
    def empty_loader(symbol, start, end, adjust):
        return pd.DataFrame()

    builder = DataBundleBuilder(loader=empty_loader)

    with pytest.raises(ValueError, match="股票池没有可用行情数据"):
        builder.build(["000001", "600000"], start="2024-01-01", end="2024-01-31")
