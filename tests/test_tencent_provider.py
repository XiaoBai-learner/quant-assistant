from quant_assistant.data.providers.tencent_provider import TencentProvider


def test_tencent_provider_parses_quote_payload():
    text = 'v_sh600519="1~贵州茅台~600519~1500.00~1490.00~1495.00~100~0~0~150000~";'
    provider = TencentProvider(client=None)

    frame = provider.parse_quote_text(text)

    assert frame.loc[0, "symbol"] == "600519.SH"
    assert frame.loc[0, "name"] == "贵州茅台"
    assert frame.loc[0, "price"] == 1500.00


class FakeTextClient:
    def __init__(self):
        self.urls = []

    def get_text(self, url):
        self.urls.append(url)
        return 'v_sz000001="1~平安银行~000001~10.00~9.90~9.95~100~0~0~1000~";'


def test_tencent_provider_realtime_quote_formats_query_codes():
    client = FakeTextClient()
    provider = TencentProvider(client=client)

    result = provider.realtime_quote(["000001.SZ"])

    assert "sz000001" in client.urls[0]
    assert result.source == "tencent"
    assert result.endpoint == "realtime_quote"
    assert result.data.loc[0, "symbol"] == "000001.SZ"
