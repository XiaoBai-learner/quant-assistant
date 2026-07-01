"""Shared HTTP client for provider requests."""
from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from quant_assistant.data.providers.errors import ProviderHTTPError, ProviderParseError
from quant_assistant.data.providers.rate_limiter import SerialRateLimiter


class HTTPClient:
    """Small requests wrapper with timeout, headers, and optional limiter."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
        headers: Optional[Dict[str, str]] = None,
        limiter: Optional[SerialRateLimiter] = None,
    ):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 quant-assistant/1.0",
        }
        self.limiter = limiter

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
        if self.limiter is not None:
            self.limiter.wait()
        request_headers = {**self.headers, **(headers or {})}
        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout,
            headers=request_headers,
        )
        try:
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - requests raises several HTTP exception types
            raise ProviderHTTPError(str(exc)) from exc
        return response
