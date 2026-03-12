"""
扩展技术指标库
增加更多技术指标和衍生因子
"""
from typing import List
import pandas as pd
import numpy as np

from .base import TechnicalFactor, FactorResult


class ADXFactor(TechnicalFactor):
    """ADX平均趋向指数 - 趋势强度"""
    
    def __init__(self, period: int = 14):
        self.period = period
        super().__init__(
            name=f"ADX{period}",
            description=f"{period}日平均趋向指数",
            params={'period': period}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        high = df['high']
        low = df['low']
        close = df['close']
        
        # +DM和-DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # TR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR
        atr = tr.rolling(window=self.period).mean()
        
        # +DI和-DI
        plus_di = 100 * (plus_dm.rolling(window=self.period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=self.period).mean() / atr)
        
        # DX和ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=self.period).mean()
        
        return FactorResult(
            name=self.name,
            values=adx,
            params=self.params,
            metadata={
                'plus_di': plus_di,
                'minus_di': minus_di,
                'adx': adx
            }
        )
    
    def _get_formula(self) -> str:
        return f"ADX({self.period}) = mean(|+DI - -DI| / (+DI + -DI))"
    
    def _get_dependencies(self) -> List[str]:
        return ['high', 'low', 'close']
    
    def _get_category(self) -> str:
        return "trend"


class CCIFactor(TechnicalFactor):
    """CCI商品通道指数"""
    
    def __init__(self, period: int = 20):
        self.period = period
        super().__init__(
            name=f"CCI{period}",
            description=f"{period}日商品通道指数",
            params={'period': period}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        tp = (df['high'] + df['low'] + df['close']) / 3
        ma = tp.rolling(window=self.period).mean()
        md = tp.rolling(window=self.period).apply(lambda x: np.abs(x - x.mean()).mean())
        cci = (tp - ma) / (0.015 * md)
        
        return FactorResult(
            name=self.name,
            values=cci,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"CCI({self.period}) = (TP - MA) / (0.015 * MD)"
    
    def _get_dependencies(self) -> List[str]:
        return ['high', 'low', 'close']
    
    def _get_category(self) -> str:
        return "momentum"


class WilliamsRFactor(TechnicalFactor):
    """威廉指标 %R"""
    
    def __init__(self, period: int = 14):
        self.period = period
        super().__init__(
            name=f"WR{period}",
            description=f"{period}日威廉指标",
            params={'period': period}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        highest_high = df['high'].rolling(window=self.period).max()
        lowest_low = df['low'].rolling(window=self.period).min()
        wr = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
        
        return FactorResult(
            name=self.name,
            values=wr,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"WR({self.period}) = -100 * (HH - Close) / (HH - LL)"
    
    def _get_dependencies(self) -> List[str]:
        return ['high', 'low', 'close']
    
    def _get_category(self) -> str:
        return "momentum"


class StochasticRSIFactor(TechnicalFactor):
    """随机RSI"""
    
    def __init__(self, rsi_period: int = 14, stoch_period: int = 14):
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        super().__init__(
            name=f"StochRSI",
            description="随机RSI指标",
            params={'rsi_period': rsi_period, 'stoch_period': stoch_period}
        )
    
    def _validate_params(self):
        if self.rsi_period <= 0 or self.stoch_period <= 0:
            raise ValueError("周期必须大于0")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        close = df['close']
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Stochastic RSI
        min_rsi = rsi.rolling(window=self.stoch_period).min()
        max_rsi = rsi.rolling(window=self.stoch_period).max()
        stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi)
        
        return FactorResult(
            name=self.name,
            values=stoch_rsi,
            params=self.params,
            metadata={'rsi': rsi}
        )
    
    def _get_formula(self) -> str:
        return "StochRSI = (RSI - min(RSI)) / (max(RSI) - min(RSI))"
    
    def _get_dependencies(self) -> List[str]:
        return ['close']
    
    def _get_category(self) -> str:
        return "momentum"


class MomentumFactor(TechnicalFactor):
    """动量因子"""
    
    def __init__(self, period: int = 10, price_col: str = 'close'):
        self.period = period
        self.price_col = price_col
        super().__init__(
            name=f"MOM{period}",
            description=f"{period}日动量",
            params={'period': period, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        mom = df[self.price_col] - df[self.price_col].shift(self.period)
        
        return FactorResult(
            name=self.name,
            values=mom,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"MOM({self.period}) = Close - Close({self.period} days ago)"
    
    def _get_dependencies(self) -> List[str]:
        return [self.price_col]
    
    def _get_category(self) -> str:
        return "momentum"


class RateOfChangeFactor(TechnicalFactor):
    """变化率因子 ROC"""
    
    def __init__(self, period: int = 10, price_col: str = 'close'):
        self.period = period
        self.price_col = price_col
        super().__init__(
            name=f"ROC{period}",
            description=f"{period}日变化率",
            params={'period': period, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        roc = (df[self.price_col] / df[self.price_col].shift(self.period) - 1) * 100
        
        return FactorResult(
            name=self.name,
            values=roc,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"ROC({self.period}) = (Close / Close({self.period}) - 1) * 100"
    
    def _get_dependencies(self) -> List[str]:
        return [self.price_col]
    
    def _get_category(self) -> str:
        return "momentum"


class PriceChangeFactor(TechnicalFactor):
    """价格变化因子"""
    
    def __init__(self, period: int = 1, price_col: str = 'close'):
        self.period = period
        self.price_col = price_col
        super().__init__(
            name=f"PriceChange{period}",
            description=f"{period}日价格变化",
            params={'period': period, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        change = df[self.price_col].pct_change(self.period)
        
        return FactorResult(
            name=self.name,
            values=change,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"PriceChange({self.period}) = pct_change(Close, {self.period})"
    
    def _get_dependencies(self) -> List[str]:
        return [self.price_col]
    
    def _get_category(self) -> str:
        return "price"


class VolatilityFactor(TechnicalFactor):
    """波动率因子"""
    
    def __init__(self, period: int = 20, price_col: str = 'close'):
        self.period = period
        self.price_col = price_col
        super().__init__(
            name=f"Volatility{period}",
            description=f"{period}日波动率",
            params={'period': period, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        returns = df[self.price_col].pct_change()
        volatility = returns.rolling(window=self.period).std() * np.sqrt(252)
        
        return FactorResult(
            name=self.name,
            values=volatility,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"Volatility({self.period}) = std(returns, {self.period}) * sqrt(252)"
    
    def _get_dependencies(self) -> List[str]:
        return [self.price_col]
    
    def _get_category(self) -> str:
        return "volatility"


class VolumeMAFactor(TechnicalFactor):
    """成交量移动平均"""
    
    def __init__(self, period: int = 5):
        self.period = period
        super().__init__(
            name=f"VolumeMA{period}",
            description=f"{period}日成交量移动平均",
            params={'period': period}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        vma = df['volume'].rolling(window=self.period).mean()
        
        return FactorResult(
            name=self.name,
            values=vma,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"VolumeMA({self.period}) = mean(Volume, {self.period})"
    
    def _get_dependencies(self) -> List[str]:
        return ['volume']
    
    def _get_category(self) -> str:
        return "volume"


class VolumeRatioFactor(TechnicalFactor):
    """量比因子"""
    
    def __init__(self, period: int = 5):
        self.period = period
        super().__init__(
            name=f"VolumeRatio{period}",
            description=f"{period}日量比",
            params={'period': period}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        current_volume = df['volume']
        avg_volume = df['volume'].rolling(window=self.period).mean()
        ratio = current_volume / avg_volume
        
        return FactorResult(
            name=self.name,
            values=ratio,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"VolumeRatio = Volume / mean(Volume, {self.period})"
    
    def _get_dependencies(self) -> List[str]:
        return ['volume']
    
    def _get_category(self) -> str:
        return "volume"


class PriceVolumeTrendFactor(TechnicalFactor):
    """价量趋势因子 PVT"""
    
    def __init__(self):
        super().__init__(
            name="PVT",
            description="价量趋势指标",
            params={}
        )
    
    def _validate_params(self):
        pass
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        close_change = df['close'].pct_change()
        pvt = (close_change * df['volume']).cumsum()
        
        return FactorResult(
            name=self.name,
            values=pvt,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return "PVT = cumsum(pct_change(Close) * Volume)"
    
    def _get_dependencies(self) -> List[str]:
        return ['close', 'volume']
    
    def _get_category(self) -> str:
        return "volume"


class MoneyFlowIndexFactor(TechnicalFactor):
    """资金流量指标 MFI"""
    
    def __init__(self, period: int = 14):
        self.period = period
        super().__init__(
            name=f"MFI{period}",
            description=f"{period}日资金流量指标",
            params={'period': period}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        raw_money_flow = typical_price * df['volume']
        
        money_flow = raw_money_flow.where(typical_price > typical_price.shift(), -raw_money_flow)
        positive_flow = money_flow.where(money_flow > 0, 0).rolling(window=self.period).sum()
        negative_flow = abs(money_flow.where(money_flow < 0, 0)).rolling(window=self.period).sum()
        
        money_ratio = positive_flow / negative_flow
        mfi = 100 - (100 / (1 + money_ratio))
        
        return FactorResult(
            name=self.name,
            values=mfi,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"MFI({self.period}) = 100 - 100/(1+PMF/NMF)"
    
    def _get_dependencies(self) -> List[str]:
        return ['high', 'low', 'close', 'volume']
    
    def _get_category(self) -> str:
        return "volume"


class TrueRangeFactor(TechnicalFactor):
    """真实波幅因子"""
    
    def __init__(self):
        super().__init__(
            name="TR",
            description="真实波幅",
            params={}
        )
    
    def _validate_params(self):
        pass
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift())
        tr3 = abs(df['low'] - df['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return FactorResult(
            name=self.name,
            values=tr,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return "TR = max(High-Low, |High-Close_prev|, |Low-Close_prev|)"
    
    def _get_dependencies(self) -> List[str]:
        return ['high', 'low', 'close']
    
    def _get_category(self) -> str:
        return "volatility"


class DonchianChannelFactor(TechnicalFactor):
    """唐奇安通道因子"""
    
    def __init__(self, period: int = 20):
        self.period = period
        super().__init__(
            name=f"DC{period}",
            description=f"{period}日唐奇安通道",
            params={'period': period}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        upper = df['high'].rolling(window=self.period).max()
        lower = df['low'].rolling(window=self.period).min()
        middle = (upper + lower) / 2
        
        # 返回通道宽度作为因子值
        channel_width = (upper - lower) / middle
        
        return FactorResult(
            name=self.name,
            values=channel_width,
            params=self.params,
            metadata={
                'upper': upper,
                'middle': middle,
                'lower': lower
            }
        )
    
    def _get_formula(self) -> str:
        return f"DC({self.period}): Upper=max(High), Lower=min(Low)"
    
    def _get_dependencies(self) -> List[str]:
        return ['high', 'low']
    
    def _get_category(self) -> str:
        return "volatility"


class IchimokuFactor(TechnicalFactor):
    """一目均衡表因子"""
    
    def __init__(self, tenkan_period: int = 9, kijun_period: int = 26):
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        super().__init__(
            name="Ichimoku",
            description="一目均衡表",
            params={'tenkan': tenkan_period, 'kijun': kijun_period}
        )
    
    def _validate_params(self):
        if self.tenkan_period <= 0 or self.kijun_period <= 0:
            raise ValueError("周期必须大于0")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        # 转换线 (Tenkan-sen)
        tenkan_sen = (df['high'].rolling(window=self.tenkan_period).max() + 
                      df['low'].rolling(window=self.tenkan_period).min()) / 2
        
        # 基准线 (Kijun-sen)
        kijun_sen = (df['high'].rolling(window=self.kijun_period).max() + 
                     df['low'].rolling(window=self.kijun_period).min()) / 2
        
        # 返回云图厚度作为因子
        cloud_thickness = abs(tenkan_sen - kijun_sen)
        
        return FactorResult(
            name=self.name,
            values=cloud_thickness,
            params=self.params,
            metadata={
                'tenkan_sen': tenkan_sen,
                'kijun_sen': kijun_sen
            }
        )
    
    def _get_formula(self) -> str:
        return "Ichimoku: Tenkan=(HH+LL)/2, Kijun=(HH+LL)/2"
    
    def _get_dependencies(self) -> List[str]:
        return ['high', 'low']
    
    def _get_category(self) -> str:
        return "trend"
