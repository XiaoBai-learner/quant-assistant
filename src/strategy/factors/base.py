"""
因子基类定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd


@dataclass
class FactorResult:
    """因子计算结果"""
    name: str
    values: pd.Series
    params: Dict[str, Any]
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FactorMetadata:
    """因子元数据"""
    name: str
    description: str
    formula: str
    dependencies: List[str]
    frequency: str  # 'D', 'W', 'M'
    factor_type: str  # 'technical', 'fundamental', 'sentiment'
    category: str
    author: str = "system"
    version: str = "1.0.0"
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'description': self.description,
            'formula': self.formula,
            'dependencies': self.dependencies,
            'frequency': self.frequency,
            'factor_type': self.factor_type,
            'category': self.category,
            'author': self.author,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Factor(ABC):
    """
    因子基类
    
    所有因子必须继承此类
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        params: Dict[str, Any] = None
    ):
        self.name = name
        self.description = description
        self.params = params or {}
        self._validate_params()
    
    @abstractmethod
    def _validate_params(self):
        """验证参数"""
        pass
    
    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> FactorResult:
        """
        计算因子值
        
        Args:
            df: 行情数据 DataFrame
            
        Returns:
            FactorResult: 因子计算结果
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> FactorMetadata:
        """获取因子元数据"""
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name}, params={self.params})"


class TechnicalFactor(Factor):
    """技术指标因子基类"""
    
    def get_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            name=self.name,
            description=self.description,
            formula=self._get_formula(),
            dependencies=self._get_dependencies(),
            frequency='D',
            factor_type='technical',
            category=self._get_category()
        )
    
    @abstractmethod
    def _get_formula(self) -> str:
        """获取公式描述"""
        pass
    
    @abstractmethod
    def _get_dependencies(self) -> List[str]:
        """获取依赖字段"""
        pass
    
    @abstractmethod
    def _get_category(self) -> str:
        """获取分类"""
        pass
