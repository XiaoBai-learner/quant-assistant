"""
策略基类定义
提供策略开发的基础框架
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class SignalType(Enum):
    """信号类型"""
    BUY = 1
    SELL = -1
    HOLD = 0


@dataclass
class Signal:
    """交易信号"""
    symbol: str
    signal_type: SignalType
    price: float
    volume: int
    timestamp: datetime
    strength: float = 1.0  # 信号强度 0-1
    source: str = ""  # 信号来源
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Bar:
    """K线数据"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float = 0.0


@dataclass
class StrategyContext:
    """策略上下文"""
    # 账户信息
    cash: float = 100000.0
    positions: Dict[str, int] = field(default_factory=dict)
    
    # 运行状态
    current_time: Optional[datetime] = None
    current_symbol: Optional[str] = None
    
    # 自定义数据
    user_data: Dict[str, Any] = field(default_factory=dict)
    
    # 历史记录
    signals: List[Signal] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)
    
    def get_position(self, symbol: str) -> int:
        """获取持仓数量"""
        return self.positions.get(symbol, 0)
    
    def set_position(self, symbol: str, volume: int):
        """设置持仓"""
        self.positions[symbol] = volume
    
    def add_signal(self, signal: Signal):
        """添加信号"""
        self.signals.append(signal)


class BaseStrategy(ABC):
    """
    策略基类
    
    所有策略必须继承此类，并实现以下方法：
    - on_init: 初始化
    - on_bar: K线处理
    """
    
    def __init__(self, name: str = None, params: Dict[str, Any] = None):
        self.name = name or self.__class__.__name__
        self.params = params or {}
        self.context: Optional[StrategyContext] = None
        self.is_initialized = False
    
    def init(self, context: StrategyContext):
        """初始化策略"""
        self.context = context
        self.on_init(context)
        self.is_initialized = True
    
    @abstractmethod
    def on_init(self, context: StrategyContext):
        """
        策略初始化
        
        在此方法中：
        - 设置参数
        - 初始化指标
        - 订阅数据
        """
        pass
    
    @abstractmethod
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """
        K线处理
        
        每根K线到达时调用
        
        Args:
            bar: K线数据
            
        Returns:
            Signal: 交易信号，无信号返回None
        """
        pass
    
    def on_signal(self, signal: Signal):
        """
        信号处理
        
        当产生信号时调用，可用于信号过滤或记录
        
        Args:
            signal: 交易信号
        """
        pass
    
    def buy(self, symbol: str, price: float, volume: int, **kwargs) -> Signal:
        """生成买入信号"""
        signal = Signal(
            symbol=symbol,
            signal_type=SignalType.BUY,
            price=price,
            volume=volume,
            timestamp=self.context.current_time if self.context else datetime.now(),
            source=self.name,
            metadata=kwargs
        )
        return signal
    
    def sell(self, symbol: str, price: float, volume: int, **kwargs) -> Signal:
        """生成卖出信号"""
        signal = Signal(
            symbol=symbol,
            signal_type=SignalType.SELL,
            price=price,
            volume=volume,
            timestamp=self.context.current_time if self.context else datetime.now(),
            source=self.name,
            metadata=kwargs
        )
        return signal
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """获取参数"""
        return self.params.get(key, default)
    
    def set_param(self, key: str, value: Any):
        """设置参数"""
        self.params[key] = value
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, params={self.params})"
