"""
向量化回测引擎
使用Pandas向量化运算，比事件驱动快10-100倍
适合简单策略和参数优化
"""
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import date
import pandas as pd
import numpy as np

from src.backtest.engine import BacktestConfig
from src.strategy.base import SignalType
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VectorizedResult:
    """向量化回测结果"""
    returns: pd.Series
    positions: pd.Series
    trades: pd.DataFrame
    metrics: Dict[str, float]


class VectorizedBacktestEngine:
    """
    向量化回测引擎
    
    使用Pandas向量化运算，适合：
    1. 简单技术指标策略
    2. 参数优化（需要快速回测）
    3. 多股票批量回测
    
    不支持：
    1. 复杂事件处理
    2. 动态仓位管理
    3. 多策略组合
    """
    
    def __init__(self, config: BacktestConfig):
        """
        初始化向量化回测引擎
        
        Args:
            config: 回测配置
        """
        self.config = config
        self.initial_cash = config.initial_cash
        self.commission_rate = config.commission_rate
        self.slippage = config.slippage
    
    def run(
        self,
        df: pd.DataFrame,
        signal_series: pd.Series
    ) -> VectorizedResult:
        """
        运行向量化回测
        
        Args:
            df: 价格数据DataFrame，包含open, high, low, close
            signal_series: 信号序列，1=买入，-1=卖出，0=持有
            
        Returns:
            VectorizedResult: 回测结果
        """
        if df.empty or len(signal_series) != len(df):
            raise ValueError("数据为空或长度不匹配")
        
        logger.info(f"开始向量化回测: {len(df)} 条数据")
        
        # 复制数据避免修改原始数据
        data = df.copy()
        data['signal'] = signal_series.values
        
        # 计算持仓
        data = self._calculate_positions(data)
        
        # 计算收益
        data = self._calculate_returns(data)
        
        # 生成交易记录
        trades = self._generate_trades(data)
        
        # 计算绩效指标
        metrics = self._calculate_metrics(data)
        
        logger.info(f"向量化回测完成: 总收益 {metrics.get('total_return', 0):.2%}")
        
        return VectorizedResult(
            returns=data['strategy_return'],
            positions=data['position'],
            trades=trades,
            metrics=metrics
        )
    
    def _calculate_positions(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算持仓"""
        # 信号变化时产生交易
        df['position_change'] = df['signal'].diff().fillna(0)
        
        # 持仓：累积信号
        df['position'] = df['signal'].cumsum()
        
        # 限制持仓在0-1之间（简化假设）
        df['position'] = df['position'].clip(0, 1)
        
        return df
    
    def _calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算收益"""
        # 价格收益
        df['price_return'] = df['close'].pct_change().fillna(0)
        
        # 策略收益（持仓 * 价格收益）
        df['strategy_return'] = df['position'].shift(1) * df['price_return']
        
        # 处理交易成本
        # 只在仓位变化时产生成本
        df['trade_cost'] = 0.0
        trade_mask = df['position_change'] != 0
        
        if trade_mask.any():
            # 交易成本 = 交易金额 * 手续费率
            trade_value = df.loc[trade_mask, 'position_change'].abs() * df.loc[trade_mask, 'close']
            df.loc[trade_mask, 'trade_cost'] = trade_value * self.commission_rate
            
            # 滑点成本
            df.loc[trade_mask, 'trade_cost'] += trade_value * self.slippage
        
        # 扣除交易成本
        df['strategy_return'] -= df['trade_cost'] / self.initial_cash
        
        # 计算累计收益
        df['cumulative_return'] = (1 + df['strategy_return']).cumprod() - 1
        
        # 计算资金曲线
        df['portfolio_value'] = self.initial_cash * (1 + df['cumulative_return'])
        
        return df
    
    def _generate_trades(self, df: pd.DataFrame) -> pd.DataFrame:
        """生成交易记录"""
        trades = []
        
        # 找到所有交易点
        trade_mask = df['position_change'] != 0
        trade_df = df[trade_mask].copy()
        
        for idx, row in trade_df.iterrows():
            side = 'buy' if row['position_change'] > 0 else 'sell'
            volume = abs(row['position_change'])
            price = row['close']
            
            trades.append({
                'timestamp': idx,
                'side': side,
                'volume': volume,
                'price': price,
                'amount': volume * price
            })
        
        return pd.DataFrame(trades)
    
    def _calculate_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算绩效指标"""
        returns = df['strategy_return'].dropna()
        
        if len(returns) == 0:
            return {}
        
        n_days = len(df)
        n_years = n_days / 252
        
        # 总收益
        total_return = df['cumulative_return'].iloc[-1] if 'cumulative_return' in df.columns else 0
        
        # 年化收益
        annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
        
        # 年化波动率
        volatility = returns.std() * np.sqrt(252)
        
        # 夏普比率
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 最大回撤
        portfolio_value = df['portfolio_value'] if 'portfolio_value' in df.columns else (1 + df['cumulative_return']) * self.initial_cash
        cummax = portfolio_value.cummax()
        drawdown = (portfolio_value - cummax) / cummax
        max_drawdown = drawdown.min()
        
        # 卡玛比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # 胜率
        win_rate = (returns > 0).sum() / len(returns)
        
        # 盈亏比
        avg_win = returns[returns > 0].mean() if (returns > 0).any() else 0
        avg_loss = abs(returns[returns < 0].mean()) if (returns < 0).any() else 1
        profit_factor = avg_win / avg_loss if avg_loss != 0 else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_days': n_days,
            'total_trades': len(df[df['position_change'] != 0])
        }
    
    def optimize_strategy(
        self,
        df: pd.DataFrame,
        strategy_func: Callable,
        param_grid: Dict[str, List]
    ) -> Dict[str, Any]:
        """
        优化策略参数
        
        Args:
            df: 价格数据
            strategy_func: 策略函数，接收参数返回信号序列
            param_grid: 参数网格
            
        Returns:
            最佳参数和结果
        """
        from itertools import product
        
        # 生成参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        
        best_result = None
        best_params = None
        best_sharpe = -np.inf
        
        logger.info(f"开始参数优化: {len(combinations)} 组参数")
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            # 生成信号
            signals = strategy_func(df, **params)
            
            # 运行回测
            try:
                result = self.run(df, signals)
                sharpe = result.metrics.get('sharpe_ratio', 0)
                
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = params
                    best_result = result
            except Exception as e:
                logger.warning(f"参数 {params} 回测失败: {e}")
                continue
        
        logger.info(f"参数优化完成: 最佳夏普比率 {best_sharpe:.2f}")
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'all_combinations': len(combinations)
        }


def create_ma_strategy(fast: int, slow: int) -> Callable:
    """
    创建双均线策略函数
    
    Args:
        fast: 短期均线周期
        slow: 长期均线周期
        
    Returns:
        策略函数
    """
    def strategy(df: pd.DataFrame) -> pd.Series:
        # 计算均线
        df['ma_fast'] = df['close'].rolling(window=fast).mean()
        df['ma_slow'] = df['close'].rolling(window=slow).mean()
        
        # 生成信号
        signal = pd.Series(0, index=df.index)
        signal[df['ma_fast'] > df['ma_slow']] = 1  # 买入
        signal[df['ma_fast'] < df['ma_slow']] = -1  # 卖出
        
        return signal
    
    return strategy


# 使用示例
if __name__ == "__main__":
    # 模拟数据
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='B')
    np.random.seed(42)
    
    data = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(len(dates)) * 0.5),
        'high': 100 + np.cumsum(np.random.randn(len(dates)) * 0.5) + 1,
        'low': 100 + np.cumsum(np.random.randn(len(dates)) * 0.5) - 1,
        'close': 100 + np.cumsum(np.random.randn(len(dates)) * 0.5),
        'volume': np.random.randint(1000000, 10000000, len(dates))
    }, index=dates)
    
    # 创建策略
    strategy = create_ma_strategy(fast=5, slow=20)
    signals = strategy(data)
    
    # 运行回测
    config = BacktestConfig(
        start_date=dates[0].date(),
        end_date=dates[-1].date()
    )
    
    engine = VectorizedBacktestEngine(config)
    result = engine.run(data, signals)
    
    print(f"总收益: {result.metrics['total_return']:.2%}")
    print(f"夏普比率: {result.metrics['sharpe_ratio']:.2f}")
