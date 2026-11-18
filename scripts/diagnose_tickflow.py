#!/usr/bin/env python3
"""Small, direct TickFlow probes. Never use fallback data to report success."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quant_assistant.data.fetcher.tickflow_fetcher import TickFlowFetcher


def build_parser():
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["free", "authenticated", "both"], default="both")
    parser.add_argument("--symbols", default="600000.SH,000001.SZ,920662.BJ")
    parser.add_argument("--start", default=(today - timedelta(days=60)).isoformat())
    parser.add_argument("--end", default=today.isoformat())
    parser.add_argument("--report", default="reports/tickflow_diagnostics.json")
    return parser


def run(args, *, fetcher_factory=TickFlowFetcher):
    report = {
        "as_of": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "fallback_enabled": False,
        "start": args.start,
        "end": args.end,
        "checks": [],
    }
    symbols = [
        TickFlowFetcher._convert_symbol(s.strip()) for s in args.symbols.split(",") if s.strip()
    ]
    if not symbols:
        raise ValueError("至少需要一个股票代码")
    if pd.Timestamp(args.start) > pd.Timestamp(args.end):
        raise ValueError("开始日期不能晚于结束日期")
    modes = ["free", "authenticated"] if args.mode == "both" else [args.mode]
    for mode in modes:
        try:
            fetcher = fetcher_factory(mode=mode, timeout=12, max_retries=1)
        except Exception as error:
            report["checks"].append(
                {"mode": mode, "check": "initialization", "status": "error", "error": str(error)}
            )
            continue
        probes = [
            ("stock_list", None, fetcher.get_stock_list),
            ("instrument", symbols[0], lambda: fetcher.get_instrument_info(symbols[0])),
        ]
        for symbol in symbols:
            probes.append(
                (
                    "daily_qfq",
                    symbol,
                    lambda s=symbol: fetcher.get_daily_quotes(s, args.start, args.end, "qfq"),
                )
            )
        for adjust in ("hfq", "none"):
            probes.append(
                (
                    f"daily_{adjust}",
                    symbols[0],
                    lambda a=adjust: fetcher.get_daily_quotes(symbols[0], args.start, args.end, a),
                )
            )
        probes.extend(
            [
                ("realtime", symbols[0], lambda: fetcher.get_realtime_quotes(symbols[:1])),
                (
                    "minute",
                    symbols[0],
                    lambda: fetcher.get_minute_quotes(
                        symbols[0], period="5m", start_date=args.end, end_date=args.end
                    ),
                ),
                ("financials", symbols[0], lambda: fetcher.get_financial_indicators(symbols[0])),
            ]
        )
        try:
            for name, symbol, probe in probes:
                started = time.monotonic()
                check = {"mode": mode, "check": name, "symbol": symbol, "source": "tickflow"}
                try:
                    data = probe()
                    check.update(status="ok" if len(data) else "empty", rows=len(data))
                    if isinstance(data, pd.DataFrame):
                        check["columns"] = list(data.columns)
                        check["metadata"] = dict(data.attrs)
                        if "trade_date" in data and not data.empty:
                            check["first_trade_date"] = str(data.trade_date.min().date())
                            check["last_trade_date"] = str(data.trade_date.max().date())
                            check["duplicate_dates"] = int(data.trade_date.duplicated().sum())
                        if "exchange" in data:
                            check["exchanges"] = {
                                str(k): int(v) for k, v in data.exchange.value_counts().items()
                            }
                        if "volume" in data and "amount" in data and "close" in data:
                            ratios = data.amount / (data.close * data.volume).replace(
                                0, float("nan")
                            )
                            ratio = ratios.median()
                            check["amount_over_close_volume_median"] = (
                                float(ratio) if pd.notna(ratio) else None
                            )
                except Exception as error:
                    details = getattr(error, "details", {})
                    status = details.get("status_code")
                    check.update(
                        status=(
                            "permission_denied"
                            if status in {401, 403}
                            else (
                                "unsupported"
                                if mode == "free" and name in {"realtime", "minute", "financials"}
                                else "error"
                            )
                        ),
                        http_status=status,
                        error=str(error),
                    )
                check["seconds"] = round(time.monotonic() - started, 3)
                report["checks"].append(check)
        finally:
            fetcher.close()
    path = Path(args.report).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    return report


def main():
    args = build_parser().parse_args()
    report = run(args)
    for check in report["checks"]:
        print(
            f"{check['mode']:14s} {check['check']:15s} {str(check.get('symbol') or '-'):12s} "
            f"{check['status']:18s} rows={check.get('rows', '-')} latest={check.get('last_trade_date', '-')}"
        )
    print(f"报告: {Path(args.report).expanduser().resolve()}")
    daily_ok = any(c["check"] == "daily_qfq" and c["status"] == "ok" for c in report["checks"])
    return 0 if daily_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
