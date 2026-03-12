"""
策略参数优化器
支持网格搜索和贝叶斯优化
"""
from typing import Dict, List, Callable, Type, Any, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging

from src.strategy.base import BaseStrategy
from src.backtest.engine import BacktestEngine, BacktestConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OptimizationResult:
    """优化结果"""
    best_params: Dict[str, Any]
    best_score: float
    all_results: pd.DataFrame
    optimization_time: float
    
    def to_dict(self) -> Dict:
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'optimization_time': self.optimization_time,
            'total_trials': len(self.all_results)
        }


class StrategyOptimizer:
    """
    策略参数优化器
    
    支持网格搜索和随机搜索
    """
    
    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        config: BacktestConfig,
        objective: str = 'sharpe_ratio'
    ):
        """
        初始化优化器
        
        Args:
            strategy_class: 策略类
            data: 回测数据
            config: 回测配置
            objective: 优化目标 ('sharpe_ratio', 'total_return', 'calmar_ratio')
        """
        self.strategy_class = strategy_class
        self.data = data
        self.config = config
        self.objective = objective
        
        # 有效的优化目标
        self.valid_objectives = [
            'sharpe_ratio',
            'total_return',
            'annual_return',
            'calmar_ratio',
            'sortino_ratio',
            'win_rate'
        ]
        
        if objective not in self.valid_objectives:
            raise ValueError(f"无效的优化目标: {objective}，可选: {self.valid_objectives}")
    
    def grid_search(
        self,
        param_grid: Dict[str, List],
        n_jobs: int = 1,
        verbose: bool = True
    ) -> OptimizationResult:
        """
        网格搜索
        
        Args:
            param_grid: 参数网格，如 {'fast_period': [5, 10, 20], 'slow_period': [20, 30, 60]}
            n_jobs: 并行进程数
            verbose: 是否打印进度
            
        Returns:
            OptimizationResult: 优化结果
        """
        start_time = datetime.now()
        
        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(itertools.product(*param_values))
        
        total = len(param_combinations)
        logger.info(f"开始网格搜索: 共 {total} 组参数")
        
        results = []
        
        if n_jobs > 1:
            # 并行搜索
            results = self._parallel_search(param_combinations, param_names, n_jobs, verbose)
        else:
            # 串行搜索
            results = self._serial_search(param_combinations, param_names, verbose)
        
        # 整理结果
        df_results = pd.DataFrame(results)
        
        # 找到最佳参数
        best_idx = df_results[self.objective].idxmax()
        best_params = df_results.loc[best_idx, param_names].to_dict()
        best_score = df_results.loc[best_idx, self.objective]
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"网格搜索完成: 最佳 {self.objective} = {best_score:.4f}")
        logger.info(f"最佳参数: {best_params}")
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=df_results,
            optimization_time=elapsed
        )
    
    def random_search(
        self,
        param_distributions: Dict[str, tuple],
        n_trials: int = 100,
        n_jobs: int = 1,
        verbose: bool = True
    ) -> OptimizationResult:
        """
        随机搜索
        
        Args:
            param_distributions: 参数分布，如 {'fast_period': (5, 20), 'slow_period': (20, 60)}
            n_trials: 搜索次数
            n_jobs: 并行进程数
            verbose: 是否打印进度
            
        Returns:
            OptimizationResult: 优化结果
        """
        start_time = datetime.now()
        
        logger.info(f"开始随机搜索: {n_trials} 次试验")
        
        # 生成随机参数组合
        param_combinations = []
        for _ in range(n_trials):
            params = {}
            for name, (low, high) in param_distributions.items():
                if isinstance(low, int):
                    params[name] = np.random.randint(low, high + 1)
                else:
                    params[name] = np.random.uniform(low, high)
            param_combinations.append(list(params.values()))
        
        param_names = list(param_distributions.keys())
        
        results = []
        if n_jobs > 1:
            results = self._parallel_search(param_combinations, param_names, n_jobs, verbose)
        else:
            results = self._serial_search(param_combinations, param_names, verbose)
        
        df_results = pd.DataFrame(results)
        
        best_idx = df_results[self.objective].idxmax()
        best_params = df_results.loc[best_idx, param_names].to_dict()
        best_score = df_results.loc[best_idx, self.objective]
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"随机搜索完成: 最佳 {self.objective} = {best_score:.4f}")
        logger.info(f"最佳参数: {best_params}")
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=df_results,
            optimization_time=elapsed
        )
    
    def _serial_search(
        self,
        param_combinations: List[List],
        param_names: List[str],
        verbose: bool
    ) -> List[Dict]:
        """串行搜索"""
        results = []
        total = len(param_combinations)
        
        for i, param_values in enumerate(param_combinations):
            if verbose and (i + 1) % 10 == 0:
                logger.info(f"进度: {i + 1}/{total}")
            
            params = dict(zip(param_names, param_values))
            result = self._evaluate_params(params)
            results.append(result)
        
        return results
    
    def _parallel_search(
        self,
        param_combinations: List[List],
        param_names: List[str],
        n_jobs: int,
        verbose: bool
    ) -> List[Dict]:
        """并行搜索"""
        results = []
        total = len(param_combinations)
        
        with ProcessPoolExecutor(max_workers=n_jobs) as executor:
            futures = []
            for param_values in param_combinations:
                params = dict(zip(param_names, param_values))
                future = executor.submit(self._evaluate_params, params)
                futures.append(future)
            
            for i, future in enumerate(as_completed(futures)):
                if verbose and (i + 1) % 10 == 0:
                    logger.info(f"进度: {i + 1}/{total}")
                
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"评估参数失败: {e}")
        
        return results
    
    def _evaluate_params(self, params: Dict[str, Any]) -> Dict:
        """评估一组参数"""
        try:
            # 创建策略实例
            strategy = self.strategy_class(**params)
            
            # 创建回测引擎
            engine = BacktestEngine(self.config)
            engine.set_strategy(strategy)
            
            # 加载数据
            symbol = self.data['symbol'].iloc[0] if 'symbol' in self.data.columns else 'unknown'
            engine.load_data(symbol, self.data)
            
            # 运行回测
            result = engine.run()
            
            # 提取指标
            metrics = result.get('metrics', {})
            
            # 构建结果
            evaluation = {
                **params,
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'total_return': metrics.get('total_return', 0),
                'annual_return': metrics.get('annual_return', 0),
                'calmar_ratio': metrics.get('calmar_ratio', 0),
                'sortino_ratio': metrics.get('sortino_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'win_rate': metrics.get('win_rate', 0),
            }
            
            return evaluation
            
        except Exception as e:
            logger.error(f"参数评估失败 {params}: {e}")
            return {**params, **{k: 0 for k in self.valid_objectives}}


class WalkForwardOptimizer:
    """
    前向优化器
    
    使用滚动窗口进行参数优化，避免过拟合
    """
    
    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        config: BacktestConfig,
        train_size: int = 252,
        test_size: int = 63,
        objective: str = 'sharpe_ratio'
    ):
        """
        初始化
        
        Args:
            strategy_class: 策略类
            data: 数据
            config: 回测配置
            train_size: 训练窗口大小（交易日）
            test_size: 测试窗口大小（交易日）
            objective: 优化目标
        """
        self.strategy_class = strategy_class
        self.data = data
        self.config = config
        self.train_size = train_size
        self.test_size = test_size
        self.objective = objective
    
    def optimize(
        self,
        param_grid: Dict[str, List],
        n_splits: int = 5
    ) -> Dict:
        """
        前向优化
        
        Args:
            param_grid: 参数网格
            n_splits: 分割次数
            
        Returns:
            Dict: 包含各期结果和综合结果
        """
        results = []
        
        # 分割数据
        total_days = len(self.data)
        window_size = self.train_size + self.test_size
        
        for i in range(n_splits):
            start_idx = i * self.test_size
            end_idx = start_idx + window_size
            
            if end_idx > total_days:
                break
            
            train_data = self.data.iloc[start_idx:start_idx + self.train_size]
            test_data = self.data.iloc[start_idx + self.train_size:end_idx]
            
            logger.info(f"前向优化第 {i+1}/{n_splits} 期")
            
            # 在训练集上优化
            optimizer = StrategyOptimizer(
                self.strategy_class,
                train_data,
                self.config,
                self.objective
            )
            
            opt_result = optimizer.grid_search(param_grid, n_jobs=1, verbose=False)
            
            # 在测试集上验证
            test_score = self._validate(opt_result.best_params, test_data)
            
            results.append({
                'period': i + 1,
                'best_params': opt_result.best_params,
                'train_score': opt_result.best_score,
                'test_score': test_score
            })
        
        # 计算平均测试得分
        avg_test_score = np.mean([r['test_score'] for r in results])
        
        # 选择最稳定的参数
        # 这里简化处理，选择平均得分最高的
        best_period = max(results, key=lambda x: x['test_score'])
        
        return {
            'period_results': results,
            'best_params': best_period['best_params'],
            'avg_test_score': avg_test_score,
            'n_splits': len(results)
        }
    
    def _validate(self, params: Dict, test_data: pd.DataFrame) -> float:
        """验证参数"""
        try:
            strategy = self.strategy_class(**params)
            engine = BacktestEngine(self.config)
            engine.set_strategy(strategy)
            
            symbol = test_data['symbol'].iloc[0] if 'symbol' in test_data.columns else 'unknown'
            engine.load_data(symbol, test_data)
            
            result = engine.run()
            metrics = result.get('metrics', {})
            
            return metrics.get(self.objective, 0)
        except Exception as e:
            logger.error(f"验证失败: {e}")
            return 0
