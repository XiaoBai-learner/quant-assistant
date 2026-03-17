"""
TickFlow 数据获取器

基于 TickFlow API 获取行情数据
- 免费版: https://free-api.tickflow.org (无需 API Key)
- 付费版: https://api.tickflow.org (需要 API Key)

免费版支持:
  - 日K线数据 (1d, 1w, 1M, 1Q, 1Y)
  - 标的信息查询
  - 财务数据 (资产负债表/利润表/现金流量表)
  - 核心财务指标
  - 交易所列表

付费版额外支持:
  - 分钟级K线 (1m, 5m, 15m, 30m, 60m)
  - 实时行情
  - 更高频率访问

文档: https://docs.tickflow.org/zh-Hans
"""
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Union
import time
import logging

import sys
import os

# 处理导入路径
try:
    from quant_assistant.data.fetcher.base_fetcher import BaseDataFetcher
    from quant_assistant.utils.logger import get_logger
    from quant_assistant.core.exceptions import DataFetchException
    logger = get_logger(__name__)
except ImportError:
    # 独立运行时使用的简化版本
    # 添加父目录到路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    fetcher_dir = current_dir
    if fetcher_dir not in sys.path:
        sys.path.insert(0, fetcher_dir)
    
    from base_fetcher import BaseDataFetcher
    logger = logging.getLogger(__name__)
    
    class DataFetchException(Exception):
        """数据获取异常"""
        def __init__(self, message, symbol=None):
            super().__init__(message)
            self.symbol = symbol


class TickFlowFetcher(BaseDataFetcher):
    """
    TickFlow 数据获取器
    
    支持免费版和付费版 API 切换
    免费版无需注册即可使用日K线等基础数据
    付费版需要 API Key，支持实时行情和分钟级数据
    
    示例:
        >>> # 免费版使用（无需 API Key）
        >>> fetcher = TickFlowFetcher()
        >>> df = fetcher.get_daily_quotes('600000.SH', start_date='2024-01-01')
        >>> 
        >>> # 付费版使用（需要 API Key）
        >>> fetcher = TickFlowFetcher(api_key='your-api-key', use_paid=True)
        >>> df = fetcher.get_minute_quotes('600000.SH', period='1m')
    """
    
    # API 基础地址
    FREE_API_BASE = "https://free-api.tickflow.org"
    PAID_API_BASE = "https://api.tickflow.org"
    
    def __init__(self, api_key: Optional[str] = None, use_paid: bool = False):
        """
        初始化 TickFlow 获取器
        
        Args:
            api_key: API Key，付费版必需，免费版可选
            use_paid: 是否使用付费版 API，默认使用免费版
        """
        self.name = "TickFlow"
        self.api_key = api_key
        self.use_paid = use_paid
        self.base_url = self.PAID_API_BASE if use_paid else self.FREE_API_BASE
        self.rate_limit_delay = 0.5  # 速率限制延迟
        
        # 检查付费版配置
        if use_paid and not api_key:
            logger.warning("使用付费版但未提供 API Key，部分接口可能无法访问")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        if self.api_key:
            headers['x-api-key'] = self.api_key
        return headers
    
    def _rate_limit(self):
        """速率限制"""
        time.sleep(self.rate_limit_delay)
    
    def _request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        method: str = 'GET'
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求
        
        Args:
            endpoint: API 端点路径
            params: 请求参数
            method: 请求方法 GET/POST
            
        Returns:
            JSON 响应数据
            
        Raises:
            DataFetchException: 请求失败时抛出
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            self._rate_limit()
            
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            else:
                response = requests.post(url, json=params, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TickFlow API 请求失败: {url}, 错误: {e}")
            raise DataFetchException(f"TickFlow API 请求失败: {e}") from e
        except Exception as e:
            logger.error(f"TickFlow API 响应解析失败: {e}")
            raise DataFetchException(f"TickFlow API 响应解析失败: {e}") from e
    
    def _convert_symbol(self, symbol: str) -> str:
        """
        转换股票代码格式
        
        TickFlow 格式: 600000.SH, 000001.SZ
        输入可能格式: 600000, 600000.SH, sh600000
        
        Args:
            symbol: 股票代码
            
        Returns:
            标准格式的股票代码 (如 600000.SH)
        """
        symbol = symbol.upper().strip()
        
        # 已经是标准格式
        if '.' in symbol:
            return symbol
        
        # 根据代码前缀判断交易所
        if symbol.startswith(('600', '601', '603', '605', '688', '689')):
            return f"{symbol}.SH"
        elif symbol.startswith(('000', '001', '002', '003', '300', '301')):
            return f"{symbol}.SZ"
        elif symbol.startswith(('8', '4', '92')):
            return f"{symbol}.BJ"
        elif symbol.startswith('SH'):
            return f"{symbol[2:]}.SH"
        elif symbol.startswith('SZ'):
            return f"{symbol[2:]}.SZ"
        else:
            # 默认上海
            logger.warning(f"无法确定交易所，默认上海: {symbol}")
            return f"{symbol}.SH"
    
    def _convert_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        转换日期格式为 YYYY-MM-DD
        
        Args:
            date_str: 输入日期字符串
            
        Returns:
            标准格式日期字符串或 None
        """
        if not date_str:
            return None
        
        # 尝试解析多种格式
        formats = ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        logger.warning(f"无法解析日期格式: {date_str}")
        return date_str
    
    def get_exchanges(self) -> pd.DataFrame:
        """
        获取交易所列表
        
        Returns:
            DataFrame 包含交易所信息
            
        示例:
            >>> fetcher = TickFlowFetcher()
            >>> exchanges = fetcher.get_exchanges()
        """
        try:
            logger.info("获取交易所列表...")
            data = self._request('/v1/exchanges')
            
            # API 返回的是 {data: [...]} 格式
            exchanges = data.get('data', [])
            df = pd.DataFrame(exchanges)
            
            logger.info(f"获取到 {len(df)} 个交易所")
            return df
            
        except Exception as e:
            logger.error(f"获取交易所列表失败: {e}")
            raise DataFetchException(f"无法获取交易所列表: {e}") from e
    
    def get_stock_list(self, exchange: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            exchange: 交易所代码，如 'SH', 'SZ', 'BJ'，None表示获取全部
            
        Returns:
            DataFrame 包含股票代码和名称
            
        示例:
            >>> fetcher = TickFlowFetcher()
            >>> # 获取全部A股
            >>> stocks = fetcher.get_stock_list()
            >>> 
            >>> # 获取上交所股票
            >>> sh_stocks = fetcher.get_stock_list('SH')
        """
        try:
            if exchange:
                logger.info(f"获取 {exchange} 交易所股票列表...")
                data = self._request(f'/v1/exchanges/{exchange}/instruments')
                # API 返回的是 {data: [...]} 格式
                instruments = data.get('data', [])
            else:
                logger.info("获取全部股票列表...")
                # 获取所有交易所的股票
                exchanges = ['SH', 'SZ', 'BJ']
                instruments = []
                for ex in exchanges:
                    try:
                        data = self._request(f'/v1/exchanges/{ex}/instruments')
                        instruments.extend(data.get('data', []))
                    except Exception as e:
                        logger.warning(f"获取 {ex} 交易所数据失败: {e}")
            
            if not instruments:
                logger.warning("未获取到股票数据")
                return pd.DataFrame()
            
            # 转换为 DataFrame
            df = pd.DataFrame(instruments)
            
            # 标准化列名
            column_mapping = {
                'symbol': 'symbol',
                'name': 'name',
                'exchange': 'exchange',
                'type': 'type',
                'list_date': 'list_date',
            }
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            # 确保有 symbol 列
            if 'symbol' not in df.columns and 'code' in df.columns:
                df['symbol'] = df['code']
            
            logger.info(f"获取到 {len(df)} 只股票")
            return df[['symbol', 'name', 'exchange']] if 'type' not in df.columns else df
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise DataFetchException(f"无法获取股票列表: {e}") from e
    
    def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取日线行情数据
        
        Args:
            symbol: 股票代码，如 '600000' 或 '600000.SH'
            start_date: 开始日期，如 '2024-01-01'
            end_date: 结束日期，如 '2024-12-31'
            
        Returns:
            DataFrame 包含 OHLCV 数据
            
        示例:
            >>> fetcher = TickFlowFetcher()
            >>> df = fetcher.get_daily_quotes('600000.SH', start_date='2024-01-01')
        """
        try:
            # 转换代码格式
            symbol = self._convert_symbol(symbol)
            start = self._convert_date(start_date)
            end = self._convert_date(end_date)
            
            logger.info(f"获取 {symbol} 日线数据: {start} ~ {end}")
            
            # 构建参数
            params = {'symbol': symbol, 'period': '1d'}
            if start:
                params['start'] = start
            if end:
                params['end'] = end
            
            data = self._request('/v1/klines', params)
            # API 返回的是 {data: {timestamp: [...], open: [...], ...}} 格式
            klines_data = data.get('data', {})
            
            if not klines_data or not klines_data.get('timestamp'):
                logger.warning(f"{symbol} 在指定日期范围内无数据")
                return pd.DataFrame()
            
            # 转换为 DataFrame
            df = pd.DataFrame({
                'trade_date': klines_data.get('timestamp', []),
                'open': klines_data.get('open', []),
                'high': klines_data.get('high', []),
                'low': klines_data.get('low', []),
                'close': klines_data.get('close', []),
                'volume': klines_data.get('volume', []),
                'amount': klines_data.get('amount', []),
            })
            
            # 处理日期 (timestamp 是毫秒时间戳)
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'], unit='ms').dt.date
            
            # 添加 symbol 列
            df['symbol'] = symbol.split('.')[0]
            
            logger.info(f"获取到 {len(df)} 条日线数据")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 日线数据失败: {e}")
            raise DataFetchException(f"无法获取 {symbol} 日线数据: {e}", symbol=symbol) from e
    
    def get_daily_quotes_incremental(
        self,
        symbol: str,
        last_date: Optional[date] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        增量获取日线数据
        
        Args:
            symbol: 股票代码
            last_date: 数据库中最新日期，None表示获取全部历史
            end_date: 结束日期，默认昨天
            
        Returns:
            DataFrame: 新增的数据
        """
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
        period: str = '1m',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取分钟级K线数据 (⚠️ 需要付费版)
        
        Args:
            symbol: 股票代码
            period: 分钟周期，支持 '1m', '5m', '15m', '30m', '60m'
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame 分钟级数据
            
        Raises:
            DataFetchException: 免费版使用此接口会报错
            
        示例:
            >>> # 付费版使用
            >>> fetcher = TickFlowFetcher(api_key='xxx', use_paid=True)
            >>> df = fetcher.get_minute_quotes('600000.SH', period='5m')
        """
        if not self.use_paid:
            raise DataFetchException(
                "分钟级数据需要 TickFlow 付费版。"
                "请使用 TickFlowFetcher(api_key='your-key', use_paid=True) 初始化"
            )
        
        try:
            symbol = self._convert_symbol(symbol)
            start = self._convert_date(start_date)
            end = self._convert_date(end_date)
            
            logger.info(f"获取 {symbol} {period} 分钟数据: {start} ~ {end}")
            
            params = {'symbol': symbol, 'period': period}
            if start:
                params['start'] = start
            if end:
                params['end'] = end
            
            data = self._request('/v1/klines', params)
            klines = data.get('klines', [])
            
            if not klines:
                return pd.DataFrame()
            
            df = pd.DataFrame(klines)
            df = df.rename(columns={
                'timestamp': 'datetime',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount',
            })
            
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            
            df['symbol'] = symbol.split('.')[0]
            
            logger.info(f"获取到 {len(df)} 条分钟数据")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 分钟数据失败: {e}")
            raise DataFetchException(f"无法获取 {symbol} 分钟数据: {e}", symbol=symbol) from e
    
    def get_realtime_quotes(self, symbols: List[str]) -> pd.DataFrame:
        """
        获取实时行情 (⚠️ 需要付费版)
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            DataFrame 实时行情数据
            
        Raises:
            DataFetchException: 免费版使用此接口会报错
        """
        if not self.use_paid:
            raise DataFetchException(
                "实时行情需要 TickFlow 付费版。"
                "请使用 TickFlowFetcher(api_key='your-key', use_paid=True) 初始化"
            )
        
        try:
            # 转换代码格式
            symbol_list = [self._convert_symbol(s) for s in symbols]
            
            logger.info(f"获取 {len(symbol_list)} 只股票实时行情...")
            
            params = {'symbols': symbol_list}
            data = self._request('/v1/quotes', params, method='POST')
            quotes = data.get('quotes', [])
            
            if not quotes:
                return pd.DataFrame()
            
            df = pd.DataFrame(quotes)
            logger.info(f"获取到 {len(df)} 条实时行情")
            return df
            
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            raise DataFetchException(f"无法获取实时行情: {e}") from e
    
    def get_financial_indicators(self, symbol: str) -> pd.DataFrame:
        """
        获取财务指标数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame 财务指标数据
            
        示例:
            >>> fetcher = TickFlowFetcher()
            >>> df = fetcher.get_financial_indicators('600000.SH')
        """
        try:
            symbol = self._convert_symbol(symbol)
            logger.info(f"获取 {symbol} 财务指标...")
            
            params = {'symbols': symbol}
            data = self._request('/v1/financials/metrics', params)
            metrics = data.get('data', [])
            
            if not metrics:
                logger.warning(f"{symbol} 无财务指标数据")
                return pd.DataFrame()
            
            df = pd.DataFrame(metrics)
            df['symbol'] = symbol.split('.')[0]
            
            logger.info(f"获取到 {len(df)} 条财务指标")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 财务指标失败: {e}")
            # 财务数据可能不存在，返回空DataFrame
            return pd.DataFrame()
    
    def get_income_statement(self, symbol: str) -> pd.DataFrame:
        """
        获取利润表数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame 利润表数据
        """
        try:
            symbol = self._convert_symbol(symbol)
            logger.info(f"获取 {symbol} 利润表...")
            
            params = {'symbols': symbol}
            data = self._request('/v1/financials/income', params)
            income_data = data.get('data', [])
            
            if not income_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(income_data)
            df['symbol'] = symbol.split('.')[0]
            
            logger.info(f"获取到 {len(df)} 条利润表数据")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 利润表失败: {e}")
            return pd.DataFrame()
    
    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """
        获取资产负债表数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame 资产负债表数据
        """
        try:
            symbol = self._convert_symbol(symbol)
            logger.info(f"获取 {symbol} 资产负债表...")
            
            params = {'symbols': symbol}
            data = self._request('/v1/financials/balance-sheet', params)
            balance_data = data.get('data', [])
            
            if not balance_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(balance_data)
            df['symbol'] = symbol.split('.')[0]
            
            logger.info(f"获取到 {len(df)} 条资产负债表数据")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 资产负债表失败: {e}")
            return pd.DataFrame()
    
    def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        """
        获取现金流量表数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame 现金流量表数据
        """
        try:
            symbol = self._convert_symbol(symbol)
            logger.info(f"获取 {symbol} 现金流量表...")
            
            params = {'symbols': symbol}
            data = self._request('/v1/financials/cash-flow', params)
            cashflow_data = data.get('data', [])
            
            if not cashflow_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(cashflow_data)
            df['symbol'] = symbol.split('.')[0]
            
            logger.info(f"获取到 {len(df)} 条现金流量表数据")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 现金流量表失败: {e}")
            return pd.DataFrame()
    
    def get_instrument_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取标的信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict 标的信息
        """
        try:
            symbol = self._convert_symbol(symbol)
            logger.info(f"获取 {symbol} 标的信息...")
            
            params = {'symbols': symbol}
            data = self._request('/v1/instruments', params)
            instruments = data.get('instruments', [])
            
            if instruments:
                return instruments[0]
            return {}
            
        except Exception as e:
            logger.error(f"获取 {symbol} 标的信息失败: {e}")
            return {}
    
    def is_available(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            bool 服务是否可用
        """
        try:
            self._request('/v1/exchanges')
            return True
        except Exception:
            return False
    
    def __repr__(self) -> str:
        """字符串表示"""
        version = "付费版" if self.use_paid else "免费版"
        return f"TickFlowFetcher({version}, api_key={'已设置' if self.api_key else '未设置'})"
