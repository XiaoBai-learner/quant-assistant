from quant_assistant.data.providers.eastmoney_provider import EastMoneyProvider


def test_eastmoney_provider_normalizes_limit_up_pool():
    provider = EastMoneyProvider(client=None)
    payload = {
        "data": {
            "pool": [
                {
                    "c": "600000",
                    "n": "浦发银行",
                    "lbc": 2,
                    "fund": 123000000,
                    "fbt": "093000",
                    "lbt": "145500",
                }
            ]
        }
    }

    frame = provider.parse_limit_up_pool(payload, trade_date="2026-07-01")

    assert frame.loc[0, "trade_date"] == "2026-07-01"
    assert frame.loc[0, "symbol"] == "600000.SH"
    assert frame.loc[0, "consecutive_boards"] == 2
    assert frame.loc[0, "sealed_amount"] == 123000000


def test_eastmoney_provider_normalizes_industry_rank():
    provider = EastMoneyProvider(client=None)
    payload = {
        "data": {
            "diff": [
                {"f12": "BK0420", "f14": "银行", "f3": 1.5, "f104": 20, "f105": 5}
            ]
        }
    }

    frame = provider.parse_industry_rank(payload, trade_date="2026-07-01")

    assert frame.loc[0, "industry_code"] == "BK0420"
    assert frame.loc[0, "industry"] == "银行"
    assert frame.loc[0, "pct_change"] == 1.5


def test_eastmoney_provider_normalizes_concept_blocks():
    provider = EastMoneyProvider(client=None)
    payload = {
        "data": {
            "diff": [
                {"f12": "BK1234", "f14": "机器人概念", "f3": 2.1, "f128": "龙头A"}
            ]
        }
    }

    frame = provider.parse_concept_blocks(payload, symbol="300750.SZ")

    assert frame.loc[0, "symbol"] == "300750.SZ"
    assert frame.loc[0, "block_code"] == "BK1234"
    assert frame.loc[0, "block_name"] == "机器人概念"
