#!/usr/bin/env python
"""Initialize or update local A-share daily Parquet cache."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from quant_assistant.data.fetcher import UnifiedDataFetcher  # noqa: E402
from quant_assistant.data.local_cache import AshareCacheUpdater, AshareDailyCache  # noqa: E402
from quant_assistant.api import QuantAPI  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A-share daily Parquet cache updater")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init-one-year", action="store_true", help="初始化近一年 A 股日线缓存")
    mode.add_argument("--update-latest", action="store_true", help="更新上一交易日 A 股日线缓存")
    parser.add_argument("--cache-dir", default=None, help="缓存目录，默认 ~/.quant_assistant/cache/ashare_daily")
    parser.add_argument("--market", default="all", choices=["all", "sh", "sz", "bj"], help="市场范围")
    parser.add_argument("--source", default="auto", choices=["auto", "akshare", "efinance", "tickflow"], help="优先数据源")
    parser.add_argument("--adjust", default="qfq", choices=["qfq", "hfq", "none"], help="复权方式")
    parser.add_argument("--end", default=None, help="初始化截止日期 YYYY-MM-DD")
    parser.add_argument("--run-date", default=None, help="增量运行日期 YYYY-MM-DD，用于计算上一交易日")
    parser.add_argument("--limit", type=int, default=None, help="仅更新前 N 只股票，便于试跑")
    parser.add_argument("--report", default="reports/ashare_cache_update.json", help="更新报告 JSON 输出路径")
    parser.add_argument("--dry-run", action="store_true", help="只打印任务参数，不拉取数据")
    return parser


def create_data_api(source: str):
    api = QuantAPI()
    fetcher = UnifiedDataFetcher(primary_source=source)
    api.data.set_fetcher(fetcher)
    return api.data


def run(args: argparse.Namespace) -> dict:
    cache = AshareDailyCache(cache_dir=args.cache_dir)
    if args.dry_run:
        report = {
            "mode": "init_one_year" if args.init_one_year else "update_latest",
            "cache_dir": str(cache.cache_dir),
            "market": args.market,
            "source": args.source,
            "adjust": args.adjust,
            "limit": args.limit,
            "dry_run": True,
        }
    else:
        updater = AshareCacheUpdater(data_api=create_data_api(args.source), cache=cache)
        if args.init_one_year:
            report = updater.initialize_one_year(
                end=args.end,
                market=args.market,
                adjust=args.adjust,
                limit=args.limit,
            )
            report["mode"] = "init_one_year"
        else:
            report = updater.update_latest(
                run_date=args.run_date,
                market=args.market,
                adjust=args.adjust,
                limit=args.limit,
            )
            report["mode"] = "update_latest"
        report["source"] = args.source

    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
