"""Shared HTTP client for provider requests."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

import requests

from quant_assistant.data.providers.errors import ProviderHTTPError, ProviderParseError
from quant_assistant.data.providers.rate_limiter import SerialRateLimiter


class HTTPClient:
    """Small requests wrapper with timeout, headers, limiter, and retries."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
        limiter: Optional[SerialRateLimiter] = None,
        retries: int = 2,
        backoff: float = 0.5,
        retry_statuses: Optional[set[int]] = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 quant-assistant/1.0",
        }
        self.limiter = limiter
        self.retries = max(0, retries)
        self.backoff = max(0.0, backoff)
        self.retry_statuses = retry_statuses or {429, 500, 502, 503, 504}
        self.sleep = sleep

    def get_text(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """Fetch text from an HTTP GET endpoint."""
        response = self._get(url, params=params, headers=headers)
        return response.text

    def get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Fetch JSON from an HTTP GET endpoint."""
        response = self._get(url, params=params, headers=headers)
        try:
            return response.json()
        except Exception as exc:  # noqa: BLE001 - requests may raise heterogeneous JSON errors
            raise ProviderParseError(str(exc)) from exc

    def _get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        request_headers = {**self.headers, **(headers or {})}
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            if self.limiter is not None:
                self.limiter.wait()
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    headers=request_headers,
                )
                response.raise_for_status()
                return response
            except Exception as exc:  # noqa: BLE001 - requests raises heterogeneous network errors
                last_error = exc
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                response_status = getattr(locals().get("response", None), "status_code", None)
                retryable_status = status_code in self.retry_statuses or response_status in self.retry_statuses
                retryable_network = status_code is None and response_status is None
                if attempt >= self.retries or not (retryable_status or retryable_network):
                    raise ProviderHTTPError(str(exc)) from exc
                self.sleep(self.backoff * (2 ** attempt))
        raise ProviderHTTPError(str(last_error))
