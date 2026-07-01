import pandas as pd

from quant_assistant.research.alternative_factors import build_limit_board_features


def test_build_limit_board_features_scores_limit_up_events():
    events = pd.DataFrame({
        "trade_date": ["2026-07-01"],
        "symbol": ["600000.SH"],
        "consecutive_boards": [2],
        "sealed_amount": [100000000.0],
    })

    features = build_limit_board_features(events)

    assert features.loc[0, "symbol"] == "600000.SH"
    assert features.loc[0, "limit_up_score"] > 0
