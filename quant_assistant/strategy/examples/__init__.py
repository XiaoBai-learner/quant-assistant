"""策略示例"""
from .ma_strategy import MAStrategy
from .macd_strategy import MACDStrategy

_STRATEGIES = {
    "ma": MAStrategy,
    "ma_cross": MAStrategy,
    "moving_average": MAStrategy,
    "macd": MACDStrategy,
    "macd_cross": MACDStrategy,
}


def get_strategy(name: str, **params):
    """按名称创建内置示例策略。"""
    key = name.lower().replace("-", "_")
    strategy_cls = _STRATEGIES.get(key)
    if strategy_cls is None:
        available = ", ".join(sorted(_STRATEGIES))
        raise ValueError(f"未知策略: {name}. 可用策略: {available}")
    return strategy_cls(**params)


def list_strategies():
    """列出可用的内置示例策略名称。"""
    return sorted(_STRATEGIES)


__all__ = ['MAStrategy', 'MACDStrategy', 'get_strategy', 'list_strategies']
