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
