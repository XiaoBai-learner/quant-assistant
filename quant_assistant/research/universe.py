"""Universe definitions for stock-pool research."""
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Universe:
    """Normalized stock universe with provenance metadata."""

    symbols: List[str]
    name: str = "custom"
    source: str = "manual"
    filters: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.symbols = self._normalize_symbols(self.symbols)
        if not self.symbols:
            raise ValueError("股票池不能为空")

    @classmethod
    def from_symbols(
        cls,
        symbols: Iterable[Optional[str]],
        name: str = "custom",
        source: str = "manual",
        filters: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Universe":
        """Create a universe from raw symbol values."""
        raw_symbols = list(symbols)
        normalized = cls._normalize_symbols(raw_symbols)
        merged_metadata = dict(metadata or {})
        merged_metadata.update({
            "original_count": len(raw_symbols),
            "unique_count": len(normalized),
            "dropped_count": len(raw_symbols) - len(normalized),
        })
        return cls(
            symbols=normalized,
            name=name,
            source=source,
            filters=list(filters or []),
            metadata=merged_metadata,
        )

    @staticmethod
    def _normalize_symbols(symbols: Iterable[Optional[str]]) -> List[str]:
        seen = set()
        normalized = []
        for symbol in symbols:
            if symbol is None:
                continue
            value = str(symbol).strip()
            if value and value not in seen:
                seen.add(value)
                normalized.append(value)
        return normalized
