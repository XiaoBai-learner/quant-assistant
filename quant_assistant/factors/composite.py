"""
复合因子
"""

import pandas as pd
from typing import List


class CompositeFactor:
    """复合因子 - 组合多个因子"""
    
    def __init__(self, factors: List = None, weights: List[float] = None):
        """
        初始化复合因子
        
        Args:
            factors: 因子列表
            weights: 权重列表
        """
        self.factors = factors or []
        self.weights = weights or []
    
    def add_factor(self, factor, weight: float = 1.0):
        """添加因子"""
        self.factors.append(factor)
        self.weights.append(weight)
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算复合因子值
        
        Args:
            data: OHLCV数据
            
        Returns:
            复合因子序列
        """
        if not self.factors:
            return pd.Series(index=data.index, data=0)
        
        result = pd.Series(index=data.index, data=0.0)
        total_weight = sum(self.weights) if self.weights else len(self.factors)
        
        for factor, weight in zip(self.factors, self.weights):
            factor_value = factor.calculate(data) if hasattr(factor, 'calculate') else factor(data)
            result += factor_value * weight / total_weight
        
        return result
    
    def __call__(self, data: pd.DataFrame) -> pd.Series:
        """便捷调用"""
        return self.calculate(data)
