import json
import pandas as pd

from quant_assistant.research import (
    DataBundle,
    ExperimentComparison,
    ExperimentRecord,
    FactorAnalysisResult,
    SelectionResearchResult,
    Universe,
)


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


def test_experiment_record_includes_factor_analysis_summary():
    universe = Universe.from_symbols(["000001"], name="demo_pool")
    bundle = DataBundle(
        universe=universe,
        panel=pd.DataFrame(),
        start="2024-01-01",
        end="2024-12-31",
        quality=None,
    )
    result = SelectionResearchResult(metrics={"total_return": 0.12})
    factor_analysis = FactorAnalysisResult(
        summary_table=pd.DataFrame({"rank_ic_mean": [0.05]}, index=["momentum_20"])
    )

    record = ExperimentRecord.from_research(
        name="demo",
        bundle=bundle,
        factors={"momentum_20": 1.0},
        top_n=10,
        rebalance="M",
        result=result,
        factor_analysis=factor_analysis,
        git_commit="abc123",
    )

    assert record.factor_summary["momentum_20"]["rank_ic_mean"] == 0.05


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
