# Experiment Record Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add lightweight experiment metadata records so stock-pool research runs can be named, reproduced, compared, and exported to JSON.

**Architecture:** Add `quant_assistant.research.experiment` as a small metadata module. It does not manage a database or rerun experiments; it serializes the configuration and key summaries already produced by `DataBundle`, `SelectionResearch`, and `FactorAnalyzer`.

**Tech Stack:** Python 3.10+, dataclasses, json, subprocess for optional git hash, pytest.

---

## File Structure

- Create `quant_assistant/research/experiment.py`: `ExperimentRecord` dataclass and constructors.
- Modify `quant_assistant/research/__init__.py`: export `ExperimentRecord`.
- Create `tests/test_research_experiment.py`: JSON export and constructor tests.
- Modify `README.md`: add short experiment record export example.

## Task 1: ExperimentRecord Dataclass And JSON Export

**Files:**
- Create: `quant_assistant/research/experiment.py`
- Modify: `quant_assistant/research/__init__.py`
- Test: `tests/test_research_experiment.py`

- [x] **Step 1: Write failing test**

```python
import json

from quant_assistant.research import ExperimentRecord


def test_experiment_record_exports_serializable_json(tmp_path):
    record = ExperimentRecord(
        name="demo",
        universe={"name": "custom", "symbols": ["000001", "600000"], "symbol_count": 2},
        period={"start": "2024-01-01", "end": "2024-12-31"},
        strategy={"factors": {"momentum_20": 1.0}, "top_n": 10, "rebalance": "M"},
        data_quality={"total_symbols": 2, "available_symbols": 2},
        metrics={"total_return": 0.12},
        git_commit="abc123",
    )

    output = tmp_path / "experiment.json"
    record.export_json(str(output))

    payload = json.loads(output.read_text())
    assert payload["name"] == "demo"
    assert payload["universe"]["symbol_count"] == 2
    assert payload["strategy"]["factors"]["momentum_20"] == 1.0
```

- [x] **Step 2: Run test and verify RED**

Run: `python -m pytest tests/test_research_experiment.py::test_experiment_record_exports_serializable_json -q`

Expected: FAIL because `ExperimentRecord` is not exported.

- [x] **Step 3: Implement dataclass**

Implement:

- Fields: `name`, `created_at`, `universe`, `period`, `strategy`, `data_quality`, `factor_summary`, `metrics`, `git_commit`, `notes`.
- `to_dict()` returning JSON-serializable payload.
- `export_json(output_path)` writing UTF-8 pretty JSON.
- `current_git_commit()` returning short hash or `None`.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_experiment.py -q`

Expected: PASS.

## Task 2: Construct From DataBundle And Research Results

**Files:**
- Modify: `quant_assistant/research/experiment.py`
- Test: `tests/test_research_experiment.py`

- [x] **Step 1: Write failing test**

```python
import pandas as pd

from quant_assistant.research import DataBundle, ExperimentRecord, SelectionResearchResult, Universe


def test_experiment_record_from_research_inputs_builds_reproducible_metadata():
    universe = Universe.from_symbols(["000001", "600000"], name="demo_pool")
    bundle = DataBundle(
        universe=universe,
        panel=pd.DataFrame(),
        start="2024-01-01",
        end="2024-12-31",
        quality=None,
    )
    result = SelectionResearchResult(metrics={"total_return": 0.12}, data_quality={"available_symbols": 2})

    record = ExperimentRecord.from_research(
        name="demo",
        bundle=bundle,
        factors={"momentum_20": 1.0, "volatility_20": -0.5},
        top_n=10,
        rebalance="M",
        result=result,
        git_commit="abc123",
    )

    payload = record.to_dict()
    assert payload["universe"]["name"] == "demo_pool"
    assert payload["period"]["start"] == "2024-01-01"
    assert payload["strategy"]["top_n"] == 10
    assert payload["data_quality"]["available_symbols"] == 2
    assert payload["metrics"]["total_return"] == 0.12
```

- [x] **Step 2: Run test and verify RED**

Run: `python -m pytest tests/test_research_experiment.py::test_experiment_record_from_research_inputs_builds_reproducible_metadata -q`

Expected: FAIL because `from_research()` is missing.

- [x] **Step 3: Implement constructor**

Implement `ExperimentRecord.from_research(...)` using:

- `bundle.universe.name`, `bundle.symbols`, symbol count, source.
- `bundle.start`, `bundle.end`.
- factors, top_n, rebalance.
- result data_quality and metrics.
- optional factor analysis summary if provided.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_experiment.py -q`

Expected: PASS.

## Task 3: README And Full Verification

**Files:**
- Modify: `README.md`
- Test: all tests

- [x] **Step 1: Update README**

Add:

```python
from quant_assistant.research import ExperimentRecord

ExperimentRecord.from_research(
    name="momentum_quality_demo",
    bundle=bundle,
    factors={"momentum_20": 1.0, "momentum_60": 1.0},
    top_n=10,
    rebalance="M",
    result=result,
    factor_analysis=factor_analysis,
).export_json("reports/experiment.json")
```

- [x] **Step 2: Run full tests**

Run: `python -m pytest tests -q`

Expected: all tests pass.

- [x] **Step 3: Commit**

```bash
git add quant_assistant/research/experiment.py \
        quant_assistant/research/__init__.py \
        tests/test_research_experiment.py \
        README.md \
        docs/superpowers/plans/2026-06-30-experiment-record.md
git commit -m "feat: add research experiment records"
```

