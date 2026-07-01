#!/usr/bin/env python
"""Cache extended A-share signal datasets to local Parquet files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Callable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from quant_assistant.data.hub import DataHub  # noqa: E402

DEFAULT_ENDPOINTS = [
    "limit_up_pool",
    "broken_limit_pool",
    "limit_down_pool",
    "industry_rank",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cache extended A-share datasets")
    parser.add_argument("--date", required=True, help="交易日期 YYYY-MM-DD")
    parser.add_argument("--cache-dir", default="~/.quant_assistant/cache/extended", help="缓存根目录")
    parser.add_argument(
        "--endpoints",
        default=",".join(DEFAULT_ENDPOINTS),
        help="逗号分隔端点列表",
    )
    parser.add_argument("--report", default="reports/a_stock_extended_cache.json", help="报告 JSON 路径")
    parser.add_argument("--dry-run", action="store_true", help="只输出计划，不拉取数据")
    return parser


def run(args: argparse.Namespace) -> dict:
    endpoints = [item.strip() for item in args.endpoints.split(",") if item.strip()]
    cache_dir = Path(args.cache_dir).expanduser()
    if args.dry_run:
        report = {
            "date": args.date,
            "cache_dir": str(cache_dir),
            "endpoints": endpoints,
            "dry_run": True,
        }
    else:
        hub = DataHub()
        report = {
            "date": args.date,
            "cache_dir": str(cache_dir),
            "endpoints": endpoints,
            "dry_run": False,
            "results": {},
        }
        for endpoint in endpoints:
            try:
                frame = _fetch_endpoint(hub, endpoint, args.date)
                path = _endpoint_path(cache_dir, endpoint, args.date)
                path.parent.mkdir(parents=True, exist_ok=True)
                frame.to_parquet(path, index=False)
                report["results"][endpoint] = {
                    "status": "ok",
                    "rows": int(len(frame)),
                    "path": str(path),
                }
            except Exception as exc:  # noqa: BLE001 - third-party endpoints fail heterogeneously
                report["results"][endpoint] = {
                    "status": "failed",
                    "rows": 0,
                    "message": str(exc),
                }

    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report


def _fetch_endpoint(hub: DataHub, endpoint: str, trade_date: str) -> pd.DataFrame:
    fetchers: dict[str, Callable[[], pd.DataFrame]] = {
        "limit_up_pool": lambda: hub.signals.limit_up_pool(trade_date),
        "broken_limit_pool": lambda: hub.signals.broken_limit_pool(trade_date),
        "limit_down_pool": lambda: hub.signals.limit_down_pool(trade_date),
        "industry_rank": lambda: hub.signals.industry_rank(trade_date),
    }
    if endpoint not in fetchers:
        raise ValueError(f"未知扩展缓存端点: {endpoint}")
    return fetchers[endpoint]()


def _endpoint_path(cache_dir: Path, endpoint: str, trade_date: str) -> Path:
    return cache_dir / endpoint / f"date={trade_date}.parquet"


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
