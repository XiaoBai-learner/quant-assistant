from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pandas as pd
import pytest
from tickflow import PermissionError as TickFlowPermissionError

from quant_assistant.core.exceptions import DataFetchException
from quant_assistant.data.fetcher.tickflow_fetcher import TickFlowFetcher
from quant_assistant.data.fetcher.unified_fetcher import DataSourceType, UnifiedDataFetcher


def bars(dates=("2026-11-16", "2026-11-17")):
    return {
        "timestamp": [int(pd.Timestamp(d, tz="Asia/Shanghai").timestamp() * 1000) for d in dates],
        "open": [10.0] * len(dates),
        "high": [11.0] * len(dates),
        "low": [9.0] * len(dates),
        "close": [10.5] * len(dates),
        "volume": [1000] * len(dates),
        "amount": [1050000.0] * len(dates),
    }


def fake_client(payload=None):
    return SimpleNamespace(
        klines=SimpleNamespace(get=Mock(return_value=payload or bars())),
        exchanges=SimpleNamespace(
            get_instruments=Mock(
                return_value=[
                    {"symbol": "600000.SH", "name": "浦发银行", "exchange": "SH", "type": "stock"},
                ]
            ),
            list=Mock(return_value=[]),
        ),
        instruments=SimpleNamespace(get=Mock(return_value={"symbol": "600000.SH"})),
        financials=SimpleNamespace(
            metrics=Mock(
                return_value={
                    "600000.SH": [
                        {"period_end": "2026-09-30", "eps": 1.2},
                    ]
                }
            )
        ),
        quotes=SimpleNamespace(
            get=Mock(return_value=[{"symbol": "600000.SH", "last_price": 10.5}])
        ),
        close=Mock(),
    )


@pytest.mark.parametrize(
    "adjust, expected",
    [
        ("qfq", "forward_additive"),
        ("hfq", "backward_additive"),
        ("none", "none"),
        ("forward", "forward"),
    ],
)
def test_daily_uses_millisecond_bounds_and_explicit_adjustment(adjust, expected):
    client = fake_client()
    fetcher = TickFlowFetcher(client=client, mode="free", min_interval=0)
    data = fetcher.get_daily_quotes("sh600000", "20261116", "2026-11-17", adjust=adjust)
    kwargs = client.klines.get.call_args.kwargs
    assert client.klines.get.call_args.args == ("600000.SH",)
    assert kwargs["adjust"] == expected
    assert kwargs["count"] == 10000
    assert kwargs["start_time"] == int(
        pd.Timestamp("2026-11-16", tz="Asia/Shanghai").timestamp() * 1000
    )
    assert (
        kwargs["end_time"]
        == int(pd.Timestamp("2026-11-18", tz="Asia/Shanghai").timestamp() * 1000) - 1
    )
    assert list(data.symbol) == ["600000", "600000"]
    assert data.trade_date.tolist() == list(pd.to_datetime(["2026-11-16", "2026-11-17"]))
    assert data.attrs["source"] == "tickflow"
    assert data.attrs["adjust"] == expected
    assert data.attrs["volume_unit"] == "lot"


def test_daily_clips_sorts_and_deduplicates():
    client = fake_client(bars(("2026-11-18", "2026-11-17", "2026-11-16", "2026-11-17")))
    frame = TickFlowFetcher(client=client, mode="free", min_interval=0).get_daily_quotes(
        "600000", "2026-11-16", "2026-11-17"
    )
    assert frame.trade_date.tolist() == list(pd.to_datetime(["2026-11-16", "2026-11-17"]))


def test_history_paginates_instead_of_silently_truncating():
    client = fake_client()
    dates = pd.date_range("1990-01-01", periods=10001, freq="D")
    client.klines.get.side_effect = [bars(dates[1:]), bars(dates[:1])]
    frame = TickFlowFetcher(client=client, mode="free", min_interval=0).get_daily_quotes("600000")
    assert len(frame) == 10001
    assert client.klines.get.call_count == 2
    assert client.klines.get.call_args.kwargs["end_time"] == bars(dates[1:2])["timestamp"][0] - 1


def test_free_rejects_unsupported_requests_without_network():
    client = fake_client()
    fetcher = TickFlowFetcher(client=client, mode="free", min_interval=0)
    for method, args in [
        (fetcher.get_minute_quotes, ("600000",)),
        (fetcher.get_realtime_quotes, (["600000"],)),
        (fetcher.get_financial_indicators, ("600000",)),
    ]:
        with pytest.raises(DataFetchException, match="免费"):
            method(*args)
    client.klines.get.assert_not_called()
    client.financials.metrics.assert_not_called()


def test_authenticated_permissions_are_reported_without_leaking_key():
    client = fake_client()
    client.klines.get.side_effect = TickFlowPermissionError(
        "无分钟K线查询权限 secret-key", code="FORBIDDEN", status_code=403
    )
    fetcher = TickFlowFetcher(
        api_key="secret-key", client=client, mode="authenticated", min_interval=0
    )
    with pytest.raises(DataFetchException, match="403") as error:
        fetcher.get_minute_quotes("600000", "5m")
    assert "secret-key" not in str(error.value)
    assert error.value.details["status_code"] == 403
    assert "secret-key" not in repr(fetcher)


def test_financials_flatten_symbol_keyed_sdk_records():
    fetcher = TickFlowFetcher(client=fake_client(), mode="authenticated", min_interval=0)
    frame = fetcher.get_financial_indicators("600000")
    assert frame.loc[0, "symbol"] == "600000"
    assert frame.loc[0, "eps"] == 1.2


def test_stock_list_uses_stock_filter_and_six_digit_symbols():
    client = fake_client()
    frame = TickFlowFetcher(client=client, mode="free", min_interval=0).get_stock_list("SH")
    client.exchanges.get_instruments.assert_called_once_with("SH", instrument_type="stock")
    assert frame.loc[0, "symbol"] == "600000"


def test_environment_key_selects_authenticated_but_explicit_free_never_sends_key(monkeypatch):
    import importlib

    module = importlib.import_module("quant_assistant.data.fetcher.tickflow_fetcher")
    monkeypatch.setenv("TICKFLOW_API_KEY", "test-only-key")
    monkeypatch.delenv("TICKFLOW_MODE", raising=False)
    monkeypatch.setattr(module, "load_dotenv", lambda *a, **kw: None)
    factory = Mock(return_value=fake_client())
    monkeypatch.setattr(module, "TickFlow", factory)
    TickFlowFetcher()
    assert factory.call_args.kwargs["api_key"] == "test-only-key"
    assert factory.call_args.kwargs["base_url"] == TickFlowFetcher.PAID_API_BASE
    TickFlowFetcher(mode="free")
    assert factory.call_args.kwargs["api_key"] == ""
    assert factory.call_args.kwargs["base_url"] == TickFlowFetcher.FREE_API_BASE


def test_sdk_retries_transient_http_error_and_keeps_adjustment():
    from tickflow import TickFlow

    responses = []

    def handler(request):
        responses.append(request)
        if len(responses) == 1:
            return httpx.Response(503, json={"error": {"code": "UNAVAILABLE", "message": "retry"}})
        return httpx.Response(200, json={"data": bars()})

    client = TickFlow(api_key="", base_url=TickFlowFetcher.FREE_API_BASE, max_retries=1)
    client._client._client.close()
    client._client._client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        data = TickFlowFetcher(client=client, mode="free", min_interval=0).get_daily_quotes(
            "600000", adjust="hfq"
        )
        assert len(data) == 2
        assert len(responses) == 2
        assert responses[-1].url.params["adjust"] == "backward_additive"
    finally:
        client.close()


def unified(monkeypatch, primary="auto", fallback=True):
    monkeypatch.setattr(UnifiedDataFetcher, "_init_fetchers", lambda *a: None)
    fetcher = UnifiedDataFetcher(primary_source=primary, fallback_enabled=fallback)
    fetcher.tickflow_fetcher = fake = SimpleNamespace(
        get_daily_quotes=Mock(return_value=pd.DataFrame({"close": [10.0]}))
    )
    fetcher.efinance_fetcher = SimpleNamespace(
        get_daily_data=Mock(return_value=pd.DataFrame({"close": [11.0]}))
    )
    fetcher.akshare_fetcher = None
    return fetcher, fake


def test_auto_prefers_tickflow_and_records_provenance(monkeypatch):
    fetcher, fake = unified(monkeypatch)
    frame = fetcher.get_daily_quotes("600000", adjust="qfq")
    assert fake.get_daily_quotes.call_args.kwargs["adjust"] == "qfq"
    fetcher.efinance_fetcher.get_daily_data.assert_not_called()
    assert frame.attrs["source"] == "tickflow"
    assert fetcher.last_source == "tickflow"


def test_fallback_records_failure_and_actual_source(monkeypatch):
    fetcher, fake = unified(monkeypatch)
    fake.get_daily_quotes.side_effect = DataFetchException("限流", details={"status_code": 429})
    frame = fetcher.get_daily_quotes("600000")
    assert frame.attrs["source"] == "efinance"
    assert fetcher.last_attempts[0]["status"] == "error"
    assert fetcher.last_attempts[0]["source"] == "tickflow"


def test_auto_fallback_disabled_never_calls_secondary(monkeypatch):
    fetcher, fake = unified(monkeypatch, fallback=False)
    fake.get_daily_quotes.side_effect = DataFetchException("限流")
    with pytest.raises(DataFetchException):
        fetcher.get_daily_quotes("600000")
    fetcher.efinance_fetcher.get_daily_data.assert_not_called()


def test_explicit_index_exchange_survives_routing(monkeypatch):
    fetcher, fake = unified(monkeypatch)
    fetcher.get_daily_quotes("000001.SH")
    assert fake.get_daily_quotes.call_args.args[0] == "000001.SH"


def test_malformed_candles_raise_instead_of_returning_incomplete_data():
    payload = bars()
    payload["amount"] = []
    fetcher = TickFlowFetcher(client=fake_client(payload), mode="free", min_interval=0)
    with pytest.raises(DataFetchException, match="字段缺失|长度"):
        fetcher.get_daily_quotes("600000")


def test_authenticated_financial_denial_does_not_become_empty_success():
    client = fake_client()
    client.financials.metrics.side_effect = TickFlowPermissionError(
        "无公司财务数据查询权限", code="FORBIDDEN", status_code=403
    )
    with pytest.raises(DataFetchException, match="403"):
        TickFlowFetcher(
            client=client, mode="authenticated", min_interval=0
        ).get_financial_indicators("600000")


def test_stock_list_failure_does_not_return_partial_market():
    client = fake_client()
    client.exchanges.get_instruments.side_effect = [
        [{"symbol": "600000.SH", "name": "浦发银行", "exchange": "SH"}],
        RuntimeError("SZ unavailable"),
    ]
    with pytest.raises(DataFetchException, match="SZ unavailable"):
        TickFlowFetcher(client=client, mode="free", min_interval=0).get_stock_list()


def test_repeated_pagination_page_raises():
    dates = pd.date_range("1990-01-01", periods=10000, freq="D")
    fetcher = TickFlowFetcher(client=fake_client(bars(dates)), mode="free", min_interval=0)
    with pytest.raises(DataFetchException, match="分页"):
        fetcher.get_daily_quotes("600000")


def test_default_source_is_tickflow(monkeypatch):
    monkeypatch.setattr(UnifiedDataFetcher, "_init_fetchers", lambda *a: None)
    assert UnifiedDataFetcher().primary_source == DataSourceType.TICKFLOW


def test_realtime_fallback_policy_is_enforced(monkeypatch):
    fetcher, fake = unified(monkeypatch, fallback=False)
    fake.get_realtime_quotes = Mock(side_effect=DataFetchException("403"))
    fetcher.akshare_fetcher = SimpleNamespace(get_realtime_quotes=Mock())
    with pytest.raises(DataFetchException):
        fetcher.get_realtime_quotes(["600000.SH"])
    fetcher.akshare_fetcher.get_realtime_quotes.assert_not_called()


def test_repr_does_not_issue_network_calls(monkeypatch):
    fetcher, fake = unified(monkeypatch)
    repr(fetcher)
    fake.get_daily_quotes.assert_not_called()


def test_invalid_source_is_not_silently_replaced():
    with pytest.raises(ValueError, match="未知数据源"):
        UnifiedDataFetcher(primary_source="typo")


@pytest.mark.parametrize("function_name", ["stock_zh_a_hist", "stock_zh_a_hist_em"])
def test_akshare_fallback_accepts_supported_api_names(monkeypatch, function_name):
    import importlib

    module = importlib.import_module("quant_assistant.data.fetcher.akshare_fetcher")
    history = Mock(return_value=pd.DataFrame({"日期": ["2026-11-17"], "收盘": [10.0]}))
    monkeypatch.setattr(module, "ak", SimpleNamespace(**{function_name: history}))
    fetcher = module.AKShareFetcher()
    fetcher.rate_limit_delay = 0
    frame = fetcher.get_daily_quotes("600000", adjust="hfq")
    assert frame.iloc[0]["close"] == 10.0
    assert history.call_args.kwargs["adjust"] == "hfq"


def test_datahub_market_routes_daily_and_realtime_through_shared_fetcher():
    from quant_assistant.data.hub import DataHub

    frame = pd.DataFrame({"symbol": ["600000"], "close": [10.0]})
    fetcher = SimpleNamespace(
        get_daily_quotes=Mock(return_value=frame), get_realtime_quotes=Mock(return_value=frame)
    )
    hub = DataHub(market_fetcher=fetcher)
    assert hub.market.daily("600000.SH").equals(frame)
    realtime = hub.market.realtime(["600000.SH"])
    assert realtime.iloc[0]["symbol"] == "600000.SH"
    assert realtime.iloc[0]["price"] == 10.0
    fetcher.get_daily_quotes.assert_called_once()
    fetcher.get_realtime_quotes.assert_called_once_with(["600000.SH"])


def test_datahub_realtime_keeps_metadata_columns_and_percentage_units():
    from quant_assistant.data.hub import DataHub

    frame = pd.DataFrame(
        {"symbol": ["600000"], "price": [10.0], "ext.name": ["浦发银行"], "ext.change_pct": [0.015]}
    )
    frame.attrs = {
        "source": "tickflow",
        "endpoint": "quotes",
        "fetch_time": "2026-11-18T16:00:00+08:00",
    }
    hub = DataHub(market_fetcher=SimpleNamespace(get_realtime_quotes=Mock(return_value=frame)))
    data = hub.market.realtime(["600000.SH"])
    assert data.iloc[0]["source"] == "tickflow"
    assert data.iloc[0]["endpoint"] == "quotes"
    assert data.iloc[0]["name"] == "浦发银行"
    assert data.iloc[0]["change_pct"] == 1.5


def test_realtime_keeps_explicit_index_exchange_in_datahub():
    from quant_assistant.data.hub import DataHub

    client = fake_client()
    client.quotes.get.return_value = [{"symbol": "000001.SH", "last_price": 3000.0}]
    fetcher = TickFlowFetcher(client=client, mode="authenticated", min_interval=0)
    frame = DataHub(market_fetcher=fetcher).market.realtime(["000001.SH"])
    assert frame.iloc[0]["symbol"] == "000001.SH"


def test_realtime_distinguishes_same_code_on_two_exchanges():
    from quant_assistant.data.hub import DataHub

    client = fake_client()
    client.quotes.get.return_value = [
        {"symbol": "000001.SH", "last_price": 3000.0},
        {"symbol": "000001.SZ", "last_price": 10.0},
    ]
    fetcher = TickFlowFetcher(client=client, mode="authenticated", min_interval=0)
    frame = DataHub(market_fetcher=fetcher).market.realtime(["000001.SH", "000001.SZ"])
    assert list(frame.symbol) == ["000001.SH", "000001.SZ"]


def test_partial_quote_batch_is_not_reported_as_complete_success():
    client = fake_client()
    fetcher = TickFlowFetcher(client=client, mode="authenticated", min_interval=0)
    with pytest.raises(DataFetchException, match="000001.SZ"):
        fetcher.get_realtime_quotes(["600000.SH", "000001.SZ"])


def test_a_share_stock_list_excludes_b_shares():
    client = fake_client()
    client.exchanges.get_instruments.return_value += [
        {"symbol": "900901.SH", "name": "B share", "exchange": "SH", "type": "stock"}
    ]
    frame = TickFlowFetcher(client=client, mode="free", min_interval=0).get_stock_list("SH")
    assert list(frame.symbol) == ["600000"]


def test_invalid_symbols_and_dates_never_issue_network_requests():
    client = fake_client()
    fetcher = TickFlowFetcher(client=client, mode="free", min_interval=0)
    for symbol, start, end in [("not-stock", None, None), ("600000", "2026-11-18", "2026-11-17")]:
        with pytest.raises(ValueError):
            fetcher.get_daily_quotes(symbol, start, end)
    client.klines.get.assert_not_called()


def test_tickflow_api_data_can_feed_existing_factor_and_backtest_engines():
    from quant_assistant import QuantAPI

    client = fake_client(bars(pd.date_range("2026-10-01", periods=35, freq="B")))
    api = QuantAPI()
    api.data.set_fetcher(TickFlowFetcher(client=client, mode="free", min_interval=0))
    data = api.data.get_stock_data("600000")
    assert api.factors.ma(data, window=5).iloc[-1] == 10.5
    result = api.backtest.run(api.strategy.create("ma_cross", fast_period=3, slow_period=5), data)
    assert "metrics" in result


def test_minute_fallback_uses_existing_efinance_contract(monkeypatch):
    fetcher, fake = unified(monkeypatch)
    fake.get_minute_quotes = Mock(side_effect=DataFetchException("403"))
    fetcher.efinance_fetcher.get_minute_data = Mock(return_value=pd.DataFrame({"close": [10.0]}))
    data = fetcher.get_minute_quotes("600000.SH", "5m", "2026-11-17", "2026-11-17")
    fetcher.efinance_fetcher.get_minute_data.assert_called_once_with(
        symbol="600000", period=5, adjust="", start="2026-11-17", end="2026-11-17"
    )
    assert data.attrs["source"] == "efinance"


def test_incremental_request_preserves_index_exchange(monkeypatch):
    from datetime import date

    fetcher, fake = unified(monkeypatch)
    fetcher.get_daily_quotes_incremental(
        "000001.SH", last_date=date(2024, 1, 1), end_date="2024-01-05"
    )
    assert fake.get_daily_quotes.call_args.args[0] == "000001.SH"


def test_unified_close_releases_tickflow_client(monkeypatch):
    fetcher, fake = unified(monkeypatch)
    fake.close = Mock()
    fetcher.close()
    fake.close.assert_called_once()


def test_data_api_close_releases_fetcher_without_initializing_new_one():
    from quant_assistant import QuantAPI

    api = QuantAPI()
    api.data.close()
    fetcher = SimpleNamespace(close=Mock())
    api.data.set_fetcher(fetcher)
    api.data.close()
    fetcher.close.assert_called_once()
