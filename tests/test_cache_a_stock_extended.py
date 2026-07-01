import json

from scripts.cache_a_stock_extended import build_parser, run


def test_extended_cache_dry_run_writes_plan(tmp_path):
    report = tmp_path / "report.json"
    parser = build_parser()
    args = parser.parse_args([
        "--date",
        "2026-07-01",
        "--cache-dir",
        str(tmp_path / "cache"),
        "--report",
        str(report),
        "--dry-run",
    ])

    result = run(args)
    payload = json.loads(report.read_text())

    assert result["dry_run"] is True
    assert payload["date"] == "2026-07-01"
    assert "limit_up_pool" in payload["endpoints"]
