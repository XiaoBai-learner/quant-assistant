"""
策略组合模块
支持多策略组合和权重配置
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np

from src.strategy.base import BaseStrategy, Signal, SignalType, Bar, StrategyContext
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyWeight:
    """策略权重"""
    strategy: BaseStrategy
    weight: float
    active: bool = True


class CompositeStrategy(BaseStrategy):
    """
    组合策略
    
    支持多策略组合，通过权重合成信号
    """
    
    def __init__(
        self,
        name: str = "Composite",
        strategies: List[StrategyWeight] = None,
        combination_method: str = "weighted_sum"
    ):
        """
        初始化组合策略
        
        Args:
            name: 策略名称
            strategies: 策略权重列表
            combination_method: 信号合成方法
                - 'weighted_sum': 加权求和
                - 'majority_vote': 多数投票
                - 'unanimous': 一致同意
        """
        super().__init__(name=name)
        self.strategies = strategies or []
        self.combination_method = combination_method
        
        # 验证权重
        self._validate_weights()
    
    def add_strategy(self, strategy: BaseStrategy, weight: float = 1.0):
        """添加子策略"""
        self.strategies.append(StrategyWeight(strategy, weight))
        self._validate_weights()
        logger.info(f"添加策略: {strategy.name}, 权重: {weight}")
    
    def remove_strategy(self, strategy_name: str):
        """移除子策略"""
        self.strategies = [
            sw for sw in self.strategies 
            if sw.strategy.name != strategy_name
        ]
        self._validate_weights()
    
    def set_weight(self, strategy_name: str, weight: float):
        """设置策略权重"""
        for sw in self.strategies:
            if sw.strategy.name == strategy_name:
                sw.weight = weight
                break
        self._validate_weights()
    
    def _validate_weights(self):
        """验证权重"""
        total_weight = sum(sw.weight for sw in self.strategies if sw.active)
        if total_weight > 0 and abs(total_weight - 1.0) > 0.001:
            # 归一化权重
            for sw in self.strategies:
                if sw.active:
                    sw.weight /= total_weight
    
    def on_init(self, context: StrategyContext):
        """初始化所有子策略"""
        for sw in self.strategies:
            sw.strategy.init(context)
        logger.info(f"组合策略初始化完成: {len(self.strategies)} 个子策略")
    
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """
        处理K线，合成信号
        
        Args:
            bar: K线数据
            
        Returns:
            Signal: 合成后的信号
        """
        # 收集所有子策略的信号
        signals = []
        for sw in self.strategies:
            if not sw.active:
                continue
            
            signal = sw.strategy.on_bar(bar)
            if signal:
                signals.append((signal, sw.weight))
        
        if not signals:
            return None
        
        # 合成信号
        if self.combination_method == 'weighted_sum':
            return self._combine_weighted_sum(signals, bar)
        elif self.combination_method == 'majority_vote':
            return self._combine_majority_vote(signals, bar)
        elif self.combination_method == 'unanimous':
            return self._combine_unanimous(signals, bar)
        else:
            raise ValueError(f"未知的合成方法: {self.combination_method}")
    
    def _combine_weighted_sum(
        self, 
        signals: List[tuple], 
        bar: Bar
    ) -> Optional[Signal]:
        """
        加权求和合成信号
        
        将买入信号计为+1，卖出信号计为-1，加权求和后决定最终信号
        """
        total_score = 0
        total_weight = 0
        
        for signal, weight in signals:
            if signal.signal_type == SignalType.BUY:
                total_score += weight
            elif signal.signal_type == SignalType.SELL:
                total_score -= weight
            total_weight += weight
        
        # 归一化得分
        normalized_score = total_score / total_weight if total_weight > 0 else 0
        
        # 根据得分决定信号
        threshold = 0.2  # 信号阈值
        
        if normalized_score > threshold:
            # 买入
            avg_volume = int(np.mean([s.volume for s, _ in signals if s.signal_type == SignalType.BUY]))
            return self.buy(bar.symbol, bar.close, max(avg_volume, 100))
        elif normalized_score < -threshold:
            # 卖出
            position = self.context.get_position(bar.symbol) if self.context else 0
            if position > 0:
                return self.sell(bar.symbol, bar.close, position)
        
        return None
    
    def _combine_majority_vote(
        self, 
        signals: List[tuple], 
        bar: Bar
    ) -> Optional[Signal]:
        """
        多数投票合成信号
        
        超过半数策略同意时才产生信号
        """
        buy_count = sum(1 for s, _ in signals if s.signal_type == SignalType.BUY)
        sell_count = sum(1 for s, _ in signals if s.signal_type == SignalType.SELL)
        total = len(signals)
        
        if buy_count > total / 2:
            avg_volume = int(np.mean([s.volume for s, _ in signals if s.signal_type == SignalType.BUY]))
            return self.buy(bar.symbol, bar.close, max(avg_volume, 100))
        elif sell_count > total / 2:
            position = self.context.get_position(bar.symbol) if self.context else 0
            if position > 0:
                return self.sell(bar.symbol, bar.close, position)
        
        return None
    
    def _combine_unanimous(
        self, 
        signals: List[tuple], 
        bar: Bar
    ) -> Optional[Signal]:
        """
        一致同意合成信号
        
        所有策略一致时才产生信号
        """
        if not signals:
            return None
        
        first_type = signals[0][0].signal_type
        
        # 检查是否全部一致
        if all(s.signal_type == first_type for s, _ in signals):
            if first_type == SignalType.BUY:
                avg_volume = int(np.mean([s.volume for s, _ in signals]))
                return self.buy(bar.symbol, bar.close, max(avg_volume, 100))
            elif first_type == SignalType.SELL:
                position = self.context.get_position(bar.symbol) if self.context else 0
                if position > 0:
                    return self.sell(bar.symbol, bar.close, position)
        
        return None
    
    def get_strategy_performance(self) -> pd.DataFrame:
        """
        获取各子策略的绩效
        
        Returns:
            DataFrame: 各策略的信号统计
        """
        data = []
        for sw in self.strategies:
            strategy = sw.strategy
            stats = {
                'strategy_name': strategy.name,
                'weight': sw.weight,
                'active': sw.active,
                'signal_count': len(strategy.context.signals) if strategy.context else 0
            }
            data.append(stats)
        
        return pd.DataFrame(data)


class EnsembleStrategy(BaseStrategy):
    """
    集成策略
    
    使用机器学习集成方法合成多个策略的信号
    """
    
    def __init__(
        self,
        name: str = "Ensemble",
        strategies: List[BaseStrategy] = None,
        ensemble_method: str = "stacking"
    ):
        """
        初始化集成策略
        
        Args:
            name: 策略名称
            strategies: 子策略列表
            ensemble_method: 集成方法 ('stacking', 'bagging', 'boosting')
        """
        super().__init__(name=name)
        self.strategies = strategies or []
        self.ensemble_method = ensemble_method
        
        # 历史信号记录，用于训练集成模型
        self.signal_history = []
        self.price_history = []
    
    def add_strategy(self, strategy: BaseStrategy):
        """添加子策略"""
        self.strategies.append(strategy)
    
    def on_init(self, context: StrategyContext):
        """初始化"""
        for strategy in self.strategies:
            strategy.init(context)
    
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """处理K线"""
        # 收集所有子策略的信号
        strategy_signals = []
        for strategy in self.strategies:
            signal = strategy.on_bar(bar)
            strategy_signals.append({
                'strategy': strategy.name,
                'signal': 1 if signal and signal.signal_type == SignalType.BUY else 
                         (-1 if signal and signal.signal_type == SignalType.SELL else 0),
                'strength': signal.strength if signal else 0
            })
        
        # 记录历史
        self.signal_history.append(strategy_signals)
        self.price_history.append(bar.close)
        
        # 简单的动态加权（基于近期表现）
        if len(self.price_history) > 20:
            weights = self._calculate_dynamic_weights()
        else:
            weights = [1.0 / len(self.strategies)] * len(self.strategies)
        
        # 加权合成
        total_score = sum(
            s['signal'] * w 
            for s, w in zip(strategy_signals, weights)
        )
        
        # 生成信号
        threshold = 0.3
        if total_score > threshold:
            return self.buy(bar.symbol, bar.close, 100)
        elif total_score < -threshold:
            position = self.context.get_position(bar.symbol) if self.context else 0
            if position > 0:
                return self.sell(bar.symbol, bar.close, position)
        
        return None
    
    def _calculate_dynamic_weights(self) -> List[float]:
        """
        计算动态权重
        
        基于各策略近期表现调整权重
        """
        if len(self.signal_history) < 20 or len(self.price_history) < 20:
            return [1.0 / len(self.strategies)] * len(self.strategies)
        
        # 计算各策略近期收益
        returns = []
        for i, strategy in enumerate(self.strategies):
            strategy_returns = []
            for j in range(-20, 0):
                if j + len(self.signal_history) >= 0:
                    signal = self.signal_history[j][i]['signal']
                    price_change = (self.price_history[j] - self.price_history[j-1]) / self.price_history[j-1]
                    strategy_returns.append(signal * price_change)
            
            avg_return = np.mean(strategy_returns) if strategy_returns else 0
            returns.append(max(avg_return, 0))  # 只考虑正收益
        
        # 归一化
        total = sum(returns)
        if total > 0:
            return [r / total for r in returns]
        else:
            return [1.0 / len(self.strategies)] * len(self.strategies)
