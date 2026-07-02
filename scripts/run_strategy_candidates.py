#!/usr/bin/env python
"""Run daily feature-wide strategy candidates and realistic backtests."""
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

from quant_assistant.research.backtest import SelectionBacktester  # noqa: E402
from quant_assistant.research.evaluation import SelectionEvaluator  # noqa: E402
from quant_assistant.research.portfolio import PortfolioConstructor  # noqa: E402
from quant_assistant.research.strategy_candidates import (  # noqa: E402
    StrategyCandidateRunner,
    default_strategy_candidates,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run daily feature-wide strategy candidates")
    parser.add_argument("--feature-wide", default="", help="已有指标宽表 Parquet 路径")
    parser.add_argument("--daily-cache-dir", default="~/.quant_assistant/cache/ashare_daily")
    parser.add_argument("--extended-cache-dir", default="~/.quant_assistant/cache/extended")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output-dir", default="reports/strategy_candidates")
    parser.add_argument("--initial-cash", type=float, default=300000.0)
    parser.add_argument("--commission-rate", type=float, default=0.0003)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--max-weight", type=float, default=0.2)
    parser.add_argument("--rebalance-step", type=int, default=20)
    parser.add_argument("--strategies", default="", help="逗号分隔策略名；为空则运行全部内置策略")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict:
    feature_wide = _load_feature_wide(args)
    strategy_names = _parse_strategy_names(args.strategies)
    candidates = _select_candidates(strategy_names)
    runnable_candidates, skipped_strategies = _split_runnable_candidates(feature_wide, candidates)
    report = {
        "start": args.start,
        "end": args.end,
        "feature_wide": args.feature_wide,
        "strategy_names": [candidate.name for candidate in candidates],
        "runnable_strategy_names": [candidate.name for candidate in runnable_candidates],
        "input_rows": int(len(feature_wide)),
        "input_symbols": int(feature_wide["symbol"].nunique()) if not feature_wide.empty else 0,
        "dry_run": bool(args.dry_run),
        "strategies": {},
        "skipped_strategies": skipped_strategies,
    }
    if args.dry_run:
        return report

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    rebalance_features = _rebalance_slice(feature_wide, args.rebalance_step)
    selections_by_strategy = StrategyCandidateRunner(runnable_candidates).run(rebalance_features)
    evaluator = SelectionEvaluator()
    portfolio = PortfolioConstructor(max_weight=args.max_weight)
    summary_rows = []

    for candidate in runnable_candidates:
        selections = selections_by_strategy[candidate.name]
        holdings = portfolio.construct(selections)
        backtest = SelectionBacktester(
            initial_cash=args.initial_cash,
            commission_rate=args.commission_rate,
            slippage=args.slippage,
        ).run(feature_wide, holdings, execution="next_open")
        metrics = evaluator.evaluate(backtest["daily_returns"])
        report["strategies"][candidate.name] = {
            "description": candidate.description,
            "expected_regime": candidate.expected_regime,
            "selection_count": int(len(selections)),
            "holding_rows": int(len(holdings)),
            "trade_count": int((backtest["trade_ledger"].get("status", pd.Series(dtype=str)) == "filled").sum()),
            "metrics": metrics,
        }
        summary_rows.append({
            "strategy_name": candidate.name,
            "expected_regime": candidate.expected_regime,
            "selection_count": int(len(selections)),
            "trade_count": report["strategies"][candidate.name]["trade_count"],
            **metrics,
        })
        _write_strategy_outputs(output_dir, candidate.name, selections, holdings, backtest)

    pd.DataFrame(summary_rows).to_csv(output_dir / "strategy_summary.csv", index=False)
    _write_json(output_dir / "strategy_report.json", report)
    return report


def _load_feature_wide(args: argparse.Namespace) -> pd.DataFrame:
    if args.feature_wide:
        data = pd.read_parquet(Path(args.feature_wide).expanduser())
    else:
        from scripts.build_daily_feature_wide import run as build_feature_wide

        output_dir = Path(args.output_dir).expanduser() / "feature_wide"
        build_report = build_feature_wide(argparse.Namespace(
            daily_cache_dir=args.daily_cache_dir,
            extended_cache_dir=args.extended_cache_dir,
            output_dir=str(output_dir),
            start=args.start,
            end=args.end,
            symbols="",
            report=str(output_dir / "build_report.json"),
            dry_run=False,
        ))
        data = pd.read_parquet(build_report["output_path"])
    data["trade_date"] = pd.to_datetime(data["trade_date"])
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end)
    return data[(data["trade_date"] >= start) & (data["trade_date"] <= end)].sort_values(["trade_date", "symbol"])


def _parse_strategy_names(raw: str) -> Optional[list[str]]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    return names or None


def _select_candidates(names: Optional[list[str]]):
    candidates = default_strategy_candidates()
    if names is None:
        return list(candidates.values())
    missing = [name for name in names if name not in candidates]
    if missing:
        raise ValueError(f"未知策略候选: {', '.join(missing)}")
    return [candidates[name] for name in names]


def _split_runnable_candidates(feature_wide: pd.DataFrame, candidates) -> tuple[list, dict]:
    available_columns = set(feature_wide.columns)
    runnable = []
    skipped = {}
    for candidate in candidates:
        required = {"trade_date", "symbol", *candidate.required_columns, *candidate.factor_weights.keys()}
        missing = sorted(required - available_columns)
        if missing:
            skipped[candidate.name] = {
                "reason": "missing_columns",
                "missing_columns": missing,
            }
            continue
        runnable.append(candidate)
    return runnable, skipped


def _rebalance_slice(feature_wide: pd.DataFrame, rebalance_step: int) -> pd.DataFrame:
    step = max(1, int(rebalance_step))
    dates = sorted(pd.to_datetime(feature_wide["trade_date"]).unique())
    selected_dates = set(dates[::step])
    return feature_wide[feature_wide["trade_date"].isin(selected_dates)].copy()


def _write_strategy_outputs(output_dir: Path, strategy_name: str, selections, holdings, backtest) -> None:
    selections_dir = output_dir / "selections"
    holdings_dir = output_dir / "holdings"
    ledger_dir = output_dir / "trade_ledgers"
    daily_dir = output_dir / "daily_returns"
    for directory in [selections_dir, holdings_dir, ledger_dir, daily_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    selections.to_parquet(selections_dir / f"{strategy_name}.parquet", index=False)
    holdings.to_parquet(holdings_dir / f"{strategy_name}.parquet", index=False)
    backtest["trade_ledger"].to_parquet(ledger_dir / f"{strategy_name}.parquet", index=False)
    backtest["daily_returns"].to_parquet(daily_dir / f"{strategy_name}.parquet", index=False)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> None:
    parser = build_parser()
    report = run(parser.parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
