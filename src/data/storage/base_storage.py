"""
数据存储基类
"""
from abc import ABC, abstractmethod
import pandas as pd


class BaseStorage(ABC):
    """数据存储抽象基类"""
    
    @abstractmethod
    def save_stocks(self, df: pd.DataFrame) -> int:
        """保存股票列表"""
        pass
    
    @abstractmethod
    def save_daily_quotes(self, df: pd.DataFrame) -> int:
        """保存日线数据"""
        pass
    
    @abstractmethod
    def save_financial_indicators(self, df: pd.DataFrame) -> int:
        """保存财务指标"""
        pass
