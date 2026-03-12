"""
模型管理模块
提供模型注册、训练、版本管理功能
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import pickle
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ModelStatus(Enum):
    """模型状态"""
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelType(Enum):
    """模型类型"""
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"
    LINEAR = "linear"


@dataclass
class ModelMetadata:
    """模型元数据"""
    model_id: str
    model_name: str
    model_type: ModelType
    description: str = ""
    
    # 训练信息
    train_start_date: datetime = None
    train_end_date: datetime = None
    features: List[str] = field(default_factory=list)
    label_config: Dict[str, Any] = field(default_factory=dict)
    
    # 超参数
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    
    # 评估指标
    metrics: Dict[str, float] = field(default_factory=dict)
    
    # 状态
    status: ModelStatus = ModelStatus.STAGING
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 文件路径
    model_path: str = ""
    pipeline_path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'model_id': self.model_id,
            'model_name': self.model_name,
            'model_type': self.model_type.value,
            'description': self.description,
            'train_start_date': self.train_start_date.isoformat() if self.train_start_date else None,
            'train_end_date': self.train_end_date.isoformat() if self.train_end_date else None,
            'features': self.features,
            'label_config': self.label_config,
            'hyperparameters': self.hyperparameters,
            'metrics': self.metrics,
            'status': self.status.value,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'model_path': self.model_path,
            'pipeline_path': self.pipeline_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        """从字典创建"""
        return cls(
            model_id=data['model_id'],
            model_name=data['model_name'],
            model_type=ModelType(data['model_type']),
            description=data.get('description', ''),
            features=data.get('features', []),
            label_config=data.get('label_config', {}),
            hyperparameters=data.get('hyperparameters', {}),
            metrics=data.get('metrics', {}),
            status=ModelStatus(data.get('status', 'staging')),
            version=data.get('version', '1.0.0'),
            model_path=data.get('model_path', ''),
            pipeline_path=data.get('pipeline_path', ''),
        )


class ModelRegistry:
    """
    模型注册表
    
    管理模型的元数据和版本
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._models: Dict[str, ModelMetadata] = {}
            cls._storage_dir = Path("models")
            cls._storage_dir.mkdir(exist_ok=True)
        return cls._instance
    
    def register(self, metadata: ModelMetadata):
        """注册模型"""
        self._models[metadata.model_id] = metadata
        self._save_metadata(metadata)
        logger.info(f"注册模型: {metadata.model_id}")
    
    def get(self, model_id: str) -> Optional[ModelMetadata]:
        """获取模型元数据"""
        return self._models.get(model_id)
    
    def list_models(
        self,
        model_type: ModelType = None,
        status: ModelStatus = None
    ) -> List[ModelMetadata]:
        """列出模型"""
        models = list(self._models.values())
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if status:
            models = [m for m in models if m.status == status]
        
        return models
    
    def update_status(self, model_id: str, status: ModelStatus):
        """更新模型状态"""
        if model_id in self._models:
            self._models[model_id].status = status
            self._models[model_id].updated_at = datetime.now()
            self._save_metadata(self._models[model_id])
            logger.info(f"更新模型状态: {model_id} -> {status.value}")
    
    def get_production_model(self) -> Optional[ModelMetadata]:
        """获取生产环境模型"""
        production_models = self.list_models(status=ModelStatus.PRODUCTION)
        if production_models:
            # 返回最新的
            return max(production_models, key=lambda m: m.created_at)
        return None
    
    def _save_metadata(self, metadata: ModelMetadata):
        """保存元数据到文件"""
        meta_path = self._storage_dir / f"{metadata.model_id}.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
    
    def load_all(self):
        """从文件加载所有元数据"""
        for meta_file in self._storage_dir.glob("*.json"):
            try:
                with open(meta_file, 'r') as f:
                    data = json.load(f)
                    metadata = ModelMetadata.from_dict(data)
                    self._models[metadata.model_id] = metadata
            except Exception as e:
                logger.error(f"加载模型元数据失败 {meta_file}: {e}")


class ModelTrainer:
    """
    模型训练器
    
    支持多种算法的模型训练
    """
    
    def __init__(self):
        self.registry = ModelRegistry()
    
    def train(
        self,
        X_train: Any,
        y_train: Any,
        X_val: Any = None,
        y_val: Any = None,
        model_type: ModelType = ModelType.LIGHTGBM,
        hyperparameters: Dict[str, Any] = None,
        model_name: str = "model",
        description: str = ""
    ) -> ModelMetadata:
        """
        训练模型
        
        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_val: 验证特征
            y_val: 验证标签
            model_type: 模型类型
            hyperparameters: 超参数
            model_name: 模型名称
            description: 模型描述
            
        Returns:
            ModelMetadata: 模型元数据
        """
        hyperparameters = hyperparameters or {}
        
        # 生成模型ID
        model_id = f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"开始训练模型: {model_id}, 类型: {model_type.value}")
        
        # 根据类型训练模型
        if model_type == ModelType.LIGHTGBM:
            model = self._train_lightgbm(X_train, y_train, X_val, y_val, hyperparameters)
        elif model_type == ModelType.XGBOOST:
            model = self._train_xgboost(X_train, y_train, X_val, y_val, hyperparameters)
        elif model_type == ModelType.RANDOM_FOREST:
            model = self._train_random_forest(X_train, y_train, hyperparameters)
        elif model_type == ModelType.LINEAR:
            model = self._train_linear(X_train, y_train, hyperparameters)
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
        
        # 评估模型
        metrics = self._evaluate_model(model, X_val, y_val) if X_val is not None else {}
        
        # 保存模型
        model_path = self._save_model(model, model_id)
        
        # 创建元数据
        metadata = ModelMetadata(
            model_id=model_id,
            model_name=model_name,
            model_type=model_type,
            description=description,
            hyperparameters=hyperparameters,
            metrics=metrics,
            model_path=str(model_path),
            created_at=datetime.now()
        )
        
        # 注册模型
        self.registry.register(metadata)
        
        logger.info(f"模型训练完成: {model_id}, 指标: {metrics}")
        
        return metadata
    
    def _train_lightgbm(
        self,
        X_train, y_train,
        X_val, y_val,
        params: Dict[str, Any]
    ):
        """训练LightGBM模型"""
        try:
            import lightgbm as lgb
        except ImportError:
            logger.error("LightGBM未安装，使用模拟模型")
            return self._create_mock_model()
        
        # 默认参数
        default_params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1
        }
        default_params.update(params)
        
        # 创建数据集
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data) if X_val is not None else None
        
        # 训练
        model = lgb.train(
            default_params,
            train_data,
            num_boost_round=100,
            valid_sets=[val_data] if val_data else None,
            callbacks=[lgb.early_stopping(10), lgb.log_evaluation(0)] if val_data else None
        )
        
        return model
    
    def _train_xgboost(
        self,
        X_train, y_train,
        X_val, y_val,
        params: Dict[str, Any]
    ):
        """训练XGBoost模型"""
        try:
            import xgboost as xgb
        except ImportError:
            logger.error("XGBoost未安装，使用模拟模型")
            return self._create_mock_model()
        
        default_params = {
            'objective': 'reg:squarederror',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100
        }
        default_params.update(params)
        
        model = xgb.XGBRegressor(**default_params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)] if X_val is not None else None,
            early_stopping_rounds=10,
            verbose=False
        )
        
        return model
    
    def _train_random_forest(
        self,
        X_train, y_train,
        params: Dict[str, Any]
    ):
        """训练随机森林模型"""
        try:
            from sklearn.ensemble import RandomForestRegressor
        except ImportError:
            logger.error("scikit-learn未安装，使用模拟模型")
            return self._create_mock_model()
        
        default_params = {
            'n_estimators': 100,
            'max_depth': 10,
            'random_state': 42
        }
        default_params.update(params)
        
        model = RandomForestRegressor(**default_params)
        model.fit(X_train, y_train)
        
        return model
    
    def _train_linear(
        self,
        X_train, y_train,
        params: Dict[str, Any]
    ):
        """训练线性模型"""
        try:
            from sklearn.linear_model import Ridge
        except ImportError:
            logger.error("scikit-learn未安装，使用模拟模型")
            return self._create_mock_model()
        
        default_params = {'alpha': 1.0}
        default_params.update(params)
        
        model = Ridge(**default_params)
        model.fit(X_train, y_train)
        
        return model
    
    def _create_mock_model(self):
        """创建模拟模型（当依赖未安装时）"""
        class MockModel:
            def predict(self, X):
                import numpy as np
                return np.zeros(len(X))
            
            def feature_importances_(self):
                return []
        
        return MockModel()
    
    def _evaluate_model(self, model, X_val, y_val) -> Dict[str, float]:
        """评估模型"""
        if X_val is None or y_val is None:
            return {}
        
        try:
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        except ImportError:
            return {}
        
        predictions = model.predict(X_val)
        
        metrics = {
            'mse': mean_squared_error(y_val, predictions),
            'mae': mean_absolute_error(y_val, predictions),
            'r2': r2_score(y_val, predictions),
        }
        
        # 计算IC
        import numpy as np
        ic = np.corrcoef(predictions, y_val)[0, 1] if len(predictions) > 1 else 0
        metrics['ic'] = ic
        
        return metrics
    
    def _save_model(self, model, model_id: str) -> Path:
        """保存模型到文件"""
        model_path = self.registry._storage_dir / f"{model_id}.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        return model_path
    
    def load_model(self, model_id: str):
        """从文件加载模型"""
        metadata = self.registry.get(model_id)
        if metadata is None:
            raise ValueError(f"模型不存在: {model_id}")
        
        model_path = Path(metadata.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        return model


# 全局注册表
model_registry = ModelRegistry()
