"""
预测服务模块
提供批量预测和实时预测功能
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import pickle

from .models import ModelRegistry, model_registry, ModelStatus
from .features import FeaturePipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Predictor:
    """
    预测器
    
    提供模型预测服务
    """
    
    def __init__(self, model_id: str = None):
        """
        初始化预测器
        
        Args:
            model_id: 模型ID，None表示使用生产环境模型
        """
        self.registry = model_registry
        self.model = None
        self.metadata = None
        self.pipeline = None
        
        if model_id:
            self.load_model(model_id)
        else:
            self.load_production_model()
    
    def load_model(self, model_id: str):
        """加载指定模型"""
        self.metadata = self.registry.get(model_id)
        if self.metadata is None:
            raise ValueError(f"模型不存在: {model_id}")
        
        # 加载模型文件
        model_path = Path(self.metadata.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        logger.info(f"加载模型: {model_id}")
    
    def load_production_model(self):
        """加载生产环境模型"""
        self.metadata = self.registry.get_production_model()
        if self.metadata is None:
            logger.warning("未找到生产环境模型")
            return
        
        self.load_model(self.metadata.model_id)
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        批量预测
        
        Args:
            X: 特征矩阵
            
        Returns:
            np.ndarray: 预测值
        """
        if self.model is None:
            raise RuntimeError("模型未加载")
        
        # 应用特征处理
        if self.pipeline:
            X = self.pipeline.transform(X)
        
        # 预测
        predictions = self.model.predict(X)
        
        return predictions
    
    def predict_single(
        self,
        features: Dict[str, float]
    ) -> float:
        """
        单样本预测
        
        Args:
            features: 特征字典
            
        Returns:
            float: 预测值
        """
        # 转换为DataFrame
        X = pd.DataFrame([features])
        
        # 预测
        prediction = self.predict(X)[0]
        
        return prediction
    
    def predict_batch(
        self,
        factor_df: pd.DataFrame,
        feature_list: List[str] = None
    ) -> pd.DataFrame:
        """
        批量预测（对多股票）
        
        Args:
            factor_df: 因子数据
            feature_list: 特征列表
            
        Returns:
            DataFrame: 预测结果
        """
        if self.model is None:
            raise RuntimeError("模型未加载")
        
        # 选择特征
        if feature_list:
            X = factor_df[feature_list]
        else:
            X = factor_df
        
        # 预测
        predictions = self.predict(X)
        
        # 构建结果
        result = factor_df.copy()
        result['prediction'] = predictions
        result['model_id'] = self.metadata.model_id if self.metadata else None
        result['predict_time'] = datetime.now()
        
        return result
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if self.model is None:
            return {}
        
        # 尝试获取特征重要性
        try:
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
            elif hasattr(self.model, 'feature_importance'):
                importances = self.model.feature_importance()
            else:
                return {}
            
            # 获取特征名
            if self.metadata and self.metadata.features:
                feature_names = self.metadata.features
            else:
                feature_names = [f"feature_{i}" for i in range(len(importances))]
            
            # 构建字典
            importance_dict = dict(zip(feature_names, importances))
            
            # 按重要性排序
            importance_dict = dict(sorted(importance_dict.items(), 
                                         key=lambda x: x[1], reverse=True))
            
            return importance_dict
        except Exception as e:
            logger.error(f"获取特征重要性失败: {e}")
            return {}
    
    def save_predictions(
        self,
        predictions: pd.DataFrame,
        output_path: str = None
    ):
        """
        保存预测结果
        
        Args:
            predictions: 预测结果DataFrame
            output_path: 输出路径
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"predictions_{timestamp}.csv"
        
        predictions.to_csv(output_path, index=False)
        logger.info(f"预测结果已保存: {output_path}")


class PredictionService:
    """
    预测服务
    
    提供REST API风格的预测接口
    """
    
    def __init__(self):
        self.registry = model_registry
        self._cache = {}
    
    def predict(
        self,
        symbol: str,
        features: Dict[str, float],
        model_id: str = None
    ) -> Dict[str, Any]:
        """
        预测接口
        
        Args:
            symbol: 股票代码
            features: 特征字典
            model_id: 模型ID，None使用生产环境模型
            
        Returns:
            Dict: 预测结果
        """
        # 创建预测器
        predictor = Predictor(model_id)
        
        # 预测
        prediction = predictor.predict_single(features)
        
        # 构建结果
        result = {
            'symbol': symbol,
            'prediction': float(prediction),
            'model_id': predictor.metadata.model_id if predictor.metadata else None,
            'timestamp': datetime.now().isoformat(),
        }
        
        return result
    
    def predict_batch(
        self,
        symbols: List[str],
        features_df: pd.DataFrame,
        model_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        批量预测接口
        
        Args:
            symbols: 股票代码列表
            features_df: 特征DataFrame
            model_id: 模型ID
            
        Returns:
            List[Dict]: 预测结果列表
        """
        predictor = Predictor(model_id)
        
        # 批量预测
        predictions = predictor.predict(features_df)
        
        # 构建结果
        results = []
        for i, (symbol, pred) in enumerate(zip(symbols, predictions)):
            results.append({
                'symbol': symbol,
                'prediction': float(pred),
                'model_id': predictor.metadata.model_id if predictor.metadata else None,
                'timestamp': datetime.now().isoformat(),
            })
        
        return results
    
    def get_model_info(self, model_id: str = None) -> Dict[str, Any]:
        """获取模型信息"""
        if model_id:
            metadata = self.registry.get(model_id)
        else:
            metadata = self.registry.get_production_model()
        
        if metadata is None:
            return {}
        
        return {
            'model_id': metadata.model_id,
            'model_name': metadata.model_name,
            'model_type': metadata.model_type.value,
            'status': metadata.status.value,
            'metrics': metadata.metrics,
            'created_at': metadata.created_at.isoformat(),
        }
    
    def list_models(self) -> List[Dict[str, Any]]:
        """列出所有模型"""
        models = self.registry.list_models()
        return [m.to_dict() for m in models]
