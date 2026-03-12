"""
双均线策略示例
当短期均线上穿长期均线时买入，下穿时卖出
"""
from typing import Optional

from ..base import BaseStrategy, Bar, Signal, SignalType, StrategyContext


class MAStrategy(BaseStrategy):
    """
    双移动平均线策略
    
    参数:
        fast_period: 短期均线周期 (默认5)
        slow_period: 长期均线周期 (默认20)
    """
    
    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        params = {
            'fast_period': fast_period,
            'slow_period': slow_period
        }
        super().__init__(name="MA_Cross", params=params)
        
        self.fast_ma = []
        self.slow_ma = []
    
    def on_init(self, context: StrategyContext):
        """初始化"""
        self.fast_period = self.get_param('fast_period', 5)
        self.slow_period = self.get_param('slow_period', 20)
        
        # 初始化历史数据存储
        self.prices = []
        self.fast_ma_values = []
        self.slow_ma_values = []
    
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """
        K线处理
        
        策略逻辑:
        1. 计算短期和长期移动平均线
        2. 短期均线上穿长期均线 -> 买入
        3. 短期均线下穿长期均线 -> 卖出
        """
        # 存储价格
        self.prices.append(bar.close)
        
        # 数据不足时跳过
        if len(self.prices) < self.slow_period:
            return None
        
        # 计算MA
        fast_ma = sum(self.prices[-self.fast_period:]) / self.fast_period
        slow_ma = sum(self.prices[-self.slow_period:]) / self.slow_period
        
        self.fast_ma_values.append(fast_ma)
        self.slow_ma_values.append(slow_ma)
        
        # 需要至少两根MA值才能判断交叉
        if len(self.fast_ma_values) < 2:
            return None
        
        # 判断交叉
        prev_fast = self.fast_ma_values[-2]
        prev_slow = self.slow_ma_values[-2]
        curr_fast = self.fast_ma_values[-1]
        curr_slow = self.slow_ma_values[-1]
        
        # 金叉: 短期上穿长期
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return self.buy(bar.symbol, bar.close, 100)
        
        # 死叉: 短期下穿长期
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            position = self.context.get_position(bar.symbol) if self.context else 0
            if position > 0:
                return self.sell(bar.symbol, bar.close, position)
        
        return None
