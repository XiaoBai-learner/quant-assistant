"""
数据获取器基类
"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class BaseDataFetcher(ABC):
    """数据获取器抽象基类"""
    
    def __init__(self):
        self.name = "BaseFetcher"
    
    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        pass
    
    @abstractmethod
    def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """获取日线数据"""
        pass
    
    @abstractmethod
    def get_financial_indicators(self, symbol: str) -> pd.DataFrame:
        """获取财务指标"""
        pass
