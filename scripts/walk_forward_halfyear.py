#!/usr/bin/env python
"""Half-year walk-forward validation: train factor direction/weights on 6 months,
test out-of-sample on the next 6 months. Nothing is tuned on the test window.

Honest design:
- Factor VALUES use only past rows (per-symbol, no future data).
- Direction (sign) and weight (|ICIR|) of each factor are learned on the TRAIN
  window only, then frozen and applied to the TEST window.
- A 20-day embargo separates train and test so training forward-returns cannot
  leak into the test period.
- Market-regime overlay (proxy index vs its 40d MA, prior-day signal) is applied
  at the return level on the test window.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripts.run_reversal_lowturnover_backtest as base
from quant_assistant.research.backtest import SelectionBacktester
from quant_assistant.research.factor_library import FactorLibrary
from quant_assistant.research.portfolio import PortfolioConstructor

CANDIDATES = [
    "turnover_cv_20", "amihud_illiq_20", "reversal_5", "reversal_10",
    "momentum_20", "momentum_60", "volatility_20", "ma_position_60",
    "max_ret_20", "high_proximity_120",
]
FWD = 20            # forward-return horizon for IC (days)
EMBARGO = 20        # trading-day gap between train and test
TOP_N = 30
STEP = 20           # rebalance step (~monthly)
MAX_W = 0.1
IC_MIN = 0.01       # keep a factor only if |train IC| clears this
MA_WIN = 40


def forward_returns(fw: pd.DataFrame, horizon: int) -> pd.DataFrame:
    parts = []
    for _, g in fw.sort_values(["symbol", "trade_date"]).groupby("symbol", sort=False):
        d = g[["symbol", "trade_date", "close"]].copy()
        d["fwd"] = d["close"].shift(-horizon) / d["close"] - 1
        parts.append(d[["symbol", "trade_date", "fwd"]])
    return pd.concat(parts, ignore_index=True)


def train_weights(processed: pd.DataFrame, fwd: pd.DataFrame, train_dates) -> dict:
    """Learn per-factor signed weight from train-window rank IC (ICIR)."""
    df = processed[processed["trade_date"].isin(train_dates)].merge(
        fwd, on=["symbol", "trade_date"], how="left"
    )
    weights = {}
    for f in CANDIDATES:
        ics = []
        for _, day in df.groupby("trade_date", sort=False):
            s = day[[f, "fwd"]].dropna()
            if len(s) < 20:
                continue
            ic = s[f].rank().corr(s["fwd"].rank())
            if not pd.isna(ic):
                ics.append(ic)
        if len(ics) < 3:
            continue
        ic_mean = float(np.mean(ics))
        ic_std = float(np.std(ics))
        if abs(ic_mean) < IC_MIN or ic_std == 0:
            continue
        icir = ic_mean / ic_std
        # weight magnitude = |ICIR|, sign = sign of IC (higher processed = higher raw)
        weights[f] = float(np.sign(ic_mean) * abs(icir))
    return weights


def regime_signal(fw: pd.DataFrame, eval_dates) -> pd.Series:
    uni = fw[fw["is_allowed_universe"] == True]
    mkt = uni.groupby("trade_date")["return_1d"].mean().sort_index()
    cum = (1 + mkt.fillna(0)).cumprod()
    ma = cum.rolling(MA_WIN, min_periods=MA_WIN).mean()
    bull = (cum > ma).shift(1)  # prior-day signal, execute today
    return bull.reindex(eval_dates).fillna(True).astype(bool)


def backtest_test_window(fw, processed, weights, test_dates):
    """Score on test dates with frozen weights, pick top-N, realistic backtest."""
    sc = processed[processed["trade_date"].isin(test_dates)].copy()
    names = list(weights)
    denom = sum(abs(w) for w in weights.values()) or 1.0
    sc["score"] = sum(sc[f] * w for f, w in weights.items()) / denom

    flags = fw[["symbol", "trade_date", "is_allowed_universe", "is_tradable_next_day"]]
    sc = sc.merge(flags, on=["symbol", "trade_date"], how="left")
    mask = sc["is_allowed_universe"].fillna(False) & sc["is_tradable_next_day"].fillna(False)
    sc = sc[mask & sc["score"].notna()]

    dates = sorted(sc["trade_date"].unique())
    rebal = set(dates[::STEP])
    sc = sc[sc["trade_date"].isin(rebal)]

    sels = []
    for td, g in sc.groupby("trade_date", sort=True):
        r = g.sort_values(["score", "symbol"], ascending=[False, True]).head(TOP_N).copy()
        r["rebalance_date"] = pd.Timestamp(td)
        sels.append(r)
    if not sels:
        return None
    selections = pd.concat(sels, ignore_index=True)
    holdings = PortfolioConstructor(max_weight=MAX_W).construct(selections)
    bt = SelectionBacktester(300000, 0.0003, 0.0005).run(fw, holdings, execution="next_open")
    daily = bt["daily_returns"].copy()
    daily["trade_date"] = pd.to_datetime(daily["trade_date"])
    # keep only test-window days, reset to 300k
    daily = daily[daily["trade_date"].isin(test_dates)].copy()
    return daily


def stats(ret, label):
    r = pd.Series(np.asarray(ret)).fillna(0)
    val = 300000 * (1 + r).cumprod()
    tot = val.iloc[-1] / 300000 - 1
    ann = (1 + tot) ** (252 / len(val)) - 1 if len(val) else 0
    vol = r.std() * np.sqrt(252)
    sharpe = ann / vol if vol > 0 else 0
    dd = (val / val.cummax() - 1).min()
    calmar = ann / abs(dd) if dd else 0
    win = (r > 0).mean()
    print(f"  {label:16s} 收益{tot*100:6.1f}%  回撤{dd*100:6.1f}%  年化{ann*100:5.1f}%  "
          f"夏普{sharpe:.2f}  Calmar{calmar:.2f}  胜率{win*100:.0f}%  终值{val.iloc[-1]/10000:.1f}万")
    return dict(total=tot, dd=dd, sharpe=sharpe, calmar=calmar)


def main():
    fw = base.load_feature_wide()
    print("computing processed factors on full panel (this is the slow step)...")
    lib = FactorLibrary()
    processed = lib.compute_processed(fw, CANDIDATES, align_direction=False)
    processed["trade_date"] = pd.to_datetime(processed["trade_date"])
    fwd = forward_returns(fw, FWD)

    all_dates = pd.Series(sorted(pd.to_datetime(fw["trade_date"]).unique()))

    folds = [
        ("2025H1", "2025H2", ("2025-01-01", "2025-06-30"), ("2025-07-01", "2025-12-31")),
        ("2025H2", "2026H1", ("2025-07-01", "2025-12-31"), ("2026-01-01", "2026-06-30")),
    ]

    for train_lbl, test_lbl, (tr_lo, tr_hi), (te_lo, te_hi) in folds:
        train_dates = all_dates[(all_dates >= tr_lo) & (all_dates <= tr_hi)]
        test_all = all_dates[(all_dates >= te_lo) & (all_dates <= te_hi)]
        test_dates = test_all.iloc[EMBARGO:]  # embargo after train

        weights = train_weights(processed, fwd, set(train_dates))
        print(f"\n=== Fold: 训练 {train_lbl} → 实测 {test_lbl} (embargo {EMBARGO}d) ===")
        if not weights:
            print("  训练期无因子通过 IC 门槛,跳过")
            continue
        wshow = {k: round(v, 2) for k, v in sorted(weights.items(), key=lambda x: -abs(x[1]))}
        print(f"  训练期学到的因子权重(符号=方向): {wshow}")

        daily = backtest_test_window(fw, processed, weights, set(test_dates))
        if daily is None or daily.empty:
            print("  实测期无有效选股")
            continue
        r0 = daily["daily_return"].values
        stats(r0, "样本外(无择时)")
        sig = regime_signal(fw, daily["trade_date"]).values
        stats(np.where(sig, r0, 0.0), "样本外+择时空仓")


if __name__ == "__main__":
    main()
