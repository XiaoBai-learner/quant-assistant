"""Configuration objects for stock-pool factor research."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CostConfig:
    """Trading cost assumptions for selection backtests."""

    commission_rate: float = 0.0003
    slippage: float = 0.0


@dataclass
class SelectionResearchConfig:
    """Configuration for one stock-pool factor selection research run."""

    universe: List[str]
    start: str
    end: str
    factors: Dict[str, float]
    top_n: int = 10
    rebalance: str = "M"
    min_history: int = 120
    max_weight: float = 0.2
    benchmark: Optional[str] = None
    cost: CostConfig = field(default_factory=CostConfig)

    def __post_init__(self) -> None:
        self.universe = self._dedupe_symbols(self.universe)
        self.factor_weights = dict(self.factors)
        if not self.universe:
            raise ValueError("universe 不能为空")
        if self.start > self.end:
            raise ValueError("start 不能晚于 end")
        if not self.factor_weights:
            raise ValueError("factors 不能为空")
        if self.top_n <= 0:
            raise ValueError("top_n 必须大于 0")
        if self.rebalance not in {"W", "M"}:
            raise ValueError("rebalance 仅支持 W 或 M")
        if self.max_weight <= 0 or self.max_weight > 1:
            raise ValueError("max_weight 必须在 (0, 1] 内")

    @staticmethod
    def _dedupe_symbols(symbols: List[str]) -> List[str]:
        seen = set()
        result = []
        for symbol in symbols:
            normalized = str(symbol).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result
