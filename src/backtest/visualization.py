"""
回测可视化模块
生成图表和报告
"""
from typing import Dict, Any, List
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class BacktestVisualizer:
    """
    回测可视化
    
    生成回测结果图表
    """
    
    def __init__(self):
        pass
    
    def plot_equity_curve(
        self,
        daily_records: pd.DataFrame,
        benchmark: pd.Series = None,
        output_path: str = None
    ):
        """
        绘制资金曲线
        
        Args:
            daily_records: 每日记录
            benchmark: 基准收益
            output_path: 输出路径
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib未安装")
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 策略净值
        if 'total_value' in daily_records.columns:
            equity = daily_records['total_value'] / daily_records['total_value'].iloc[0]
            ax.plot(daily_records['date'], equity, label='Strategy', linewidth=2)
        
        # 基准
        if benchmark is not None:
            benchmark_normalized = benchmark / benchmark.iloc[0]
            ax.plot(benchmark.index, benchmark_normalized, label='Benchmark', alpha=0.7)
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Normalized Value')
        ax.set_title('Equity Curve')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"资金曲线已保存: {output_path}")
        else:
            plt.show()
    
    def plot_drawdown(
        self,
        daily_records: pd.DataFrame,
        output_path: str = None
    ):
        """
        绘制回撤图
        
        Args:
            daily_records: 每日记录
            output_path: 输出路径
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib未安装")
            return
        
        if 'total_value' not in daily_records.columns:
            return
        
        # 计算回撤
        cummax = daily_records['total_value'].cummax()
        drawdown = (daily_records['total_value'] - cummax) / cummax
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.fill_between(daily_records['date'], drawdown, 0, alpha=0.5, color='red')
        ax.plot(daily_records['date'], drawdown, color='darkred', linewidth=1)
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Drawdown')
        ax.set_title('Drawdown Curve')
        ax.grid(True, alpha=0.3)
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"回撤图已保存: {output_path}")
        else:
            plt.show()
    
    def plot_monthly_returns(
        self,
        daily_records: pd.DataFrame,
        output_path: str = None
    ):
        """
        绘制月度收益热力图
        
        Args:
            daily_records: 每日记录
            output_path: 输出路径
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError:
            logger.warning("matplotlib或seaborn未安装")
            return
        
        if 'return' not in daily_records.columns:
            return
        
        # 计算月度收益
        daily_records['year'] = pd.to_datetime(daily_records['date']).dt.year
        daily_records['month'] = pd.to_datetime(daily_records['date']).dt.month
        
        monthly_returns = daily_records.groupby(['year', 'month'])['return'].apply(
            lambda x: (1 + x).prod() - 1
        ).unstack()
        
        fig, ax = plt.subplots(figsize=(12, 8))
        sns.heatmap(monthly_returns, annot=True, fmt='.2%', cmap='RdYlGn', center=0, ax=ax)
        ax.set_title('Monthly Returns Heatmap')
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"月度收益图已保存: {output_path}")
        else:
            plt.show()
    
    def plot_trade_distribution(
        self,
        trade_records: pd.DataFrame,
        output_path: str = None
    ):
        """
        绘制交易分布
        
        Args:
            trade_records: 交易记录
            output_path: 输出路径
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning("matplotlib未安装")
            return
        
        if trade_records.empty:
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 交易量分布
        axes[0].hist(trade_records['volume'], bins=30, edgecolor='black')
        axes[0].set_xlabel('Volume')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Trade Volume Distribution')
        
        # 交易时间分布
        trade_records['hour'] = pd.to_datetime(trade_records['timestamp']).dt.hour
        axes[1].hist(trade_records['hour'], bins=24, edgecolor='black')
        axes[1].set_xlabel('Hour')
        axes[1].set_ylabel('Frequency')
        axes[1].set_title('Trade Time Distribution')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"交易分布图已保存: {output_path}")
        else:
            plt.show()
    
    def generate_full_report(
        self,
        results: Dict[str, Any],
        output_dir: str = "backtest_report"
    ):
        """
        生成完整报告
        
        Args:
            results: 回测结果
            output_dir: 输出目录
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        daily_records = results.get('daily_records')
        trade_records = results.get('trade_records')
        metrics = results.get('metrics', {})
        
        # 生成图表
        if daily_records is not None:
            self.plot_equity_curve(
                daily_records,
                output_path=f"{output_dir}/equity_curve.png"
            )
            self.plot_drawdown(
                daily_records,
                output_path=f"{output_dir}/drawdown.png"
            )
            self.plot_monthly_returns(
                daily_records,
                output_path=f"{output_dir}/monthly_returns.png"
            )
        
        if trade_records is not None:
            self.plot_trade_distribution(
                trade_records,
                output_path=f"{output_dir}/trade_distribution.png"
            )
        
        # 生成报告文本
        analyzer = PerformanceAnalyzer()
        report = analyzer.generate_report(
            metrics,
            output_path=f"{output_dir}/report.txt"
        )
        
        logger.info(f"完整报告已生成: {output_dir}/")
        
        return report
