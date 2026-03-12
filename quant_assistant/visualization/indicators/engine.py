"""
指标计算引擎
统一管理所有技术指标的计算
"""
from typing import List, Dict, Any, Optional
import pandas as pd

from .base import BaseIndicator, IndicatorResult
from .moving_average import MAIndicator
from .macd import MACDIndicator
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IndicatorEngine:
    """
    指标计算引擎
    
    管理所有技术指标的注册、计算和缓存
    """
    
    def __init__(self):
        self._indicators: Dict[str, BaseIndicator] = {}
        self._cache: Dict[str, IndicatorResult] = {}
        self._register_builtin_indicators()
    
    def _register_builtin_indicators(self):
        """注册内置指标"""
        # 移动平均线
        self.register(MAIndicator(period=5))
        self.register(MAIndicator(period=10))
        self.register(MAIndicator(period=20))
        
        # MACD
        self.register(MACDIndicator())
        
        logger.debug("内置指标注册完成")
    
    def register(self, indicator: BaseIndicator):
        """
        注册指标
        
        Args:
            indicator: 指标实例
        """
        self._indicators[indicator.name] = indicator
        logger.debug(f"注册指标: {indicator.name}")
    
    def get(self, name: str) -> Optional[BaseIndicator]:
        """
        获取指标
        
        Args:
            name: 指标名称
            
        Returns:
            BaseIndicator 或 None
        """
        return self._indicators.get(name)
    
    def calculate(
        self,
        df: pd.DataFrame,
        indicator_names: List[str] = None
    ) -> Dict[str, IndicatorResult]:
        """
        批量计算指标
        
        Args:
            df: 行情数据
            indicator_names: 要计算的指标列表，None表示计算所有
            
        Returns:
            Dict[str, IndicatorResult]: 指标计算结果字典
        """
        results = {}
        
        names = indicator_names or list(self._indicators.keys())
        
        for name in names:
            indicator = self._indicators.get(name)
            if indicator is None:
                logger.warning(f"未找到指标: {name}")
                continue
            
            try:
                result = indicator.calculate(df)
                results[name] = result
                logger.debug(f"指标计算完成: {name}")
            except Exception as e:
                logger.error(f"指标计算失败 {name}: {e}")
                raise
        
        return results
    
    def list_indicators(self) -> List[str]:
        """获取所有已注册指标名称"""
        return list(self._indicators.keys())
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        logger.debug("指标缓存已清空")
