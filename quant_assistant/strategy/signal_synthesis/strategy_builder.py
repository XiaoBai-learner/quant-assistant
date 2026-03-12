"""
策略构建器
支持自定义指标组合规则
"""
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)


class Operator(Enum):
    """操作符"""
    GT = ">"      # 大于
    LT = "<"      # 小于
    EQ = "=="     # 等于
    GTE = ">="    # 大于等于
    LTE = "<="    # 小于等于
    NEQ = "!="    # 不等于
    AND = "and"   # 逻辑与
    OR = "or"     # 逻辑或


class LogicOp(Enum):
    """逻辑操作符"""
    AND = "and"
    OR = "or"


@dataclass
class Condition:
    """条件"""
    factor: str           # 因子名称
    operator: Operator    # 操作符
    threshold: float      # 阈值
    weight: float = 1.0   # 权重
    
    def evaluate(self, value: float) -> bool:
        """评估条件"""
        if self.operator == Operator.GT:
            return value > self.threshold
        elif self.operator == Operator.LT:
            return value < self.threshold
        elif self.operator == Operator.GTE:
            return value >= self.threshold
        elif self.operator == Operator.LTE:
            return value <= self.threshold
        elif self.operator == Operator.EQ:
            return abs(value - self.threshold) < 1e-8
        elif self.operator == Operator.NEQ:
            return abs(value - self.threshold) >= 1e-8
        return False
    
    def __repr__(self):
        return f"{self.factor} {self.operator.value} {self.threshold}"


@dataclass
class StrategyRule:
    """
    策略规则
    
    支持多条件组合
    """
    name: str
    description: str = ""
    conditions: List[Condition] = field(default_factory=list)
    logic_op: LogicOp = LogicOp.AND
    weights: List[float] = None
    
    def __post_init__(self):
        if self.weights is None:
            self.weights = [1.0] * len(self.conditions)
    
    def evaluate(self, factor_values: Dict[str, float]) -> tuple:
        """
        评估规则
        
        Args:
            factor_values: 因子值字典
            
        Returns:
            (是否满足, 得分)
        """
        scores = []
        
        for condition, weight in zip(self.conditions, self.weights):
            if condition.factor in factor_values:
                value = factor_values[condition.factor]
                satisfied = condition.evaluate(value)
                
                # 计算得分 (距离阈值的远近)
                if condition.operator in [Operator.GT, Operator.GTE]:
                    score = (value - condition.threshold) / (abs(condition.threshold) + 1e-8)
                elif condition.operator in [Operator.LT, Operator.LTE]:
                    score = (condition.threshold - value) / (abs(condition.threshold) + 1e-8)
                else:
                    score = 1.0 if satisfied else 0.0
                
                scores.append(score * weight if satisfied else 0)
            else:
                scores.append(0)
        
        # 根据逻辑操作符计算总得分
        if self.logic_op == LogicOp.AND:
            satisfied = all(s > 0 for s in scores)
            total_score = min(scores) if scores else 0
        else:  # OR
            satisfied = any(s > 0 for s in scores)
            total_score = max(scores) if scores else 0
        
        return satisfied, total_score
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'description': self.description,
            'conditions': [
                {
                    'factor': c.factor,
                    'operator': c.operator.value,
                    'threshold': c.threshold,
                    'weight': c.weight
                }
                for c in self.conditions
            ],
            'logic_op': self.logic_op.value,
            'weights': self.weights
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyRule':
        """从字典创建"""
        conditions = [
            Condition(
                factor=c['factor'],
                operator=Operator(c['operator']),
                threshold=c['threshold'],
                weight=c.get('weight', 1.0)
            )
            for c in data['conditions']
        ]
        
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            conditions=conditions,
            logic_op=LogicOp(data.get('logic_op', 'and')),
            weights=data.get('weights')
        )


class StrategyBuilder:
    """
    策略构建器
    
    用于构建和组合指标策略
    """
    
    def __init__(self):
        self.rules: Dict[str, StrategyRule] = {}
    
    def add_rule(self, rule: StrategyRule):
        """添加规则"""
        self.rules[rule.name] = rule
        logger.info(f"添加规则: {rule.name}")
    
    def remove_rule(self, name: str):
        """删除规则"""
        if name in self.rules:
            del self.rules[name]
            logger.info(f"删除规则: {name}")
    
    def get_rule(self, name: str) -> Optional[StrategyRule]:
        """获取规则"""
        return self.rules.get(name)
    
    def list_rules(self) -> List[str]:
        """列出所有规则"""
        return list(self.rules.keys())
    
    def build_strategy(
        self,
        name: str,
        rule_names: List[str],
        logic_op: LogicOp = LogicOp.AND
    ) -> StrategyRule:
        """
        组合多个规则形成新策略
        
        Args:
            name: 策略名称
            rule_names: 规则名称列表
            logic_op: 逻辑操作符
            
        Returns:
            StrategyRule: 组合后的策略
        """
        all_conditions = []
        
        for rule_name in rule_names:
            rule = self.get_rule(rule_name)
            if rule:
                all_conditions.extend(rule.conditions)
        
        combined_rule = StrategyRule(
            name=name,
            description=f"组合策略: {' + '.join(rule_names)}",
            conditions=all_conditions,
            logic_op=logic_op
        )
        
        self.add_rule(combined_rule)
        
        return combined_rule
    
    def create_condition(
        self,
        factor: str,
        operator: str,
        threshold: float,
        weight: float = 1.0
    ) -> Condition:
        """创建条件"""
        return Condition(
            factor=factor,
            operator=Operator(operator),
            threshold=threshold,
            weight=weight
        )
    
    def save_rules(self, filepath: str):
        """保存规则到文件"""
        import json
        
        data = {name: rule.to_dict() for name, rule in self.rules.items()}
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"规则已保存: {filepath}")
    
    def load_rules(self, filepath: str):
        """从文件加载规则"""
        import json
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        for name, rule_data in data.items():
            self.rules[name] = StrategyRule.from_dict(rule_data)
        
        logger.info(f"规则已加载: {filepath}, 共{len(data)}条")


class ThresholdOptimizer:
    """
    阈值优化器
    
    使用网格搜索优化阈值
    """
    
    def __init__(self):
        pass
    
    def optimize(
        self,
        rule: StrategyRule,
        factor_data: pd.DataFrame,
        returns: pd.Series,
        metric: str = 'sharpe'
    ) -> Dict[str, float]:
        """
        优化阈值
        
        Args:
            rule: 策略规则
            factor_data: 因子数据
            returns: 收益数据
            metric: 优化目标 (sharpe/return/ic)
            
        Returns:
            Dict: 最优阈值
        """
        best_thresholds = {}
        best_score = -float('inf')
        
        # 对每个条件进行网格搜索
        for condition in rule.conditions:
            factor = condition.factor
            if factor not in factor_data.columns:
                continue
            
            # 生成候选阈值
            values = factor_data[factor].dropna()
            if len(values) == 0:
                continue
            
            candidates = np.linspace(values.quantile(0.1), values.quantile(0.9), 20)
            
            for candidate in candidates:
                # 临时修改阈值
                original_threshold = condition.threshold
                condition.threshold = candidate
                
                # 评估策略
                score = self._evaluate_rule(rule, factor_data, returns, metric)
                
                # 恢复阈值
                condition.threshold = original_threshold
                
                if score > best_score:
                    best_score = score
                    best_thresholds[factor] = candidate
        
        logger.info(f"阈值优化完成: {best_thresholds}, 得分: {best_score:.4f}")
        
        return best_thresholds
    
    def _evaluate_rule(
        self,
        rule: StrategyRule,
        factor_data: pd.DataFrame,
        returns: pd.Series,
        metric: str
    ) -> float:
        """评估规则性能"""
        # 生成信号
        signals = []
        for idx, row in factor_data.iterrows():
            factor_values = row.to_dict()
            satisfied, _ = rule.evaluate(factor_values)
            signals.append(1 if satisfied else 0)
        
        signals = pd.Series(signals, index=factor_data.index)
        
        # 计算策略收益
        strategy_returns = returns * signals
        
        if metric == 'sharpe':
            # 夏普比率
            mean_return = strategy_returns.mean()
            std_return = strategy_returns.std()
            if std_return == 0:
                return 0
            return mean_return / std_return * np.sqrt(252)
        
        elif metric == 'return':
            # 累计收益
            return strategy_returns.sum()
        
        elif metric == 'ic':
            # 信息系数
            return signals.corr(returns)
        
        return 0
