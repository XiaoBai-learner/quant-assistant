"""
机器学习预测器
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')


class MLPredictor:
    """机器学习预测器"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_cols = None
        self.target_col = None
        self.is_trained = False
    
    def train(
        self,
        data: pd.DataFrame,
        target: str = 'close',
        features: Optional[List[str]] = None,
        model_type: str = 'random_forest',
        test_size: float = 0.2
    ) -> 'MLPredictor':
        """
        训练预测模型
        
        Args:
            data: 训练数据
            target: 目标列名
            features: 特征列列表，None则使用所有数值列
            model_type: 模型类型
            test_size: 测试集比例
            
        Returns:
            self
        """
        self.target_col = target
        
        # 自动选择特征
        if features is None:
            features = data.select_dtypes(include=[np.number]).columns.tolist()
            features = [f for f in features if f != target]
        self.feature_cols = features
        
        # 准备数据
        df = data[features + [target]].dropna()
        X = df[features]
        y = df[target]
        
        # 划分训练测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False
        )
        
        # 标准化
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # 创建模型
        self.model = self._create_model(model_type)
        
        # 训练
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        
        return self
    
    def _create_model(self, model_type: str):
        """创建模型"""
        if model_type == 'random_forest':
            return RandomForestRegressor(n_estimators=100, random_state=42)
        elif model_type == 'gradient_boosting':
            return GradientBoostingRegressor(n_estimators=100, random_state=42)
        elif model_type == 'linear':
            return LinearRegression()
        else:
            return RandomForestRegressor(n_estimators=100, random_state=42)
    
    def predict(self, data: pd.DataFrame) -> pd.Series:
        """
        预测
        
        Args:
            data: 预测数据
            
        Returns:
            预测结果序列
        """
        if not self.is_trained:
            raise ValueError("模型未训练，请先调用train()")
        
        X = data[self.feature_cols].dropna()
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        
        return pd.Series(predictions, index=X.index, name='prediction')
    
    def evaluate(
        self,
        data: pd.DataFrame,
        target: Optional[str] = None
    ) -> Dict[str, float]:
        """
        评估模型
        
        Args:
            data: 测试数据
            target: 目标列名
            
        Returns:
            评估指标字典
        """
        if not self.is_trained:
            raise ValueError("模型未训练")
        
        target = target or self.target_col
        df = data[self.feature_cols + [target]].dropna()
        
        X = df[self.feature_cols]
        y_true = df[target]
        
        X_scaled = self.scaler.transform(X)
        y_pred = self.model.predict(X_scaled)
        
        # 计算指标
        mse = np.mean((y_true - y_pred) ** 2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(y_true - y_pred))
        r2 = 1 - np.sum((y_true - y_pred) ** 2) / np.sum((y_true - y_true.mean()) ** 2)
        
        return {
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2': r2
        }
    
    def feature_importance(self) -> pd.Series:
        """
        获取特征重要性
        
        Returns:
            特征重要性序列
        """
        if not self.is_trained:
            raise ValueError("模型未训练")
        
        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importance = np.abs(self.model.coef_)
        else:
            return pd.Series()
        
        return pd.Series(importance, index=self.feature_cols).sort_values(ascending=False)
