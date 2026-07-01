# A Stock Data Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production-grade slice of the `a-stock-data` integration: provider infrastructure, Tencent market data, EastMoney signal data, Parquet caching, and research-factor handoff.

**Architecture:** External endpoints are wrapped by small provider classes under `quant_assistant/data/providers`; datasets normalize provider output under `quant_assistant/data/datasets`; scripts call datasets and write Parquet caches. Research code consumes only normalized tables, not raw external fields.

**Tech Stack:** Python 3.10+, `requests`, `pandas`, `pyarrow`, pytest, existing `quant_assistant.data.local_cache` patterns.

---

## File Structure

- Create `quant_assistant/data/providers/base.py`: provider result dataclass and provider protocol.
- Create `quant_assistant/data/providers/errors.py`: provider-specific exceptions.
- Create `quant_assistant/data/providers/rate_limiter.py`: serial interval limiter for EastMoney.
- Create `quant_assistant/data/providers/http_client.py`: shared requests session wrapper with retries and metadata.
- Create `quant_assistant/data/providers/symbol.py`: A-share symbol normalization and Tencent/EastMoney prefix helpers.
- Create `quant_assistant/data/providers/tencent_provider.py`: Tencent quote and valuation endpoint.
- Create `quant_assistant/data/providers/eastmoney_provider.py`: EastMoney limit-board, dragon-tiger, capital-flow, industry, concept endpoints.
- Create `quant_assistant/data/providers/__init__.py`: public provider exports.
- Create `quant_assistant/data/datasets/market.py`: normalized market data functions.
- Create `quant_assistant/data/datasets/signals.py`: normalized signal data functions.
- Create `quant_assistant/data/datasets/__init__.py`: public dataset exports.
- Create `quant_assistant/data/hub.py`: `DataHub` facade.
- Modify `quant_assistant/data/__init__.py`: export `DataHub`.
- Create `scripts/cache_a_stock_extended.py`: daily cache script for MVP endpoints.
- Create tests:
  - `tests/test_provider_symbol.py`
  - `tests/test_provider_rate_limiter.py`
  - `tests/test_provider_http_client.py`
  - `tests/test_tencent_provider.py`
  - `tests/test_eastmoney_provider.py`
  - `tests/test_datahub.py`
  - `tests/test_cache_a_stock_extended.py`

## Task 1: Provider Base Types

**Files:**
- Create: `quant_assistant/data/providers/base.py`
- Create: `quant_assistant/data/providers/errors.py`
- Test: `tests/test_provider_http_client.py`

- [ ] **Step 1: Write the failing test**

```python
from quant_assistant.data.providers.base import ProviderResult


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_provider_http_client.py::test_provider_result_keeps_source_metadata -q`

Expected: FAIL with `ModuleNotFoundError` for `quant_assistant.data.providers`.

- [ ] **Step 3: Implement provider base types**

```python
"""Base provider contracts for external data sources."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Protocol


@dataclass
class ProviderResult:
    """Data returned by one external provider call with trace metadata."""

    data: Any
    source: str
    endpoint: str
    params: Dict[str, Any] = field(default_factory=dict)
    raw_hash: str = ""
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataProvider(Protocol):
    """Protocol implemented by all external data providers."""

    source: str
```

```python
"""Provider exceptions."""


class ProviderError(RuntimeError):
    """Base error for external data provider failures."""


class ProviderHTTPError(ProviderError):
    """Raised when an HTTP provider returns an invalid response."""


class ProviderParseError(ProviderError):
    """Raised when provider payload parsing fails."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_provider_http_client.py::test_provider_result_keeps_source_metadata -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quant_assistant/data/providers/base.py quant_assistant/data/providers/errors.py tests/test_provider_http_client.py
git commit -m "feat: add provider result contracts"
```

## Task 2: Symbol Normalization

**Files:**
- Create: `quant_assistant/data/providers/symbol.py`
- Test: `tests/test_provider_symbol.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_provider_symbol.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement symbol helpers**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_provider_symbol.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quant_assistant/data/providers/symbol.py tests/test_provider_symbol.py
git commit -m "feat: add ashare symbol provider helpers"
```

## Task 3: Rate Limiter and HTTP Client

**Files:**
- Create: `quant_assistant/data/providers/rate_limiter.py`
- Create: `quant_assistant/data/providers/http_client.py`
- Test: `tests/test_provider_rate_limiter.py`
- Test: `tests/test_provider_http_client.py`

- [ ] **Step 1: Write failing tests**

```python
from quant_assistant.data.providers.rate_limiter import SerialRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def test_serial_rate_limiter_waits_between_calls():
    clock = FakeClock()
    limiter = SerialRateLimiter(min_interval=1.0, jitter=0.0, monotonic=clock.monotonic, sleep=clock.sleep)

    limiter.wait()
    limiter.wait()

    assert clock.sleeps == [1.0]
```

```python
from quant_assistant.data.providers.http_client import HTTPClient


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_provider_rate_limiter.py tests/test_provider_http_client.py -q`

Expected: FAIL for missing modules/classes.

- [ ] **Step 3: Implement limiter and client**

```python
"""Serial rate limiter for fragile data sources."""
from __future__ import annotations

import random
import time
from typing import Callable


class SerialRateLimiter:
    """Ensure calls are spaced by at least min_interval plus jitter."""

    def __init__(
        self,
        min_interval: float = 1.0,
        jitter: float | tuple[float, float] = 0.0,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.min_interval = min_interval
        self.jitter = jitter
        self.monotonic = monotonic
        self.sleep = sleep
        self._last_call: float | None = None

    def wait(self) -> None:
        now = self.monotonic()
        if self._last_call is not None:
            delay = self.min_interval - (now - self._last_call)
            if delay > 0:
                self.sleep(delay + self._jitter())
        self._last_call = self.monotonic()

    def _jitter(self) -> float:
        if isinstance(self.jitter, tuple):
            return random.uniform(self.jitter[0], self.jitter[1])
        return float(self.jitter)
```

```python
"""Shared HTTP client for provider requests."""
from __future__ import annotations

from typing import Any, Dict

import requests

from .errors import ProviderHTTPError, ProviderParseError
from .rate_limiter import SerialRateLimiter


class HTTPClient:
    """Small requests wrapper with timeout, headers, and optional limiter."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = 10.0,
        headers: Dict[str, str] | None = None,
        limiter: SerialRateLimiter | None = None,
    ):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 quant-assistant/1.0",
        }
        self.limiter = limiter

    def get_text(self, url: str, params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None) -> str:
        if self.limiter is not None:
            self.limiter.wait()
        request_headers = {**self.headers, **(headers or {})}
        response = self.session.get(url, params=params, timeout=self.timeout, headers=request_headers)
        try:
            response.raise_for_status()
        except Exception as exc:
            raise ProviderHTTPError(str(exc)) from exc
        return response.text

    def get_json(self, url: str, params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None) -> Any:
        if self.limiter is not None:
            self.limiter.wait()
        request_headers = {**self.headers, **(headers or {})}
        response = self.session.get(url, params=params, timeout=self.timeout, headers=request_headers)
        try:
            response.raise_for_status()
            return response.json()
        except ProviderHTTPError:
            raise
        except Exception as exc:
            raise ProviderParseError(str(exc)) from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_provider_rate_limiter.py tests/test_provider_http_client.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quant_assistant/data/providers/rate_limiter.py quant_assistant/data/providers/http_client.py tests/test_provider_rate_limiter.py tests/test_provider_http_client.py
git commit -m "feat: add provider http client and limiter"
```

## Task 4: Tencent Provider

**Files:**
- Create: `quant_assistant/data/providers/tencent_provider.py`
- Test: `tests/test_tencent_provider.py`

- [ ] **Step 1: Write failing parser tests**

```python
from quant_assistant.data.providers.tencent_provider import TencentProvider


def test_tencent_provider_parses_quote_payload():
    text = 'v_sh600519="1~贵州茅台~600519~1500.00~1490.00~1495.00~100~0~0~150000~";'
    provider = TencentProvider(client=None)

    frame = provider.parse_quote_text(text)

    assert frame.loc[0, "symbol"] == "600519.SH"
    assert frame.loc[0, "name"] == "贵州茅台"
    assert frame.loc[0, "price"] == 1500.00
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tencent_provider.py -q`

Expected: FAIL for missing provider.

- [ ] **Step 3: Implement Tencent parser and quote method**

```python
"""Tencent Finance provider."""
from __future__ import annotations

import re

import pandas as pd

from .base import ProviderResult
from .http_client import HTTPClient
from .symbol import normalize_symbol, tencent_code


class TencentProvider:
    """Fetch realtime quote and valuation fields from Tencent Finance."""

    source = "tencent"
    quote_url = "https://qt.gtimg.cn/q="

    def __init__(self, client: HTTPClient | None = None):
        self.client = client or HTTPClient(headers={"User-Agent": "Mozilla/5.0"})

    def realtime_quote(self, symbols: list[str]) -> ProviderResult:
        codes = ",".join(tencent_code(symbol) for symbol in symbols)
        text = self.client.get_text(self.quote_url + codes)
        return ProviderResult(
            data=self.parse_quote_text(text),
            source=self.source,
            endpoint="realtime_quote",
            params={"symbols": symbols},
        )

    def parse_quote_text(self, text: str) -> pd.DataFrame:
        rows = []
        for match in re.finditer(r'v_([a-z]{2})(\\d{6})="([^"]*)"', text):
            exchange, code, payload = match.groups()
            fields = payload.split("~")
            symbol = normalize_symbol(f"{code}.{exchange.upper()}")
            rows.append({
                "symbol": symbol,
                "name": fields[1] if len(fields) > 1 else "",
                "price": _to_float(fields[3] if len(fields) > 3 else None),
                "prev_close": _to_float(fields[4] if len(fields) > 4 else None),
                "open": _to_float(fields[5] if len(fields) > 5 else None),
                "volume": _to_float(fields[6] if len(fields) > 6 else None),
                "amount": _to_float(fields[9] if len(fields) > 9 else None),
            })
        return pd.DataFrame(rows)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_tencent_provider.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quant_assistant/data/providers/tencent_provider.py tests/test_tencent_provider.py
git commit -m "feat: add tencent market provider"
```

## Task 5: EastMoney Provider MVP

**Files:**
- Create: `quant_assistant/data/providers/eastmoney_provider.py`
- Test: `tests/test_eastmoney_provider.py`

- [ ] **Step 1: Write failing parser tests**

```python
from quant_assistant.data.providers.eastmoney_provider import EastMoneyProvider


def test_eastmoney_provider_normalizes_limit_up_pool():
    provider = EastMoneyProvider(client=None)
    payload = {
        "data": {
            "pool": [
                {"c": "600000", "n": "浦发银行", "lbc": 2, "fund": 123000000, "fbt": "093000", "lbt": "145500"}
            ]
        }
    }

    frame = provider.parse_limit_up_pool(payload, trade_date="2026-07-01")

    assert frame.loc[0, "trade_date"] == "2026-07-01"
    assert frame.loc[0, "symbol"] == "600000.SH"
    assert frame.loc[0, "consecutive_boards"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_eastmoney_provider.py -q`

Expected: FAIL for missing provider.

- [ ] **Step 3: Implement MVP parser methods and request shells**

Implement these methods first:

```python
limit_up_pool(trade_date: str) -> ProviderResult
broken_limit_pool(trade_date: str) -> ProviderResult
limit_down_pool(trade_date: str) -> ProviderResult
industry_rank() -> ProviderResult
stock_fund_flow_120d(symbol: str) -> ProviderResult
concept_blocks(symbol: str) -> ProviderResult
```

Each method should:

- call `HTTPClient.get_json`;
- return `ProviderResult`;
- parse payload through a dedicated `parse_*` method;
- never call EastMoney without the limiter-enabled client.

- [ ] **Step 4: Run parser tests**

Run: `python -m pytest tests/test_eastmoney_provider.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quant_assistant/data/providers/eastmoney_provider.py tests/test_eastmoney_provider.py
git commit -m "feat: add eastmoney signal provider"
```

## Task 6: Dataset Normalization and DataHub

**Files:**
- Create: `quant_assistant/data/datasets/market.py`
- Create: `quant_assistant/data/datasets/signals.py`
- Create: `quant_assistant/data/datasets/__init__.py`
- Create: `quant_assistant/data/hub.py`
- Modify: `quant_assistant/data/__init__.py`
- Test: `tests/test_datahub.py`

- [ ] **Step 1: Write failing DataHub test**

```python
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


def test_datahub_market_realtime_uses_tencent_provider():
    hub = DataHub(tencent=FakeTencent())

    frame = hub.market.realtime(["000001.SZ"])

    assert frame.loc[0, "symbol"] == "000001.SZ"
    assert frame.loc[0, "source"] == "tencent"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_datahub.py -q`

Expected: FAIL for missing `DataHub`.

- [ ] **Step 3: Implement market and signal facades**

`DataHub.market.realtime` should append metadata columns:

```text
source
endpoint
fetch_time
```

`DataHub.signals.limit_up_pool` should call EastMoney provider and return normalized frame.

- [ ] **Step 4: Export DataHub**

Add `DataHub` to `quant_assistant/data/__init__.py`.

- [ ] **Step 5: Run test**

Run: `python -m pytest tests/test_datahub.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add quant_assistant/data/datasets quant_assistant/data/hub.py quant_assistant/data/__init__.py tests/test_datahub.py
git commit -m "feat: add datahub facade"
```

## Task 7: Extended Cache Script

**Files:**
- Create: `scripts/cache_a_stock_extended.py`
- Test: `tests/test_cache_a_stock_extended.py`

- [ ] **Step 1: Write failing dry-run test**

```python
import json

from scripts.cache_a_stock_extended import build_parser, run


def test_extended_cache_dry_run_writes_plan(tmp_path):
    report = tmp_path / "report.json"
    parser = build_parser()
    args = parser.parse_args([
        "--date",
        "2026-07-01",
        "--cache-dir",
        str(tmp_path / "cache"),
        "--report",
        str(report),
        "--dry-run",
    ])

    result = run(args)
    payload = json.loads(report.read_text())

    assert result["dry_run"] is True
    assert payload["date"] == "2026-07-01"
    assert "limit_up_pool" in payload["endpoints"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cache_a_stock_extended.py -q`

Expected: FAIL for missing script.

- [ ] **Step 3: Implement script**

CLI args:

```text
--date YYYY-MM-DD
--cache-dir PATH
--endpoints limit_up_pool,broken_limit_pool,limit_down_pool,industry_rank
--report reports/a_stock_extended_cache.json
--dry-run
```

Default endpoints:

```text
limit_up_pool
broken_limit_pool
limit_down_pool
industry_rank
```

In non-dry-run mode:

- call `DataHub.signals`;
- write one Parquet per endpoint under `cache-dir`;
- write JSON report with row counts and failures.

- [ ] **Step 4: Run test**

Run: `python -m pytest tests/test_cache_a_stock_extended.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/cache_a_stock_extended.py tests/test_cache_a_stock_extended.py
git commit -m "feat: add extended data cache script"
```

## Task 8: Research Factor Handoff

**Files:**
- Create: `quant_assistant/research/alternative_factors.py`
- Test: `tests/test_research_alternative_factors.py`

- [ ] **Step 1: Write failing factor test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_research_alternative_factors.py -q`

Expected: FAIL for missing module.

- [ ] **Step 3: Implement first alternative factor builder**

```python
"""Alternative data factors for stock-pool research."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_limit_board_features(limit_up_events: pd.DataFrame) -> pd.DataFrame:
    """Build daily limit-board features by symbol."""
    if limit_up_events.empty:
        return pd.DataFrame(columns=["trade_date", "symbol", "limit_up_score"])
    data = limit_up_events.copy()
    data["trade_date"] = pd.to_datetime(data["trade_date"])
    data["consecutive_boards"] = pd.to_numeric(data.get("consecutive_boards", 0), errors="coerce").fillna(0)
    data["sealed_amount"] = pd.to_numeric(data.get("sealed_amount", 0), errors="coerce").fillna(0)
    data["limit_up_score"] = data["consecutive_boards"] + np.log1p(data["sealed_amount"]) / 20
    return data[["trade_date", "symbol", "limit_up_score"]]
```

- [ ] **Step 4: Run test**

Run: `python -m pytest tests/test_research_alternative_factors.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add quant_assistant/research/alternative_factors.py tests/test_research_alternative_factors.py
git commit -m "feat: add alternative data factor builder"
```

## Task 9: Full Verification

**Files:**
- All files changed in Tasks 1-8.

- [ ] **Step 1: Run focused tests**

Run:

```bash
python -m pytest \
  tests/test_provider_symbol.py \
  tests/test_provider_rate_limiter.py \
  tests/test_provider_http_client.py \
  tests/test_tencent_provider.py \
  tests/test_eastmoney_provider.py \
  tests/test_datahub.py \
  tests/test_cache_a_stock_extended.py \
  tests/test_research_alternative_factors.py \
  -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Run dry-run script**

Run:

```bash
python scripts/cache_a_stock_extended.py \
  --date 2026-07-01 \
  --dry-run \
  --report /tmp/a_stock_extended_dry_run.json
```

Expected: JSON report includes default endpoints and no network calls.

- [ ] **Step 4: Commit verification docs if changed**

```bash
git status --short
```

Expected: no unexpected files. Commit any intentional documentation updates.

## Self-Review

- Spec coverage: The plan covers provider contracts, symbol handling, rate limiting, Tencent MVP, EastMoney MVP, DataHub, cache script, and first research-factor handoff.
- Placeholder scan: No `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: `ProviderResult`, `HTTPClient`, `SerialRateLimiter`, `DataHub`, and factor builder names are used consistently across tasks.
