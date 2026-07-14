"""
技术指标因子库
实现常用的技术分析指标
"""
from typing import List
import pandas as pd
import numpy as np

from .base import TechnicalFactor, FactorResult, FactorMetadata
from quant_assistant.factors import indicators


class MAFactor(TechnicalFactor):
    """移动平均线因子"""
    
    def __init__(self, period: int = 5, price_col: str = 'close'):
        self.period = period
        self.price_col = price_col
        super().__init__(
            name=f"MA{period}",
            description=f"{period}日简单移动平均线",
            params={'period': period, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        ma = indicators.ma(df[self.price_col], self.period)

        return FactorResult(
            name=self.name,
            values=ma,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"MA({self.period}) = mean(close, {self.period})"
    
    def _get_dependencies(self) -> List[str]:
        return [self.price_col]
    
    def _get_category(self) -> str:
        return "trend"


class EMAFactor(TechnicalFactor):
    """指数移动平均线因子"""
    
    def __init__(self, period: int = 12, price_col: str = 'close'):
        self.period = period
        self.price_col = price_col
        super().__init__(
            name=f"EMA{period}",
            description=f"{period}日指数移动平均线",
            params={'period': period, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        ema = indicators.ema(df[self.price_col], self.period)

        return FactorResult(
            name=self.name,
            values=ema,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"EMA({self.period}) = EMA(close, {self.period})"
    
    def _get_dependencies(self) -> List[str]:
        return [self.price_col]
    
    def _get_category(self) -> str:
        return "trend"


class MACDFactor(TechnicalFactor):
    """MACD因子"""
    
    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        price_col: str = 'close'
    ):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.price_col = price_col
        super().__init__(
            name="MACD",
            description="MACD指标",
            params={'fast': fast, 'slow': slow, 'signal': signal, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.fast >= self.slow:
            raise ValueError("快线周期必须小于慢线周期")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        prices = df[self.price_col]
        
        components = indicators.macd(prices, self.fast, self.slow, self.signal)
        dif = components["macd"]
        dea = components["signal"]
        macd = 2 * (dif - dea)
        
        return FactorResult(
            name=self.name,
            values=macd,
            params=self.params,
            metadata={
                'DIF': dif,
                'DEA': dea,
                'MACD': macd
            }
        )
    
    def _get_formula(self) -> str:
        return f"MACD = 2*(EMA({self.fast})-EMA({self.slow})-DEA({self.signal}))"
    
    def _get_dependencies(self) -> List[str]:
        return [self.price_col]
    
    def _get_category(self) -> str:
        return "trend"


class RSIFactor(TechnicalFactor):
    """RSI相对强弱指数因子"""
    
    def __init__(self, period: int = 14, price_col: str = 'close'):
        self.period = period
        self.price_col = price_col
        super().__init__(
            name=f"RSI{period}",
            description=f"{period}日相对强弱指数",
            params={'period': period, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        rsi = indicators.rsi(df[self.price_col], self.period)

        return FactorResult(
            name=self.name,
            values=rsi,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"RSI({self.period}) = 100 - 100/(1+RS)"
    
    def _get_dependencies(self) -> List[str]:
        return [self.price_col]
    
    def _get_category(self) -> str:
        return "momentum"


class BOLLFactor(TechnicalFactor):
    """布林带因子"""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0, price_col: str = 'close'):
        self.period = period
        self.std_dev = std_dev
        self.price_col = price_col
        super().__init__(
            name="BOLL",
            description="布林带指标",
            params={'period': period, 'std_dev': std_dev, 'price_col': price_col}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        prices = df[self.price_col]

        boll = indicators.bollinger(prices, self.period, self.std_dev)
        middle, upper, lower = boll["middle"], boll["upper"], boll["lower"]

        # 带宽 (%B)
        bandwidth = (prices - lower) / (upper - lower)
        
        return FactorResult(
            name=self.name,
            values=bandwidth,
            params=self.params,
            metadata={
                'upper': upper,
                'middle': middle,
                'lower': lower,
                'bandwidth': bandwidth
            }
        )
    
    def _get_formula(self) -> str:
        return f"BOLL = MA({self.period}) ± {self.std_dev}*STD"
    
    def _get_dependencies(self) -> List[str]:
        return [self.price_col]
    
    def _get_category(self) -> str:
        return "volatility"


class KDJFactor(TechnicalFactor):
    """KDJ随机指标因子"""
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        self.n = n
        self.m1 = m1
        self.m2 = m2
        super().__init__(
            name="KDJ",
            description="KDJ随机指标",
            params={'n': n, 'm1': m1, 'm2': m2}
        )
    
    def _validate_params(self):
        if self.n <= 0 or self.m1 <= 0 or self.m2 <= 0:
            raise ValueError("周期必须大于0")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        kdj = indicators.kdj(df, self.n, self.m1, self.m2)
        k, d, j = kdj["k"], kdj["d"], kdj["j"]

        return FactorResult(
            name=self.name,
            values=j,
            params=self.params,
            metadata={
                'K': k,
                'D': d,
                'J': j
            }
        )
    
    def _get_formula(self) -> str:
        return "KDJ: K=EMA(RSV,3), D=EMA(K,3), J=3K-2D"
    
    def _get_dependencies(self) -> List[str]:
        return ['high', 'low', 'close']
    
    def _get_category(self) -> str:
        return "momentum"


class ATRFactor(TechnicalFactor):
    """ATR真实波动幅度因子"""
    
    def __init__(self, period: int = 14):
        self.period = period
        super().__init__(
            name=f"ATR{period}",
            description=f"{period}日真实波动幅度",
            params={'period': period}
        )
    
    def _validate_params(self):
        if self.period <= 0:
            raise ValueError(f"周期必须大于0: {self.period}")
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        atr = indicators.atr(df, self.period, min_periods=1)

        return FactorResult(
            name=self.name,
            values=atr,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return f"ATR({self.period}) = mean(TR, {self.period})"
    
    def _get_dependencies(self) -> List[str]:
        return ['high', 'low', 'close']
    
    def _get_category(self) -> str:
        return "volatility"


class OBVFactor(TechnicalFactor):
    """OBV能量潮因子"""
    
    def __init__(self):
        super().__init__(
            name="OBV",
            description="能量潮指标",
            params={}
        )
    
    def _validate_params(self):
        pass
    
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        close_diff = df['close'].diff()
        
        obv = pd.Series(index=df.index, dtype=float)
        obv.iloc[0] = df['volume'].iloc[0]
        
        for i in range(1, len(df)):
            if close_diff.iloc[i] > 0:
                obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
            elif close_diff.iloc[i] < 0:
                obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return FactorResult(
            name=self.name,
            values=obv,
            params=self.params
        )
    
    def _get_formula(self) -> str:
        return "OBV = Σ(volume * sign(close_change))"
    
    def _get_dependencies(self) -> List[str]:
        return ['close', 'volume']
    
    def _get_category(self) -> str:
        return "volume"
