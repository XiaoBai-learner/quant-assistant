"""
因子计算模块

提供技术指标和自定义因子计算功能。
支持多时间粒度：日线、分钟级、实时

示例:
    >>> from quant_assistant.factors import FactorEngine, FactorEngineV2
    >>> 
    >>> # 基础引擎
    >>> engine = FactorEngine()
    >>> ma20 = engine.ma(data['close'], window=20)
    >>> 
    >>> # V2引擎（支持多粒度）
    >>> engine_v2 = FactorEngineV2()
    >>> df = engine_v2.compute_factors(data)  # 自动检测粒度
"""

from quant_assistant.factors.engine import FactorEngine
from quant_assistant.factors.engine_v2 import FactorEngineV2, TimeGranularity, FactorCategory
from quant_assistant.factors.technical import TechnicalFactor
from quant_assistant.factors.composite import CompositeFactor

__all__ = [
    'FactorEngine',
    'FactorEngineV2',
    'TimeGranularity',
    'FactorCategory',
    'TechnicalFactor',
    'CompositeFactor',
]
