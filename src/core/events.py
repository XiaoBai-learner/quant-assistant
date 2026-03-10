"""
事件系统 - 实现模块间解耦通信
"""
from enum import Enum, auto
from typing import Dict, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from collections import defaultdict


class EventType(Enum):
    """事件类型定义"""
    # 数据事件
    DATA_UPDATED = auto()
    DATA_ERROR = auto()
    
    # 策略事件
    SIGNAL_GENERATED = auto()
    STRATEGY_STARTED = auto()
    STRATEGY_STOPPED = auto()
    
    # 交易事件
    ORDER_SUBMITTED = auto()
    ORDER_FILLED = auto()
    ORDER_CANCELLED = auto()
    ORDER_REJECTED = auto()
    POSITION_CHANGED = auto()
    
    # 风控事件
    RISK_TRIGGERED = auto()
    RISK_WARNING = auto()
    
    # 系统事件
    SYSTEM_STARTED = auto()
    SYSTEM_STOPPED = auto()
    SYSTEM_ERROR = auto()


@dataclass
class Event:
    """事件对象"""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


class EventBus:
    """事件总线 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = defaultdict(list)
            cls._instance._async_handlers = defaultdict(list)
        return cls._instance
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """订阅事件"""
        self._handlers[event_type].append(handler)
    
    def subscribe_async(self, event_type: EventType, handler: Callable):
        """订阅异步事件"""
        self._async_handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """取消订阅"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
    
    def emit(self, event: Event):
        """发送事件（同步）"""
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"事件处理错误: {e}")
    
    async def emit_async(self, event: Event):
        """发送事件（异步）"""
        # 处理同步处理器
        self.emit(event)
        
        # 处理异步处理器
        async_handlers = self._async_handlers.get(event.type, [])
        tasks = []
        for handler in async_handlers:
            tasks.append(asyncio.create_task(handler(event)))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def clear(self):
        """清空所有处理器"""
        self._handlers.clear()
        self._async_handlers.clear()


# 全局事件总线实例
event_bus = EventBus()
