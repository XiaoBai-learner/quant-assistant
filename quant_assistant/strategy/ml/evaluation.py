"""
模型评估模块
提供模型评估、可视化、解释功能
"""
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EvaluationResult:
    """评估结果"""
    metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    predictions: pd.Series
    actuals: pd.Series


class ModelEvaluator:
    """
    模型评估器
    
    提供全面的模型评估功能
    """
    
    def __init__(self):
        pass
    
    def evaluate_regression(
        self,
        y_true: pd.Series,
        y_pred: pd.Series
    ) -> Dict[str, float]:
        """
        评估回归模型
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            Dict: 评估指标
        """
        try:
            from sklearn.metrics import (
                mean_squared_error, mean_absolute_error, r2_score,
                mean_absolute_percentage_error
            )
        except ImportError:
            logger.warning("scikit-learn未安装，使用基础指标")
            return self._basic_metrics(y_true, y_pred)
        
        # 基础指标
        metrics = {
            'mse': mean_squared_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'mae': mean_absolute_error(y_true, y_pred),
            'r2': r2_score(y_true, y_pred),
        }
        
        # MAPE (避免除零)
        y_true_nonzero = y_true[y_true != 0]
        y_pred_nonzero = y_pred[y_true != 0]
        if len(y_true_nonzero) > 0:
            metrics['mape'] = mean_absolute_percentage_error(y_true_nonzero, y_pred_nonzero)
        
        # 信息系数 (IC)
        metrics['ic'] = self._calculate_ic(y_true, y_pred)
        
        # Rank IC
        metrics['rank_ic'] = self._calculate_rank_ic(y_true, y_pred)
        
        return metrics
    
    def evaluate_classification(
        self,
        y_true: pd.Series,
        y_pred: pd.Series,
        y_prob: pd.Series = None
    ) -> Dict[str, float]:
        """
        评估分类模型
        
        Args:
            y_true: 真实标签
            y_pred: 预测标签
            y_prob: 预测概率
            
        Returns:
            Dict: 评估指标
        """
        try:
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score, f1_score,
                confusion_matrix, roc_auc_score, classification_report
            )
        except ImportError:
            logger.warning("scikit-learn未安装，使用基础指标")
            return self._basic_classification_metrics(y_true, y_pred)
        
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_true, y_pred, average='weighted', zero_division=0),
            'f1': f1_score(y_true, y_pred, average='weighted', zero_division=0),
        }
        
        # AUC
        if y_prob is not None:
            try:
                metrics['auc'] = roc_auc_score(y_true, y_prob)
            except:
                pass
        
        return metrics
    
    def _basic_metrics(self, y_true: pd.Series, y_pred: pd.Series) -> Dict[str, float]:
        """基础指标计算"""
        mse = ((y_true - y_pred) ** 2).mean()
        mae = (y_true - y_pred).abs().mean()
        
        # R2
        ss_res = ((y_true - y_pred) ** 2).sum()
        ss_tot = ((y_true - y_true.mean()) ** 2).sum()
        r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0
        
        return {
            'mse': mse,
            'rmse': np.sqrt(mse),
            'mae': mae,
            'r2': r2,
        }
    
    def _basic_classification_metrics(
        self,
        y_true: pd.Series,
        y_pred: pd.Series
    ) -> Dict[str, float]:
        """基础分类指标"""
        correct = (y_true == y_pred).sum()
        total = len(y_true)
        accuracy = correct / total if total > 0 else 0
        
        return {'accuracy': accuracy}
    
    def _calculate_ic(self, y_true: pd.Series, y_pred: pd.Series) -> float:
        """计算信息系数 (Pearson相关系数)"""
        return y_true.corr(y_pred)
    
    def _calculate_rank_ic(self, y_true: pd.Series, y_pred: pd.Series) -> float:
        """计算Rank IC (Spearman相关系数)"""
        return y_true.rank().corr(y_pred.rank())
    
    def calculate_quantile_returns(
        self,
        y_true: pd.Series,
        y_pred: pd.Series,
        n_quantiles: int = 5
    ) -> Dict[int, float]:
        """
        计算分位数收益
        
        将预测值分为n组，计算每组的平均真实收益
        
        Args:
            y_true: 真实收益
            y_pred: 预测收益
            n_quantiles: 分位数数量
            
        Returns:
            Dict: 每组平均收益
        """
        # 创建DataFrame
        df = pd.DataFrame({
            'true': y_true,
            'pred': y_pred
        }).dropna()
        
        # 按预测值分位数分组
        df['quantile'] = pd.qcut(df['pred'], n_quantiles, labels=False, duplicates='drop')
        
        # 计算每组平均收益
        quantile_returns = df.groupby('quantile')['true'].mean().to_dict()
        
        return quantile_returns
    
    def generate_report(
        self,
        y_true: pd.Series,
        y_pred: pd.Series,
        feature_importance: Dict[str, float] = None
    ) -> str:
        """
        生成评估报告
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            feature_importance: 特征重要性
            
        Returns:
            str: 报告文本
        """
        # 计算指标
        metrics = self.evaluate_regression(y_true, y_pred)
        
        # 分位数收益
        quantile_returns = self.calculate_quantile_returns(y_true, y_pred)
        
        # 构建报告
        report_lines = [
            "=" * 60,
            "模型评估报告",
            "=" * 60,
            "",
            "【基础指标】",
            f"  MSE:  {metrics.get('mse', 0):.6f}",
            f"  RMSE: {metrics.get('rmse', 0):.6f}",
            f"  MAE:  {metrics.get('mae', 0):.6f}",
            f"  R²:   {metrics.get('r2', 0):.6f}",
            "",
            "【IC指标】",
            f"  IC:      {metrics.get('ic', 0):.6f}",
            f"  Rank IC: {metrics.get('rank_ic', 0):.6f}",
            "",
            "【分位数收益】",
        ]
        
        for q, ret in sorted(quantile_returns.items()):
            report_lines.append(f"  第{q+1}组: {ret:.4f}")
        
        # 单调性检查
        returns_list = [quantile_returns.get(i, 0) for i in range(len(quantile_returns))]
        if len(returns_list) >= 2:
            monotonic = all(returns_list[i] <= returns_list[i+1] for i in range(len(returns_list)-1))
            report_lines.extend([
                "",
                f"【单调性】: {'通过' if monotonic else '未通过'}",
            ])
        
        # 特征重要性
        if feature_importance:
            report_lines.extend([
                "",
                "【特征重要性 Top 10】",
            ])
            for i, (feature, importance) in enumerate(list(feature_importance.items())[:10]):
                report_lines.append(f"  {i+1}. {feature}: {importance:.4f}")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        
        return '\n'.join(report_lines)
    
    def plot_learning_curve(
        self,
        train_sizes: List[int],
        train_scores: List[float],
        val_scores: List[float],
        output_path: str = None
    ):
        """
        绘制学习曲线
        
        Args:
            train_sizes: 训练样本数
            train_scores: 训练分数
            val_scores: 验证分数
            output_path: 输出路径
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib未安装，无法绘图")
            return
        
        plt.figure(figsize=(10, 6))
        plt.plot(train_sizes, train_scores, 'o-', label='Training Score')
        plt.plot(train_sizes, val_scores, 'o-', label='Validation Score')
        plt.xlabel('Training Examples')
        plt.ylabel('Score')
        plt.title('Learning Curve')
        plt.legend()
        plt.grid(True)
        
        if output_path:
            plt.savefig(output_path)
            logger.info(f"学习曲线已保存: {output_path}")
        else:
            plt.show()
    
    def plot_feature_importance(
        self,
        feature_importance: Dict[str, float],
        top_n: int = 20,
        output_path: str = None
    ):
        """
        绘制特征重要性
        
        Args:
            feature_importance: 特征重要性字典
            top_n: 显示前N个
            output_path: 输出路径
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib未安装，无法绘图")
            return
        
        # 排序
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
        features, importances = zip(*sorted_features)
        
        plt.figure(figsize=(10, 8))
        plt.barh(range(len(features)), importances, align='center')
        plt.yticks(range(len(features)), features)
        plt.xlabel('Importance')
        plt.title(f'Top {top_n} Feature Importance')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path)
            logger.info(f"特征重要性图已保存: {output_path}")
        else:
            plt.show()
    
    def plot_prediction_distribution(
        self,
        y_true: pd.Series,
        y_pred: pd.Series,
        output_path: str = None
    ):
        """
        绘制预测分布
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            output_path: 输出路径
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib未安装，无法绘图")
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # 预测vs真实散点图
        axes[0].scatter(y_true, y_pred, alpha=0.5)
        axes[0].plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--')
        axes[0].set_xlabel('True Values')
        axes[0].set_ylabel('Predicted Values')
        axes[0].set_title('Prediction vs True')
        axes[0].grid(True)
        
        # 残差分布
        residuals = y_true - y_pred
        axes[1].hist(residuals, bins=50, edgecolor='black')
        axes[1].set_xlabel('Residuals')
        axes[1].set_ylabel('Frequency')
        axes[1].set_title('Residual Distribution')
        axes[1].axvline(x=0, color='r', linestyle='--')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path)
            logger.info(f"预测分布图已保存: {output_path}")
        else:
            plt.show()


class CrossValidator:
    """
    交叉验证器
    
    支持时间序列交叉验证
    """
    
    def __init__(self, n_splits: int = 5, test_size: int = 60):
        """
        初始化
        
        Args:
            n_splits: 折数
            test_size: 测试集大小（交易日）
        """
        self.n_splits = n_splits
        self.test_size = test_size
    
    def time_series_split(
        self,
        df: pd.DataFrame,
        date_col: str = 'trade_date'
    ):
        """
        时间序列分割
        
        生成训练集和验证集的索引
        
        Args:
            df: 数据
            date_col: 日期列
            
        Yields:
            Tuple: (train_idx, val_idx)
        """
        # 按日期排序
        df_sorted = df.sort_values(date_col)
        
        # 获取唯一日期
        unique_dates = df_sorted[date_col].unique()
        n_dates = len(unique_dates)
        
        # 计算每折的大小
        fold_size = (n_dates - self.test_size) // self.n_splits
        
        for i in range(self.n_splits):
            # 训练集结束日期
            train_end_idx = (i + 1) * fold_size
            # 验证集结束日期
            val_end_idx = train_end_idx + self.test_size
            
            if val_end_idx > n_dates:
                break
            
            # 获取日期范围
            train_dates = unique_dates[:train_end_idx]
            val_dates = unique_dates[train_end_idx:val_end_idx]
            
            # 获取索引
            train_idx = df_sorted[df_sorted[date_col].isin(train_dates)].index
            val_idx = df_sorted[df_sorted[date_col].isin(val_dates)].index
            
            yield train_idx, val_idx
