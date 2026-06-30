# Experiment Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add lightweight experiment comparison so multiple exported `experiment.json` files can be loaded, ranked, and exported as a comparison table.

**Architecture:** Extend `quant_assistant.research.experiment` with `ExperimentComparison`. It reads JSON records, flattens key metadata/metrics/factor summaries into a pandas DataFrame, and writes CSV for spreadsheet-style review.

**Tech Stack:** Python 3.10+, json, pathlib, pandas, pytest.

---

## File Structure

- Modify `quant_assistant/research/experiment.py`: add `ExperimentComparison`.
- Modify `quant_assistant/research/__init__.py`: export `ExperimentComparison`.
- Modify `tests/test_research_experiment.py`: add comparison tests.
- Modify `README.md`: add short experiment comparison example.

## Task 1: Load JSON Records And Build Comparison Table

**Files:**
- Modify: `quant_assistant/research/experiment.py`
- Modify: `quant_assistant/research/__init__.py`
- Test: `tests/test_research_experiment.py`

- [x] **Step 1: Write failing test**

```python
def test_experiment_comparison_loads_json_records_and_builds_table(tmp_path):
    ExperimentRecord(
        name="exp_a",
        universe={"symbol_count": 10},
        period={"start": "2024-01-01", "end": "2024-12-31"},
        strategy={"top_n": 10, "rebalance": "M", "factors": {"momentum_20": 1.0}},
        data_quality={"available_symbols": 9},
        metrics={"total_return": 0.12, "max_drawdown": -0.08},
        factor_summary={"momentum_20": {"rank_ic_mean": 0.04, "top_bottom_mean": 0.02}},
    ).export_json(str(tmp_path / "exp_a.json"))
    ExperimentRecord(
        name="exp_b",
        universe={"symbol_count": 10},
        period={"start": "2024-01-01", "end": "2024-12-31"},
        strategy={"top_n": 20, "rebalance": "M", "factors": {"momentum_60": 1.0}},
        data_quality={"available_symbols": 8},
        metrics={"total_return": 0.2, "max_drawdown": -0.1},
        factor_summary={"momentum_60": {"rank_ic_mean": 0.06, "top_bottom_mean": 0.03}},
    ).export_json(str(tmp_path / "exp_b.json"))

    comparison = ExperimentComparison.from_json_files([str(tmp_path / "exp_a.json"), str(tmp_path / "exp_b.json")])
    table = comparison.to_frame()

    assert list(table["name"]) == ["exp_b", "exp_a"]
    assert table.loc[0, "total_return"] == 0.2
    assert table.loc[0, "available_symbols"] == 8
    assert table.loc[0, "factor_count"] == 1
```

- [x] **Step 2: Run test and verify RED**

Run: `python -m pytest tests/test_research_experiment.py::test_experiment_comparison_loads_json_records_and_builds_table -q`

Expected: FAIL because `ExperimentComparison` is not exported.

- [x] **Step 3: Implement comparison**

Implement:

- `ExperimentComparison(records)`.
- `from_json_files(paths)`.
- `to_frame(sort_by="total_return", ascending=False)`.
- Flatten columns: `name`, `created_at`, `start`, `end`, `symbol_count`, `available_symbols`, `top_n`, `rebalance`, `factor_count`, `total_return`, `max_drawdown`, `mean_rank_ic`, `mean_top_bottom`.

- [x] **Step 4: Run tests and verify GREEN**

Run: `python -m pytest tests/test_research_experiment.py -q`

Expected: PASS.

## Task 2: CSV Export And Directory Loading

**Files:**
- Modify: `quant_assistant/research/experiment.py`
- Test: `tests/test_research_experiment.py`

- [x] **Step 1: Write failing test**

```python
def test_experiment_comparison_loads_directory_and_exports_csv(tmp_path):
    ExperimentRecord(
        name="exp_a",
        universe={"symbol_count": 10},
        period={"start": "2024-01-01", "end": "2024-12-31"},
        strategy={"top_n": 10, "rebalance": "M", "factors": {"momentum_20": 1.0}},
        metrics={"total_return": 0.12},
    ).export_json(str(tmp_path / "exp_a.json"))

    comparison = ExperimentComparison.from_directory(str(tmp_path))
    output = tmp_path / "comparison.csv"
    comparison.export_csv(str(output))

    exported = pd.read_csv(output)
    assert exported.loc[0, "name"] == "exp_a"
    assert output.exists()
```

- [x] **Step 2: Run test and verify RED**

Run: `python -m pytest tests/test_research_experiment.py::test_experiment_comparison_loads_directory_and_exports_csv -q`

Expected: FAIL because `from_directory()` or `export_csv()` is missing.

- [x] **Step 3: Implement helpers**

Implement:

- `from_directory(directory, pattern="*.json")`, sorted by filename.
- `export_csv(output_path, sort_by="total_return", ascending=False)`.

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
from quant_assistant.research import ExperimentComparison

comparison = ExperimentComparison.from_directory("reports/experiments")
comparison.export_csv("reports/experiment_comparison.csv")
print(comparison.to_frame())
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
        docs/superpowers/plans/2026-06-30-experiment-comparison.md
git commit -m "feat: add experiment comparison tables"
```

