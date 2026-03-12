"""
Quant Assistant 主 API 接口

提供简洁的高层 API，方便快速使用框架功能。

示例:
    >>> from quant_assistant import QuantAPI
    >>> api = QuantAPI()
    >>> 
    >>> # 获取迈为股份数据
    >>> data = api.data.get_stock_data('300751', start='2024-01-01')
    >>> 
    >>> # 计算技术指标
    >>> ma20 = api.factors.ma(data, window=20)
    >>> 
    >>> # 运行回测
    >>> result = api.backtest.run(strategy, data)
"""

from typing import Optional, Dict, List, Any, Union
from datetime import datetime, date
import pandas as pd

from quant_assistant.utils.logger import get_logger

logger = get_logger(__name__)


class QuantAPI:
    """
    Quant Assistant 主 API 类
    
    提供简洁的接口来访问框架的所有功能。
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 API
        
        Args:
            config_path: 配置文件路径，默认使用环境变量或默认配置
        """
        self.config_path = config_path
        
        # 懒加载的组件
        self._data_api = None
        self._factors_api = None
        self._strategy_api = None
        self._backtest_api = None
        self._ml_api = None
    
    @property
    def data(self) -> 'DataAPI':
        """数据 API"""
        if self._data_api is None:
            self._data_api = DataAPI(self)
        return self._data_api
    
    @property
    def factors(self) -> 'FactorAPI':
        """因子 API"""
        if self._factors_api is None:
            self._factors_api = FactorAPI(self)
        return self._factors_api
    
    @property
    def strategy(self) -> 'StrategyAPI':
        """策略 API"""
        if self._strategy_api is None:
            self._strategy_api = StrategyAPI(self)
        return self._strategy_api
    
    @property
    def backtest(self) -> 'BacktestAPI':
        """回测 API"""
        if self._backtest_api is None:
            self._backtest_api = BacktestAPI(self)
        return self._backtest_api
    
    @property
    def ml(self) -> 'MLAPI':
        """机器学习 API"""
        if self._ml_api is None:
            self._ml_api = MLAPI(self)
        return self._ml_api


class DataAPI:
    """数据 API - 提供数据获取、存储、查询功能"""
    
    def __init__(self, api: QuantAPI):
        self._api = api
        self._fetcher = None
        self._storage = None
        self._query = None
    
    def _get_fetcher(self):
        """懒加载数据获取器"""
        if self._fetcher is None:
            from quant_assistant.data.fetcher import DataFetcher
            self._fetcher = DataFetcher()
        return self._fetcher
    
    def _get_storage(self):
        """懒加载存储器"""
        if self._storage is None:
            from quant_assistant.data.storage import MySQLStorage
            self._storage = MySQLStorage()
        return self._storage
    
    def _get_query(self):
        """懒加载查询器"""
        if self._query is None:
            from quant_assistant.data.query import DataQuery
            self._query = DataQuery()
        return self._query
    
    def get_stock_data(
        self,
        symbol: str,
        start: Optional[Union[str, date]] = None,
        end: Optional[Union[str, date]] = None,
        period: str = 'daily',
        adjust: str = 'qfq'
    ) -> pd.DataFrame:
        """
        获取股票行情数据
        
        Args:
            symbol: 股票代码，如 '300751'
            start: 开始日期，如 '2024-01-01'
            end: 结束日期，如 '2024-12-31'
            period: 周期，可选 'daily', 'weekly', 'monthly'
            adjust: 复权类型，'qfq' 前复权，'hfq' 后复权
            
        Returns:
            DataFrame 包含 OHLCV 数据
            
        示例:
            >>> data = api.data.get_stock_data('300751', start='2024-01-01')
        """
        fetcher = self._get_fetcher()
        return fetcher.get_stock_data(
            symbol=symbol,
            start_date=start,
            end_date=end,
            period=period,
            adjust=adjust
        )
    
    def get_stock_list(self, market: str = 'all') -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: 市场，'all', 'sh', 'sz', 'bj'
            
        Returns:
            DataFrame 包含股票基础信息
        """
        fetcher = self._get_fetcher()
        return fetcher.get_stock_list(market=market)
    
    def get_financial_data(
        self,
        symbol: str,
        report_type: str = 'quarterly'
    ) -> pd.DataFrame:
        """
        获取财务数据
        
        Args:
            symbol: 股票代码
            report_type: 报告类型，'quarterly', 'annual'
            
        Returns:
            DataFrame 包含财务指标
        """
        fetcher = self._get_fetcher()
        return fetcher.get_financial_data(symbol, report_type)
    
    def save(self, data: pd.DataFrame, table: str, **kwargs) -> bool:
        """
        保存数据到数据库
        
        Args:
            data: 要保存的数据
            table: 表名
            
        Returns:
            是否成功
        """
        storage = self._get_storage()
        return storage.save(data, table, **kwargs)
    
    def query(
        self,
        table: str,
        symbol: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        **filters
    ) -> pd.DataFrame:
        """
        查询数据
        
        Args:
            table: 表名
            symbol: 股票代码
            start: 开始日期
            end: 结束日期
            **filters: 其他过滤条件
            
        Returns:
            DataFrame 查询结果
        """
        query = self._get_query()
        return query.query(
            table=table,
            symbol=symbol,
            start=start,
            end=end,
            **filters
        )


class FactorAPI:
    """因子 API - 提供技术指标和因子计算"""
    
    def __init__(self, api: QuantAPI):
        self._api = api
        self._engine = None
    
    def _get_engine(self):
        """懒加载因子引擎"""
        if self._engine is None:
            from quant_assistant.factors.engine import FactorEngine
            self._engine = FactorEngine()
        return self._engine
    
    def _get_engine_v2(self):
        """懒加载因子引擎V2"""
        if not hasattr(self, '_engine_v2') or self._engine_v2 is None:
            from quant_assistant.factors.engine_v2 import FactorEngineV2
            self._engine_v2 = FactorEngineV2()
        return self._engine_v2
    
    def ma(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        计算移动平均线
        
        Args:
            data: 包含 'close' 列的 DataFrame
            window: 窗口大小
            
        Returns:
            MA 序列
        """
        engine = self._get_engine()
        return engine.ma(data['close'], window=window)
    
    def ema(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """计算指数移动平均线"""
        engine = self._get_engine()
        return engine.ema(data['close'], window=window)
    
    def macd(
        self,
        data: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Dict[str, pd.Series]:
        """
        计算 MACD 指标
        
        Returns:
            {'macd': ..., 'signal': ..., 'histogram': ...}
        """
        engine = self._get_engine()
        return engine.macd(data['close'], fast=fast, slow=slow, signal=signal)
    
    def rsi(self, data: pd.DataFrame, window: int = 14) -> pd.Series:
        """计算 RSI 指标"""
        engine = self._get_engine()
        return engine.rsi(data['close'], window=window)
    
    def bollinger(
        self,
        data: pd.DataFrame,
        window: int = 20,
        std: int = 2
    ) -> Dict[str, pd.Series]:
        """
        计算布林带
        
        Returns:
            {'upper': ..., 'middle': ..., 'lower': ...}
        """
        engine = self._get_engine()
        return engine.bollinger(data['close'], window=window, std=std)
    
    def kdj(
        self,
        data: pd.DataFrame,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Dict[str, pd.Series]:
        """
        计算 KDJ 指标
        
        Returns:
            {'k': ..., 'd': ..., 'j': ...}
        """
        engine = self._get_engine()
        return engine.kdj(data, n=n, m1=m1, m2=m2)
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有常用技术指标（基础版）
        
        Args:
            data: OHLCV 数据
            
        Returns:
            添加了技术指标列的 DataFrame
        """
        engine = self._get_engine()
        return engine.compute_all(data)
    
    def compute_all_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有策略因子（完整版）
        
        一次性计算所有常用技术指标、量价因子、波动率因子等，
        自动检测数据粒度（日线/分钟级/实时），计算适合的因子。
        包含120+个因子，方便策略开发和机器学习特征工程。
        
        Args:
            data: OHLCV 数据
            
        Returns:
            添加了所有因子列的 DataFrame
            
        计算的因子类别:
            - 趋势类: MA, EMA, MACD, 均线差值/比值
            - 动量类: RSI, KDJ, CCI, WR, 价格动量
            - 波动率类: 布林带, ATR, 历史波动率
            - 量价类: 成交量MA, 量价关系, OBV, MFI
            - 形态类: 影线, 价格位置
            - 统计类: 收益率统计, 最大回撤
            - 复合信号: 均线排列, 趋势强度
            - 实时因子: 实时换手率, 涨速, 量比等
            
        示例:
            >>> data = api.data.get_stock_data('300751')
            >>> df = api.factors.compute_all_factors(data)
            >>> print(f"共计算 {len(df.columns)} 个因子")
            >>> print(df[['ma5', 'rsi14', 'macd', 'boll_width_20']].tail())
        """
        engine = self._get_engine()
        return engine.compute_all_factors(data)
    
    def compute_factors_v2(
        self,
        data: pd.DataFrame,
        granularity = None,
        categories = None
    ) -> pd.DataFrame:
        """
        计算策略因子 V2（支持多粒度）⭐
        
        根据数据粒度自动选择合适的因子进行计算：
        - 日线数据：计算中长期因子（MA5-120, RSI等）
        - 分钟数据：计算短周期因子（短周期MA, 日内指标等）
        - 实时数据：计算实时因子（换手率, 涨速, 量比等）
        
        Args:
            data: OHLCV数据或实时行情数据
            granularity: 指定粒度，None则自动检测
            categories: 指定计算的因子类别，None则计算所有
            
        Returns:
            添加了因子的DataFrame
            
        示例:
            >>> from quant_assistant import TimeGranularity, FactorCategory
            >>> 
            >>> # 自动检测粒度并计算
            >>> df = api.factors.compute_factors_v2(data)
            >>> 
            >>> # 指定粒度和类别
            >>> df = api.factors.compute_factors_v2(
            ...     data,
            ...     granularity=TimeGranularity.MINUTE_5,
            ...     categories=[FactorCategory.TREND, FactorCategory.MOMENTUM]
            ... )
        """
        engine = self._get_engine_v2()
        return engine.compute_factors(data, granularity, categories)


class StrategyAPI:
    """策略 API - 提供策略开发和信号生成"""
    
    def __init__(self, api: QuantAPI):
        self._api = api
    
    def create(self, name: str, **params):
        """
        创建策略实例
        
        Args:
            name: 策略名称，如 'macd', 'ma_cross'
            **params: 策略参数
            
        Returns:
            策略实例
        """
        from quant_assistant.strategy.examples import get_strategy
        return get_strategy(name, **params)
    
    def generate_signals(self, strategy, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            strategy: 策略实例
            data: 行情数据
            
        Returns:
            添加了信号列的 DataFrame
        """
        return strategy.generate_signals(data)
    
    def select_stocks(
        self,
        strategy,
        symbols: List[str],
        date: Optional[str] = None
    ) -> List[str]:
        """
        选股
        
        Args:
            strategy: 选股策略
            symbols: 候选股票列表
            date: 选股日期
            
        Returns:
            选中的股票列表
        """
        from quant_assistant.strategy.signal_synthesis import StockSelector
        selector = StockSelector(strategy)
        return selector.select(symbols, date)


class BacktestAPI:
    """回测 API - 提供回测和绩效分析"""
    
    def __init__(self, api: QuantAPI):
        self._api = api
        self._engine = None
    
    def _get_engine(self):
        """懒加载回测引擎"""
        if self._engine is None:
            from quant_assistant.backtest.engine import BacktestEngine
            self._engine = BacktestEngine()
        return self._engine
    
    def run(
        self,
        strategy,
        data: pd.DataFrame,
        initial_capital: float = 100000.0,
        commission: float = 0.0003,
        slippage: float = 0.0
    ) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            strategy: 策略实例
            data: 行情数据
            initial_capital: 初始资金
            commission: 手续费率
            slippage: 滑点
            
        Returns:
            回测结果字典
        """
        engine = self._get_engine()
        return engine.run(
            strategy=strategy,
            data=data,
            initial_capital=initial_capital,
            commission=commission,
            slippage=slippage
        )
    
    def analyze(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析回测结果
        
        Args:
            result: 回测结果
            
        Returns:
            绩效指标
        """
        from quant_assistant.backtest.performance import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        return analyzer.analyze(result)


class MLAPI:
    """机器学习 API - 提供自动化预测功能"""
    
    def __init__(self, api: QuantAPI):
        self._api = api
        self._predictor = None
    
    def _get_predictor(self):
        """懒加载预测器"""
        if self._predictor is None:
            from quant_assistant.ml.predictor import MLPredictor
            self._predictor = MLPredictor()
        return self._predictor
    
    def train(
        self,
        data: pd.DataFrame,
        target: str = 'close',
        features: Optional[List[str]] = None,
        model_type: str = 'xgboost'
    ):
        """
        训练预测模型
        
        Args:
            data: 训练数据
            target: 目标列
            features: 特征列列表
            model_type: 模型类型，'xgboost', 'lightgbm', 'random_forest'
            
        Returns:
            训练好的预测器
        """
        predictor = self._get_predictor()
        predictor.train(data, target=target, features=features, model_type=model_type)
        return predictor
    
    def predict(self, predictor, data: pd.DataFrame) -> pd.Series:
        """
        使用模型预测
        
        Args:
            predictor: 训练好的预测器
            data: 预测数据
            
        Returns:
            预测结果
        """
        return predictor.predict(data)
    
    def evaluate(
        self,
        predictor,
        data: pd.DataFrame,
        target: str = 'close'
    ) -> Dict[str, float]:
        """
        评估模型性能
        
        Args:
            predictor: 训练好的预测器
            data: 测试数据
            target: 目标列
            
        Returns:
            评估指标
        """
        return predictor.evaluate(data, target=target)
