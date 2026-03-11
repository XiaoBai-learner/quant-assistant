"""
回测模拟层
提供策略回测、绩效分析、参数优化功能
支持事件驱动和向量化两种回测模式
"""
from .engine import BacktestEngine, BacktestConfig
from .broker import Broker, Order, Trade
from .portfolio import Portfolio, Position
from .performance import PerformanceAnalyzer
from .visualization import BacktestVisualizer
from .vectorized_engine import VectorizedBacktestEngine, VectorizedResult
from .realistic_broker import RealisticBroker, OrderBook, PriceLevel

__all__ = [
    # 事件驱动回测
    'BacktestEngine',
    'BacktestConfig',
    'Broker',
    'Order',
    'Trade',
    'Portfolio',
    'Position',
    'PerformanceAnalyzer',
    'BacktestVisualizer',
    # 向量化回测
    'VectorizedBacktestEngine',
    'VectorizedResult',
    # 真实撮合
    'RealisticBroker',
    'OrderBook',
    'PriceLevel',
]
