"""
特征工程模块
提供特征筛选、处理、标准化功能
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FeatureConfig:
    """特征配置"""
    # 缺失值处理
    missing_threshold: float = 0.3  # 缺失率阈值
    fill_strategy: str = 'median'  # 'mean', 'median', 'ffill', 'zero'
    
    # 方差过滤
    variance_threshold: float = 0.01
    
    # 相关性过滤
    corr_threshold: float = 0.95
    
    # 标准化
    standardize: bool = True
    scaler_type: str = 'zscore'  # 'zscore', 'minmax', 'robust'
    
    # IC预筛选
    ic_filter: bool = False
    ic_top_k: int = 50


class FeatureTransformer(ABC):
    """特征转换器基类"""
    
    @abstractmethod
    def fit(self, df: pd.DataFrame):
        """拟合转换器"""
        pass
    
    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """转换数据"""
        pass
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """拟合并转换"""
        self.fit(df)
        return self.transform(df)


class MissingValueHandler(FeatureTransformer):
    """缺失值处理器"""
    
    def __init__(self, strategy: str = 'median', threshold: float = 0.3):
        self.strategy = strategy
        self.threshold = threshold
        self.fill_values = {}
        self.dropped_columns = []
    
    def fit(self, df: pd.DataFrame):
        """计算填充值"""
        # 删除缺失率过高的列
        missing_ratio = df.isnull().mean()
        self.dropped_columns = missing_ratio[missing_ratio > self.threshold].index.tolist()
        
        df_clean = df.drop(columns=self.dropped_columns, errors='ignore')
        
        # 计算填充值
        for col in df_clean.columns:
            if df_clean[col].isnull().any():
                if self.strategy == 'mean':
                    self.fill_values[col] = df_clean[col].mean()
                elif self.strategy == 'median':
                    self.fill_values[col] = df_clean[col].median()
                elif self.strategy == 'zero':
                    self.fill_values[col] = 0
                elif self.strategy == 'ffill':
                    self.fill_values[col] = df_clean[col].ffill().iloc[-1]
                else:
                    self.fill_values[col] = 0
        
        logger.info(f"缺失值处理: 删除{len(self.dropped_columns)}列, 填充{len(self.fill_values)}列")
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """填充缺失值"""
        df = df.drop(columns=self.dropped_columns, errors='ignore')
        
        for col, value in self.fill_values.items():
            if col in df.columns:
                df[col] = df[col].fillna(value)
        
        return df


class VarianceFilter(FeatureTransformer):
    """方差过滤器"""
    
    def __init__(self, threshold: float = 0.01):
        self.threshold = threshold
        self.dropped_columns = []
    
    def fit(self, df: pd.DataFrame):
        """识别低方差特征"""
        variances = df.var()
        self.dropped_columns = variances[variances < self.threshold].index.tolist()
        logger.info(f"方差过滤: 删除{len(self.dropped_columns)}个低方差特征")
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """删除低方差特征"""
        return df.drop(columns=self.dropped_columns, errors='ignore')


class CorrelationFilter(FeatureTransformer):
    """相关性过滤器"""
    
    def __init__(self, threshold: float = 0.95):
        self.threshold = threshold
        self.dropped_columns = []
    
    def fit(self, df: pd.DataFrame):
        """识别高相关特征对"""
        corr_matrix = df.corr().abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        
        # 找出高相关的特征对
        to_drop = set()
        for col in upper.columns:
            high_corr = upper[col][upper[col] > self.threshold].index.tolist()
            to_drop.update(high_corr)
        
        self.dropped_columns = list(to_drop)
        logger.info(f"相关性过滤: 删除{len(self.dropped_columns)}个高相关特征")
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """删除高相关特征"""
        return df.drop(columns=self.dropped_columns, errors='ignore')


class StandardScaler(FeatureTransformer):
    """标准化处理器"""
    
    def __init__(self, scaler_type: str = 'zscore'):
        self.scaler_type = scaler_type
        self.params = {}
    
    def fit(self, df: pd.DataFrame):
        """计算标准化参数"""
        for col in df.columns:
            if self.scaler_type == 'zscore':
                self.params[col] = {
                    'mean': df[col].mean(),
                    'std': df[col].std()
                }
            elif self.scaler_type == 'minmax':
                self.params[col] = {
                    'min': df[col].min(),
                    'max': df[col].max()
                }
            elif self.scaler_type == 'robust':
                self.params[col] = {
                    'median': df[col].median(),
                    'iqr': df[col].quantile(0.75) - df[col].quantile(0.25)
                }
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化数据"""
        df_scaled = df.copy()
        
        for col in df.columns:
            if col not in self.params:
                continue
            
            params = self.params[col]
            
            if self.scaler_type == 'zscore':
                df_scaled[col] = (df[col] - params['mean']) / (params['std'] + 1e-8)
            elif self.scaler_type == 'minmax':
                range_val = params['max'] - params['min']
                df_scaled[col] = (df[col] - params['min']) / (range_val + 1e-8)
            elif self.scaler_type == 'robust':
                df_scaled[col] = (df[col] - params['median']) / (params['iqr'] + 1e-8)
        
        return df_scaled


class FeaturePipeline:
    """特征处理流水线"""
    
    def __init__(self, config: FeatureConfig = None):
        self.config = config or FeatureConfig()
        self.transformers: List[FeatureTransformer] = []
        self._build_pipeline()
    
    def _build_pipeline(self):
        """构建处理流程"""
        self.transformers = [
            MissingValueHandler(
                strategy=self.config.fill_strategy,
                threshold=self.config.missing_threshold
            ),
            VarianceFilter(threshold=self.config.variance_threshold),
            CorrelationFilter(threshold=self.config.corr_threshold),
        ]
        
        if self.config.standardize:
            self.transformers.append(
                StandardScaler(scaler_type=self.config.scaler_type)
            )
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """拟合并转换"""
        for transformer in self.transformers:
            df = transformer.fit_transform(df)
        return df
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """转换新数据"""
        for transformer in self.transformers:
            df = transformer.transform(df)
        return df
    
    def get_feature_names(self) -> List[str]:
        """获取处理后的特征名"""
        # 返回最后转换器的列名
        return []


class FeatureEngineer:
    """
    特征工程师
    
    负责从原始数据构建特征矩阵
    """
    
    def __init__(self, config: FeatureConfig = None):
        self.config = config or FeatureConfig()
        self.pipeline = FeaturePipeline(self.config)
    
    def build_features(
        self,
        factor_df: pd.DataFrame,
        feature_list: List[str] = None
    ) -> pd.DataFrame:
        """
        构建特征矩阵
        
        Args:
            factor_df: 因子数据，格式为宽表 (index=[symbol, date], columns=factors)
            feature_list: 特征列表，None表示使用所有
            
        Returns:
            DataFrame: 特征矩阵
        """
        # 选择特征
        if feature_list:
            available_features = [f for f in feature_list if f in factor_df.columns]
            X = factor_df[available_features].copy()
        else:
            X = factor_df.copy()
        
        logger.info(f"原始特征数: {X.shape[1]}")
        
        # 应用特征处理流水线
        X_processed = self.pipeline.fit_transform(X)
        
        logger.info(f"处理后特征数: {X_processed.shape[1]}")
        
        return X_processed
    
    def build_labels(
        self,
        price_df: pd.DataFrame,
        horizon: int = 5,
        label_type: str = 'regression',
        threshold: float = 0.0
    ) -> pd.Series:
        """
        构建标签
        
        Args:
            price_df: 价格数据 (DataFrame with 'close' column)
            horizon: 预测周期
            label_type: 'regression' 或 'classification'
            threshold: 分类阈值
            
        Returns:
            Series: 标签
        """
        close = price_df['close']
        
        if label_type == 'regression':
            # 未来收益率 (对数收益率)
            future_close = close.shift(-horizon)
            label = np.log(future_close / close)
        elif label_type == 'classification':
            # 分类标签
            future_return = close.pct_change(horizon).shift(-horizon)
            if threshold == 0:
                label = (future_return > 0).astype(int)
            else:
                # 三分类
                label = pd.Series(1, index=close.index)  # 平
                label[future_return > threshold] = 2  # 涨
                label[future_return < -threshold] = 0  # 跌
        else:
            raise ValueError(f"不支持的标签类型: {label_type}")
        
        return label
    
    def align_features_labels(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        对齐特征和标签
        
        删除特征和标签中任一为NaN的样本
        """
        # 合并
        combined = pd.concat([X, y.rename('label')], axis=1)
        
        # 删除NaN
        combined_clean = combined.dropna()
        
        # 分离
        X_aligned = combined_clean.drop(columns=['label'])
        y_aligned = combined_clean['label']
        
        logger.info(f"对齐后样本数: {len(X_aligned)}")
        
        return X_aligned, y_aligned
    
    def calculate_ic(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict[str, float]:
        """
        计算信息系数 (IC)
        
        Args:
            X: 特征矩阵
            y: 标签
            
        Returns:
            Dict: 每个特征的IC值
        """
        ic_values = {}
        
        for col in X.columns:
            # 计算Pearson相关系数
            corr = X[col].corr(y)
            ic_values[col] = corr
        
        # 按IC绝对值排序
        ic_values = dict(sorted(ic_values.items(), key=lambda x: abs(x[1]), reverse=True))
        
        return ic_values
    
    def select_by_ic(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        top_k: int = 50
    ) -> pd.DataFrame:
        """
        根据IC选择Top K特征
        
        Args:
            X: 特征矩阵
            y: 标签
            top_k: 选择数量
            
        Returns:
            DataFrame: 筛选后的特征
        """
        ic_values = self.calculate_ic(X, y)
        top_features = list(ic_values.keys())[:top_k]
        
        logger.info(f"IC筛选: 保留Top {top_k}特征")
        
        return X[top_features]
