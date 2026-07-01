import pandas as pd

from quant_assistant.data.hub import DataHub
from quant_assistant.data.providers.base import ProviderResult


class FakeTencent:
    def realtime_quote(self, symbols):
        return ProviderResult(
            data=pd.DataFrame({"symbol": symbols, "price": [10.0]}),
            source="tencent",
            endpoint="realtime_quote",
            params={"symbols": symbols},
        )


class FakeEastMoney:
    def limit_up_pool(self, trade_date):
        return ProviderResult(
            data=pd.DataFrame({"trade_date": [trade_date], "symbol": ["600000.SH"]}),
            source="eastmoney",
            endpoint="limit_up_pool",
            params={"date": trade_date},
        )


def test_datahub_market_realtime_uses_tencent_provider():
    hub = DataHub(tencent=FakeTencent())

    frame = hub.market.realtime(["000001.SZ"])

    assert frame.loc[0, "symbol"] == "000001.SZ"
    assert frame.loc[0, "source"] == "tencent"
    assert frame.loc[0, "endpoint"] == "realtime_quote"


def test_datahub_signals_limit_up_uses_eastmoney_provider():
    hub = DataHub(eastmoney=FakeEastMoney())

    frame = hub.signals.limit_up_pool("2026-07-01")

    assert frame.loc[0, "trade_date"] == "2026-07-01"
    assert frame.loc[0, "source"] == "eastmoney"
