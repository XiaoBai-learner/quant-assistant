"""
因子计算模块

提供技术指标和自定义因子计算功能。

示例:
    >>> from quant_assistant.factors import FactorEngine
    >>> engine = FactorEngine()
    >>> ma20 = engine.ma(data['close'], window=20)
    >>> macd = engine.macd(data['close'])
"""

from quant_assistant.factors.engine import FactorEngine
from quant_assistant.factors.technical import TechnicalFactor
from quant_assistant.factors.composite import CompositeFactor

__all__ = [
    'FactorEngine',
    'TechnicalFactor',
    'CompositeFactor',
]
