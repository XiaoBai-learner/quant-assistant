# Stock Pool Phase 2 Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build the phase-two stock-pool data layer with universe normalization, multi-stock data bundles, data quality diagnostics, and partial-failure tolerant data loading.

**Architecture:** Add focused modules under `quant_assistant.research` without changing the existing `SelectionResearch` workflow. `Universe` owns stock-pool metadata, `DataQualityReport` summarizes panel health, and `DataBundleBuilder` converts `QuantAPI.data` or a custom loader into a reusable `DataBundle`.

**Tech Stack:** Python 3.10+, dataclasses, pandas, pytest.

---

## File Structure

- Create `quant_assistant/research/universe.py`: `Universe` dataclass and symbol normalization.
- Create `quant_assistant/research/data_quality.py`: `SymbolDataQuality` and `DataQualityReport`.
- Create `quant_assistant/research/panel.py`: `DataBundle` and `DataBundleBuilder`.
- Modify `quant_assistant/research/__init__.py`: export new public classes.
- Create `tests/test_research_data_layer.py`: TDD coverage for universe, quality report, and bundle builder.
- Modify `README.md`: add a short data bundle example after the stock-pool research section.

## Task 1: Universe And DataBundle Objects

**Files:**
- Create: `quant_assistant/research/universe.py`
- Create: `quant_assistant/research/panel.py`
- Modify: `quant_assistant/research/__init__.py`
- Test: `tests/test_research_data_layer.py`

- [x] **Step 1: Write failing tests**

```python
import pandas as pd

from quant_assistant.research import DataBundle, Universe


def test_universe_normalizes_symbols_and_records_metadata():
    universe = Universe.from_symbols(
        [" 000001 ", "600000", "000001", None, ""],
        name="core",
        source="manual",
    )

    assert universe.symbols == ["000001", "600000"]
    assert universe.name == "core"
    assert universe.source == "manual"
    assert universe.metadata["original_count"] == 5
    assert universe.metadata["dropped_count"] == 3


def test_data_bundle_exposes_basic_summary():
    universe = Universe.from_symbols(["000001", "600000"])
    panel = pd.DataFrame({
        "symbol": ["000001", "600000"],
        "trade_date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        "open": [10.0, 20.0],
        "high": [11.0, 21.0],
        "low": [9.0, 19.0],
        "close": [10.5, 20.5],
        "volume": [1000.0, 2000.0],
        "amount": [10500.0, 41000.0],
    })

    bundle = DataBundle(universe=universe, panel=panel, start="2024-01-01", end="2024-01-31")

    assert bundle.symbols == ["000001", "600000"]
    assert bundle.summary()["rows"] == 2
```

- [x] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_research_data_layer.py -q`

Expected: FAIL because `Universe` and `DataBundle` are not exported.

- [x] **Step 3: Implement minimal classes**

Create `Universe.from_symbols()` with whitespace trimming, `None`/empty removal, deduplication preserving input order, and metadata counts. Create `DataBundle` with `symbols` and `summary()`.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_data_layer.py -q`

Expected: PASS.

## Task 2: Data Quality Report

**Files:**
- Create: `quant_assistant/research/data_quality.py`
- Modify: `quant_assistant/research/panel.py`
- Modify: `quant_assistant/research/__init__.py`
- Test: `tests/test_research_data_layer.py`

- [x] **Step 1: Write failing tests**

```python
import pandas as pd

from quant_assistant.research import DataQualityReport, Universe


def test_data_quality_report_flags_missing_duplicates_and_invalid_prices():
    universe = Universe.from_symbols(["000001", "600000", "300001"])
    panel = pd.DataFrame({
        "symbol": ["000001", "000001", "000001", "600000"],
        "trade_date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-01"]),
        "open": [10.0, 10.1, None, 20.0],
        "high": [11.0, 11.1, 10.0, 18.0],
        "low": [9.0, 9.1, 10.5, 19.0],
        "close": [10.5, 10.6, -1.0, 20.5],
        "volume": [1000.0, 1100.0, 0.0, 2000.0],
        "amount": [10500.0, 11660.0, 0.0, 41000.0],
    })

    report = DataQualityReport.from_panel(universe, panel, start="2024-01-01", end="2024-01-03")
    summary = report.summary()

    assert summary["total_symbols"] == 3
    assert summary["available_symbols"] == 2
    assert summary["failed_symbols"] == 1
    assert report.by_symbol["000001"].duplicate_rows == 1
    assert report.by_symbol["000001"].missing_ohlcv == 1
    assert report.by_symbol["000001"].invalid_price_rows == 1
    assert report.by_symbol["000001"].zero_volume_rows == 1
    assert report.by_symbol["300001"].status == "failed"
```

- [x] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_research_data_layer.py::test_data_quality_report_flags_missing_duplicates_and_invalid_prices -q`

Expected: FAIL because `DataQualityReport` does not exist.

- [x] **Step 3: Implement report**

Implement `SymbolDataQuality` and `DataQualityReport.from_panel()`. Coverage is `unique_trade_dates / expected_business_days` using `pd.bdate_range(start, end)`. Status is `failed` for zero rows, `warning` for coverage below `min_coverage` or any missing/invalid/duplicate rows, otherwise `ok`.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_data_layer.py -q`

Expected: PASS.

## Task 3: DataBundleBuilder With Partial Failure Tolerance

**Files:**
- Modify: `quant_assistant/research/panel.py`
- Test: `tests/test_research_data_layer.py`

- [x] **Step 1: Write failing tests**

```python
import pandas as pd

from quant_assistant.research import DataBundleBuilder


class FakeDataAPI:
    def get_stock_data(self, symbol, start=None, end=None, adjust="qfq"):
        if symbol == "600000":
            raise RuntimeError("source unavailable")
        if symbol == "300001":
            return pd.DataFrame()
        return pd.DataFrame({
            "symbol": [symbol, symbol],
            "trade_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "open": [10.0, 10.5],
            "high": [11.0, 11.5],
            "low": [9.0, 9.5],
            "close": [10.5, 11.0],
            "volume": [1000.0, 1200.0],
            "amount": [10500.0, 13200.0],
        })


def test_data_bundle_builder_keeps_usable_symbols_when_some_fail():
    builder = DataBundleBuilder(data_api=FakeDataAPI())

    bundle = builder.build(
        universe=["000001", "600000", "300001"],
        start="2024-01-01",
        end="2024-01-31",
    )

    assert bundle.symbols == ["000001", "600000", "300001"]
    assert set(bundle.panel["symbol"]) == {"000001"}
    assert bundle.fetch_log["000001"]["status"] == "ok"
    assert bundle.fetch_log["600000"]["status"] == "failed"
    assert bundle.fetch_log["300001"]["status"] == "empty"
    assert bundle.quality.summary()["available_symbols"] == 1
    assert "600000" in bundle.quality.failed_symbols
```

- [x] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_research_data_layer.py::test_data_bundle_builder_keeps_usable_symbols_when_some_fail -q`

Expected: FAIL because `DataBundleBuilder` does not exist.

- [x] **Step 3: Implement builder**

Implement `DataBundleBuilder(data_api=None, loader=None)` where `loader(symbol, start, end, adjust)` can replace `data_api.get_stock_data()`. Build one symbol at a time, record `fetch_log`, concatenate valid frames, standardize required columns, sort and drop duplicate symbol/date rows. Raise `ValueError("股票池没有可用行情数据")` only when no valid rows remain.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_data_layer.py -q`

Expected: PASS.

## Task 4: Documentation And Full Verification

**Files:**
- Modify: `README.md`
- Test: all tests

- [x] **Step 1: Update README example**

Add a short example under "股票池多因子选股研究" showing `DataBundleBuilder` before `SelectionResearch`.

- [x] **Step 2: Run full tests**

Run: `python -m pytest tests -q`

Expected: all tests pass.

- [x] **Step 3: Inspect git diff**

Run: `git diff --stat`

Expected: changes are limited to research data-layer files, tests, README, and this plan.

- [x] **Step 4: Commit**

```bash
git add quant_assistant/research/universe.py \
        quant_assistant/research/data_quality.py \
        quant_assistant/research/panel.py \
        quant_assistant/research/__init__.py \
        tests/test_research_data_layer.py \
        README.md \
        docs/superpowers/plans/2026-06-30-stock-pool-phase2-data.md
git commit -m "feat: add stock pool data bundle layer"
```

