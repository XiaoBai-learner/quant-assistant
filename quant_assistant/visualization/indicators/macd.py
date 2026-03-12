"""
MACD 指标 - 指数平滑异同移动平均线
"""
import pandas as pd
import numpy as np

from .base import BaseIndicator, IndicatorResult


class MACDIndicator(BaseIndicator):
    """
    MACD 指标
    
    组成:
    - DIF (快线): EMA(12) - EMA(26)
    - DEA (慢线/信号线): DIF 的 EMA(9)
    - MACD (柱状图): 2 * (DIF - DEA)
    """
    
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        price_col: str = 'close'
    ):
        """
        初始化MACD指标
        
        Args:
            fast_period: 快线周期 (默认12)
            slow_period: 慢线周期 (默认26)
            signal_period: 信号线周期 (默认9)
            price_col: 价格列名
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.price_col = price_col
        
        params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'price_col': price_col
        }
        super().__init__("MACD", params)
    
    def _validate_params(self):
        """验证参数"""
        if self.fast_period >= self.slow_period:
            raise ValueError(f"快线周期必须小于慢线周期: {self.fast_period} >= {self.slow_period}")
        if self.signal_period <= 0:
            raise ValueError(f"信号线周期必须大于0: {self.signal_period}")
    
    def calculate(self, df: pd.DataFrame) -> IndicatorResult:
        """
        计算MACD指标
        
        Args:
            df: 包含价格数据的DataFrame
            
        Returns:
            IndicatorResult: MACD计算结果
            - values: MACD柱状图
            - metadata: 包含 DIF 和 DEA
        """
        if self.price_col not in df.columns:
            raise ValueError(f"数据中缺少价格列: {self.price_col}")
        
        prices = df[self.price_col]
        
        # 计算EMA
        ema_fast = prices.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=self.slow_period, adjust=False).mean()
        
        # DIF (快线)
        dif = ema_fast - ema_slow
        
        # DEA (慢线/信号线)
        dea = dif.ewm(span=self.signal_period, adjust=False).mean()
        
        # MACD柱状图
        macd = 2 * (dif - dea)
        
        return IndicatorResult(
            name="MACD",
            values=macd,
            params=self.params,
            metadata={
                'DIF': dif,
                'DEA': dea,
                'MACD': macd
            }
        )
    
    def get_signal(self, df: pd.DataFrame) -> pd.Series:
        """
        获取MACD交易信号
        
        信号规则:
        - 1 (买入): DIF上穿DEA (金叉)
        - -1 (卖出): DIF下穿DEA (死叉)
        - 0 (持有): 无信号
        
        Args:
            df: 行情数据
            
        Returns:
            pd.Series: 交易信号
        """
        result = self.calculate(df)
        dif = result.metadata['DIF']
        dea = result.metadata['DEA']
        
        # 计算交叉
        dif_above = (dif > dea).astype(int)
        signal = dif_above.diff()
        
        # 转换为 -1, 0, 1
        signal = signal.replace({1: 1, -1: -1, 0: 0})
        
        return signal
