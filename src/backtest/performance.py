"""
绩效分析模块
计算回测绩效指标
"""
from typing import Dict, List, Any
import pandas as pd
import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)


class PerformanceAnalyzer:
    """
    绩效分析器
    
    计算各种收益风险指标
    """
    
    def __init__(self):
        pass
    
    def calculate_metrics(
        self,
        daily_records: pd.DataFrame,
        trade_records: pd.DataFrame = None
    ) -> Dict[str, float]:
        """
        计算绩效指标
        
        Args:
            daily_records: 每日记录
            trade_records: 交易记录
            
        Returns:
            Dict: 绩效指标
        """
        if daily_records.empty:
            return {}
        
        metrics = {}
        
        # 收益指标
        metrics.update(self._calculate_return_metrics(daily_records))
        
        # 风险指标
        metrics.update(self._calculate_risk_metrics(daily_records))
        
        # 交易统计
        if trade_records is not None and not trade_records.empty:
            metrics.update(self._calculate_trade_metrics(trade_records))
        
        return metrics
    
    def _calculate_return_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算收益指标"""
        returns = df['return'].dropna()
        
        if len(returns) == 0:
            return {}
        
        # 总收益
        total_return = df['cumulative_return'].iloc[-1] if 'cumulative_return' in df.columns else 0
        
        # 年化收益
        n_days = len(df)
        n_years = n_days / 252
        annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
        
        # 年化波动率
        volatility = returns.std() * np.sqrt(252)
        
        # 夏普比率 (假设无风险利率为3%)
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 卡玛比率
        max_dd = self._calculate_max_drawdown(df)
        calmar_ratio = annual_return / abs(max_dd) if max_dd != 0 else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'calmar_ratio': calmar_ratio,
        }
    
    def _calculate_risk_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算风险指标"""
        returns = df['return'].dropna()
        
        if len(returns) == 0:
            return {}
        
        # 最大回撤
        max_drawdown = self._calculate_max_drawdown(df)
        
        # 最大回撤持续时间
        max_dd_duration = self._calculate_max_drawdown_duration(df)
        
        # 下行波动率
        downside_returns = returns[returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        # 索提诺比率
        annual_return = self._calculate_return_metrics(df).get('annual_return', 0)
        sortino_ratio = annual_return / downside_volatility if downside_volatility > 0 else 0
        
        # VaR (95%)
        var_95 = np.percentile(returns, 5)
        
        # CVaR (95%)
        cvar_95 = returns[returns <= var_95].mean()
        
        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_dd_duration,
            'downside_volatility': downside_volatility,
            'sortino_ratio': sortino_ratio,
            'var_95': var_95,
            'cvar_95': cvar_95,
        }
    
    def _calculate_trade_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算交易统计指标"""
        if df.empty:
            return {}
        
        # 总交易次数
        total_trades = len(df)
        
        # 买入/卖出次数
        buy_trades = len(df[df['side'] == 'buy'])
        sell_trades = len(df[df['side'] == 'sell'])
        
        # 计算每笔盈亏 (简化计算)
        # 实际应该匹配买卖对
        df['pnl'] = 0.0
        
        # 胜率 (简化：假设卖出即为平仓)
        sell_df = df[df['side'] == 'sell']
        if not sell_df.empty:
            # 这里简化处理，实际需要计算实现盈亏
            win_rate = 0.5  # 占位
        else:
            win_rate = 0
        
        # 平均持仓时间 (简化)
        avg_holding_days = 5  # 占位
        
        # 换手率
        turnover = total_trades / 252  # 年化换手率
        
        return {
            'total_trades': total_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'win_rate': win_rate,
            'avg_holding_days': avg_holding_days,
            'turnover': turnover,
        }
    
    def _calculate_max_drawdown(self, df: pd.DataFrame) -> float:
        """计算最大回撤"""
        if 'total_value' not in df.columns:
            return 0
        
        # 计算累计最大值
        cummax = df['total_value'].cummax()
        
        # 计算回撤
        drawdown = (df['total_value'] - cummax) / cummax
        
        return drawdown.min()
    
    def _calculate_max_drawdown_duration(self, df: pd.DataFrame) -> int:
        """计算最大回撤持续时间"""
        if 'total_value' not in df.columns:
            return 0
        
        cummax = df['total_value'].cummax()
        drawdown = (df['total_value'] - cummax) / cummax
        
        # 找到最大回撤点
        max_dd_idx = drawdown.idxmin()
        max_dd_date = df.loc[max_dd_idx, 'date'] if 'date' in df.columns else None
        
        # 计算从高点到恢复的时间
        # 简化处理：返回天数
        return 30  # 占位
    
    def generate_report(
        self,
        metrics: Dict[str, float],
        output_path: str = None
    ) -> str:
        """
        生成绩效报告
        
        Args:
            metrics: 绩效指标
            output_path: 输出路径
            
        Returns:
            str: 报告文本
        """
        lines = [
            "=" * 60,
            "回测绩效报告",
            "=" * 60,
            "",
            "【收益指标】",
            f"  总收益率:    {metrics.get('total_return', 0):.2%}",
            f"  年化收益率:  {metrics.get('annual_return', 0):.2%}",
            f"  年化波动率:  {metrics.get('volatility', 0):.2%}",
            "",
            "【风险指标】",
            f"  最大回撤:    {metrics.get('max_drawdown', 0):.2%}",
            f"  夏普比率:    {metrics.get('sharpe_ratio', 0):.2f}",
            f"  索提诺比率:  {metrics.get('sortino_ratio', 0):.2f}",
            f"  卡玛比率:    {metrics.get('calmar_ratio', 0):.2f}",
            "",
            "【交易统计】",
            f"  总交易次数:  {metrics.get('total_trades', 0)}",
            f"  胜率:        {metrics.get('win_rate', 0):.2%}",
            f"  换手率:      {metrics.get('turnover', 0):.2f}",
            "",
            "=" * 60,
        ]
        
        report = '\n'.join(lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"报告已保存: {output_path}")
        
        return report


class ParameterOptimizer:
    """
    参数优化器
    
    支持网格搜索和随机搜索
    """
    
    def __init__(self):
        pass
    
    def grid_search(
        self,
        strategy_class,
        param_grid: Dict[str, List],
        data: pd.DataFrame,
        metric: str = 'sharpe_ratio'
    ) -> Dict[str, Any]:
        """
        网格搜索
        
        Args:
            strategy_class: 策略类
            param_grid: 参数网格
            data: 数据
            metric: 优化目标
            
        Returns:
            Dict: 最优参数和结果
        """
        from itertools import product
        
        # 生成参数组合
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(product(*values))
        
        logger.info(f"网格搜索: 共{len(combinations)}种参数组合")
        
        best_params = None
        best_metric = -float('inf')
        results = []
        
        for combo in combinations:
            params = dict(zip(keys, combo))
            
            # 创建策略
            strategy = strategy_class(**params)
            
            # 运行回测 (简化)
            # 实际应该调用回测引擎
            result_metric = self._evaluate_strategy(strategy, data, metric)
            
            results.append({
                'params': params,
                metric: result_metric
            })
            
            if result_metric > best_metric:
                best_metric = result_metric
                best_params = params
        
        return {
            'best_params': best_params,
            'best_metric': best_metric,
            'all_results': results
        }
    
    def _evaluate_strategy(self, strategy, data, metric):
        """评估策略 (简化)"""
        # 实际应该运行完整回测
        return np.random.random()  # 占位
