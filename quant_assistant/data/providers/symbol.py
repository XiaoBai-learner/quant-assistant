"""A-share symbol normalization helpers."""
from __future__ import annotations


def normalize_symbol(symbol: str) -> str:
    """Return six-digit symbol with exchange suffix."""
    value = str(symbol).strip().upper()
    if value.startswith(("SH", "SZ", "BJ")):
        value = value[2:] + "." + value[:2]
    if "." in value:
        code, exchange = value.split(".", 1)
        return f"{code.zfill(6)}.{exchange.upper()}"
    code = value.zfill(6)
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return f"{code}.SH"
    if code.startswith(("000", "001", "002", "003", "300", "301")):
        return f"{code}.SZ"
    if code.startswith(("43", "83", "87", "88", "92")):
        return f"{code}.BJ"
    return code


def tencent_code(symbol: str) -> str:
    """Return Tencent quote code such as sh600519."""
    normalized = normalize_symbol(symbol)
    code, exchange = normalized.split(".")
    return f"{exchange.lower()}{code}"


def eastmoney_secid(symbol: str) -> str:
    """Return EastMoney secid such as 1.600519 or 0.000001."""
    normalized = normalize_symbol(symbol)
    code, exchange = normalized.split(".")
    market = {"SH": "1", "SZ": "0", "BJ": "0"}.get(exchange, "0")
    return f"{market}.{code}"


def eastmoney_secids(symbols: list[str]) -> str:
    """Return comma-separated EastMoney secids."""
    return ",".join(eastmoney_secid(symbol) for symbol in symbols)
