"""因子挖掘模块"""
from .base import Factor, FactorResult, FactorMetadata, TechnicalFactor
from .registry import FactorRegistry, factor_registry
from .engine import FactorEngine

# 基础技术指标
from .technical import (
    MAFactor, EMAFactor, MACDFactor, RSIFactor,
    BOLLFactor, KDJFactor, ATRFactor, OBVFactor
)

# 扩展技术指标
from .technical_extended import (
    ADXFactor, CCIFactor, WilliamsRFactor, StochasticRSIFactor,
    MomentumFactor, RateOfChangeFactor, PriceChangeFactor,
    VolatilityFactor, VolumeMAFactor, VolumeRatioFactor,
    PriceVolumeTrendFactor, MoneyFlowIndexFactor,
    TrueRangeFactor, DonchianChannelFactor, IchimokuFactor
)

__all__ = [
    # 基础类
    'Factor',
    'FactorResult',
    'FactorMetadata',
    'TechnicalFactor',
    'FactorRegistry',
    'factor_registry',
    'FactorEngine',
    
    # 基础技术指标 (8个)
    'MAFactor',
    'EMAFactor',
    'MACDFactor',
    'RSIFactor',
    'BOLLFactor',
    'KDJFactor',
    'ATRFactor',
    'OBVFactor',
    
    # 扩展技术指标 (15个)
    'ADXFactor',
    'CCIFactor',
    'WilliamsRFactor',
    'StochasticRSIFactor',
    'MomentumFactor',
    'RateOfChangeFactor',
    'PriceChangeFactor',
    'VolatilityFactor',
    'VolumeMAFactor',
    'VolumeRatioFactor',
    'PriceVolumeTrendFactor',
    'MoneyFlowIndexFactor',
    'TrueRangeFactor',
    'DonchianChannelFactor',
    'IchimokuFactor',
]


def register_all_factors():
    """注册所有技术指标到全局注册表"""
    from .technical import (
        MAFactor, EMAFactor, MACDFactor, RSIFactor,
        BOLLFactor, KDJFactor, ATRFactor, OBVFactor
    )
    from .technical_extended import (
        ADXFactor, CCIFactor, WilliamsRFactor, StochasticRSIFactor,
        MomentumFactor, RateOfChangeFactor, PriceChangeFactor,
        VolatilityFactor, VolumeMAFactor, VolumeRatioFactor,
        PriceVolumeTrendFactor, MoneyFlowIndexFactor,
        TrueRangeFactor, DonchianChannelFactor, IchimokuFactor
    )
    
    # 基础指标
    base_factors = [
        MAFactor, EMAFactor, MACDFactor, RSIFactor,
        BOLLFactor, KDJFactor, ATRFactor, OBVFactor,
    ]
    
    # 扩展指标
    extended_factors = [
        ADXFactor, CCIFactor, WilliamsRFactor, StochasticRSIFactor,
        MomentumFactor, RateOfChangeFactor, PriceChangeFactor,
        VolatilityFactor, VolumeMAFactor, VolumeRatioFactor,
        PriceVolumeTrendFactor, MoneyFlowIndexFactor,
        TrueRangeFactor, DonchianChannelFactor, IchimokuFactor,
    ]
    
    registry = FactorRegistry()
    
    for factor_class in base_factors + extended_factors:
        registry.register(factor_class)
    
    return len(base_factors) + len(extended_factors)
