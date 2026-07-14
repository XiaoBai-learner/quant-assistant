#!/usr/bin/env python
"""Real backtest of a reversal + low-turnover strategy on cached A-share data.

Factors are chosen ONLY from those whose direction was confirmed on the actual
2024-07..2026-07 sample via FactorLibrary.validate (see conversation). This is
an honest backtest: it reports whatever the data produces, with no target
return baked in.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from quant_assistant.research.backtest import SelectionBacktester  # noqa: E402
from quant_assistant.research.evaluation import SelectionEvaluator  # noqa: E402
from quant_assistant.research.factor_library import FactorLibrary  # noqa: E402
from quant_assistant.research.portfolio import PortfolioConstructor  # noqa: E402


def load_feature_wide() -> pd.DataFrame:
    path = glob.glob(
        os.path.expanduser("~/.quant_assistant/cache/daily_feature_wide/**/*.parquet"),
        recursive=True,
    )[0]
    fw = pd.read_parquet(path)
    fw["trade_date"] = pd.to_datetime(fw["trade_date"])
    return fw.sort_values(["trade_date", "symbol"]).reset_index(drop=True)


def build_selections(
    fw: pd.DataFrame, weights: dict, top_n: int, rebalance_step: int
) -> pd.DataFrame:
    """Compute composite score, then pick top_n tradable names per rebalance."""
    lib = FactorLibrary()
    scored = lib.composite_score(fw, weights)  # symbol/trade_date/score (higher=better)
    scored["trade_date"] = pd.to_datetime(scored["trade_date"])

    # attach tradability flags from feature_wide
    flags = fw[["symbol", "trade_date", "is_allowed_universe", "is_tradable_next_day"]].copy()
    merged = scored.merge(flags, on=["symbol", "trade_date"], how="left")
    mask = merged["is_allowed_universe"].fillna(False) & merged["is_tradable_next_day"].fillna(False)
    merged = merged[mask & merged["score"].notna()].copy()

    dates = sorted(merged["trade_date"].unique())
    rebalance_dates = set(dates[::max(1, rebalance_step)])
    merged = merged[merged["trade_date"].isin(rebalance_dates)]

    selections = []
    for trade_date, group in merged.groupby("trade_date", sort=True):
        ranked = group.sort_values(["score", "symbol"], ascending=[False, True]).head(top_n).copy()
        ranked["rank"] = range(1, len(ranked) + 1)
        ranked["rebalance_date"] = pd.Timestamp(trade_date)
        selections.append(ranked)
    return pd.concat(selections, ignore_index=True) if selections else pd.DataFrame()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--rebalance-step", type=int, default=20)
    parser.add_argument("--initial-cash", type=float, default=300000.0)
    parser.add_argument("--commission-rate", type=float, default=0.0003)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--max-weight", type=float, default=0.2)
    parser.add_argument("--output-dir", default="reports/reversal_lowturnover")
    args = parser.parse_args()

    # direction-confirmed factors (composite uses higher=better after alignment)
    weights = {
        "turnover_cv_20": 1.0,      # ICIR -0.60 raw; low turnover-vol = good
        "amihud_illiq_20": 0.6,     # ICIR +0.26; illiquidity premium
        "reversal_10": 0.6,         # ICIR -0.23 raw; short-term reversal
        "momentum_60": 0.4,         # ICIR -0.34 raw; long momentum reverses
    }

    fw = load_feature_wide()
    print(f"loaded feature_wide: {len(fw)} rows, {fw['symbol'].nunique()} symbols, "
          f"{fw['trade_date'].min().date()}..{fw['trade_date'].max().date()}")

    selections = build_selections(fw, weights, args.top_n, args.rebalance_step)
    print(f"selections: {len(selections)} rows over {selections['rebalance_date'].nunique()} rebalances")

    holdings = PortfolioConstructor(max_weight=args.max_weight).construct(selections)
    backtest = SelectionBacktester(
        initial_cash=args.initial_cash,
        commission_rate=args.commission_rate,
        slippage=args.slippage,
    ).run(fw, holdings, execution="next_open")
    metrics = SelectionEvaluator().evaluate(backtest["daily_returns"])

    daily = backtest["daily_returns"]
    final_value = float(daily["portfolio_value"].iloc[-1]) if not daily.empty else args.initial_cash

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(out / "daily_returns.parquet", index=False)
    holdings.to_parquet(out / "holdings.parquet", index=False)
    selections.to_parquet(out / "selections.parquet", index=False)
    backtest["trade_ledger"].to_parquet(out / "trade_ledger.parquet", index=False)

    result = {
        "weights": weights,
        "top_n": args.top_n,
        "rebalance_step": args.rebalance_step,
        "initial_cash": args.initial_cash,
        "final_value": final_value,
        "profit_cny": final_value - args.initial_cash,
        "metrics": metrics,
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
