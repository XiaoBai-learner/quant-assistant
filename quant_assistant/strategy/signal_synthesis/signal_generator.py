"""
信号生成器
生成买卖信号
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import pandas as pd
import numpy as np

from .strategy_builder import StrategyRule, LogicOp
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SignalType(Enum):
    """信号类型"""
    BUY = 1
    SELL = -1
    HOLD = 0
    STRONG_BUY = 2
    STRONG_SELL = -2


@dataclass
class TradeSignal:
    """交易信号"""
    symbol: str
    signal_type: SignalType
    timestamp: datetime
    price: float
    confidence: float = 1.0  # 置信度 0-1
    strategy_name: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'signal': self.signal_type.name,
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'confidence': self.confidence,
            'strategy': self.strategy_name,
            'metadata': self.metadata
        }


class SignalGenerator:
    """
    信号生成器
    
    基于规则生成买卖信号
    """
    
    def __init__(self):
        self.buy_rules: Dict[str, StrategyRule] = {}
        self.sell_rules: Dict[str, StrategyRule] = {}
    
    def add_buy_rule(self, rule: StrategyRule):
        """添加买入规则"""
        self.buy_rules[rule.name] = rule
    
    def add_sell_rule(self, rule: StrategyRule):
        """添加卖出规则"""
        self.sell_rules[rule.name] = rule
    
    def generate_signals(
        self,
        symbol: str,
        factor_data: pd.DataFrame,
        price_data: pd.Series,
        timestamp: datetime = None
    ) -> List[TradeSignal]:
        """
        生成信号
        
        Args:
            symbol: 股票代码
            factor_data: 因子数据 (单行或多行)
            price_data: 价格数据
            timestamp: 时间戳
            
        Returns:
            List[TradeSignal]: 信号列表
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        signals = []
        
        # 获取最新数据
        if isinstance(factor_data, pd.DataFrame):
            latest_factors = factor_data.iloc[-1].to_dict()
            current_price = price_data.iloc[-1] if isinstance(price_data, pd.Series) else price_data
        else:
            latest_factors = factor_data.to_dict()
            current_price = price_data
        
        # 评估买入规则
        buy_scores = []
        for rule_name, rule in self.buy_rules.items():
            satisfied, score = rule.evaluate(latest_factors)
            if satisfied:
                buy_scores.append((rule_name, score))
        
        # 评估卖出规则
        sell_scores = []
        for rule_name, rule in self.sell_rules.items():
            satisfied, score = rule.evaluate(latest_factors)
            if satisfied:
                sell_scores.append((rule_name, score))
        
        # 生成信号
        if buy_scores and (not sell_scores or max([s[1] for s in buy_scores]) > max([s[1] for s in sell_scores])):
            # 买入信号
            best_rule, best_score = max(buy_scores, key=lambda x: x[1])
            confidence = min(best_score, 1.0)
            
            signal_type = SignalType.STRONG_BUY if confidence > 0.8 else SignalType.BUY
            
            signal = TradeSignal(
                symbol=symbol,
                signal_type=signal_type,
                timestamp=timestamp,
                price=current_price,
                confidence=confidence,
                strategy_name=best_rule,
                metadata={'score': best_score, 'factors': latest_factors}
            )
            signals.append(signal)
        
        elif sell_scores and (not buy_scores or max([s[1] for s in sell_scores]) > max([s[1] for s in buy_scores])):
            # 卖出信号
            best_rule, best_score = max(sell_scores, key=lambda x: x[1])
            confidence = min(best_score, 1.0)
            
            signal_type = SignalType.STRONG_SELL if confidence > 0.8 else SignalType.SELL
            
            signal = TradeSignal(
                symbol=symbol,
                signal_type=signal_type,
                timestamp=timestamp,
                price=current_price,
                confidence=confidence,
                strategy_name=best_rule,
                metadata={'score': best_score, 'factors': latest_factors}
            )
            signals.append(signal)
        
        return signals
    
    def batch_generate(
        self,
        factor_data_dict: Dict[str, pd.DataFrame],
        price_data_dict: Dict[str, pd.Series],
        timestamp: datetime = None
    ) -> Dict[str, List[TradeSignal]]:
        """
        批量生成信号
        
        Args:
            factor_data_dict: 因子数据字典 {symbol: factor_data}
            price_data_dict: 价格数据字典 {symbol: price_data}
            timestamp: 时间戳
            
        Returns:
            Dict: {symbol: [signals]}
        """
        all_signals = {}
        
        for symbol in factor_data_dict.keys():
            if symbol in price_data_dict:
                signals = self.generate_signals(
                    symbol,
                    factor_data_dict[symbol],
                    price_data_dict[symbol],
                    timestamp
                )
                if signals:
                    all_signals[symbol] = signals
        
        return all_signals
    
    def filter_signals(
        self,
        signals: List[TradeSignal],
        min_confidence: float = 0.5,
        signal_types: List[SignalType] = None
    ) -> List[TradeSignal]:
        """
        过滤信号
        
        Args:
            signals: 信号列表
            min_confidence: 最小置信度
            signal_types: 允许的_signal类型
            
        Returns:
            List[TradeSignal]: 过滤后的信号
        """
        filtered = []
        
        for signal in signals:
            if signal.confidence < min_confidence:
                continue
            
            if signal_types and signal.signal_type not in signal_types:
                continue
            
            filtered.append(signal)
        
        return filtered
    
    def generate_summary(self, signals: List[TradeSignal]) -> Dict[str, Any]:
        """
        生成信号汇总
        
        Args:
            signals: 信号列表
            
        Returns:
            Dict: 汇总统计
        """
        if not signals:
            return {}
        
        buy_signals = [s for s in signals if s.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]]
        sell_signals = [s for s in signals if s.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]]
        
        summary = {
            'total_signals': len(signals),
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'strong_buy': len([s for s in signals if s.signal_type == SignalType.STRONG_BUY]),
            'strong_sell': len([s for s in signals if s.signal_type == SignalType.STRONG_SELL]),
            'avg_confidence': np.mean([s.confidence for s in signals]),
            'top_buy': [s.symbol for s in sorted(buy_signals, key=lambda x: x.confidence, reverse=True)[:5]],
            'top_sell': [s.symbol for s in sorted(sell_signals, key=lambda x: x.confidence, reverse=True)[:5]],
        }
        
        return summary
    
    def backtest_signals(
        self,
        signals_history: List[TradeSignal],
        price_data: pd.DataFrame,
        holding_period: int = 5
    ) -> pd.DataFrame:
        """
        回测信号
        
        Args:
            signals_history: 历史信号列表
            price_data: 价格数据
            holding_period: 持有期
            
        Returns:
            DataFrame: 回测结果
        """
        results = []
        
        for signal in signals_history:
            symbol = signal.symbol
            entry_price = signal.price
            entry_date = signal.timestamp
            
            # 查找退出价格
            try:
                exit_idx = price_data.index.get_loc(entry_date) + holding_period
                if exit_idx < len(price_data):
                    exit_price = price_data.iloc[exit_idx][symbol] if symbol in price_data.columns else entry_price
                else:
                    exit_price = entry_price
            except:
                exit_price = entry_price
            
            # 计算收益
            if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
                pnl = (exit_price - entry_price) / entry_price
            else:
                pnl = (entry_price - exit_price) / entry_price
            
            results.append({
                'symbol': symbol,
                'signal_type': signal.signal_type.name,
                'entry_date': entry_date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl,
                'confidence': signal.confidence,
                'strategy': signal.strategy_name
            })
        
        return pd.DataFrame(results)


class SignalCombiner:
    """
    信号合成器
    
    合成多个信号源的信号
    """
    
    def __init__(self):
        self.signal_sources: Dict[str, float] = {}  # source_name: weight
    
    def add_source(self, source_name: str, weight: float = 1.0):
        """添加信号源"""
        self.signal_sources[source_name] = weight
    
    def combine(
        self,
        signals_dict: Dict[str, List[TradeSignal]],
        method: str = 'weighted_vote'
    ) -> Dict[str, TradeSignal]:
        """
        合成信号
        
        Args:
            signals_dict: {source_name: [signals]}
            method: 合成方法 ('weighted_vote', 'majority', 'average')
            
        Returns:
            Dict: {symbol: combined_signal}
        """
        # 按股票分组
        symbol_signals = {}
        
        for source_name, signals in signals_dict.items():
            weight = self.signal_sources.get(source_name, 1.0)
            
            for signal in signals:
                symbol = signal.symbol
                if symbol not in symbol_signals:
                    symbol_signals[symbol] = []
                symbol_signals[symbol].append((signal, weight))
        
        # 合成
        combined = {}
        
        for symbol, signal_list in symbol_signals.items():
            if method == 'weighted_vote':
                # 加权投票
                buy_score = sum(s.confidence * w for s, w in signal_list if s.signal_type in [SignalType.BUY, SignalType.STRONG_BUY])
                sell_score = sum(s.confidence * w for s, w in signal_list if s.signal_type in [SignalType.SELL, SignalType.STRONG_SELL])
                
                if buy_score > sell_score and buy_score > 0.5:
                    combined[symbol] = TradeSignal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        timestamp=datetime.now(),
                        price=signal_list[0][0].price,
                        confidence=min(buy_score, 1.0),
                        strategy_name='combined'
                    )
                elif sell_score > buy_score and sell_score > 0.5:
                    combined[symbol] = TradeSignal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        timestamp=datetime.now(),
                        price=signal_list[0][0].price,
                        confidence=min(sell_score, 1.0),
                        strategy_name='combined'
                    )
        
        return combined
