import json
import pandas as pd

from scripts.diagnose_tickflow import build_parser, run
from quant_assistant.core.exceptions import DataFetchException


class FakeFetcher:
    def __init__(self, mode, **kwargs):
        self.mode = mode
        self.closed = False

    def get_stock_list(self):
        return pd.DataFrame(
            {"symbol": ["600000", "000001", "920662"], "exchange": ["SH", "SZ", "BJ"]}
        )

    def get_instrument_info(self, symbol):
        return {"symbol": symbol, "name": "sample"}

    def get_daily_quotes(self, symbol, start, end, adjust):
        frame = pd.DataFrame(
            {
                "trade_date": pd.to_datetime(["2026-11-16", "2026-11-17"]),
                "close": [10.0, 10.1],
                "volume": [1000, 1100],
                "amount": [1000000, 1111000],
            }
        )
        frame.attrs = {"source": "tickflow", "mode": self.mode, "adjust": adjust}
        return frame

    def get_realtime_quotes(self, symbols):
        return pd.DataFrame({"symbol": symbols, "price": [10.0] * len(symbols)})

    def get_minute_quotes(self, symbol, **kwargs):
        raise DataFetchException("403 无分钟K线查询权限", details={"status_code": 403})

    def get_financial_indicators(self, symbol):
        raise DataFetchException("403 无财务权限", details={"status_code": 403})

    def close(self):
        self.closed = True


def test_probe_reports_permission_denials_without_fallback(tmp_path):
    args = build_parser().parse_args(
        [
            "--mode",
            "both",
            "--start",
            "2026-11-01",
            "--end",
            "2026-11-17",
            "--symbols",
            "600000,000001",
            "--report",
            str(tmp_path / "probe.json"),
        ]
    )
    fetchers = []

    def factory(**kwargs):
        fetcher = FakeFetcher(**kwargs)
        fetchers.append(fetcher)
        return fetcher

    report = run(args, fetcher_factory=factory)
    saved = json.loads((tmp_path / "probe.json").read_text())
    assert report["fallback_enabled"] is False
    assert saved["checks"]
    denial = next(
        c for c in saved["checks"] if c["mode"] == "authenticated" and c["check"] == "minute"
    )
    assert denial["status"] == "permission_denied"
    assert denial["http_status"] == 403
    assert all(f.closed for f in fetchers)


def test_probe_checks_adjustment_variants_and_records_freshness(tmp_path):
    args = build_parser().parse_args(
        ["--mode", "free", "--symbols", "600000", "--report", str(tmp_path / "probe.json")]
    )
    report = run(args, fetcher_factory=FakeFetcher)
    checks = report["checks"]
    assert {c["check"] for c in checks} >= {
        "daily_qfq",
        "daily_hfq",
        "daily_none",
        "stock_list",
        "instrument",
    }
    daily = next(c for c in checks if c["check"] == "daily_qfq")
    assert daily["last_trade_date"] == "2026-11-17"
    assert daily["source"] == "tickflow"
