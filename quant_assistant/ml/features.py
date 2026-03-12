"""
特征工程模块
"""

import pandas as pd
import numpy as np
from typing import List, Optional


class FeatureEngineer:
    """特征工程器"""
    
    def __init__(self):
        self.feature_names = []
    
    def create_price_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        创建价格相关特征
        
        Args:
            data: OHLCV数据
            
        Returns:
            添加了价格特征的DataFrame
        """
        df = data.copy()
        
        # 价格变化率
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # 价格波动
        df['price_range'] = (df['high'] - df['low']) / df['close']
        df['price_change'] = (df['close'] - df['open']) / df['open']
        
        # 上下影线
        df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
        df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
        
        return df
    
    def create_volume_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        创建成交量特征
        
        Args:
            data: OHLCV数据
            
        Returns:
            添加了成交量特征的DataFrame
        """
        df = data.copy()
        
        # 成交量变化
        df['volume_change'] = df['volume'].pct_change()
        df['volume_ma5'] = df['volume'].rolling(5).mean()
        df['volume_ma20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        # 量价关系
        df['price_volume'] = df['returns'] * df['volume_change']
        
        return df
    
    def create_lag_features(
        self,
        data: pd.DataFrame,
        columns: Optional[List[str]] = None,
        lags: List[int] = [1, 2, 3, 5]
    ) -> pd.DataFrame:
        """
        创建滞后特征
        
        Args:
            data: 输入数据
            columns: 要创建滞后特征的列，None则使用所有数值列
            lags: 滞后周期列表
            
        Returns:
            添加了滞后特征的DataFrame
        """
        df = data.copy()
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            for lag in lags:
                df[f'{col}_lag{lag}'] = df[col].shift(lag)
        
        return df
    
    def create_rolling_features(
        self,
        data: pd.DataFrame,
        columns: Optional[List[str]] = None,
        windows: List[int] = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        创建滚动统计特征
        
        Args:
            data: 输入数据
            columns: 要处理的列
            windows: 窗口大小列表
            
        Returns:
            添加了滚动特征的DataFrame
        """
        df = data.copy()
        
        if columns is None:
            columns = ['close', 'volume']
        
        for col in columns:
            if col not in df.columns:
                continue
            for window in windows:
                df[f'{col}_roll_mean_{window}'] = df[col].rolling(window).mean()
                df[f'{col}_roll_std_{window}'] = df[col].rolling(window).std()
                df[f'{col}_roll_max_{window}'] = df[col].rolling(window).max()
                df[f'{col}_roll_min_{window}'] = df[col].rolling(window).min()
        
        return df
    
    def prepare_ml_data(
        self,
        data: pd.DataFrame,
        target: str = 'close',
        horizon: int = 1
    ) -> pd.DataFrame:
        """
        准备机器学习数据
        
        Args:
            data: 原始数据
            target: 目标列
            horizon: 预测 horizon
            
        Returns:
            准备好的ML数据
        """
        df = data.copy()
        
        # 创建特征
        df = self.create_price_features(df)
        df = self.create_volume_features(df)
        df = self.create_lag_features(df, lags=[1, 2, 3, 5])
        df = self.create_rolling_features(df, windows=[5, 10, 20])
        
        # 创建目标变量 (未来收益率)
        df['target'] = df[target].shift(-horizon) / df[target] - 1
        
        # 删除包含NaN的行
        df = df.dropna()
        
        return df
