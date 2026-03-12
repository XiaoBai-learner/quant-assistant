"""
核心接口定义
使用 Protocol 定义模块间的契约接口
"""
from typing import Protocol, List, Optional, Dict, Any
from datetime import date
import pandas as pd

from src.backtest.broker import Order, Trade
from src.strategy.base import Signal, Bar


# ==================== 数据层接口 ====================

class IDataFetcher(Protocol):
    """数据获取器接口"""
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        ...
    
    def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """获取日线数据"""
        ...
    
    def get_daily_quotes_incremental(
        self,
        symbol: str,
        last_date: Optional[date] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """增量获取日线数据"""
        ...


class IDataStorage(Protocol):
    """数据存储接口"""
    
    def save_stocks(self, df: pd.DataFrame) -> int:
        """保存股票列表"""
        ...
    
    def save_daily_quotes(self, df: pd.DataFrame, validate: bool = True) -> int:
        """保存日线数据"""
        ...
    
    def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """查询日线数据"""
        ...
    
    def get_last_update_date(self, symbol: str, table: str = 'daily_quotes') -> Optional[date]:
        """获取最后更新日期"""
        ...


class IDataValidator(Protocol):
    """数据校验器接口"""
    
    def validate_price_data(self, df: pd.DataFrame) -> Any:
        """校验价格数据"""
        ...
    
    def validate_stock_list(self, df: pd.DataFrame) -> Any:
        """校验股票列表"""
        ...


# ==================== 回测层接口 ====================

class IBroker(Protocol):
    """券商接口"""
    
    def submit_order(self, order: Order) -> bool:
        """提交订单"""
        ...
    
    def execute_order(self, order: Order, bar) -> List[Trade]:
        """执行订单撮合"""
        ...
    
    def cancel_order(self, order_id: str) -> bool:
        """撤销订单"""
        ...
    
    def get_orders(self) -> List[Order]:
        """获取所有订单"""
        ...
    
    def get_trades(self) -> List[Trade]:
        """获取所有成交"""
        ...


class IPortfolio(Protocol):
    """投资组合接口"""
    
    def update_position(self, symbol: str, volume: int, price: float) -> None:
        """更新持仓"""
        ...
    
    def get_position(self, symbol: str) -> int:
        """获取持仓数量"""
        ...
    
    def get_position_value(self, symbol: str, price: float) -> float:
        """获取持仓市值"""
        ...
    
    def get_total_value(self, prices: Dict[str, float]) -> float:
        """获取总资产"""
        ...
    
    def get_returns(self) -> float:
        """获取收益率"""
        ...
    
    def can_trade(self, symbol: str, volume: int, price: float) -> bool:
        """检查是否可交易"""
        ...


class IPerformanceAnalyzer(Protocol):
    """绩效分析器接口"""
    
    def calculate_metrics(
        self,
        daily_records: pd.DataFrame,
        trade_records: pd.DataFrame = None
    ) -> Dict[str, float]:
        """计算绩效指标"""
        ...
    
    def generate_report(
        self,
        metrics: Dict[str, float],
        output_path: str = None
    ) -> str:
        """生成绩效报告"""
        ...


# ==================== 风控层接口 ====================

class IRiskManager(Protocol):
    """风险管理器接口"""
    
    def check_order(self, order: Order, portfolio: Dict[str, Any]) -> Any:
        """检查订单风险"""
        ...
    
    def check_signal(self, signal: Signal, portfolio: Dict[str, Any]) -> Any:
        """检查信号风险"""
        ...


# ==================== 策略层接口 ====================

class IStrategy(Protocol):
    """策略接口"""
    
    name: str
    params: Dict[str, Any]
    
    def on_init(self, context: Any) -> None:
        """初始化策略"""
        ...
    
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """处理K线"""
        ...
    
    def buy(self, symbol: str, price: float, volume: int, **kwargs) -> Signal:
        """生成买入信号"""
        ...
    
    def sell(self, symbol: str, price: float, volume: int, **kwargs) -> Signal:
        """生成卖出信号"""
        ...


class IFactorEngine(Protocol):
    """因子引擎接口"""
    
    def calculate(
        self,
        df: pd.DataFrame,
        factor_names: List[str] = None
    ) -> Dict[str, Any]:
        """批量计算因子"""
        ...
    
    def calculate_single(
        self,
        df: pd.DataFrame,
        factor_name: str,
        params: Dict[str, Any] = None
    ) -> Any:
        """计算单个因子"""
        ...


class ISignalGenerator(Protocol):
    """信号生成器接口"""
    
    def generate_signals(
        self,
        symbol: str,
        factor_data: pd.DataFrame,
        price_data: pd.Series,
        timestamp: Any = None
    ) -> List[Any]:
        """生成信号"""
        ...


# ==================== 可视化层接口 ====================

class IIndicator(Protocol):
    """指标接口"""
    
    name: str
    params: Dict[str, Any]
    
    def calculate(self, df: pd.DataFrame) -> Any:
        """计算指标"""
        ...


class IRenderer(Protocol):
    """渲染器接口"""
    
    def render_candlestick(self, df: pd.DataFrame, width: int = 80, height: int = 20) -> str:
        """渲染K线图"""
        ...
    
    def render_volume(self, df: pd.DataFrame, width: int = 80) -> str:
        """渲染成交量"""
        ...
    
    def render_indicator(self, df: pd.DataFrame, indicator: Any, width: int = 80, height: int = 10) -> str:
        """渲染指标"""
        ...


# ==================== 配置层接口 ====================

class IConfig(Protocol):
    """配置接口"""
    
    database: Any
    data: Any
    logging: Any
    backtest: Any
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "IConfig":
        """加载配置"""
        ...
