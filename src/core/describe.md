# Core 核心模块

## 模块概述

核心模块提供量化交易系统的基础架构支持，包括事件驱动机制和全局上下文管理。采用单例模式设计，确保系统各模块间的高效通信和状态共享。

## 子模块说明

### events.py - 事件系统

**功能**: 实现模块间解耦的发布-订阅通信机制

**核心类**:
- `EventType`: 事件类型枚举
  - 数据事件: DATA_UPDATED, DATA_ERROR
  - 策略事件: SIGNAL_GENERATED, STRATEGY_STARTED, STRATEGY_STOPPED
  - 交易事件: ORDER_SUBMITTED, ORDER_FILLED, ORDER_CANCELLED, ORDER_REJECTED, POSITION_CHANGED
  - 风控事件: RISK_TRIGGERED, RISK_WARNING
  - 系统事件: SYSTEM_STARTED, SYSTEM_STOPPED, SYSTEM_ERROR

- `Event`: 事件对象
  - 属性: type, data, timestamp, source

- `EventBus`: 事件总线（单例）
  - `subscribe(event_type, handler)`: 订阅同步事件
  - `subscribe_async(event_type, handler)`: 订阅异步事件
  - `unsubscribe(event_type, handler)`: 取消订阅
  - `emit(event)`: 发送同步事件
  - `emit_async(event)`: 发送异步事件
  - `clear()`: 清空所有处理器

**使用示例**:
```python
from src.core import event_bus, EventType, Event

# 订阅事件
def on_data_updated(event):
    print(f"数据更新: {event.data}")

event_bus.subscribe(EventType.DATA_UPDATED, on_data_updated)

# 发送事件
event = Event(type=EventType.DATA_UPDATED, data={'symbol': '000001'})
event_bus.emit(event)
```

### context.py - 上下文管理

**功能**: 提供全局状态管理和配置访问

**核心类**:
- `Context`: 上下文对象
  - 属性: mode (backtest/paper/live), start_time, config, variables, metadata
  - `get(key, default)`: 获取变量
  - `set(key, value)`: 设置变量
  - `update_config(config)`: 更新配置

- `GlobalContext`: 全局上下文管理器（线程安全单例）
  - `context`: 获取上下文对象
  - `reset()`: 重置上下文

**便捷函数**:
- `get_context()`: 获取全局上下文

**使用示例**:
```python
from src.core import get_context

ctx = get_context()
ctx.set('current_symbol', '000001')
symbol = ctx.get('current_symbol')
```

## 设计模式

- **单例模式**: EventBus 和 GlobalContext 确保全局唯一实例
- **发布-订阅模式**: 事件系统实现模块间解耦通信
- **线程安全**: GlobalContext 使用锁机制保证线程安全
