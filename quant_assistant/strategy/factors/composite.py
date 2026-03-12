"""
复合因子和衍生指标
组合多个基础因子生成新的衍生因子
"""
from typing import List, Dict
import pandas as pd
import numpy as np

from .base import Factor, FactorResult, FactorMetadata
from .registry import factor_registry
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CompositeFactor(Factor):
    """
    复合因子基类
    组合多个基础因子生成新的衍生因子
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        component_factors: List[str],
        weights: List[float] = None
    ):
        self.component_factors = component_factors
        self.weights = weights or [1.0 / len(component_factors)] * len(component_factors)
        
        params = {
            'components': component_factors,
            'weights': self.weights
        }
        super().__init__(name, description, params)
    
    def _validate_params(self):
        if len(self.component_factors) != len(self.weights):
            raise ValueError("因子数量和权重数量不匹配")
        if abs(sum(self.weights) - 1.0) > 0.001:
            logger.warning(f"权重之和不为1: {sum(self.weights)}")
    
    def get_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            name=self.name,
            description=self.description,
            formula=f"Composite({self.component_factors})",
            dependencies=self.component_factors,
            frequency='D',
            factor_type='composite',
            category='composite'
        )


class PriceMomentumComposite(CompositeFactor):
    """价格动量复合因子"""
    
    def __init__(self):
        super().__init__(
            name="PriceMomentum",
            description="价格动量复合因子 (ROC + Momentum)",
            component_factors=['ROC10', 'MOM10'],
            weights=[0.5, 0.5]
        )
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        # 获取组件因子
        registry = factor_registry
        
        roc_result = registry.create_factor('ROC10').calculate(df)
        mom_result = registry.create_factor('MOM10').calculate(df)
        
        # 标准化
        roc_norm = (roc_result.values - roc_result.values.mean()) / roc_result.values.std()
        mom_norm = (mom_result.values - mom_result.values.mean()) / mom_result.values.std()
        
        # 加权组合
        composite = 0.5 * roc_norm + 0.5 * mom_norm
        
        return FactorResult(
            name=self.name,
            values=composite,
            params=self.params,
            metadata={
                'roc': roc_result.values,
                'momentum': mom_result.values
            }
        )


class TrendStrengthComposite(CompositeFactor):
    """趋势强度复合因子"""
    
    def __init__(self):
        super().__init__(
            name="TrendStrength",
            description="趋势强度复合因子 (ADX + MACD)",
            component_factors=['ADX14', 'MACD'],
            weights=[0.6, 0.4]
        )
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        registry = factor_registry
        
        adx_result = registry.create_factor('ADX14').calculate(df)
        macd_result = registry.create_factor('MACD').calculate(df)
        
        # 标准化
        adx_norm = adx_result.values / 100  # ADX已经是0-100
        macd_norm = (macd_result.values - macd_result.values.mean()) / macd_result.values.std()
        macd_norm = macd_norm / 3  # 缩放到合理范围
        
        # 加权组合
        composite = 0.6 * adx_norm + 0.4 * macd_norm
        
        return FactorResult(
            name=self.name,
            values=composite,
            params=self.params,
            metadata={
                'adx': adx_result.values,
                'macd': macd_result.values
            }
        )


class VolumePriceComposite(CompositeFactor):
    """量价复合因子"""
    
    def __init__(self):
        super().__init__(
            name="VolumePrice",
            description="量价复合因子 (OBV + VolumeRatio + PVT)",
            component_factors=['OBV', 'VolumeRatio5', 'PVT'],
            weights=[0.4, 0.3, 0.3]
        )
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        registry = factor_registry
        
        obv_result = registry.create_factor('OBV').calculate(df)
        vr_result = registry.create_factor('VolumeRatio5').calculate(df)
        pvt_result = registry.create_factor('PVT').calculate(df)
        
        # 标准化 (使用z-score)
        def z_score(series):
            return (series - series.mean()) / series.std()
        
        obv_norm = z_score(obv_result.values)
        vr_norm = z_score(vr_result.values)
        pvt_norm = z_score(pvt_result.values)
        
        # 加权组合
        composite = 0.4 * obv_norm + 0.3 * vr_norm + 0.3 * pvt_norm
        
        return FactorResult(
            name=self.name,
            values=composite,
            params=self.params,
            metadata={
                'obv': obv_result.values,
                'volume_ratio': vr_result.values,
                'pvt': pvt_result.values
            }
        )


class VolatilityRegimeFactor(Factor):
    """波动率状态因子"""
    
    def __init__(self, vol_period: int = 20, atr_period: int = 14):
        self.vol_period = vol_period
        self.atr_period = atr_period
        super().__init__(
            name="VolatilityRegime",
            description="波动率状态因子 (高/中/低波动)",
            params={'vol_period': vol_period, 'atr_period': atr_period}
        )
    
    def _validate_params(self):
        if self.vol_period <= 0 or self.atr_period <= 0:
            raise ValueError("周期必须大于0")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        registry = factor_registry
        
        # 获取波动率和ATR
        vol_result = registry.create_factor(f'Volatility{self.vol_period}').calculate(df)
        atr_result = registry.create_factor(f'ATR{self.atr_period}').calculate(df)
        
        # 计算波动率分位数
        vol_series = vol_result.values
        vol_percentile = vol_series.rolling(window=252, min_periods=60).apply(
            lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) if x.max() != x.min() else 0.5
        )
        
        # 波动率状态: -1=低波动, 0=中波动, 1=高波动
        regime = pd.Series(index=df.index, dtype=float)
        regime[vol_percentile > 0.7] = 1  # 高波动
        regime[vol_percentile < 0.3] = -1  # 低波动
        regime[(vol_percentile >= 0.3) & (vol_percentile <= 0.7)] = 0  # 中波动
        
        return FactorResult(
            name=self.name,
            values=regime,
            params=self.params,
            metadata={
                'volatility': vol_result.values,
                'atr': atr_result.values,
                'percentile': vol_percentile
            }
        )
    
    def get_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            name=self.name,
            description=self.description,
            formula="Regime based on volatility percentile",
            dependencies=['Volatility', 'ATR'],
            frequency='D',
            factor_type='regime',
            category='volatility'
        )


class MeanReversionFactor(Factor):
    """均值回复因子"""
    
    def __init__(self, period: int = 20, price_col: str = 'close'):
        self.period = period
        self.price_col = price_col
        super().__init__(
            name="MeanReversion",
            description=f"{period}日均值回复因子",
            params={'period': period, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        price = df[self.price_col]
        
        # 计算移动平均
        ma = price.rolling(window=self.period).mean()
        
        # 计算标准差
        std = price.rolling(window=self.period).std()
        
        # Z-score (偏离度)
        z_score = (price - ma) / std
        
        # 均值回复信号: 负值表示价格高于均值(可能回落), 正值表示低于均值(可能反弹)
        # 反转符号使其符合直觉: 正值表示买入信号
        mean_reversion = -z_score
        
        return FactorResult(
            name=self.name,
            values=mean_reversion,
            params=self.params,
            metadata={
                'ma': ma,
                'std': std,
                'z_score': z_score
            }
        )
    
    def get_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            name=self.name,
            description=self.description,
            formula=f"-(Close - MA({self.period})) / STD({self.period})",
            dependencies=[self.price_col],
            frequency='D',
            factor_type='mean_reversion',
            category='mean_reversion'
        )


class BreakoutFactor(Factor):
    """突破因子"""
    
    def __init__(self, period: int = 20):
        self.period = period
        super().__init__(
            name=f"Breakout{period}",
            description=f"{period}日突破因子",
            params={'period': period}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        close = df['close']
        high = df['high']
        low = df['low']
        
        # N日最高/最低
        highest_high = high.rolling(window=self.period).max()
        lowest_low = low.rolling(window=self.period).min()
        
        # 突破强度
        upper_breakout = (close - highest_high.shift(1)) / highest_high.shift(1)
        lower_breakout = (close - lowest_low.shift(1)) / lowest_low.shift(1)
        
        # 合并突破信号
        breakout = upper_breakout.where(upper_breakout > 0, lower_breakout)
        
        return FactorResult(
            name=self.name,
            values=breakout,
            params=self.params,
            metadata={
                'highest_high': highest_high,
                'lowest_low': lowest_low,
                'upper_breakout': upper_breakout,
                'lower_breakout': lower_breakout
            }
        )
    
    def get_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            name=self.name,
            description=self.description,
            formula=f"Breakout = (Close - HH/LL) / HH/LL",
            dependencies=['high', 'low', 'close'],
            frequency='D',
            factor_type='breakout',
            category='breakout'
        )


class MultiTimeframeFactor(Factor):
    """多时间框架因子"""
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        self.short_period = short_period
        self.long_period = long_period
        super().__init__(
            name=f"MTF_{short_period}_{long_period}",
            description=f"多时间框架因子 (短{short_period}/长{long_period})",
            params={'short': short_period, 'long': long_period}
        )
    
    def _validate_params(self):
        if self.short_period >= self.long_period:
            raise ValueError("短周期必须小于长周期")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        close = df['close']
        
        # 短期和长期趋势
        short_ma = close.rolling(window=self.short_period).mean()
        long_ma = close.rolling(window=self.long_period).mean()
        
        # 短期和长期动量
        short_mom = close.pct_change(self.short_period)
        long_mom = close.pct_change(self.long_period)
        
        # 趋势一致性
        trend_alignment = ((short_ma > long_ma).astype(int) * 2 - 1) * \
                         ((short_mom > 0).astype(int) * 2 - 1)
        
        return FactorResult(
            name=self.name,
            values=trend_alignment,
            params=self.params,
            metadata={
                'short_ma': short_ma,
                'long_ma': long_ma,
                'short_momentum': short_mom,
                'long_momentum': long_mom
            }
        )
    
    def get_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            name=self.name,
            description=self.description,
            formula=f"MTF = alignment(MA{self.short_period}, MA{self.long_period})",
            dependencies=['close'],
            frequency='D',
            factor_type='multi_timeframe',
            category='trend'
        )
