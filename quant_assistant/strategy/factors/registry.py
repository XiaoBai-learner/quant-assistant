"""
因子注册表
管理所有因子的注册、查询和元数据
"""
from typing import Dict, List, Optional, Type
import json

from .base import Factor, FactorMetadata
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FactorRegistry:
    """
    因子注册表 - 单例模式
    
    管理所有因子的注册和查询
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factors: Dict[str, Type[Factor]] = {}
            cls._instance._metadata: Dict[str, FactorMetadata] = {}
        return cls._instance
    
    def register(self, factor_class: Type[Factor]):
        """
        注册因子类
        
        Args:
            factor_class: 因子类
        """
        # 创建临时实例获取元数据
        try:
            temp_instance = factor_class()
            name = temp_instance.name
            metadata = temp_instance.get_metadata()
            
            self._factors[name] = factor_class
            self._metadata[name] = metadata
            
            logger.debug(f"注册因子: {name}")
        except Exception as e:
            logger.error(f"注册因子失败 {factor_class.__name__}: {e}")
            raise
    
    def get(self, name: str) -> Optional[Type[Factor]]:
        """
        获取因子类
        
        Args:
            name: 因子名称
            
        Returns:
            因子类或None
        """
        return self._factors.get(name)
    
    def get_metadata(self, name: str) -> Optional[FactorMetadata]:
        """获取因子元数据"""
        return self._metadata.get(name)
    
    def list_factors(
        self,
        factor_type: str = None,
        category: str = None
    ) -> List[str]:
        """
        列出因子
        
        Args:
            factor_type: 因子类型筛选
            category: 分类筛选
            
        Returns:
            因子名称列表
        """
        result = []
        for name, metadata in self._metadata.items():
            if factor_type and metadata.factor_type != factor_type:
                continue
            if category and metadata.category != category:
                continue
            result.append(name)
        return result
    
    def list_all(self) -> Dict[str, Dict]:
        """列出所有因子及其元数据"""
        return {
            name: metadata.to_dict()
            for name, metadata in self._metadata.items()
        }
    
    def create_factor(self, name: str, params: Dict = None):
        """
        创建因子实例
        
        Args:
            name: 因子名称
            params: 因子参数
            
        Returns:
            因子实例
        """
        factor_class = self.get(name)
        if factor_class is None:
            raise ValueError(f"未找到因子: {name}")
        
        return factor_class(**(params or {}))
    
    def unregister(self, name: str):
        """注销因子"""
        if name in self._factors:
            del self._factors[name]
            del self._metadata[name]
            logger.debug(f"注销因子: {name}")
    
    def clear(self):
        """清空所有因子"""
        self._factors.clear()
        self._metadata.clear()
        logger.debug("清空所有因子")


# 全局注册表实例
factor_registry = FactorRegistry()
