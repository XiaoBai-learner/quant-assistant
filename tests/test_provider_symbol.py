from quant_assistant.data.providers.symbol import (
    eastmoney_secids,
    normalize_symbol,
    tencent_code,
)


def test_normalize_symbol_adds_exchange_suffix():
    assert normalize_symbol("600519") == "600519.SH"
    assert normalize_symbol("000001") == "000001.SZ"
    assert normalize_symbol("920002") == "920002.BJ"
    assert normalize_symbol("sz000001") == "000001.SZ"


def test_provider_specific_code_formats():
    assert tencent_code("600519.SH") == "sh600519"
    assert tencent_code("000001.SZ") == "sz000001"
    assert eastmoney_secids(["600519.SH", "000001.SZ"]) == "1.600519,0.000001"
