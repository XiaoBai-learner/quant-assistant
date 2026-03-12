"""
WP1: Data Adapter - 数据适配器
负责数据格式转换、重采样和清洗
"""
import pandas as pd
import numpy as np
from typing import Optional, Literal
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataAdapter:
    """
    数据适配器
    
    将原始行情数据转换为可视化所需的格式
    支持数据重采样 (日线 -> 周线/月线)
    """
    
    def __init__(self):
        self.name = "DataAdapter"
    
    def resample(
        self,
        df: pd.DataFrame,
        period: Literal['D', 'W', 'M'] = 'D'
    ) -> pd.DataFrame:
        """
        数据重采样
        
        Args:
            df: 原始日线数据 DataFrame
            period: 目标周期 'D'=日线, 'W'=周线, 'M'=月线
            
        Returns:
            DataFrame: 重采样后的数据
        """
        if df.empty:
            logger.warning("输入数据为空，无法重采样")
            return pd.DataFrame()
        
        if period == 'D':
            return df.copy()
        
        # 确保 trade_date 是 datetime 类型
        df = df.copy()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        
        # 重采样规则
        if period == 'W':
            # 周线: 周一为每周开始
            rule = 'W-MON'
        elif period == 'M':
            # 月线: 每月第一天
            rule = 'MS'
        else:
            raise ValueError(f"不支持的周期: {period}")
        
        try:
            resampled = df.resample(rule).agg({
                'symbol': 'first',
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'amount': 'sum',
            })
            
            # 删除没有交易的周期
            resampled = resampled.dropna(subset=['close'])
            
            # 重置索引
            resampled.reset_index(inplace=True)
            resampled['trade_date'] = resampled['trade_date'].dt.date
            
            logger.info(f"数据重采样完成: {len(df)} 条 -> {len(resampled)} 条 ({period})")
            return resampled
            
        except Exception as e:
            logger.error(f"数据重采样失败: {e}")
            raise
    
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        数据标准化处理
        
        - 确保列名正确
        - 数据类型转换
        - 排序
        
        Args:
            df: 原始数据
            
        Returns:
            DataFrame: 标准化后的数据
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # 必需的列
        required_cols = ['trade_date', 'open', 'high', 'low', 'close', 'volume']
        
        # 检查必需列
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")
        
        # 数据类型转换
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 按日期排序
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        logger.debug(f"数据标准化完成: {len(df)} 条记录")
        return df
    
    def fill_missing(
        self,
        df: pd.DataFrame,
        method: str = 'ffill'
    ) -> pd.DataFrame:
        """
        缺失值填充
        
        Args:
            df: 原始数据
            method: 填充方法 'ffill'=前值填充, 'bfill'=后值填充, 'linear'=线性插值
            
        Returns:
            DataFrame: 填充后的数据
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # 价格数据使用前向填充
        price_cols = ['open', 'high', 'low', 'close']
        
        if method == 'ffill':
            df[price_cols] = df[price_cols].fillna(method='ffill')
        elif method == 'bfill':
            df[price_cols] = df[price_cols].fillna(method='bfill')
        elif method == 'linear':
            df[price_cols] = df[price_cols].interpolate(method='linear')
        else:
            raise ValueError(f"不支持的填充方法: {method}")
        
        # 成交量缺失填0
        if 'volume' in df.columns:
            df['volume'] = df['volume'].fillna(0)
        
        logger.debug(f"缺失值填充完成: 方法={method}")
        return df
    
    def prepare_for_chart(
        self,
        df: pd.DataFrame,
        period: Literal['D', 'W', 'M'] = 'D'
    ) -> pd.DataFrame:
        """
        一站式数据准备
        
        执行: 标准化 -> 重采样 -> 填充缺失值
        
        Args:
            df: 原始数据
            period: 目标周期
            
        Returns:
            DataFrame: 准备好的数据
        """
        df = self.normalize(df)
        df = self.resample(df, period)
        df = self.fill_missing(df)
        return df
