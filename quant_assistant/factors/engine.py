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
        计算所有常用技术指标（基础版）
        
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
    
    def compute_all_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有策略因子（完整版）
        
        一次性计算所有常用技术指标、量价因子、波动率因子等，
        方便策略开发和机器学习特征工程。
        
        Args:
            data: 包含OHLCV的DataFrame
            
        Returns:
            添加了所有因子的DataFrame
            
        示例:
            >>> engine = FactorEngine()
            >>> df = engine.compute_all_factors(data)
            >>> print(df.columns)  # 查看所有因子
        """
        df = data.copy()
        
        # ========== 趋势类因子 ==========
        # 多周期移动平均线
        for window in [5, 10, 20, 30, 60, 120]:
            df[f'ma{window}'] = self.ma(df['close'], window)
            df[f'ema{window}'] = self.ema(df['close'], window)
        
        # 均线差值和比值
        df['ma5_10_diff'] = df['ma5'] - df['ma10']
        df['ma10_20_diff'] = df['ma10'] - df['ma20']
        df['ma20_60_diff'] = df['ma20'] - df['ma60']
        df['ma5_10_ratio'] = df['ma5'] / df['ma10']
        df['ma10_20_ratio'] = df['ma10'] / df['ma20']
        
        # MACD及其变体
        macd = self.macd(df['close'], 12, 26, 9)
        df['macd'] = macd['macd']
        df['macd_signal'] = macd['signal']
        df['macd_hist'] = macd['histogram']
        df['macd_golden_cross'] = ((df['macd'] > df['macd_signal']) & 
                                   (df['macd'].shift(1) <= df['macd_signal'].shift(1))).astype(int)
        df['macd_dead_cross'] = ((df['macd'] < df['macd_signal']) & 
                                 (df['macd'].shift(1) >= df['macd_signal'].shift(1))).astype(int)
        
        # ========== 动量类因子 ==========
        # 多周期RSI
        for window in [6, 12, 14, 24]:
            df[f'rsi{window}'] = self.rsi(df['close'], window)
        
        # KDJ
        kdj = self.kdj(df, 9, 3, 3)
        df['kdj_k'] = kdj['k']
        df['kdj_d'] = kdj['d']
        df['kdj_j'] = kdj['j']
        df['kdj_golden_cross'] = ((df['kdj_k'] > df['kdj_d']) & 
                                  (df['kdj_k'].shift(1) <= df['kdj_d'].shift(1))).astype(int)
        
        # 价格动量
        for window in [5, 10, 20, 60]:
            df[f'momentum{window}'] = df['close'] / df['close'].shift(window) - 1
            df[f'price_change_{window}'] = df['close'].pct_change(window)
        
        # ========== 波动率类因子 ==========
        # 布林带
        for window in [20, 60]:
            bb = self.bollinger(df['close'], window, 2)
            df[f'boll_upper_{window}'] = bb['upper']
            df[f'boll_middle_{window}'] = bb['middle']
            df[f'boll_lower_{window}'] = bb['lower']
            df[f'boll_width_{window}'] = (bb['upper'] - bb['lower']) / bb['middle']
            df[f'boll_position_{window}'] = (df['close'] - bb['lower']) / (bb['upper'] - bb['lower'])
        
        # 历史波动率
        for window in [5, 10, 20, 60]:
            df[f'volatility_{window}'] = df['close'].pct_change().rolling(window).std() * np.sqrt(252)
        
        # ATR (平均真实波幅)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        for window in [14, 20]:
            df[f'atr{window}'] = tr.rolling(window).mean()
            df[f'atr_ratio_{window}'] = df[f'atr{window}'] / df['close']
        
        # ========== 量价类因子 ==========
        # 成交量移动平均
        for window in [5, 10, 20]:
            df[f'volume_ma{window}'] = df['volume'].rolling(window).mean()
        
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        df['volume_change'] = df['volume'].pct_change()
        
        # 量价关系
        df['price_volume_corr'] = df['close'].rolling(20).corr(df['volume'])
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        
        # 成交额
        df['amount'] = df['close'] * df['volume']
        for window in [5, 10, 20]:
            df[f'amount_ma{window}'] = df['amount'].rolling(window).mean()
        
        # ========== 价格形态因子 ==========
        # 影线
        df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
        df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
        df['body'] = np.abs(df['close'] - df['open']) / df['close']
        
        # 价格位置
        for window in [20, 60]:
            high_max = df['high'].rolling(window).max()
            low_min = df['low'].rolling(window).min()
            df[f'price_position_{window}'] = (df['close'] - low_min) / (high_max - low_min)
        
        # ========== 统计类因子 ==========
        # 收益率统计
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        for window in [5, 10, 20]:
            df[f'returns_mean_{window}'] = df['returns'].rolling(window).mean()
            df[f'returns_std_{window}'] = df['returns'].rolling(window).std()
            df[f'returns_skew_{window}'] = df['returns'].rolling(window).skew()
            df[f'returns_kurt_{window}'] = df['returns'].rolling(window).kurt()
        
        # 最大回撤
        for window in [20, 60]:
            rolling_max = df['close'].rolling(window).max()
            df[f'drawdown_{window}'] = (df['close'] - rolling_max) / rolling_max
        
        # ========== 复合信号因子 ==========
        # 均线多头排列
        df['ma_bull'] = ((df['ma5'] > df['ma10']) & 
                         (df['ma10'] > df['ma20']) & 
                         (df['ma20'] > df['ma60'])).astype(int)
        
        # 均线空头排列
        df['ma_bear'] = ((df['ma5'] < df['ma10']) & 
                         (df['ma10'] < df['ma20']) & 
                         (df['ma20'] < df['ma60'])).astype(int)
        
        # 综合趋势强度
        df['trend_strength'] = (df['ma5_10_ratio'] + df['ma10_20_ratio']) / 2
        
        return df
