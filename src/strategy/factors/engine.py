"""
因子计算引擎
负责因子的批量计算、存储和查询
"""
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime, date

from .base import Factor, FactorResult
from .registry import factor_registry
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FactorEngine:
    """
    因子计算引擎
    
    提供因子的批量计算、质量检查和数据管理
    """
    
    def __init__(self):
        self.registry = factor_registry
    
    def calculate(
        self,
        df: pd.DataFrame,
        factor_names: List[str] = None
    ) -> Dict[str, FactorResult]:
        """
        批量计算因子
        
        Args:
            df: 行情数据
            factor_names: 因子名称列表，None表示计算所有
            
        Returns:
            Dict[str, FactorResult]: 因子计算结果
        """
        results = {}
        
        names = factor_names or self.registry.list_factors()
        
        for name in names:
            try:
                factor = self.registry.create_factor(name)
                result = factor.calculate(df)
                results[name] = result
                logger.debug(f"因子计算完成: {name}")
            except Exception as e:
                logger.error(f"因子计算失败 {name}: {e}")
                raise
        
        return results
    
    def calculate_single(
        self,
        df: pd.DataFrame,
        factor_name: str,
        params: Dict[str, Any] = None
    ) -> FactorResult:
        """
        计算单个因子
        
        Args:
            df: 行情数据
            factor_name: 因子名称
            params: 因子参数
            
        Returns:
            FactorResult: 因子计算结果
        """
        factor = self.registry.create_factor(factor_name, params)
        return factor.calculate(df)
    
    def quality_check(self, result: FactorResult) -> Dict[str, Any]:
        """
        因子质量检查
        
        Args:
            result: 因子计算结果
            
        Returns:
            质量报告
        """
        values = result.values.dropna()
        
        if len(values) == 0:
            return {
                'name': result.name,
                'status': 'failed',
                'reason': '无有效数据',
                'coverage': 0.0
            }
        
        # 基础统计
        report = {
            'name': result.name,
            'status': 'passed',
            'count': len(values),
            'coverage': len(values) / len(result.values),
            'mean': float(values.mean()),
            'std': float(values.std()),
            'min': float(values.min()),
            'max': float(values.max()),
            'skewness': float(values.skew()),
            'kurtosis': float(values.kurtosis()),
        }
        
        # 缺失率检查
        if report['coverage'] < 0.5:
            report['status'] = 'warning'
            report['warning'] = '缺失率过高'
        
        # 零值检查
        zero_ratio = (values == 0).sum() / len(values)
        if zero_ratio > 0.5:
            report['status'] = 'warning'
            report['warning'] = '零值比例过高'
        
        return report
    
    def get_factor_values(
        self,
        results: Dict[str, FactorResult]
    ) -> pd.DataFrame:
        """
        将因子结果合并为DataFrame
        
        Args:
            results: 因子计算结果字典
            
        Returns:
            DataFrame: 因子值矩阵
        """
        df = pd.DataFrame()
        
        for name, result in results.items():
            df[name] = result.values
        
        return df
    
    def register_builtin_factors(self):
        """注册内置因子"""
        from .technical import (
            MAFactor, EMAFactor, MACDFactor, RSIFactor,
            BOLLFactor, KDJFactor, ATRFactor, OBVFactor
        )
        
        factors = [
            MAFactor,
            EMAFactor,
            MACDFactor,
            RSIFactor,
            BOLLFactor,
            KDJFactor,
            ATRFactor,
            OBVFactor,
        ]
        
        for factor_class in factors:
            self.registry.register(factor_class)
        
        logger.info(f"已注册 {len(factors)} 个内置因子")
