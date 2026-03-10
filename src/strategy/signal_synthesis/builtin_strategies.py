"""
内置策略库
提供常用的选股策略和买卖点策略
"""
from typing import List, Dict, Any
import pandas as pd
import numpy as np

from .strategy_builder import StrategyBuilder, StrategyRule, Condition, Operator, LogicOp
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StrategyFactory:
    """策略工厂"""
    
    @staticmethod
    def create_trend_following_strategy() -> StrategyRule:
        """
        趋势跟踪策略
        
        条件:
        - 价格在MA20上方 (趋势向上)
        - MACD > 0 (多头)
        - ADX > 25 (趋势强度足够)
        """
        conditions = [
            Condition(factor='close', operator=Operator.GT, threshold=0, weight=1.0),  # 占位，实际用MA20
            Condition(factor='MACD', operator=Operator.GT, threshold=0, weight=1.2),
            Condition(factor='ADX14', operator=Operator.GT, threshold=25, weight=1.0),
        ]
        
        return StrategyRule(
            name="TrendFollowing",
            description="趋势跟踪策略: 价格站上MA20 + MACD多头 + ADX>25",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.0, 1.2, 1.0]
        )
    
    @staticmethod
    def create_mean_reversion_strategy() -> StrategyRule:
        """
        均值回复策略
        
        条件:
        - RSI < 30 (超卖)
        - 价格低于布林带下轨
        - 成交量放大
        """
        conditions = [
            Condition(factor='RSI14', operator=Operator.LT, threshold=30, weight=1.2),
            Condition(factor='BOLL', operator=Operator.LT, threshold=0.2, weight=1.0),  # %B < 0.2
            Condition(factor='VolumeRatio5', operator=Operator.GT, threshold=1.5, weight=0.8),
        ]
        
        return StrategyRule(
            name="MeanReversion",
            description="均值回复策略: RSI超卖 + 价格低于布林带下轨 + 放量",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.2, 1.0, 0.8]
        )
    
    @staticmethod
    def create_breakout_strategy() -> StrategyRule:
        """
        突破策略
        
        条件:
        - 价格突破20日高点
        - 成交量放大
        - ATR放大 (波动率扩大)
        """
        conditions = [
            Condition(factor='Breakout20', operator=Operator.GT, threshold=0, weight=1.2),
            Condition(factor='VolumeRatio5', operator=Operator.GT, threshold=1.3, weight=1.0),
            Condition(factor='ATR14', operator=Operator.GT, threshold=0, weight=0.8),  # 占位
        ]
        
        return StrategyRule(
            name="Breakout",
            description="突破策略: 价格突破20日高点 + 放量 + ATR放大",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.2, 1.0, 0.8]
        )
    
    @staticmethod
    def create_multi_factor_strategy() -> StrategyRule:
        """
        多因子综合策略
        
        结合估值、动量、质量、情绪
        """
        conditions = [
            # 动量因子
            Condition(factor='MOM10', operator=Operator.GT, threshold=0, weight=1.0),
            # 趋势因子
            Condition(factor='MACD', operator=Operator.GT, threshold=0, weight=1.0),
            # 情绪因子
            Condition(factor='RSI14', operator=Operator.GT, threshold=40, weight=0.8),
            Condition(factor='RSI14', operator=Operator.LT, threshold=70, weight=0.8),
        ]
        
        return StrategyRule(
            name="MultiFactor",
            description="多因子策略: 动量 + 趋势 + 情绪",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.0, 1.0, 0.8, 0.8]
        )
    
    @staticmethod
    def create_value_strategy() -> StrategyRule:
        """
        价值投资策略
        
        条件:
        - 低估值 (PE/PB)
        - 稳定盈利
        - 高股息
        """
        conditions = [
            Condition(factor='PriceChange20', operator=Operator.LT, threshold=0.1, weight=0.8),
            Condition(factor='Volatility20', operator=Operator.LT, threshold=0.3, weight=1.0),
        ]
        
        return StrategyRule(
            name="Value",
            description="价值投资策略: 低波动 + 稳健",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[0.8, 1.0]
        )
    
    @staticmethod
    def create_momentum_strategy() -> StrategyRule:
        """
        动量策略
        
        条件:
        - 短期动量强劲
        - 成交量配合
        - 趋势确认
        """
        conditions = [
            Condition(factor='ROC10', operator=Operator.GT, threshold=0.05, weight=1.2),
            Condition(factor='MOM10', operator=Operator.GT, threshold=0, weight=1.0),
            Condition(factor='VolumeRatio5', operator=Operator.GT, threshold=1.2, weight=0.8),
        ]
        
        return StrategyRule(
            name="Momentum",
            description="动量策略: ROC>5% + 正动量 + 放量",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.2, 1.0, 0.8]
        )
    
    @staticmethod
    def create_quality_strategy() -> StrategyRule:
        """
        质量策略
        
        条件:
        - 低波动
        - 稳定趋势
        - 高夏普比率
        """
        conditions = [
            Condition(factor='Volatility20', operator=Operator.LT, threshold=0.25, weight=1.0),
            Condition(factor='ADX14', operator=Operator.GT, threshold=20, weight=0.8),
        ]
        
        return StrategyRule(
            name="Quality",
            description="质量策略: 低波动 + 趋势明确",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.0, 0.8]
        )
    
    @staticmethod
    def create_buy_signal_strategy() -> StrategyRule:
        """
        买入信号策略
        
        条件:
        - MACD金叉
        - RSI从超卖区回升
        - 放量
        """
        conditions = [
            Condition(factor='MACD', operator=Operator.GT, threshold=0, weight=1.2),
            Condition(factor='RSI14', operator=Operator.GT, threshold=30, weight=1.0),
            Condition(factor='RSI14', operator=Operator.LT, threshold=50, weight=1.0),
            Condition(factor='VolumeRatio5', operator=Operator.GT, threshold=1.2, weight=0.8),
        ]
        
        return StrategyRule(
            name="BuySignal",
            description="买入信号: MACD金叉 + RSI回升 + 放量",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.2, 1.0, 1.0, 0.8]
        )
    
    @staticmethod
    def create_sell_signal_strategy() -> StrategyRule:
        """
        卖出信号策略
        
        条件:
        - MACD死叉
        - RSI从超买区回落
        - 缩量
        """
        conditions = [
            Condition(factor='MACD', operator=Operator.LT, threshold=0, weight=1.2),
            Condition(factor='RSI14', operator=Operator.GT, threshold=60, weight=1.0),
            Condition(factor='RSI14', operator=Operator.LT, threshold=80, weight=1.0),
        ]
        
        return StrategyRule(
            name="SellSignal",
            description="卖出信号: MACD死叉 + RSI从超买回落",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.2, 1.0, 1.0]
        )
    
    @staticmethod
    def create_growth_strategy() -> StrategyRule:
        """
        成长策略
        
        条件:
        - 价格创新高
        - 动量强劲
        - 趋势向上
        """
        conditions = [
            Condition(factor='ROC20', operator=Operator.GT, threshold=0.1, weight=1.2),
            Condition(factor='MOM20', operator=Operator.GT, threshold=0, weight=1.0),
            Condition(factor='ADX14', operator=Operator.GT, threshold=25, weight=0.8),
        ]
        
        return StrategyRule(
            name="Growth",
            description="成长策略: ROC>10% + 正动量 + 强趋势",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.2, 1.0, 0.8]
        )
    
    @staticmethod
    def create_contrarian_strategy() -> StrategyRule:
        """
        逆势策略
        
        条件:
        - 价格大幅下跌
        - RSI严重超卖
        - 成交量萎缩后放量
        """
        conditions = [
            Condition(factor='ROC10', operator=Operator.LT, threshold=-0.1, weight=1.0),
            Condition(factor='RSI14', operator=Operator.LT, threshold=25, weight=1.2),
            Condition(factor='VolumeRatio5', operator=Operator.GT, threshold=1.5, weight=0.8),
        ]
        
        return StrategyRule(
            name="Contrarian",
            description="逆势策略: 大跌 + RSI超卖 + 放量",
            conditions=conditions,
            logic_op=LogicOp.AND,
            weights=[1.0, 1.2, 0.8]
        )


class BuiltinStrategies:
    """内置策略集合"""
    
    def __init__(self):
        self.factory = StrategyFactory()
        self.builder = StrategyBuilder()
        self._register_all()
    
    def _register_all(self):
        """注册所有内置策略"""
        strategies = [
            self.factory.create_trend_following_strategy(),
            self.factory.create_mean_reversion_strategy(),
            self.factory.create_breakout_strategy(),
            self.factory.create_multi_factor_strategy(),
            self.factory.create_value_strategy(),
            self.factory.create_momentum_strategy(),
            self.factory.create_quality_strategy(),
            self.factory.create_buy_signal_strategy(),
            self.factory.create_sell_signal_strategy(),
            self.factory.create_growth_strategy(),
            self.factory.create_contrarian_strategy(),
        ]
        
        for strategy in strategies:
            self.builder.add_rule(strategy)
            logger.info(f"注册内置策略: {strategy.name}")
    
    def get_strategy(self, name: str) -> StrategyRule:
        """获取策略"""
        return self.builder.get_rule(name)
    
    def list_strategies(self) -> List[str]:
        """列出所有策略"""
        return self.builder.list_rules()
    
    def get_all_strategies(self) -> Dict[str, StrategyRule]:
        """获取所有策略"""
        return self.builder.rules


# 便捷访问函数
def get_builtin_strategies() -> BuiltinStrategies:
    """获取内置策略实例"""
    return BuiltinStrategies()


# 预定义策略实例
TrendFollowingStrategy = StrategyFactory.create_trend_following_strategy
MeanReversionStrategy = StrategyFactory.create_mean_reversion_strategy
BreakoutStrategy = StrategyFactory.create_breakout_strategy
MultiFactorStrategy = StrategyFactory.create_multi_factor_strategy
