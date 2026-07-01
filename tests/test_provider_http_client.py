from quant_assistant.data.providers.base import ProviderResult
from quant_assistant.data.providers.http_client import HTTPClient


def test_provider_result_keeps_source_metadata():
    result = ProviderResult(
        data={"ok": True},
        source="eastmoney",
        endpoint="limit_up_pool",
        params={"date": "2026-07-01"},
        raw_hash="sha256:abc",
    )

    assert result.source == "eastmoney"
    assert result.endpoint == "limit_up_pool"
    assert result.params["date"] == "2026-07-01"
    assert result.raw_hash == "sha256:abc"
    assert result.fetched_at is not None


class FakeResponse:
    status_code = 200
    text = '{"ok": true}'
    content = b'{"ok": true}'

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse()


def test_http_client_get_json_uses_timeout_and_headers():
    session = FakeSession()
    client = HTTPClient(session=session, timeout=3.0, headers={"User-Agent": "qa-test"})

    payload = client.get_json("https://example.test/api", params={"a": 1})

    assert payload == {"ok": True}
    assert session.calls[0][1]["timeout"] == 3.0
    assert session.calls[0][1]["headers"]["User-Agent"] == "qa-test"
