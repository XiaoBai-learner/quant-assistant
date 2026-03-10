"""
回测模拟层
提供策略回测、绩效分析、参数优化功能
"""
from .engine import BacktestEngine, BacktestConfig
from .broker import Broker, Order, Trade
from .portfolio import Portfolio, Position
from .performance import PerformanceAnalyzer
from .visualization import BacktestVisualizer

__all__ = [
    'BacktestEngine',
    'BacktestConfig',
    'Broker',
    'Order',
    'Trade',
    'Portfolio',
    'Position',
    'PerformanceAnalyzer',
    'BacktestVisualizer',
]
