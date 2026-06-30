import pandas as pd

from quant_assistant.research import FactorAnalysisResult, ResearchReport, SelectionResearchResult


def make_selection_result():
    return SelectionResearchResult(
        metrics={"total_return": 0.12, "max_drawdown": -0.08},
        selections=pd.DataFrame({
            "rebalance_date": pd.to_datetime(["2024-03-29", "2024-03-29"]),
            "symbol": ["000001", "600000"],
            "rank": [1, 2],
            "score": [1.2, 0.8],
        }),
        factor_contributions=pd.DataFrame({
            "trade_date": pd.to_datetime(["2024-03-29"]),
            "symbol": ["000001"],
            "momentum_20_contribution": [0.7],
        }),
        warnings=["sample warning"],
    )


def test_research_report_renders_core_markdown_sections(tmp_path):
    output = tmp_path / "report.md"

    ResearchReport().write_markdown(make_selection_result(), output_path=str(output))

    text = output.read_text()
    assert "# 股票池多因子研究报告" in text
    assert "## 研究配置" in text
    assert "## 回测绩效摘要" in text
    assert "## 最新一期选股" in text
    assert "sample warning" in text


def test_research_report_includes_data_quality_and_factor_analysis(tmp_path):
    output = tmp_path / "report.md"
    factor_analysis = FactorAnalysisResult(
        summary_table=pd.DataFrame({
            "rank_ic_mean": [0.05],
            "icir": [0.8],
            "top_bottom_mean": [0.02],
            "factor_coverage": [0.95],
        }, index=["momentum_20"]),
        correlation_matrix=pd.DataFrame([[1.0]], index=["momentum_20"], columns=["momentum_20"]),
    )
    result = make_selection_result()
    result.data_quality = {
        "total_symbols": 10,
        "available_symbols": 8,
        "failed_symbols": 2,
        "warnings": ["600000: source unavailable"],
    }

    ResearchReport().write_markdown(result, factor_analysis=factor_analysis, output_path=str(output))

    text = output.read_text()
    assert "## 数据质量摘要" in text
    assert "available_symbols" in text
    assert "## 因子有效性摘要" in text
    assert "momentum_20" in text
    assert "## 因子相关性摘要" in text


def test_research_report_render_markdown_returns_text_without_writing():
    text = ResearchReport().render_markdown(make_selection_result(), metadata={"name": "demo"})

    assert "# 股票池多因子研究报告" in text
    assert "demo" in text
