"""
技术因子基类
"""

from abc import ABC, abstractmethod
import pandas as pd


class TechnicalFactor(ABC):
    """技术因子基类"""
    
    def __init__(self, name: str, params: dict = None):
        self.name = name
        self.params = params or {}
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        计算因子值
        
        Args:
            data: OHLCV数据
            
        Returns:
            因子序列
        """
        pass
    
    def __call__(self, data: pd.DataFrame) -> pd.Series:
        """便捷调用"""
        return self.calculate(data)
