# Daily Feature Wide and Strategy Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stable daily stock-feature pipeline that turns local daily A-share data plus external board, capital, event, margin, shareholder, and sentiment datasets into a `trade_date + symbol` feature wide table for next-day stock selection research.

**Architecture:** Keep provider reliability in `quant_assistant.data.providers`, cache orchestration in scripts, and research-facing feature engineering in `quant_assistant.research`. First-stage implementation stays daily-only and avoids intraday trading monitors. Strategies consume the wide table through explicit factor columns and must be backtested with next-day executable prices.

**Tech Stack:** Python, pandas, pyarrow Parquet, pytest, local Parquet cache under `~/.quant_assistant/cache`.

---

## Task List

### Task 1: Provider Stability Baseline

**Files:**
- Modify: `quant_assistant/data/providers/http_client.py`
- Test: `tests/test_provider_http_client.py`

- [ ] Add retry configuration to `HTTPClient`: `retries`, `backoff`, and retryable status codes.
- [ ] Retry network and HTTP failures with deterministic sleep injection in tests.
- [ ] Keep JSON parse errors non-retryable because repeated parsing will not fix malformed payloads.
- [ ] Verify provider tests pass.

### Task 2: Daily Feature Wide Builder

**Files:**
- Create: `quant_assistant/research/daily_features.py`
- Modify: `quant_assistant/research/__init__.py`
- Test: `tests/test_research_daily_features.py`

- [ ] Build daily OHLCV features from local market panel without future rows.
- [ ] Merge optional board, fund-flow, event, margin, shareholder, and sentiment datasets by `trade_date + symbol`.
- [ ] Add tradability flags: non-tradable when high equals low, missing OHLCV, zero volume, or STAR Market symbol.
- [ ] Add factor metadata with feature groups and expected directions.
- [ ] Verify daily feature tests pass.

### Task 3: Feature Wide Cache Script

**Files:**
- Create: `scripts/build_daily_feature_wide.py`
- Test: `tests/test_build_daily_feature_wide.py`

- [ ] Read local daily Parquet cache for symbols and date range.
- [ ] Optionally read external cached Parquet folders when present.
- [ ] Write `daily_feature_wide/date_range=<start>_<end>.parquet`.
- [ ] Write a JSON quality report with row count, symbol count, feature coverage, and unusable-row counts.

### Task 4: Strategy Candidate Definitions

**Files:**
- Create: `quant_assistant/research/strategy_candidates.py`
- Test: `tests/test_strategy_candidates.py`

- [ ] Define trend momentum, low-volatility reversal, capital-flow, sector-rotation, and event-enhanced candidate strategies.
- [ ] Each strategy declares factor weights, hard filters, max holdings, and expected market regime.
- [ ] Candidate scoring reads the daily feature wide table and outputs ranked selections.

### Task 5: Realistic Daily Selection Backtest Upgrade

**Files:**
- Modify: `quant_assistant/research/backtest.py`
- Test: `tests/test_research_backtest_execution.py`

- [ ] Add next-day open execution mode.
- [ ] Skip buys and sells on dates where `high == low`.
- [ ] Prevent buying limit-up or non-tradable stocks when execution price is unavailable.
- [ ] Emit detailed trade ledger with date, action, symbol, requested weight, shares, price, commission, slippage, and reason.

### Task 6: Two-Year Research Runner

**Files:**
- Create: `scripts/run_strategy_candidates.py`
- Test: `tests/test_run_strategy_candidates.py`

- [ ] Load two-year local daily data.
- [ ] Build or load feature wide table.
- [ ] Run all candidate strategies.
- [ ] Output ranked strategy report and trade ledgers.

## Feasibility and Efficiency

- Highest feasibility: daily OHLCV, board/event pools, industry rank, and stock fund-flow features. These datasets already have local cache or provider foundations.
- Medium feasibility: margin trading, shareholder count, hot rank, and announcements. These need endpoint-specific parser work and smoke tests.
- Lowest first-stage priority: intraday monitoring, minute-level execution, and live alerting. They are intentionally excluded from this stage.
- Efficient execution order: stabilize provider reliability, create daily feature wide table, then add strategy candidates. This prevents strategy work from overfitting to incomplete ad hoc columns.

## Acceptance Checks

- `python -m pytest tests/test_research_daily_features.py tests/test_provider_http_client.py -q`
- `python -m pytest -q`
- `python scripts/build_daily_feature_wide.py --start <date> --end <date> --dry-run`
