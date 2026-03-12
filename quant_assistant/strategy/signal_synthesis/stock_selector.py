"""
选股器
基于多维度指标组合筛选股票
"""
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

from .strategy_builder import StrategyRule, LogicOp
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SelectionResult:
    """选股结果"""
    
    def __init__(self):
        self.selected_stocks: List[str] = []
        self.scores: Dict[str, float] = {}
        self.details: Dict[str, Dict] = {}
        self.timestamp: datetime = datetime.now()
    
    def add_stock(self, symbol: str, score: float, details: Dict = None):
        """添加选中股票"""
        self.selected_stocks.append(symbol)
        self.scores[symbol] = score
        self.details[symbol] = details or {}
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为DataFrame"""
        data = []
        for symbol in self.selected_stocks:
            row = {
                'symbol': symbol,
                'score': self.scores[symbol],
                **self.details.get(symbol, {})
            }
            data.append(row)
        
        return pd.DataFrame(data)
    
    def __repr__(self):
        return f"SelectionResult(stocks={len(self.selected_stocks)}, top={self.selected_stocks[:5] if self.selected_stocks else []})"


class StockSelector:
    """
    选股器
    
    基于多维度指标筛选股票
    """
    
    def __init__(self):
        self.rules: Dict[str, StrategyRule] = {}
    
    def add_rule(self, rule: StrategyRule):
        """添加选股规则"""
        self.rules[rule.name] = rule
    
    def select(
        self,
        factor_data: pd.DataFrame,
        rule_name: str,
        top_n: int = 20,
        min_score: float = 0.0
    ) -> SelectionResult:
        """
        选股
        
        Args:
            factor_data: 因子数据 (index=symbol, columns=factors)
            rule_name: 规则名称
            top_n: 返回前N只股票
            min_score: 最低得分阈值
            
        Returns:
            SelectionResult: 选股结果
        """
        rule = self.rules.get(rule_name)
        if rule is None:
            raise ValueError(f"规则不存在: {rule_name}")
        
        result = SelectionResult()
        
        # 遍历每只股票
        for symbol, row in factor_data.iterrows():
            factor_values = row.to_dict()
            satisfied, score = rule.evaluate(factor_values)
            
            if satisfied and score >= min_score:
                result.add_stock(symbol, score, factor_values)
        
        # 按得分排序
        result.selected_stocks.sort(key=lambda x: result.scores[x], reverse=True)
        
        # 限制数量
        if top_n > 0:
            result.selected_stocks = result.selected_stocks[:top_n]
        
        logger.info(f"选股完成: 从{len(factor_data)}只中选出{len(result.selected_stocks)}只")
        
        return result
    
    def multi_factor_select(
        self,
        factor_data: pd.DataFrame,
        rules_config: List[Dict[str, Any]],
        aggregation: str = 'weighted',
        top_n: int = 20
    ) -> SelectionResult:
        """
        多因子综合选股
        
        Args:
            factor_data: 因子数据
            rules_config: 规则配置列表
                [{ 'rule': StrategyRule, 'weight': 1.0 }, ...]
            aggregation: 聚合方式 ('weighted', 'product', 'min')
            top_n: 返回前N只
            
        Returns:
            SelectionResult: 选股结果
        """
        result = SelectionResult()
        
        # 计算每只股票的综合得分
        for symbol, row in factor_data.iterrows():
            factor_values = row.to_dict()
            
            scores = []
            weights = []
            
            for config in rules_config:
                rule = config['rule']
                weight = config.get('weight', 1.0)
                
                satisfied, score = rule.evaluate(factor_values)
                if satisfied:
                    scores.append(score)
                    weights.append(weight)
            
            if not scores:
                continue
            
            # 聚合得分
            if aggregation == 'weighted':
                total_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
            elif aggregation == 'product':
                total_score = np.prod(scores)
            elif aggregation == 'min':
                total_score = min(scores)
            else:
                total_score = sum(scores) / len(scores)
            
            result.add_stock(symbol, total_score, factor_values)
        
        # 排序并限制
        result.selected_stocks.sort(key=lambda x: result.scores[x], reverse=True)
        if top_n > 0:
            result.selected_stocks = result.selected_stocks[:top_n]
        
        logger.info(f"多因子选股完成: 选出{len(result.selected_stocks)}只")
        
        return result
    
    def filter_by_sector(
        self,
        selection_result: SelectionResult,
        sector_data: pd.Series,
        sectors: List[str] = None,
        max_per_sector: int = None
    ) -> SelectionResult:
        """
        按行业过滤
        
        Args:
            selection_result: 选股结果
            sector_data: 行业数据 (index=symbol, values=sector)
            sectors: 允许的行业列表
            max_per_sector: 每行业最多选择数量
            
        Returns:
            SelectionResult: 过滤后的结果
        """
        filtered = SelectionResult()
        sector_counts = {}
        
        for symbol in selection_result.selected_stocks:
            sector = sector_data.get(symbol)
            
            # 行业过滤
            if sectors and sector not in sectors:
                continue
            
            # 数量限制
            if max_per_sector:
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
                if sector_counts[sector] > max_per_sector:
                    continue
            
            filtered.add_stock(
                symbol,
                selection_result.scores[symbol],
                selection_result.details[symbol]
            )
        
        return filtered
    
    def filter_by_market_cap(
        self,
        selection_result: SelectionResult,
        market_cap_data: pd.Series,
        min_cap: float = None,
        max_cap: float = None
    ) -> SelectionResult:
        """
        按市值过滤
        
        Args:
            selection_result: 选股结果
            market_cap_data: 市值数据
            min_cap: 最小市值
            max_cap: 最大市值
            
        Returns:
            SelectionResult: 过滤后的结果
        """
        filtered = SelectionResult()
        
        for symbol in selection_result.selected_stocks:
            cap = market_cap_data.get(symbol)
            if cap is None:
                continue
            
            if min_cap and cap < min_cap:
                continue
            if max_cap and cap > max_cap:
                continue
            
            filtered.add_stock(
                symbol,
                selection_result.scores[symbol],
                selection_result.details[symbol]
            )
        
        return filtered
    
    def backtest_selection(
        self,
        factor_data_dict: Dict[str, pd.DataFrame],
        returns_dict: Dict[str, pd.Series],
        rule_name: str,
        rebalance_freq: str = 'M'
    ) -> pd.DataFrame:
        """
        回测选股策略
        
        Args:
            factor_data_dict: 因子数据字典 {date: factor_data}
            returns_dict: 收益数据字典 {date: returns}
            rule_name: 规则名称
            rebalance_freq: 调仓频率
            
        Returns:
            DataFrame: 回测结果
        """
        results = []
        
        for date, factor_data in sorted(factor_data_dict.items()):
            # 选股
            selection = self.select(factor_data, rule_name)
            
            # 计算组合收益
            if date in returns_dict and selection.selected_stocks:
                returns = returns_dict[date]
                portfolio_return = returns[selection.selected_stocks].mean()
                
                results.append({
                    'date': date,
                    'n_stocks': len(selection.selected_stocks),
                    'portfolio_return': portfolio_return,
                    'selected_stocks': ','.join(selection.selected_stocks[:10])  # 只记录前10只
                })
        
        return pd.DataFrame(results)
