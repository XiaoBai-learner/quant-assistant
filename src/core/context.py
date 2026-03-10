"""
上下文管理 - 提供全局状态和配置访问
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import threading


@dataclass
class Context:
    """上下文对象"""
    # 运行状态
    mode: str = "backtest"  # backtest, paper, live
    start_time: datetime = field(default_factory=datetime.now)
    
    # 配置
    config: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时数据
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置变量"""
        self.variables[key] = value
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)


class GlobalContext:
    """全局上下文管理器 - 线程安全单例"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._context = Context()
        return cls._instance
    
    @property
    def context(self) -> Context:
        return self._context
    
    def reset(self):
        """重置上下文"""
        self._context = Context()


# 便捷访问函数
def get_context() -> Context:
    """获取全局上下文"""
    return GlobalContext().context
