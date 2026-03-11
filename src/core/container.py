"""
依赖注入容器
提供依赖管理和自动注入功能
"""
from typing import Dict, Type, Any, Optional, Callable
from functools import wraps
import inspect


class DIContainer:
    """
    依赖注入容器
    
    管理组件的注册、解析和生命周期
    """
    
    def __init__(self):
        # 注册的类型映射
        self._registrations: Dict[Type, Callable] = {}
        # 单例实例缓存
        self._singletons: Dict[Type, Any] = {}
        # 配置
        self._config: Dict[str, Any] = {}
    
    def register_instance(self, interface: Type, instance: Any):
        """
        注册实例（单例）
        
        Args:
            interface: 接口类型
            instance: 实例对象
        """
        self._singletons[interface] = instance
    
    def register_factory(
        self,
        interface: Type,
        factory: Callable,
        singleton: bool = False
    ):
        """
        注册工厂函数
        
        Args:
            interface: 接口类型
            factory: 工厂函数
            singleton: 是否单例
        """
        self._registrations[interface] = {
            'factory': factory,
            'singleton': singleton
        }
    
    def register_type(
        self,
        interface: Type,
        implementation: Type,
        singleton: bool = False
    ):
        """
        注册类型映射
        
        Args:
            interface: 接口类型
            implementation: 实现类型
            singleton: 是否单例
        """
        def factory():
            return self.resolve(implementation)
        
        self.register_factory(interface, factory, singleton)
    
    def resolve(self, interface: Type) -> Any:
        """
        解析依赖
        
        Args:
            interface: 接口类型
            
        Returns:
            实例对象
        """
        # 1. 检查单例缓存
        if interface in self._singletons:
            return self._singletons[interface]
        
        # 2. 检查注册
        if interface in self._registrations:
            reg = self._registrations[interface]
            instance = reg['factory']()
            
            if reg['singleton']:
                self._singletons[interface] = instance
            
            return instance
        
        # 3. 尝试自动创建
        return self._create_instance(interface)
    
    def _create_instance(self, cls: Type) -> Any:
        """自动创建实例，解析构造函数参数"""
        # 获取构造函数签名
        sig = inspect.signature(cls.__init__)
        params = list(sig.parameters.items())[1:]  # 跳过self
        
        # 解析参数
        kwargs = {}
        for name, param in params:
            if param.default is not inspect.Parameter.empty:
                # 有默认值，跳过
                continue
            
            # 尝试从配置获取
            if name in self._config:
                kwargs[name] = self._config[name]
            else:
                # 尝试解析类型
                annotation = param.annotation
                if annotation is not inspect.Parameter.empty:
                    try:
                        kwargs[name] = self.resolve(annotation)
                    except Exception:
                        # 解析失败，使用None
                        kwargs[name] = None
        
        return cls(**kwargs)
    
    def set_config(self, key: str, value: Any):
        """设置配置项"""
        self._config[key] = value
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config.get(key, default)
    
    def inject(self, func: Callable) -> Callable:
        """
        装饰器：自动注入依赖
        
        根据函数参数类型自动注入依赖
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数签名
            sig = inspect.signature(func)
            
            # 解析参数
            for name, param in sig.parameters.items():
                if name in kwargs:
                    continue
                
                annotation = param.annotation
                if annotation is not inspect.Parameter.empty:
                    try:
                        kwargs[name] = self.resolve(annotation)
                    except Exception:
                        pass
            
            return func(*args, **kwargs)
        
        return wrapper
    
    def build_provider(self) -> 'ServiceProvider':
        """构建服务提供者"""
        return ServiceProvider(self)


class ServiceProvider:
    """服务提供者，用于向组件提供依赖"""
    
    def __init__(self, container: DIContainer):
        self._container = container
    
    def get_service(self, interface: Type) -> Any:
        """获取服务"""
        return self._container.resolve(interface)


# 全局容器实例
_default_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """获取全局容器实例"""
    global _default_container
    if _default_container is None:
        _default_container = DIContainer()
    return _default_container


def reset_container():
    """重置全局容器"""
    global _default_container
    _default_container = DIContainer()


# 便捷注册函数
def register_instance(interface: Type, instance: Any):
    """注册实例到全局容器"""
    get_container().register_instance(interface, instance)


def register_factory(interface: Type, factory: Callable, singleton: bool = False):
    """注册工厂到全局容器"""
    get_container().register_factory(interface, factory, singleton)


def register_type(interface: Type, implementation: Type, singleton: bool = False):
    """注册类型到全局容器"""
    get_container().register_type(interface, implementation, singleton)


def resolve(interface: Type) -> Any:
    """从全局容器解析依赖"""
    return get_container().resolve(interface)


def inject(func: Callable) -> Callable:
    """全局注入装饰器"""
    return get_container().inject(func)
