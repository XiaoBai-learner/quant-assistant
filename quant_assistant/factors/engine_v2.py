"""
因子计算引擎 V2

支持多时间粒度因子计算，包括：
- 日线级因子：适合中长期策略
- 分钟级因子：适合日内/短线策略  
- 实时因子：适合高频/实时交易

因子分类：
- 趋势类：MA, EMA, MACD, ADX等
- 动量类：RSI, KDJ, CCI, WR等
- 波动率类：布林带, ATR, 唐奇安通道等
- 量价类：成交量, 换手率, OBV, MFI等
- 实时类：实时换手率, 实时涨速, 实时量比等
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum


class TimeGranularity(Enum):
    """时间粒度枚举"""
    DAILY = "daily"           # 日线
    MINUTE_1 = "1min"         # 1分钟
    MINUTE_5 = "5min"         # 5分钟
    MINUTE_15 = "15min"       # 15分钟
    MINUTE_30 = "30min"       # 30分钟
    MINUTE_60 = "60min"       # 60分钟
    REALTIME = "realtime"     # 实时


class FactorCategory(Enum):
    """因子类别枚举"""
    TREND = "trend"           # 趋势
    MOMENTUM = "momentum"     # 动量
    VOLATILITY = "volatility" # 波动率
    VOLUME_PRICE = "vp"       # 量价
    PATTERN = "pattern"       # 形态
    STATISTIC = "statistic"   # 统计
    SIGNAL = "signal"         # 信号
    REALTIME = "realtime"     # 实时


class FactorMetadata:
    """因子元数据"""
    def __init__(self, name: str, category: FactorCategory, 
                 granularity: List[TimeGranularity], description: str,
                 min_bars: int = 1):
        self.name = name
        self.category = category
        self.granularity = granularity
        self.description = description
        self.min_bars = min_bars  # 计算所需最小K线数


# 因子元数据注册表
FACTOR_REGISTRY: Dict[str, FactorMetadata] = {
    # ========== 趋势类因子 (日线级) ==========
    'ma5': FactorMetadata('ma5', FactorCategory.TREND, [TimeGranularity.DAILY], 
                          '5日均线', 5),
    'ma10': FactorMetadata('ma10', FactorCategory.TREND, [TimeGranularity.DAILY], 
                           '10日均线', 10),
    'ma20': FactorMetadata('ma20', FactorCategory.TREND, [TimeGranularity.DAILY], 
                           '20日均线', 20),
    'ma60': FactorMetadata('ma60', FactorCategory.TREND, [TimeGranularity.DAILY], 
                           '60日均线', 60),
    'ema12': FactorMetadata('ema12', FactorCategory.TREND, [TimeGranularity.DAILY], 
                            '12日指数移动平均', 12),
    'macd': FactorMetadata('macd', FactorCategory.TREND, [TimeGranularity.DAILY], 
                           'MACD指标', 26),
    
    # ========== 动量类因子 (日线/分钟级) ==========
    'rsi14': FactorMetadata('rsi14', FactorCategory.MOMENTUM, 
                            [TimeGranularity.DAILY, TimeGranularity.MINUTE_5], 
                            '14日RSI', 14),
    'kdj': FactorMetadata('kdj', FactorCategory.MOMENTUM, 
                          [TimeGranularity.DAILY, TimeGranularity.MINUTE_5], 
                          'KDJ指标', 9),
    
    # ========== 波动率类因子 (日线级) ==========
    'boll': FactorMetadata('boll', FactorCategory.VOLATILITY, [TimeGranularity.DAILY], 
                           '布林带', 20),
    'atr14': FactorMetadata('atr14', FactorCategory.VOLATILITY, 
                            [TimeGranularity.DAILY, TimeGranularity.MINUTE_5], 
                            '14日ATR', 14),
    
    # ========== 量价类因子 (日线/分钟级) ==========
    'volume_ma20': FactorMetadata('volume_ma20', FactorCategory.VOLUME_PRICE, 
                                  [TimeGranularity.DAILY], '20日成交量均线', 20),
    'obv': FactorMetadata('obv', FactorCategory.VOLUME_PRICE, 
                          [TimeGranularity.DAILY, TimeGranularity.MINUTE_5], 
                          'OBV能量潮', 1),
    
    # ========== 实时因子 (高频) ==========
    'realtime_turnover': FactorMetadata('realtime_turnover', FactorCategory.REALTIME, 
                                        [TimeGranularity.REALTIME], '实时换手率', 1),
    'realtime_rise_speed': FactorMetadata('realtime_rise_speed', FactorCategory.REALTIME, 
                                          [TimeGranularity.REALTIME], '实时涨速', 1),
    'realtime_volume_ratio': FactorMetadata('realtime_volume_ratio', FactorCategory.REALTIME, 
                                            [TimeGranularity.REALTIME], '实时量比', 1),
    'realtime_order_ratio': FactorMetadata('realtime_order_ratio', FactorCategory.REALTIME, 
                                           [TimeGranularity.REALTIME], '实时委比', 1),
    'realtime_inflow': FactorMetadata('realtime_inflow', FactorCategory.REALTIME, 
                                      [TimeGranularity.REALTIME], '实时资金流向', 1),
}


class FactorEngineV2:
    """
    因子计算引擎 V2
    
    支持多时间粒度因子计算
    """
    
    def __init__(self):
        self.metadata = FACTOR_REGISTRY
    
    def detect_granularity(self, data: pd.DataFrame) -> TimeGranularity:
        """
        自动检测数据时间粒度
        
        Args:
            data: 包含datetime索引的DataFrame
            
        Returns:
            检测到的粒度类型
        """
        if len(data) < 2:
            return TimeGranularity.REALTIME
        
        # 计算时间间隔
        time_diff = data.index[1] - data.index[0]
        minutes = time_diff.total_seconds() / 60
        
        if minutes < 1:
            return TimeGranularity.REALTIME
        elif minutes == 1:
            return TimeGranularity.MINUTE_1
        elif minutes == 5:
            return TimeGranularity.MINUTE_5
        elif minutes == 15:
            return TimeGranularity.MINUTE_15
        elif minutes == 30:
            return TimeGranularity.MINUTE_30
        elif minutes == 60:
            return TimeGranularity.MINUTE_60
        else:
            return TimeGranularity.DAILY
    
    def compute_factors(
        self,
        data: pd.DataFrame,
        granularity: Optional[TimeGranularity] = None,
        categories: Optional[List[FactorCategory]] = None
    ) -> pd.DataFrame:
        """
        计算适合当前粒度的因子
        
        Args:
            data: OHLCV数据
            granularity: 指定粒度，None则自动检测
            categories: 指定计算的因子类别，None则计算所有
            
        Returns:
            添加了因子的DataFrame
        """
        df = data.copy()
        
        # 自动检测粒度
        if granularity is None:
            granularity = self.detect_granularity(df)
        
        print(f"检测到数据粒度: {granularity.value}")
        
        # 根据粒度选择因子
        if granularity == TimeGranularity.DAILY:
            df = self._compute_daily_factors(df, categories)
        elif granularity in [TimeGranularity.MINUTE_1, TimeGranularity.MINUTE_5, 
                             TimeGranularity.MINUTE_15, TimeGranularity.MINUTE_30, 
                             TimeGranularity.MINUTE_60]:
            df = self._compute_minute_factors(df, granularity, categories)
        elif granularity == TimeGranularity.REALTIME:
            df = self._compute_realtime_factors(df, categories)
        
        return df
    
    def _compute_daily_factors(
        self,
        data: pd.DataFrame,
        categories: Optional[List[FactorCategory]] = None
    ) -> pd.DataFrame:
        """计算日线级因子"""
        df = data.copy()
        
        # ========== 趋势类因子 ==========
        if categories is None or FactorCategory.TREND in categories:
            df = self._compute_trend_factors(df, windows=[5, 10, 20, 30, 60, 120])
        
        # ========== 动量类因子 ==========
        if categories is None or FactorCategory.MOMENTUM in categories:
            df = self._compute_momentum_factors(df, windows=[6, 12, 14, 24])
        
        # ========== 波动率类因子 ==========
        if categories is None or FactorCategory.VOLATILITY in categories:
            df = self._compute_volatility_factors(df, windows=[20, 60])
        
        # ========== 量价类因子 ==========
        if categories is None or FactorCategory.VOLUME_PRICE in categories:
            df = self._compute_volume_price_factors(df, windows=[5, 10, 20])
        
        # ========== 形态类因子 ==========
        if categories is None or FactorCategory.PATTERN in categories:
            df = self._compute_pattern_factors(df, windows=[20, 60])
        
        # ========== 统计类因子 ==========
        if categories is None or FactorCategory.STATISTIC in categories:
            df = self._compute_statistic_factors(df, windows=[5, 10, 20, 60])
        
        # ========== 信号类因子 ==========
        if categories is None or FactorCategory.SIGNAL in categories:
            df = self._compute_signal_factors(df)
        
        return df
    
    def _compute_minute_factors(
        self,
        data: pd.DataFrame,
        granularity: TimeGranularity,
        categories: Optional[List[FactorCategory]] = None
    ) -> pd.DataFrame:
        """计算分钟级因子"""
        df = data.copy()
        
        # 分钟级使用更短的窗口
        if granularity == TimeGranularity.MINUTE_1:
            windows = [5, 10, 20, 30]  # 5/10/20/30分钟
        elif granularity == TimeGranularity.MINUTE_5:
            windows = [5, 12, 24, 48]  # 25/60/120/240分钟
        elif granularity == TimeGranularity.MINUTE_15:
            windows = [4, 8, 16, 32]   # 1/2/4/8小时
        elif granularity == TimeGranularity.MINUTE_30:
            windows = [4, 8, 16]       # 2/4/8小时
        else:  # MINUTE_60
            windows = [2, 5, 10, 20]   # 2/5/10/20小时
        
        # ========== 趋势类因子（分钟级） ==========
        if categories is None or FactorCategory.TREND in categories:
            for window in windows:
                df[f'ma{window}'] = df['close'].rolling(window, min_periods=1).mean()
                df[f'ema{window}'] = df['close'].ewm(span=window, adjust=False).mean()
            
            # MACD（分钟级使用更短参数）
            ema_fast = df['close'].ewm(span=12, adjust=False).mean()
            ema_slow = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema_fast - ema_slow
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ========== 动量类因子（分钟级） ==========
        if categories is None or FactorCategory.MOMENTUM in categories:
            # RSI
            for window in [6, 14]:
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0).rolling(window, min_periods=1).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window, min_periods=1).mean()
                rs = gain / loss
                df[f'rsi{window}'] = 100 - (100 / (1 + rs))
            
            # KDJ（分钟级）
            low_list = df['low'].rolling(window=9, min_periods=1).min()
            high_list = df['high'].rolling(window=9, min_periods=1).max()
            rsv = (df['close'] - low_list) / (high_list - low_list) * 100
            df['kdj_k'] = rsv.ewm(com=2, adjust=False).mean()
            df['kdj_d'] = df['kdj_k'].ewm(com=2, adjust=False).mean()
            df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        # ========== 波动率类因子（分钟级） ==========
        if categories is None or FactorCategory.VOLATILITY in categories:
            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['atr14'] = tr.rolling(14, min_periods=1).mean()
            
            # 分钟级波动率
            df['intraday_volatility'] = df['close'].pct_change().rolling(20, min_periods=1).std()
        
        # ========== 量价类因子（分钟级） ==========
        if categories is None or FactorCategory.VOLUME_PRICE in categories:
            df['volume_ma20'] = df['volume'].rolling(20, min_periods=1).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma20']
            df['amount'] = df['close'] * df['volume']
            
            # 分钟级OBV
            df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        
        # ========== 实时类因子（分钟级也适用） ==========
        if categories is None or FactorCategory.REALTIME in categories:
            df = self._compute_intraday_factors(df)
        
        return df
    
    def _compute_realtime_factors(
        self,
        data: pd.DataFrame,
        categories: Optional[List[FactorCategory]] = None
    ) -> pd.DataFrame:
        """计算实时因子（Tick级或实时行情）"""
        df = data.copy()
        
        # ========== 实时因子 ==========
        if categories is None or FactorCategory.REALTIME in categories:
            df = self._compute_realtime_only_factors(df)
        
        # ========== 超短周期技术指标 ==========
        if categories is None or FactorCategory.TREND in categories:
            # 超短周期MA
            df['ma5'] = df['close'].rolling(5, min_periods=1).mean()
            df['ma10'] = df['close'].rolling(10, min_periods=1).mean()
        
        if categories is None or FactorCategory.MOMENTUM in categories:
            # 实时RSI（5周期）
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(5, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(5, min_periods=1).mean()
            rs = gain / loss
            df['rsi5'] = 100 - (100 / (1 + rs))
        
        return df
    
    def _compute_realtime_only_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算纯实时因子（需要实时行情字段）"""
        # 实时换手率
        if 'turnover' in df.columns:
            df['realtime_turnover'] = df['turnover']
        elif 'float_market_cap' in df.columns and 'amount' in df.columns:
            df['realtime_turnover'] = df['amount'] / df['float_market_cap'] * 100
        
        # 实时涨速（5分钟）
        if 'rise_speed' in df.columns:
            df['realtime_rise_speed'] = df['rise_speed']
        else:
            df['realtime_rise_speed'] = df['close'].pct_change(5) * 100
        
        # 实时量比
        if 'volume_ratio' in df.columns:
            df['realtime_volume_ratio'] = df['volume_ratio']
        else:
            df['realtime_volume_ratio'] = df['volume'] / df['volume'].rolling(20, min_periods=1).mean()
        
        # 实时委比
        if 'order_ratio' in df.columns:
            df['realtime_order_ratio'] = df['order_ratio']
        
        # 实时资金流向估算
        if all(col in df.columns for col in ['outer_disc', 'inner_disc']):
            df['realtime_inflow'] = df['outer_disc'] - df['inner_disc']
        
        # 实时振幅
        if 'amplitude' in df.columns:
            df['realtime_amplitude'] = df['amplitude']
        else:
            df['realtime_amplitude'] = (df['high'] - df['low']) / df['low'] * 100
        
        # 实时价格位置（日内）
        if 'pre_close' in df.columns:
            df['realtime_price_position'] = (df['close'] - df['pre_close']) / df['pre_close'] * 100
        
        # 实时买卖力度
        if all(col in df.columns for col in ['high', 'low', 'close', 'open']):
            df['buying_power'] = (df['close'] - df['low']) / (df['high'] - df['low'])
            df['selling_pressure'] = (df['high'] - df['close']) / (df['high'] - df['low'])
        
        return df
    
    def _compute_intraday_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算日内因子（适用于分钟级数据）"""
        # 日内涨跌幅
        if len(df) > 0:
            first_price = df['close'].iloc[0]
            df['intraday_change'] = (df['close'] - first_price) / first_price * 100
        
        # 日内最高/最低位置
        df['intraday_high_pos'] = df['high'].expanding().max()
        df['intraday_low_pos'] = df['low'].expanding().min()
        df['intraday_position'] = (df['close'] - df['intraday_low_pos']) / (
            df['intraday_high_pos'] - df['intraday_low_pos'] + 1e-10)
        
        # 日内成交量分布
        df['volume_cumsum'] = df['volume'].cumsum()
        df['volume_pct'] = df['volume'] / df['volume'].sum() if df['volume'].sum() > 0 else 0
        
        # 日内均价
        df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
        df['vwap_deviation'] = (df['close'] - df['vwap']) / df['vwap']
        
        return df
    
    def _compute_trend_factors(self, df: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        """计算趋势类因子"""
        for window in windows:
            df[f'ma{window}'] = df['close'].rolling(window, min_periods=1).mean()
            df[f'ema{window}'] = df['close'].ewm(span=window, adjust=False).mean()
        
        # 均线差值和比值
        df['ma5_10_diff'] = df['ma5'] - df['ma10']
        df['ma10_20_diff'] = df['ma10'] - df['ma20']
        df['ma20_60_diff'] = df['ma20'] - df['ma60']
        df['ma5_10_ratio'] = df['ma5'] / df['ma10']
        df['ma10_20_ratio'] = df['ma10'] / df['ma20']
        
        # MACD
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df
    
    def _compute_momentum_factors(self, df: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        """计算动量类因子"""
        for window in windows:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window, min_periods=1).mean()
            rs = gain / loss
            df[f'rsi{window}'] = 100 - (100 / (1 + rs))
        
        # KDJ
        low_list = df['low'].rolling(window=9, min_periods=1).min()
        high_list = df['high'].rolling(window=9, min_periods=1).max()
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        df['kdj_k'] = rsv.ewm(com=2, adjust=False).mean()
        df['kdj_d'] = df['kdj_k'].ewm(com=2, adjust=False).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        # CCI
        tp = (df['high'] + df['low'] + df['close']) / 3
        ma_tp = tp.rolling(window=20, min_periods=1).mean()
        md_tp = tp.rolling(window=20, min_periods=1).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True)
        df['cci20'] = (tp - ma_tp) / (0.015 * md_tp)
        
        # 威廉指标
        highest_high = df['high'].rolling(window=14, min_periods=1).max()
        lowest_low = df['low'].rolling(window=14, min_periods=1).min()
        df['wr14'] = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
        
        # 动量和ROC
        for window in [10, 20]:
            df[f'mom{window}'] = df['close'] - df['close'].shift(window)
            df[f'roc{window}'] = (df['close'] / df['close'].shift(window) - 1) * 100
        
        return df
    
    def _compute_volatility_factors(self, df: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        """计算波动率类因子"""
        for window in windows:
            middle = df['close'].rolling(window, min_periods=1).mean()
            std = df['close'].rolling(window, min_periods=1).std()
            df[f'boll_upper_{window}'] = middle + 2 * std
            df[f'boll_middle_{window}'] = middle
            df[f'boll_lower_{window}'] = middle - 2 * std
            df[f'boll_width_{window}'] = 4 * std / middle
            df[f'boll_position_{window}'] = (df['close'] - (middle - 2 * std)) / (4 * std + 1e-10)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr14'] = tr.rolling(14, min_periods=1).mean()
        df['atr_ratio_14'] = df['atr14'] / df['close']
        
        # 历史波动率
        for window in [20, 60]:
            df[f'volatility_{window}'] = df['close'].pct_change().rolling(window, min_periods=1).std() * np.sqrt(252)
        
        return df
    
    def _compute_volume_price_factors(self, df: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        """计算量价类因子"""
        for window in windows:
            df[f'volume_ma{window}'] = df['volume'].rolling(window, min_periods=1).mean()
        
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        df['volume_change'] = df['volume'].pct_change()
        
        df['amount'] = df['close'] * df['volume']
        for window in windows:
            df[f'amount_ma{window}'] = df['amount'].rolling(window, min_periods=1).mean()
        
        df['price_volume_corr'] = df['close'].rolling(20, min_periods=1).corr(df['volume'])
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        
        # MFI
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        raw_money_flow = typical_price * df['volume']
        money_flow = raw_money_flow.where(typical_price > typical_price.shift(), -raw_money_flow)
        positive_flow = money_flow.where(money_flow > 0, 0).rolling(14, min_periods=1).sum()
        negative_flow = np.abs(money_flow.where(money_flow < 0, 0)).rolling(14, min_periods=1).sum()
        money_ratio = positive_flow / (negative_flow + 1e-10)
        df['mfi14'] = 100 - (100 / (1 + money_ratio))
        
        return df
    
    def _compute_pattern_factors(self, df: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        """计算形态类因子"""
        df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
        df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
        df['body'] = np.abs(df['close'] - df['open']) / df['close']
        
        for window in windows:
            high_max = df['high'].rolling(window, min_periods=1).max()
            low_min = df['low'].rolling(window, min_periods=1).min()
            df[f'price_position_{window}'] = (df['close'] - low_min) / (high_max - low_min + 1e-10)
        
        return df
    
    def _compute_statistic_factors(self, df: pd.DataFrame, windows: List[int]) -> pd.DataFrame:
        """计算统计类因子"""
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        for window in windows:
            df[f'returns_mean_{window}'] = df['returns'].rolling(window, min_periods=1).mean()
            df[f'returns_std_{window}'] = df['returns'].rolling(window, min_periods=1).std()
            df[f'returns_skew_{window}'] = df['returns'].rolling(window, min_periods=1).skew()
            df[f'returns_kurt_{window}'] = df['returns'].rolling(window, min_periods=1).kurt()
        
        for window in [20, 60]:
            rolling_max = df['close'].rolling(window, min_periods=1).max()
            df[f'drawdown_{window}'] = (df['close'] - rolling_max) / rolling_max
        
        return df
    
    def _compute_signal_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算信号类因子"""
        # MACD金叉死叉
        df['macd_golden_cross'] = ((df['macd'] > df['macd_signal']) & 
                                   (df['macd'].shift(1) <= df['macd_signal'].shift(1))).astype(int)
        df['macd_dead_cross'] = ((df['macd'] < df['macd_signal']) & 
                                 (df['macd'].shift(1) >= df['macd_signal'].shift(1))).astype(int)
        
        # KDJ金叉
        df['kdj_golden_cross'] = ((df['kdj_k'] > df['kdj_d']) & 
                                  (df['kdj_k'].shift(1) <= df['kdj_d'].shift(1))).astype(int)
        
        # 均线排列
        df['ma_bull'] = ((df['ma5'] > df['ma10']) & 
                         (df['ma10'] > df['ma20']) & 
                         (df['ma20'] > df['ma60'])).astype(int)
        df['ma_bear'] = ((df['ma5'] < df['ma10']) & 
                         (df['ma10'] < df['ma20']) & 
                         (df['ma20'] < df['ma60'])).astype(int)
        
        df['trend_strength'] = (df['ma5_10_ratio'] + df['ma10_20_ratio']) / 2
        
        return df
    
    def get_factor_info(self) -> pd.DataFrame:
        """
        获取所有因子的元数据信息
        
        Returns:
            DataFrame 包含因子名称、类别、适用粒度、描述
        """
        info = []
        for name, meta in self.metadata.items():
            info.append({
                'name': meta.name,
                'category': meta.category.value,
                'granularity': [g.value for g in meta.granularity],
                'description': meta.description,
                'min_bars': meta.min_bars
            })
        return pd.DataFrame(info)
