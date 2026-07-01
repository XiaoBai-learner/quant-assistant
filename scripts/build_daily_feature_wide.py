#!/usr/bin/env python
"""Build daily stock feature wide table from local Parquet caches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from quant_assistant.research.daily_features import DailyFeatureWideBuilder, feature_quality_report  # noqa: E402


OPTIONAL_DATASETS = {
    "industry": ["industry_rank"],
    "fund_flow": ["stock_fund_flow_120d", "fund_flow"],
    "events": ["limit_up_pool", "broken_limit_pool", "limit_down_pool", "dragon_tiger"],
    "margin": ["margin_trading"],
    "shareholders": ["holder_num_change", "shareholders"],
    "sentiment": ["em_hot_rank", "ths_hot_rank", "sentiment"],
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build daily A-share feature wide table")
    parser.add_argument("--daily-cache-dir", default="~/.quant_assistant/cache/ashare_daily")
    parser.add_argument("--extended-cache-dir", default="~/.quant_assistant/cache/extended")
    parser.add_argument("--output-dir", default="~/.quant_assistant/cache/daily_feature_wide")
    parser.add_argument("--start", required=True, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--symbols", default="", help="逗号分隔股票代码；为空则读取目录内全部 parquet")
    parser.add_argument("--report", default="reports/daily_feature_wide.json")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict:
    daily_cache_dir = Path(args.daily_cache_dir).expanduser()
    extended_cache_dir = Path(args.extended_cache_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    symbols = _parse_symbols(args.symbols)
    warnings = []
    if args.dry_run and not daily_cache_dir.exists():
        market = pd.DataFrame(columns=DailyFeatureWideBuilder.required_market_columns)
        warnings.append("日线缓存目录不存在")
    else:
        market = _read_market_cache(daily_cache_dir, args.start, args.end, symbols)
    report = {
        "start": args.start,
        "end": args.end,
        "daily_cache_dir": str(daily_cache_dir),
        "extended_cache_dir": str(extended_cache_dir),
        "input_symbols": int(market["symbol"].nunique()) if not market.empty else 0,
        "input_rows": int(len(market)),
        "dry_run": bool(args.dry_run),
        "warnings": warnings,
    }

    if args.dry_run:
        _write_report(Path(args.report), report)
        return report

    extras = {
        name: _read_first_available_extended(extended_cache_dir, folders, args.start, args.end)
        for name, folders in OPTIONAL_DATASETS.items()
    }
    features = DailyFeatureWideBuilder().build(market, **extras)
    output_path = output_dir / f"date_range={args.start}_{args.end}.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output_path, index=False)
    report["output_path"] = str(output_path)
    report["quality"] = feature_quality_report(features)
    report["optional_sources"] = {
        name: {"rows": int(len(frame)) if frame is not None else 0}
        for name, frame in extras.items()
    }
    _write_report(Path(args.report), report)
    return report


def _parse_symbols(raw: str) -> Optional[list[str]]:
    symbols = [item.strip() for item in raw.split(",") if item.strip()]
    return symbols or None


def _read_market_cache(cache_dir: Path, start: str, end: str, symbols: Optional[list[str]]) -> pd.DataFrame:
    if not cache_dir.exists():
        raise FileNotFoundError(f"日线缓存目录不存在: {cache_dir}")
    files = [cache_dir / f"{symbol}.parquet" for symbol in symbols] if symbols else sorted(cache_dir.glob("*.parquet"))
    frames = []
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    for path in files:
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        if "trade_date" not in frame.columns:
            continue
        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        frame = frame[(frame["trade_date"] >= start_ts) & (frame["trade_date"] <= end_ts)]
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=DailyFeatureWideBuilder.required_market_columns)
    return pd.concat(frames, ignore_index=True)


def _read_first_available_extended(
    cache_dir: Path,
    folder_names: list[str],
    start: str,
    end: str,
) -> Optional[pd.DataFrame]:
    for folder_name in folder_names:
        folder = cache_dir / folder_name
        frame = _read_partitioned_parquet(folder, start, end)
        if frame is not None and not frame.empty:
            return frame
    return None


def _read_partitioned_parquet(folder: Path, start: str, end: str) -> Optional[pd.DataFrame]:
    if not folder.exists():
        return None
    frames = []
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    for path in sorted(folder.rglob("*.parquet")):
        frame = pd.read_parquet(path)
        if "trade_date" not in frame.columns:
            continue
        frame["trade_date"] = pd.to_datetime(frame["trade_date"])
        frame = frame[(frame["trade_date"] >= start_ts) & (frame["trade_date"] <= end_ts)]
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> None:
    parser = build_parser()
    report = run(parser.parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
