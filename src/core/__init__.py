"""
核心框架模块
提供事件系统、上下文管理、异常定义、接口定义和依赖注入
"""
from .events import EventBus, EventType, Event
from .context import Context, GlobalContext
from .exceptions import (
    QuantException,
    DataException,
    StrategyException,
    TradingException,
    RiskException
)
from .interfaces import (
    IBroker, IPortfolio, IPerformanceAnalyzer,
    IDataFetcher, IDataStorage, IDataValidator,
    IStrategy, IRiskManager
)
from .container import (
    DIContainer, ServiceProvider,
    get_container, register_instance, register_factory, register_type, resolve, inject
)

__all__ = [
    # 事件系统
    'EventBus', 'EventType', 'Event',
    # 上下文
    'Context', 'GlobalContext',
    # 异常
    'QuantException', 'DataException', 
    'StrategyException', 'TradingException', 'RiskException',
    # 接口
    'IBroker', 'IPortfolio', 'IPerformanceAnalyzer',
    'IDataFetcher', 'IDataStorage', 'IDataValidator',
    'IStrategy', 'IRiskManager',
    # 依赖注入
    'DIContainer', 'ServiceProvider',
    'get_container', 'register_instance', 'register_factory', 'register_type', 'resolve', 'inject'
]
