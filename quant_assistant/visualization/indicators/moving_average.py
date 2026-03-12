"""
移动平均线指标
"""
import pandas as pd
import numpy as np
from typing import Literal

from .base import BaseIndicator, IndicatorResult


class MAIndicator(BaseIndicator):
    """
    移动平均线指标 (MA)
    
    支持: SMA (简单移动平均), EMA (指数移动平均)
    """
    
    def __init__(
        self,
        period: int = 5,
        ma_type: Literal['sma', 'ema'] = 'sma',
        price_col: str = 'close'
    ):
        """
        初始化MA指标
        
        Args:
            period: 周期 (默认5)
            ma_type: 移动平均类型 'sma' 或 'ema'
            price_col: 价格列名
        """
        self.period = period
        self.ma_type = ma_type
        self.price_col = price_col
        
        name = f"{ma_type.upper()}{period}"
        params = {
            'period': period,
            'ma_type': ma_type,
            'price_col': price_col
        }
        super().__init__(name, params)
    
    def _validate_params(self):
        """验证参数"""
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
        if self.ma_type not in ['sma', 'ema']:
            raise ValueError(f"不支持的MA类型: {self.ma_type}")
    
    def calculate(self, df: pd.DataFrame) -> IndicatorResult:
        """
        计算移动平均线
        
        Args:
            df: 包含价格数据的DataFrame
            
        Returns:
            IndicatorResult: MA计算结果
        """
        if self.price_col not in df.columns:
            raise ValueError(f"数据中缺少价格列: {self.price_col}")
        
        prices = df[self.price_col]
        
        if self.ma_type == 'sma':
            # 简单移动平均
            values = prices.rolling(window=self.period, min_periods=1).mean()
        else:  # ema
            # 指数移动平均
            values = prices.ewm(span=self.period, adjust=False).mean()
        
        return IndicatorResult(
            name=self.name,
            values=values,
            params=self.params
        )


class MA5Indicator(MAIndicator):
    """5日移动平均线"""
    def __init__(self, ma_type: Literal['sma', 'ema'] = 'sma'):
        super().__init__(period=5, ma_type=ma_type)


class MA10Indicator(MAIndicator):
    """10日移动平均线"""
    def __init__(self, ma_type: Literal['sma', 'ema'] = 'sma'):
        super().__init__(period=10, ma_type=ma_type)


class MA20Indicator(MAIndicator):
    """20日移动平均线"""
    def __init__(self, ma_type: Literal['sma', 'ema'] = 'sma'):
        super().__init__(period=20, ma_type=ma_type)
