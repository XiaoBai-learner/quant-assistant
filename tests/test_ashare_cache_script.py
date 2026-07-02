import json

from scripts.cache_ashare_daily import build_parser, run


def test_cache_script_dry_run_writes_report(tmp_path):
    report_path = tmp_path / "report.json"
    parser = build_parser()
    args = parser.parse_args([
        "--update-latest",
        "--cache-dir",
        str(tmp_path / "cache"),
        "--source",
        "auto",
        "--limit",
        "3",
        "--report",
        str(report_path),
        "--dry-run",
    ])

    report = run(args)
    payload = json.loads(report_path.read_text())

    assert report["dry_run"] is True
    assert payload["mode"] == "update_latest"
    assert payload["limit"] == 3
    assert payload["stock_list_source"] == "tickflow"


def test_cache_script_accepts_explicit_stock_list_source(tmp_path):
    parser = build_parser()
    args = parser.parse_args([
        "--update-latest",
        "--cache-dir",
        str(tmp_path / "cache"),
        "--source",
        "akshare",
        "--stock-list-source",
        "tickflow",
        "--dry-run",
    ])

    report = run(args)

    assert report["source"] == "akshare"
    assert report["stock_list_source"] == "tickflow"


def test_cache_script_dry_run_reports_explicit_symbols(tmp_path):
    parser = build_parser()
    args = parser.parse_args([
        "--update-range",
        "--start",
        "2024-01-01",
        "--end",
        "2024-01-02",
        "--symbols",
        "000001,600000.SH",
        "--cache-dir",
        str(tmp_path / "cache"),
        "--dry-run",
    ])

    report = run(args)

    assert report["symbols"] == ["000001", "600000.SH"]
