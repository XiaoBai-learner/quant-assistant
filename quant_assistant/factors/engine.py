"""
因子计算引擎

提供常用技术指标的计算功能。
"""

import pandas as pd
import numpy as np
from typing import Dict


class FactorEngine:
    """因子计算引擎"""
    
    def ma(self, series: pd.Series, window: int = 20) -> pd.Series:
        """
        计算简单移动平均线
        
        Args:
            series: 价格序列
            window: 窗口大小
            
        Returns:
            MA序列
        """
        return series.rolling(window=window, min_periods=1).mean()
    
    def ema(self, series: pd.Series, window: int = 20) -> pd.Series:
        """
        计算指数移动平均线
        
        Args:
            series: 价格序列
            window: 窗口大小
            
        Returns:
            EMA序列
        """
        return series.ewm(span=window, adjust=False).mean()
    
    def macd(
        self,
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Dict[str, pd.Series]:
        """
        计算MACD指标
        
        Args:
            series: 价格序列
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            {'macd': ..., 'signal': ..., 'histogram': ...}
        """
        ema_fast = self.ema(series, fast)
        ema_slow = self.ema(series, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def rsi(self, series: pd.Series, window: int = 14) -> pd.Series:
        """
        计算RSI指标
        
        Args:
            series: 价格序列
            window: 窗口大小
            
        Returns:
            RSI序列
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=1).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def bollinger(
        self,
        series: pd.Series,
        window: int = 20,
        std: int = 2
    ) -> Dict[str, pd.Series]:
        """
        计算布林带
        
        Args:
            series: 价格序列
            window: 窗口大小
            std: 标准差倍数
            
        Returns:
            {'upper': ..., 'middle': ..., 'lower': ...}
        """
        middle = self.ma(series, window)
        rolling_std = series.rolling(window=window, min_periods=1).std()
        upper = middle + (rolling_std * std)
        lower = middle - (rolling_std * std)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    def kdj(
        self,
        data: pd.DataFrame,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Dict[str, pd.Series]:
        """
        计算KDJ指标
        
        Args:
            data: 包含high, low, close的DataFrame
            n: RSV周期
            m1: K平滑周期
            m2: D平滑周期
            
        Returns:
            {'k': ..., 'd': ..., 'j': ...}
        """
        low_list = data['low'].rolling(window=n, min_periods=1).min()
        high_list = data['high'].rolling(window=n, min_periods=1).max()
        rsv = (data['close'] - low_list) / (high_list - low_list) * 100
        
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return {'k': k, 'd': d, 'j': j}
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有常用技术指标
        
        Args:
            data: 包含OHLCV的DataFrame
            
        Returns:
            添加了技术指标的DataFrame
        """
        df = data.copy()
        
        # 移动平均线
        df['ma5'] = self.ma(df['close'], 5)
        df['ma10'] = self.ma(df['close'], 10)
        df['ma20'] = self.ma(df['close'], 20)
        df['ma60'] = self.ma(df['close'], 60)
        
        # EMA
        df['ema12'] = self.ema(df['close'], 12)
        df['ema26'] = self.ema(df['close'], 26)
        
        # MACD
        macd = self.macd(df['close'])
        df['macd'] = macd['macd']
        df['macd_signal'] = macd['signal']
        df['macd_hist'] = macd['histogram']
        
        # RSI
        df['rsi6'] = self.rsi(df['close'], 6)
        df['rsi12'] = self.rsi(df['close'], 12)
        df['rsi24'] = self.rsi(df['close'], 24)
        
        # 布林带
        bb = self.bollinger(df['close'])
        df['boll_upper'] = bb['upper']
        df['boll_middle'] = bb['middle']
        df['boll_lower'] = bb['lower']
        
        # KDJ
        kdj = self.kdj(df)
        df['kdj_k'] = kdj['k']
        df['kdj_d'] = kdj['d']
        df['kdj_j'] = kdj['j']
        
        return df
