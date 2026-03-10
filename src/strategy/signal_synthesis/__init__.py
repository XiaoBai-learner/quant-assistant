"""
信号合成与指标组合策略模块
支持多维度指标组合、选股策略、买卖点策略
集成遗传算法进行阈值优化
"""
from .strategy_builder import StrategyBuilder, StrategyRule
from .stock_selector import StockSelector
from .signal_generator import SignalGenerator
from .ga_optimizer import GAOptimizer
from .builtin_strategies import (
    TrendFollowingStrategy,
    MeanReversionStrategy,
    BreakoutStrategy,
    MultiFactorStrategy
)

__all__ = [
    'StrategyBuilder',
    'StrategyRule',
    'StockSelector',
    'SignalGenerator',
    'GAOptimizer',
    'TrendFollowingStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy',
    'MultiFactorStrategy',
]
