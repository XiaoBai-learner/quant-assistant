"""
策略研究层 - 量化交易核心
提供因子挖掘、策略开发、信号生成功能
"""
from .base import BaseStrategy, StrategyContext
from .factors import Factor, FactorRegistry, FactorEngine
from .factors.technical import (
    MAFactor, MACDFactor, RSIFactor, 
    BOLLFactor, KDJFactor, ATRFactor, OBVFactor
)

__version__ = "1.0.0"
__all__ = [
    'BaseStrategy',
    'StrategyContext',
    'Factor',
    'FactorRegistry',
    'FactorEngine',
    'MAFactor',
    'MACDFactor',
    'RSIFactor',
    'BOLLFactor',
    'KDJFactor',
    'ATRFactor',
    'OBVFactor',
]
