from argparse import Namespace

import pandas as pd

from scripts.build_daily_feature_wide import run


def write_symbol(path, symbol, dates):
    rows = []
    for i, trade_date in enumerate(dates):
        close = 10 + i
        rows.append({
            "symbol": symbol,
            "trade_date": trade_date,
            "open": close - 0.1,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "volume": 1000 + i,
            "amount": close * (1000 + i),
        })
    pd.DataFrame(rows).to_parquet(path / f"{symbol}.parquet", index=False)


def test_build_daily_feature_wide_dry_run_reports_plan(tmp_path):
    cache_dir = tmp_path / "daily"
    cache_dir.mkdir()
    write_symbol(cache_dir, "000001", pd.date_range("2024-01-01", periods=5, freq="B"))

    report = run(Namespace(
        daily_cache_dir=str(cache_dir),
        extended_cache_dir=str(tmp_path / "extended"),
        output_dir=str(tmp_path / "features"),
        start="2024-01-01",
        end="2024-01-05",
        symbols="",
        report=str(tmp_path / "report.json"),
        dry_run=True,
    ))

    assert report["dry_run"] is True
    assert report["input_symbols"] == 1
    assert not (tmp_path / "features").exists()


def test_build_daily_feature_wide_dry_run_reports_missing_cache_without_crashing(tmp_path):
    report = run(Namespace(
        daily_cache_dir=str(tmp_path / "missing-daily-cache"),
        extended_cache_dir=str(tmp_path / "extended"),
        output_dir=str(tmp_path / "features"),
        start="2024-01-01",
        end="2024-01-05",
        symbols="",
        report=str(tmp_path / "report.json"),
        dry_run=True,
    ))

    assert report["dry_run"] is True
    assert report["input_symbols"] == 0
    assert report["warnings"] == ["日线缓存目录不存在"]


def test_build_daily_feature_wide_writes_parquet_and_report(tmp_path):
    cache_dir = tmp_path / "daily"
    cache_dir.mkdir()
    dates = pd.date_range("2024-01-01", periods=25, freq="B")
    write_symbol(cache_dir, "000001", dates)
    write_symbol(cache_dir, "600000", dates)

    report = run(Namespace(
        daily_cache_dir=str(cache_dir),
        extended_cache_dir=str(tmp_path / "extended"),
        output_dir=str(tmp_path / "features"),
        start="2024-01-01",
        end="2024-02-05",
        symbols="000001,600000",
        report=str(tmp_path / "report.json"),
        dry_run=False,
    ))

    output_path = tmp_path / "features" / "date_range=2024-01-01_2024-02-05.parquet"
    assert output_path.exists()
    feature_data = pd.read_parquet(output_path)
    assert {"momentum_20", "is_tradable_next_day"}.issubset(feature_data.columns)
    assert report["quality"]["symbol_count"] == 2
    assert report["output_path"] == str(output_path)
