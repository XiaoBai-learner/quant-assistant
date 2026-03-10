"""
指标基类定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd


@dataclass
class IndicatorResult:
    """指标计算结果"""
    name: str
    values: pd.Series
    params: Dict[str, Any]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseIndicator(ABC):
    """技术指标基类"""
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        self.name = name
        self.params = params or {}
        self._validate_params()
    
    @abstractmethod
    def _validate_params(self):
        """验证参数"""
        pass
    
    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> IndicatorResult:
        """
        计算指标
        
        Args:
            df: 行情数据 DataFrame
            
        Returns:
            IndicatorResult: 指标计算结果
        """
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, params={self.params})"
