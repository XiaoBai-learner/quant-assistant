"""
图表渲染器基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd

from ..indicators.base import IndicatorResult


class BaseRenderer(ABC):
    """图表渲染器基类"""
    
    def __init__(self, width: int = 80, height: int = 20):
        self.width = width
        self.height = height
    
    @abstractmethod
    def render(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, IndicatorResult] = None,
        title: str = ""
    ) -> str:
        """
        渲染图表
        
        Args:
            df: 行情数据
            indicators: 指标计算结果
            title: 图表标题
            
        Returns:
            str: 渲染后的图表字符串
        """
        pass
    
    @abstractmethod
    def render_candlestick(
        self,
        df: pd.DataFrame,
        title: str = ""
    ) -> str:
        """渲染K线图"""
        pass
    
    @abstractmethod
    def render_indicator(
        self,
        result: IndicatorResult,
        title: str = ""
    ) -> str:
        """渲染指标"""
        pass
