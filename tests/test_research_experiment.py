import json
import pandas as pd

from quant_assistant.research import DataBundle, ExperimentRecord, FactorAnalysisResult, SelectionResearchResult, Universe


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
