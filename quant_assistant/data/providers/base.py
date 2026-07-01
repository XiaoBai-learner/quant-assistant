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
