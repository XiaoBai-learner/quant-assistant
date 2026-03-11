"""
回测引擎
事件驱动的回测核心，支持依赖注入
"""
from typing import Dict, List, Any, Optional, Callable, Protocol
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import pandas as pd
import numpy as np

from .broker import Broker, Order, OrderType, OrderSide
from .portfolio import Portfolio
from .performance import PerformanceAnalyzer
from src.strategy.base import BaseStrategy, Bar, StrategyContext, Signal
from src.utils.logger import get_logger

logger = get_logger(__name__)


# 接口定义
class IBroker(Protocol):
    """券商接口"""
    def submit_order(self, order: Order) -> bool: ...
    def execute_order(self, order: Order, bar) -> List[Any]: ...
    def cancel_order(self, order_id: str) -> bool: ...


class IPortfolio(Protocol):
    """投资组合接口"""
    def update_position(self, symbol: str, volume: int, price: float) -> None: ...
    def get_position(self, symbol: str) -> int: ...
    def get_total_value(self, prices: Dict[str, float]) -> float: ...


class IPerformanceAnalyzer(Protocol):
    """绩效分析器接口"""
    def calculate_metrics(self, daily_records: pd.DataFrame, trade_records: pd.DataFrame = None) -> Dict[str, float]: ...
    def generate_report(self, metrics: Dict[str, float], output_path: str = None) -> str: ...


class IRiskManager(Protocol):
    """风险管理器接口"""
    def check_order(self, order: Order, portfolio: Dict[str, Any]) -> Any: ...


class BacktestMode(Enum):
    """回测模式"""
    EVENT_DRIVEN = "event_driven"  # 事件驱动
    VECTORIZED = "vectorized"      # 向量化


@dataclass
class BacktestConfig:
    """回测配置"""
    # 基础配置
    start_date: date
    end_date: date
    initial_cash: float = 100000.0
    
    # 成本配置
    commission_rate: float = 0.00025  # 手续费率 (万2.5)
    slippage: float = 0.001           # 滑点 (0.1%)
    stamp_duty: float = 0.001         # 印花税 (卖出时)
    
    # 风控配置
    max_position_pct: float = 1.0     # 最大仓位比例
    max_drawdown_limit: float = 0.2   # 最大回撤限制
    
    # 模式
    mode: BacktestMode = BacktestMode.EVENT_DRIVEN
    
    # 其他
    benchmark: str = None             # 基准代码
    log_level: str = "INFO"


class BacktestEngine:
    """
    回测引擎
    
    事件驱动的回测核心，支持依赖注入
    """
    
    def __init__(
        self,
        config: BacktestConfig,
        broker: Optional[IBroker] = None,
        portfolio: Optional[IPortfolio] = None,
        analyzer: Optional[IPerformanceAnalyzer] = None,
        risk_manager: Optional[IRiskManager] = None
    ):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置
            broker: 券商实例（可选，默认使用Broker）
            portfolio: 投资组合实例（可选，默认使用Portfolio）
            analyzer: 绩效分析器实例（可选，默认使用PerformanceAnalyzer）
            risk_manager: 风险管理器实例（可选）
        """
        self.config = config
        
        # 依赖注入，使用默认实现
        self.broker = broker or Broker(config)
        self.portfolio = portfolio or Portfolio(config.initial_cash)
        self.analyzer = analyzer or PerformanceAnalyzer()
        self.risk_manager = risk_manager
        
        # 策略
        self.strategy: Optional[BaseStrategy] = None
        self.context: Optional[StrategyContext] = None
        
        # 数据
        self.data: Dict[str, pd.DataFrame] = {}
        self.current_date: Optional[date] = None
        
        # 记录
        self.daily_records: List[Dict] = []
        self.trade_records: List[Dict] = []
        self.signal_records: List[Dict] = []
        
        # 状态
        self.is_running = False
        self.current_bar: Optional[Bar] = None
    
    def set_strategy(self, strategy: BaseStrategy):
        """设置策略"""
        self.strategy = strategy
        self.context = StrategyContext(
            cash=self.config.initial_cash,
            current_time=datetime.combine(self.config.start_date, datetime.min.time())
        )
        strategy.init(self.context)
        logger.info(f"设置策略: {strategy.name}")
    
    def load_data(self, symbol: str, data: pd.DataFrame):
        """加载历史数据"""
        # 过滤日期范围
        mask = (data.index >= pd.Timestamp(self.config.start_date)) & \
               (data.index <= pd.Timestamp(self.config.end_date))
        self.data[symbol] = data[mask].copy()
        logger.info(f"加载数据: {symbol}, {len(self.data[symbol])}条")
    
    def run(self) -> Dict[str, Any]:
        """
        运行回测
        
        Returns:
            Dict: 回测结果
        """
        if self.strategy is None:
            raise ValueError("策略未设置")
        
        if not self.data:
            raise ValueError("数据未加载")
        
        self.is_running = True
        logger.info(f"开始回测: {self.config.start_date} ~ {self.config.end_date}")
        
        # 获取所有交易日
        all_dates = self._get_trading_dates()
        
        # 逐日回测
        for current_date in all_dates:
            self.current_date = current_date
            self._process_day(current_date)
        
        self.is_running = False
        
        # 生成结果
        results = self._generate_results()
        
        logger.info(f"回测完成: 总收益 {results['total_return']:.2%}")
        
        return results
    
    def _get_trading_dates(self) -> List[date]:
        """获取交易日列表"""
        # 从第一个数据集中提取日期
        first_symbol = list(self.data.keys())[0]
        dates = self.data[first_symbol].index.date
        return sorted(list(set(dates)))
    
    def _process_day(self, current_date: date):
        """处理单日"""
        # 更新上下文时间
        if self.context:
            self.context.current_time = datetime.combine(current_date, datetime.min.time())
        
        # 处理每个标的
        for symbol, df in self.data.items():
            # 获取当日数据
            day_data = df[df.index.date == current_date]
            
            if day_data.empty:
                continue
            
            # 逐K线处理
            for idx, row in day_data.iterrows():
                bar = Bar(
                    symbol=symbol,
                    timestamp=idx,
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=int(row['volume']),
                    amount=row.get('amount', 0)
                )
                
                self.current_bar = bar
                self._process_bar(bar)
        
        # 日终结算
        self._daily_settlement(current_date)
    
    def _process_bar(self, bar: Bar):
        """处理单根K线"""
        # 调用策略
        if self.strategy:
            signal = self.strategy.on_bar(bar)
            
            if signal:
                # 记录信号
                self.signal_records.append({
                    'timestamp': bar.timestamp,
                    'symbol': bar.symbol,
                    'signal_type': signal.signal_type.name,
                    'price': signal.price,
                    'volume': signal.volume,
                    'source': signal.source
                })
                
                # 执行交易
                self._execute_signal(signal)
    
    def _execute_signal(self, signal):
        """执行交易信号"""
        # 创建订单
        order = Order(
            symbol=signal.symbol,
            side=OrderSide.BUY if signal.signal_type.value > 0 else OrderSide.SELL,
            order_type=OrderType.MARKET,
            volume=signal.volume,
            price=signal.price
        )
        
        # 提交给券商
        trades = self.broker.execute_order(order, self.current_bar)
        
        # 更新持仓
        for trade in trades:
            self._process_trade(trade)
    
    def _process_trade(self, trade):
        """处理成交"""
        # 计算成本
        commission = trade.amount * self.config.commission_rate
        if trade.side == OrderSide.SELL:
            commission += trade.amount * self.config.stamp_duty
        
        slippage_cost = trade.amount * self.config.slippage
        total_cost = commission + slippage_cost
        
        # 更新组合
        self.portfolio.update_position(
            symbol=trade.symbol,
            volume=trade.volume if trade.side == OrderSide.BUY else -trade.volume,
            price=trade.price,
            cost=total_cost
        )
        
        # 记录交易
        self.trade_records.append({
            'timestamp': trade.timestamp,
            'symbol': trade.symbol,
            'side': trade.side.value,
            'volume': trade.volume,
            'price': trade.price,
            'amount': trade.amount,
            'commission': commission,
            'slippage': slippage_cost,
        })
    
    def _daily_settlement(self, current_date: date):
        """日终结算"""
        # 计算当日净值
        total_value = self.portfolio.total_value(self.data, current_date)
        
        # 记录
        self.daily_records.append({
            'date': current_date,
            'cash': self.portfolio.cash,
            'market_value': total_value - self.portfolio.cash,
            'total_value': total_value,
            'positions': len(self.portfolio.positions)
        })
    
    def _generate_results(self) -> Dict[str, Any]:
        """生成回测结果"""
        if not self.daily_records:
            return {}
        
        # 转换为DataFrame
        df_daily = pd.DataFrame(self.daily_records)
        df_trades = pd.DataFrame(self.trade_records)
        
        # 计算收益
        df_daily['return'] = df_daily['total_value'].pct_change()
        df_daily['cumulative_return'] = (1 + df_daily['return']).cumprod() - 1
        
        # 绩效分析
        metrics = self.analyzer.calculate_metrics(df_daily, df_trades)
        
        return {
            'config': self.config,
            'daily_records': df_daily,
            'trade_records': df_trades,
            'signal_records': pd.DataFrame(self.signal_records),
            'metrics': metrics,
            'total_return': metrics.get('total_return', 0),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'max_drawdown': metrics.get('max_drawdown', 0),
            'win_rate': metrics.get('win_rate', 0),
        }


class VectorizedBacktestEngine:
    """
    向量化回测引擎
    
    适用于简单策略，速度更快
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.analyzer = PerformanceAnalyzer()
    
    def run(
        self,
        price_data: pd.DataFrame,
        signal_series: pd.Series
    ) -> Dict[str, Any]:
        """
        运行向量化回测
        
        Args:
            price_data: 价格数据 (close)
            signal_series: 信号序列 (1=买入, -1=卖出, 0=持仓)
            
        Returns:
            Dict: 回测结果
        """
        # 计算持仓
        position = signal_series.shift(1).fillna(0)
        
        # 计算收益
        returns = price_data.pct_change()
        strategy_returns = position * returns
        
        # 累计收益
        cumulative_returns = (1 + strategy_returns).cumprod() - 1
        
        # 生成每日记录
        daily_records = pd.DataFrame({
            'date': price_data.index,
            'close': price_data.values,
            'signal': signal_series.values,
            'position': position.values,
            'return': strategy_returns.values,
            'cumulative_return': cumulative_returns.values
        })
        
        # 计算指标
        metrics = self._calculate_vectorized_metrics(daily_records)
        
        return {
            'daily_records': daily_records,
            'metrics': metrics,
            'total_return': metrics.get('total_return', 0),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'max_drawdown': metrics.get('max_drawdown', 0),
        }
    
    def _calculate_vectorized_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算向量化回测指标"""
        returns = df['return'].dropna()
        
        if len(returns) == 0:
            return {}
        
        # 总收益
        total_return = df['cumulative_return'].iloc[-1]
        
        # 年化收益
        n_years = len(df) / 252
        annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
        
        # 波动率
        volatility = returns.std() * np.sqrt(252)
        
        # 夏普比率
        sharpe = annual_return / volatility if volatility > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'calmar_ratio': annual_return / abs(max_drawdown) if max_drawdown != 0 else 0,
        }
