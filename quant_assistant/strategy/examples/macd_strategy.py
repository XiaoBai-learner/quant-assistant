"""
MACD策略示例
基于MACD金叉死叉进行交易
"""
from typing import Optional, List

from ..base import BaseStrategy, Bar, Signal, StrategyContext


class MACDStrategy(BaseStrategy):
    """
    MACD策略
    
    参数:
        fast: 快线周期 (默认12)
        slow: 慢线周期 (默认26)
        signal: 信号线周期 (默认9)
    """
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        params = {
            'fast': fast,
            'slow': slow,
            'signal': signal
        }
        super().__init__(name="MACD_Cross", params=params)
        
        self.prices: List[float] = []
    
    def on_init(self, context: StrategyContext):
        """初始化"""
        self.fast = self.get_param('fast', 12)
        self.slow = self.get_param('slow', 26)
        self.signal_period = self.get_param('signal', 9)
        
        self.dif_values: List[float] = []
        self.dea_values: List[float] = []
    
    def _calculate_ema(self, data: List[float], period: int) -> float:
        """计算EMA"""
        if len(data) < period:
            return sum(data) / len(data)
        
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """
        K线处理
        
        策略逻辑:
        1. 计算DIF (快线EMA - 慢线EMA)
        2. 计算DEA (DIF的EMA)
        3. DIF上穿DEA (金叉) -> 买入
        4. DIF下穿DEA (死叉) -> 卖出
        """
        self.prices.append(bar.close)
        
        # 数据不足时跳过
        min_periods = max(self.fast, self.slow, self.signal_period)
        if len(self.prices) < min_periods:
            return None
        
        # 计算EMA
        ema_fast = self._calculate_ema(self.prices, self.fast)
        ema_slow = self._calculate_ema(self.prices, self.slow)
        
        # DIF
        dif = ema_fast - ema_slow
        self.dif_values.append(dif)
        
        # 需要足够数据计算DEA
        if len(self.dif_values) < self.signal_period:
            return None
        
        # DEA (DIF的EMA)
        dea = self._calculate_ema(self.dif_values, self.signal_period)
        self.dea_values.append(dea)
        
        # 需要至少两个值判断交叉
        if len(self.dif_values) < 2 or len(self.dea_values) < 2:
            return None
        
        prev_dif = self.dif_values[-2]
        prev_dea = self.dea_values[-2]
        curr_dif = self.dif_values[-1]
        curr_dea = self.dea_values[-1]
        
        # 金叉: DIF上穿DEA
        if prev_dif <= prev_dea and curr_dif > curr_dea:
            return self.buy(bar.symbol, bar.close, 100)
        
        # 死叉: DIF下穿DEA
        if prev_dif >= prev_dea and curr_dif < curr_dea:
            position = self.context.get_position(bar.symbol) if self.context else 0
            if position > 0:
                return self.sell(bar.symbol, bar.close, position)
        
        return None
