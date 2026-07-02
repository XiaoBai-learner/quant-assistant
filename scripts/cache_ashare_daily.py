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
    mode.add_argument("--init-years", type=int, default=None, help="初始化近 N 年 A 股日线缓存")
    mode.add_argument("--update-range", action="store_true", help="按 start/end 更新指定日期范围")
    mode.add_argument("--update-latest", action="store_true", help="更新上一交易日 A 股日线缓存")
    parser.add_argument("--cache-dir", default=None, help="缓存目录，默认 ~/.quant_assistant/cache/ashare_daily")
    parser.add_argument("--market", default="all", choices=["all", "sh", "sz", "bj"], help="市场范围")
    parser.add_argument("--source", default="auto", choices=["auto", "akshare", "efinance", "tickflow"], help="日线行情优先数据源")
    parser.add_argument(
        "--stock-list-source",
        default="tickflow",
        choices=["auto", "akshare", "efinance", "tickflow"],
        help="股票列表数据源，默认 tickflow 以减少列表获取阶段的无效重试",
    )
    parser.add_argument("--adjust", default="qfq", choices=["qfq", "hfq", "none"], help="复权方式")
    parser.add_argument("--start", default=None, help="范围更新开始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="初始化截止日期 YYYY-MM-DD")
    parser.add_argument("--run-date", default=None, help="增量运行日期 YYYY-MM-DD，用于计算上一交易日")
    parser.add_argument("--limit", type=int, default=None, help="仅更新前 N 只股票，便于试跑")
    parser.add_argument("--symbols", default="", help="逗号分隔股票代码；为空则按 market 获取全市场列表")
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
    symbols = _parse_symbols(args.symbols)
    if args.dry_run:
        mode = "init_one_year"
        if args.init_years is not None:
            mode = "init_years"
        elif args.update_range:
            mode = "update_range"
        elif args.update_latest:
            mode = "update_latest"
        report = {
            "mode": mode,
            "cache_dir": str(cache.cache_dir),
            "market": args.market,
            "source": args.source,
            "stock_list_source": args.stock_list_source,
            "adjust": args.adjust,
            "start": args.start,
            "end": args.end,
            "limit": args.limit,
            "symbols": symbols,
            "dry_run": True,
        }
    else:
        updater = AshareCacheUpdater(
            data_api=create_data_api(args.source),
            stock_list_api=create_data_api(args.stock_list_source),
            cache=cache,
        )
        if args.init_one_year:
            report = updater.initialize_one_year(
                end=args.end,
                market=args.market,
                adjust=args.adjust,
                limit=args.limit,
                symbols=symbols,
            )
            report["mode"] = "init_one_year"
        elif args.init_years is not None:
            report = updater.initialize_years(
                end=args.end,
                years=args.init_years,
                market=args.market,
                adjust=args.adjust,
                limit=args.limit,
                symbols=symbols,
            )
            report["mode"] = "init_years"
            report["years"] = args.init_years
        elif args.update_range:
            if not args.start or not args.end:
                raise ValueError("--update-range 需要同时提供 --start 和 --end")
            report = updater.update_range(
                start=args.start,
                end=args.end,
                market=args.market,
                adjust=args.adjust,
                limit=args.limit,
                symbols=symbols,
            )
            report["mode"] = "update_range"
        else:
            report = updater.update_latest(
                run_date=args.run_date,
                market=args.market,
                adjust=args.adjust,
                limit=args.limit,
                symbols=symbols,
            )
            report["mode"] = "update_latest"
        report["source"] = args.source
        report["stock_list_source"] = args.stock_list_source
        report["requested_symbols"] = symbols

    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report


def _parse_symbols(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
