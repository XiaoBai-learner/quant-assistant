"""
统一数据获取器

将 AKShare 和 TickFlow 数据源统一封装，对外提供一致的接口。
支持配置化数据源选择和故障自动切换。

使用示例:
    >>> from quant_assistant.data import UnifiedDataFetcher
    >>> 
    >>> # 默认使用 AKShare 为主，TickFlow 为备用
    >>> fetcher = UnifiedDataFetcher()
    >>> 
    >>> # 指定优先使用 TickFlow
    >>> fetcher = UnifiedDataFetcher(primary_source='tickflow')
    >>> 
    >>> # 获取数据
    >>> df = fetcher.get_daily_quotes('600000', start_date='2024-01-01')
"""
import pandas as pd
from datetime import date, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import inspect
import time
import logging

from quant_assistant.data.fetcher.base_fetcher import BaseDataFetcher
from quant_assistant.utils.logger import get_logger
from quant_assistant.core.exceptions import DataFetchException

logger = get_logger(__name__)


class DataSourceType(Enum):
    """数据源类型枚举"""
    AKSHARE = "akshare"
    EFINANCE = "efinance"
    TICKFLOW = "tickflow"
    AUTO = "auto"  # 自动选择/故障切换


class UnifiedDataFetcher(BaseDataFetcher):
    """
    统一数据获取器
    
    整合 AKShare 和 TickFlow 两个数据源，提供统一的对外接口。
    支持配置化选择主要数据源，并在主数据源故障时自动切换到备用数据源。
    
    特性:
        - 统一接口: 无论底层使用哪个数据源，调用方式完全一致
        - 配置灵活: 支持通过参数或配置文件指定数据源优先级
        - 故障切换: 主数据源失败时自动尝试备用数据源
        - 智能合并: 部分接口可以合并多个数据源的结果
    
    Attributes:
        primary_source: 主要数据源类型
        fallback_enabled: 是否启用故障自动切换
        akshare_fetcher: AKShare 数据获取器实例
        tickflow_fetcher: TickFlow 数据获取器实例
    
    示例:
        >>> # 基本使用 - 默认 AKShare 为主
        >>> fetcher = UnifiedDataFetcher()
        >>> stocks = fetcher.get_stock_list()
        >>> 
        >>> # 使用 TickFlow 为主
        >>> fetcher = UnifiedDataFetcher(primary_source='tickflow')
        >>> 
        >>> # 禁用故障切换
        >>> fetcher = UnifiedDataFetcher(fallback_enabled=False)
    """
    
    def __init__(
        self,
        primary_source: Union[str, DataSourceType] = DataSourceType.AKSHARE,
        fallback_enabled: bool = True,
        tickflow_api_key: Optional[str] = None,
        tickflow_use_paid: bool = False
    ):
        """
        初始化统一数据获取器
        
        Args:
            primary_source: 主要数据源，可选 'akshare', 'tickflow', 'auto'，默认为 'akshare'
            fallback_enabled: 是否启用故障自动切换，默认为 True
            tickflow_api_key: TickFlow API Key（付费版需要）
            tickflow_use_paid: 是否使用 TickFlow 付费版
        
        Raises:
            DataFetchException: 初始化数据源失败时抛出
        """
        self.name = "UnifiedDataFetcher"
        
        # 解析主数据源类型
        if isinstance(primary_source, str):
            try:
                self.primary_source = DataSourceType(primary_source.lower())
            except ValueError:
                logger.warning(f"未知数据源类型: {primary_source}，使用默认 AKShare")
                self.primary_source = DataSourceType.AKSHARE
        else:
            self.primary_source = primary_source
        
        self.fallback_enabled = fallback_enabled
        
        # 初始化数据源获取器
        self._init_fetchers(tickflow_api_key, tickflow_use_paid)
        
        logger.info(f"统一数据获取器初始化完成: 主数据源={self.primary_source.value}, "
                   f"故障切换={'启用' if fallback_enabled else '禁用'}")
    
    def _init_fetchers(self, tickflow_api_key: Optional[str], tickflow_use_paid: bool):
        """
        初始化底层数据获取器
        
        Args:
            tickflow_api_key: TickFlow API Key
            tickflow_use_paid: 是否使用 TickFlow 付费版
        """
        self.akshare_fetcher = None
        self.efinance_fetcher = None
        self.tickflow_fetcher = None
        
        # 初始化 AKShare
        try:
            from quant_assistant.data.fetcher.akshare_fetcher import AKShareFetcher
            self.akshare_fetcher = AKShareFetcher()
            logger.debug("AKShare 数据获取器初始化成功")
        except Exception as e:
            logger.warning(f"AKShare 初始化失败: {e}")

        # 初始化 EFinance
        try:
            from quant_assistant.data.fetcher.efinance_fetcher import EFinanceFetcher
            self.efinance_fetcher = EFinanceFetcher()
            logger.debug("EFinance 数据获取器初始化成功")
        except Exception as e:
            logger.warning(f"EFinance 初始化失败: {e}")
        
        # 初始化 TickFlow
        try:
            from quant_assistant.data.fetcher.tickflow_fetcher import TickFlowFetcher
            self.tickflow_fetcher = TickFlowFetcher(
                api_key=tickflow_api_key,
                use_paid=tickflow_use_paid
            )
            logger.debug("TickFlow 数据获取器初始化成功")
        except Exception as e:
            logger.warning(f"TickFlow 初始化失败: {e}")
        
        # 检查至少有一个数据源可用
        if not self.akshare_fetcher and not self.efinance_fetcher and not self.tickflow_fetcher:
            raise DataFetchException("所有数据源初始化失败，无法获取数据")
    
    def _get_fetcher(self, source_type: DataSourceType) -> Optional[BaseDataFetcher]:
        """
        根据数据源类型获取对应的数据获取器
        
        Args:
            source_type: 数据源类型
        
        Returns:
            对应的数据获取器实例，如果不可用则返回 None
        """
        if source_type == DataSourceType.AKSHARE:
            return self.akshare_fetcher
        elif source_type == DataSourceType.EFINANCE:
            return self.efinance_fetcher
        elif source_type == DataSourceType.TICKFLOW:
            return self.tickflow_fetcher
        return None
    
    def _execute_with_fallback(
        self,
        method_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        执行方法并支持故障切换
        
        先尝试主数据源，如果失败且启用了故障切换，则尝试备用数据源。
        
        Args:
            method_name: 要执行的方法名
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            方法执行结果
        
        Raises:
            DataFetchException: 所有数据源都失败时抛出
        """
        # 确定数据源顺序
        if self.primary_source == DataSourceType.AUTO:
            sources = [DataSourceType.EFINANCE, DataSourceType.AKSHARE, DataSourceType.TICKFLOW]
        else:
            sources = [self.primary_source]
            if self.fallback_enabled:
                # 添加备用数据源
                for s in [DataSourceType.EFINANCE, DataSourceType.AKSHARE, DataSourceType.TICKFLOW]:
                    if s not in sources:
                        sources.append(s)
        
        last_error = None
        
        for source in sources:
            fetcher = self._get_fetcher(source)
            if not fetcher:
                continue
            
            try:
                logger.debug(f"尝试使用 {source.value} 执行 {method_name}")
                if not hasattr(fetcher, method_name) and source == DataSourceType.EFINANCE:
                    method_aliases = {
                        'get_daily_quotes': 'get_daily_data',
                        'get_financial_indicators': 'get_financial_data',
                    }
                    method_name_to_call = method_aliases.get(method_name, method_name)
                else:
                    method_name_to_call = method_name
                method = getattr(fetcher, method_name_to_call)
                result = self._call_fetcher_method(source, method_name, method, *args, **kwargs)
                if isinstance(result, pd.DataFrame) and result.empty:
                    raise DataFetchException(f"{source.value} 返回空数据")
                logger.debug(f"{source.value} 执行 {method_name} 成功")
                return result
            except Exception as e:
                logger.warning(f"{source.value} 执行 {method_name} 失败: {e}")
                last_error = e
                continue
        
        # 所有数据源都失败
        error_msg = f"所有数据源执行 {method_name} 失败"
        if last_error:
            error_msg += f": {last_error}"
        raise DataFetchException(error_msg)

    def _call_fetcher_method(
        self,
        source: DataSourceType,
        method_name: str,
        method,
        *args,
        **kwargs
    ) -> Any:
        """按数据源差异适配方法参数。"""
        if method_name == 'get_stock_list':
            exchange = args[0] if args else kwargs.get('exchange')
            if source == DataSourceType.EFINANCE:
                market_map = {'SH': 'sh', 'SZ': 'sz', 'BJ': 'bj', None: 'all'}
                return method(market=market_map.get(exchange, 'all'))
            if source == DataSourceType.AKSHARE:
                df = method()
                if exchange and 'exchange' in df.columns:
                    df = df[df['exchange'] == exchange]
                return df
            return method(exchange)

        if method_name == 'get_daily_quotes':
            symbol = args[0] if len(args) > 0 else kwargs.get('symbol')
            start_date = args[1] if len(args) > 1 else kwargs.get('start_date')
            end_date = args[2] if len(args) > 2 else kwargs.get('end_date')
            adjust = kwargs.get('adjust', 'qfq')
            if source == DataSourceType.EFINANCE:
                return method(symbol=symbol, start=start_date, end=end_date, adjust=adjust)
            return method(symbol, start_date, end_date)

        if method_name == 'get_financial_indicators' and source == DataSourceType.EFINANCE:
            symbol = args[0] if args else kwargs.get('symbol')
            return method(symbol)

        try:
            signature = inspect.signature(method)
            accepted_kwargs = {k: v for k, v in kwargs.items() if k in signature.parameters}
            return method(*args, **accepted_kwargs)
        except (TypeError, ValueError):
            return method(*args, **kwargs)
    
    def get_stock_list(self, exchange: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票列表
        
        从配置的主数据源获取A股股票列表。如果主数据源失败且启用了故障切换，
        会自动尝试备用数据源。
        
        Args:
            exchange: 交易所代码过滤，可选 'SH'(上海), 'SZ'(深圳), 'BJ'(北京)，
                     None 表示获取全部A股
        
        Returns:
            DataFrame 包含股票信息，列包括:
                - symbol: 股票代码 (如 '600000')
                - name: 股票名称
                - exchange: 交易所代码 (SH/SZ/BJ)
        
        Raises:
            DataFetchException: 所有数据源都失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> 
            >>> # 获取全部A股
            >>> all_stocks = fetcher.get_stock_list()
            >>> 
            >>> # 仅获取上交所股票
            >>> sh_stocks = fetcher.get_stock_list('SH')
        """
        return self._execute_with_fallback('get_stock_list', exchange)
    
    def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取日线行情数据
        
        获取指定股票的日K线数据，包括开盘价、最高价、最低价、收盘价、成交量等。
        默认使用前复权数据。
        
        Args:
            symbol: 股票代码，支持多种格式:
                   - '600000' (纯代码，自动判断交易所)
                   - '600000.SH' (带交易所后缀)
                   - 'SH600000' (带交易所前缀)
            start_date: 开始日期，格式 'YYYY-MM-DD' 或 'YYYYMMDD'，
                       None 表示获取全部历史数据
            end_date: 结束日期，格式同上，None 表示到最近交易日
            adjust: 复权类型，'qfq'(前复权), 'hfq'(后复权), 'none'(不复权)，默认前复权
        
        Returns:
            DataFrame 包含日线数据，列包括:
                - trade_date: 交易日期
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                - amount: 成交额
                - pct_change: 涨跌幅(%)
                - symbol: 股票代码
        
        Raises:
            DataFetchException: 所有数据源都失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> 
            >>> # 获取全部历史数据
            >>> df = fetcher.get_daily_quotes('600000')
            >>> 
            >>> # 获取指定日期范围
            >>> df = fetcher.get_daily_quotes('000001', 
            ...                               start_date='2024-01-01',
            ...                               end_date='2024-12-31')
        """
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        
        df = self._execute_with_fallback(
            'get_daily_quotes',
            symbol,
            start_date,
            end_date
        )
        if isinstance(df, pd.DataFrame):
            df = df.rename(columns={
                'date': 'trade_date',
                'change_percent': 'pct_change',
            })
            if 'symbol' not in df.columns:
                df['symbol'] = symbol
        return df
    
    def get_daily_quotes_incremental(
        self,
        symbol: str,
        last_date: Optional[date] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        增量获取日线数据
        
        用于数据库增量更新场景。根据数据库中最新日期，只获取新增的数据。
        
        Args:
            symbol: 股票代码
            last_date: 数据库中最新日期，None 表示获取全部历史
            end_date: 结束日期，None 表示到昨天
        
        Returns:
            DataFrame 新增的数据，如果已是最新则返回空 DataFrame
        
        Raises:
            DataFetchException: 数据获取失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> 
            >>> # 首次获取全部历史
            >>> df = fetcher.get_daily_quotes_incremental('600000')
            >>> 
            >>> # 增量更新（假设数据库最新日期是 2024-01-10）
            >>> from datetime import date
            >>> df = fetcher.get_daily_quotes_incremental('600000', 
            ...                                           last_date=date(2024, 1, 10))
        """
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        
        # 确定起始日期
        if last_date is None:
            start_date = None  # 获取全部
        else:
            next_date = last_date + timedelta(days=1)
            start_date = next_date.strftime('%Y-%m-%d')
        
        # 确定结束日期
        if end_date is None:
            yesterday = date.today() - timedelta(days=1)
            end_date = yesterday.strftime('%Y-%m-%d')
        
        # 检查是否需要更新
        if last_date and last_date >= date.today() - timedelta(days=1):
            logger.info(f"[{symbol}] 数据已是最新，无需更新")
            return pd.DataFrame()
        
        logger.info(f"[{symbol}] 增量更新: {start_date} ~ {end_date}")
        return self.get_daily_quotes(symbol, start_date, end_date)
    
    def get_minute_quotes(
        self,
        symbol: str,
        period: str = '5m',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取分钟级K线数据
        
        获取指定周期的分钟K线数据。注意：分钟级数据主要依赖 TickFlow，
        AKShare 对分钟数据支持有限。
        
        Args:
            symbol: 股票代码
            period: 分钟周期，支持 '1m', '5m', '15m', '30m', '60m'，默认 '5m'
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'
        
        Returns:
            DataFrame 分钟级数据，列包括:
                - datetime: 时间戳
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
                - symbol: 股票代码
        
        Raises:
            DataFetchException: 数据获取失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> 
            >>> # 获取5分钟K线
            >>> df = fetcher.get_minute_quotes('600000', period='5m')
            >>> 
            >>> # 获取1分钟K线（需要 TickFlow 付费版）
            >>> df = fetcher.get_minute_quotes('600000', period='1m')
        """
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        
        # 分钟数据优先使用 TickFlow
        if self.tickflow_fetcher:
            try:
                logger.debug(f"使用 TickFlow 获取分钟数据: {symbol}")
                return self.tickflow_fetcher.get_minute_quotes(
                    symbol, period, start_date, end_date
                )
            except Exception as e:
                logger.warning(f"TickFlow 获取分钟数据失败: {e}")
        
        # 尝试 AKShare（支持有限）
        if self.akshare_fetcher:
            try:
                logger.debug(f"使用 AKShare 获取分钟数据: {symbol}")
                # AKShare 分钟数据接口可能不同，这里调用通用方法
                return self._execute_with_fallback(
                    'get_minute_quotes',
                    symbol,
                    period,
                    start_date,
                    end_date
                )
            except Exception as e:
                logger.warning(f"AKShare 获取分钟数据失败: {e}")
        
        raise DataFetchException("无法获取分钟数据，请检查数据源配置")
    
    def get_realtime_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取实时行情数据
        
        获取多只股票的最新行情数据。实时行情主要依赖 TickFlow（尤其是付费版）。
        
        Args:
            symbols: 股票代码列表，如 ['600000', '000001', '000858']
        
        Returns:
            DataFrame 实时行情数据，列因数据源而异，通常包括:
                - symbol: 股票代码
                - name: 股票名称
                - price: 当前价格
                - change: 涨跌额
                - pct_change: 涨跌幅(%)
                - volume: 成交量
        
        Raises:
            DataFetchException: 数据获取失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> 
            >>> # 获取多只股票实时行情
            >>> df = fetcher.get_realtime_quotes(['600000', '000001', '000858'])
        """
        # 标准化股票代码列表
        symbols = [self._normalize_symbol(s) for s in symbols]
        
        # 实时行情优先使用 TickFlow
        if self.tickflow_fetcher:
            try:
                logger.debug(f"使用 TickFlow 获取实时行情: {len(symbols)} 只股票")
                return self.tickflow_fetcher.get_realtime_quotes(symbols)
            except Exception as e:
                logger.warning(f"TickFlow 获取实时行情失败: {e}")
        
        # 尝试 AKShare
        if self.akshare_fetcher:
            try:
                logger.debug(f"使用 AKShare 获取实时行情: {len(symbols)} 只股票")
                return self._execute_with_fallback('get_realtime_quotes', symbols)
            except Exception as e:
                logger.warning(f"AKShare 获取实时行情失败: {e}")
        
        raise DataFetchException("无法获取实时行情，请检查数据源配置")
    
    def get_financial_indicators(self, symbol: str) -> pd.DataFrame:
        """
        获取财务指标数据
        
        获取指定股票的核心财务指标，如每股收益(EPS)、净资产收益率(ROE)、
        营业收入、净利润等。
        
        Args:
            symbol: 股票代码
        
        Returns:
            DataFrame 财务指标数据，列因数据源而异，通常包括:
                - report_date: 报告期
                - eps: 每股收益
                - roe: 净资产收益率
                - revenue: 营业收入
                - net_profit: 净利润
                - symbol: 股票代码
        
        Raises:
            DataFetchException: 所有数据源都失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> df = fetcher.get_financial_indicators('600000')
        """
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        
        return self._execute_with_fallback('get_financial_indicators', symbol)
    
    def get_income_statement(self, symbol: str) -> pd.DataFrame:
        """
        获取利润表数据
        
        获取指定股票的利润表数据，包括营业收入、营业成本、营业利润、净利润等。
        
        Args:
            symbol: 股票代码
        
        Returns:
            DataFrame 利润表数据
        
        Raises:
            DataFetchException: 数据获取失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> df = fetcher.get_income_statement('600000')
        """
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        
        # 利润表优先使用 TickFlow
        if self.tickflow_fetcher:
            try:
                return self.tickflow_fetcher.get_income_statement(symbol)
            except Exception as e:
                logger.warning(f"TickFlow 获取利润表失败: {e}")
        
        # 尝试 AKShare
        return self._execute_with_fallback('get_income_statement', symbol)
    
    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """
        获取资产负债表数据
        
        获取指定股票的资产负债表数据，包括资产、负债、所有者权益等。
        
        Args:
            symbol: 股票代码
        
        Returns:
            DataFrame 资产负债表数据
        
        Raises:
            DataFetchException: 数据获取失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> df = fetcher.get_balance_sheet('600000')
        """
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        
        # 资产负债表优先使用 TickFlow
        if self.tickflow_fetcher:
            try:
                return self.tickflow_fetcher.get_balance_sheet(symbol)
            except Exception as e:
                logger.warning(f"TickFlow 获取资产负债表失败: {e}")
        
        # 尝试 AKShare
        return self._execute_with_fallback('get_balance_sheet', symbol)
    
    def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        """
        获取现金流量表数据
        
        获取指定股票的现金流量表数据，包括经营活动、投资活动、筹资活动现金流等。
        
        Args:
            symbol: 股票代码
        
        Returns:
            DataFrame 现金流量表数据
        
        Raises:
            DataFetchException: 数据获取失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> df = fetcher.get_cash_flow('600000')
        """
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        
        # 现金流量表优先使用 TickFlow
        if self.tickflow_fetcher:
            try:
                return self.tickflow_fetcher.get_cash_flow(symbol)
            except Exception as e:
                logger.warning(f"TickFlow 获取现金流量表失败: {e}")
        
        # 尝试 AKShare
        return self._execute_with_fallback('get_cash_flow', symbol)
    
    def get_instrument_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取标的信息
        
        获取指定股票的详细信息，如公司名称、行业、上市日期等。
        
        Args:
            symbol: 股票代码
        
        Returns:
            Dict 标的信息，可能包含:
                - symbol: 股票代码
                - name: 股票名称
                - exchange: 交易所
                - industry: 所属行业
                - list_date: 上市日期
        
        Raises:
            DataFetchException: 数据获取失败时抛出
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> info = fetcher.get_instrument_info('600000')
            >>> print(info['name'])  # 输出: 浦发银行
        """
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        
        # 标的信息优先使用 TickFlow
        if self.tickflow_fetcher:
            try:
                return self.tickflow_fetcher.get_instrument_info(symbol)
            except Exception as e:
                logger.warning(f"TickFlow 获取标的信息失败: {e}")
        
        # 尝试 AKShare
        return self._execute_with_fallback('get_instrument_info', symbol)
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码格式
        
        将各种格式的股票代码统一为纯数字代码（如 '600000'）。
        支持格式:
            - '600000' (纯代码)
            - '600000.SH' (带交易所后缀)
            - 'SH600000' (带交易所前缀)
        
        Args:
            symbol: 原始股票代码
        
        Returns:
            标准化的股票代码（纯数字）
        """
        symbol = symbol.upper().strip()
        
        # 移除交易所后缀
        if '.' in symbol:
            symbol = symbol.split('.')[0]
        
        # 移除交易所前缀
        if symbol.startswith('SH') or symbol.startswith('SZ') or symbol.startswith('BJ'):
            symbol = symbol[2:]
        
        return symbol
    
    def _get_exchange(self, symbol: str) -> str:
        """
        根据股票代码判断交易所
        
        Args:
            symbol: 股票代码（纯数字）
        
        Returns:
            交易所代码: 'SH'(上海), 'SZ'(深圳), 'BJ'(北京), 'UNKNOWN'(未知)
        """
        if symbol.startswith(('600', '601', '603', '605', '688', '689')):
            return 'SH'
        elif symbol.startswith(('000', '001', '002', '003', '300', '301')):
            return 'SZ'
        elif symbol.startswith(('8', '4', '92')):
            return 'BJ'
        else:
            return 'UNKNOWN'
    
    def is_available(self, source: Optional[DataSourceType] = None) -> bool:
        """
        检查数据源是否可用
        
        Args:
            source: 指定检查的数据源，None 表示检查主数据源
        
        Returns:
            bool 数据源是否可用
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> 
            >>> # 检查主数据源
            >>> if fetcher.is_available():
            ...     df = fetcher.get_stock_list()
            >>> 
            >>> # 检查特定数据源
            >>> if fetcher.is_available(DataSourceType.TICKFLOW):
            ...     print("TickFlow 可用")
        """
        if source is None:
            source = self.primary_source
        
        fetcher = self._get_fetcher(source)
        if not fetcher:
            return False
        
        # 尝试调用 is_available 方法
        if hasattr(fetcher, 'is_available'):
            try:
                return fetcher.is_available()
            except Exception:
                pass
        
        # 尝试获取股票列表来验证
        try:
            df = fetcher.get_stock_list()
            return len(df) > 0
        except Exception:
            return False
    
    def get_available_sources(self) -> List[str]:
        """
        获取当前可用的数据源列表
        
        Returns:
            List[str] 可用数据源名称列表
        
        示例:
            >>> fetcher = UnifiedDataFetcher()
            >>> sources = fetcher.get_available_sources()
            >>> print(sources)  # ['akshare', 'tickflow']
        """
        available = []
        
        for source in [DataSourceType.EFINANCE, DataSourceType.AKSHARE, DataSourceType.TICKFLOW]:
            if self.is_available(source):
                available.append(source.value)
        
        return available
    
    def __repr__(self) -> str:
        """
        字符串表示
        
        Returns:
            描述字符串
        """
        sources = self.get_available_sources()
        return (f"UnifiedDataFetcher(primary={self.primary_source.value}, "
                f"fallback={'on' if self.fallback_enabled else 'off'}, "
                f"available={sources})")
