"""
EFinance 数据获取器

基于 efinance 库获取细粒度、高时效性的股票数据
支持分钟级、分笔级数据获取

依赖:
    pip install efinance

示例:
    >>> from quant_assistant.data.fetcher.efinance_fetcher import EFinanceFetcher
    >>> fetcher = EFinanceFetcher()
    >>> 
    >>> # 获取实时行情
    >>> realtime = fetcher.get_realtime_quotes('300751')
    >>> 
    >>> # 获取分钟数据
    >>> minute_data = fetcher.get_minute_data('300751', period=1)
    >>> 
    >>> # 获取分笔数据
    >>> tick_data = fetcher.get_tick_data('300751')
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EFinanceFetcher:
    """
    EFinance 数据获取器
    
    提供细粒度、高时效性的股票数据获取功能
    """
    
    def __init__(self):
        self._efinance = None
        self._try_import()
    
    def _try_import(self):
        """尝试导入 efinance 库"""
        try:
            import efinance as ef
            self._efinance = ef
            logger.info("EFinance 库加载成功")
        except ImportError:
            logger.warning("EFinance 库未安装，请运行: pip install efinance")
            self._efinance = None
    
    def is_available(self) -> bool:
        """检查 EFinance 是否可用"""
        return self._efinance is not None
    
    def get_realtime_quotes(
        self,
        symbols: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取实时行情数据
        
        Args:
            symbols: 股票代码列表，None表示获取全市场
            
        Returns:
            DataFrame 包含实时行情
            
        示例:
            >>> # 获取单只股票
            >>> df = fetcher.get_realtime_quotes(['300751'])
            >>> 
            >>> # 获取多只股票
            >>> df = fetcher.get_realtime_quotes(['300751', '000001'])
            >>> 
            >>> # 获取全市场（约5000+股票）
            >>> df = fetcher.get_realtime_quotes()
        """
        if not self.is_available():
            raise ImportError("EFinance 库未安装，请运行: pip install efinance")
        
        try:
            if symbols is None:
                # 获取全市场实时行情
                df = self._efinance.stock.get_realtime_quotes()
            else:
                # 获取指定股票
                df = self._efinance.stock.get_realtime_quotes(symbols)
            
            # 标准化列名
            df = self._standardize_realtime_columns(df)
            logger.info(f"获取实时行情成功: {len(df)} 条数据")
            return df
            
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            raise
    
    def _standardize_realtime_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化实时行情列名"""
        column_mapping = {
            '股票代码': 'symbol',
            '股票名称': 'name',
            '最新价': 'close',
            '最新时间': 'time',
            '涨跌额': 'change_amount',
            '涨跌幅': 'change_percent',
            '成交量': 'volume',
            '成交额': 'amount',
            '开盘价': 'open',
            '最高价': 'high',
            '最低价': 'low',
            '昨收': 'pre_close',
            '换手率': 'turnover',
            '市盈率': 'pe',
            '振幅': 'amplitude',
            '量比': 'volume_ratio',
            '委比': 'order_ratio',
            '委差': 'order_diff',
            '外盘': 'outer_disc',
            '内盘': 'inner_disc',
            '总市值': 'total_market_cap',
            '流通市值': 'float_market_cap',
            '涨速': 'rise_speed',
            '5分钟涨跌': 'change_5min',
            '60日涨跌幅': 'change_60d',
            '年初至今涨跌幅': 'change_ytd',
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        return df
    
    def get_minute_data(
        self,
        symbol: str,
        period: int = 1,
        adjust: str = 'qfq',
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取分钟级历史数据
        
        Args:
            symbol: 股票代码，如 '300751'
            period: 分钟周期，支持 1, 5, 15, 30, 60
            adjust: 复权类型，'qfq'前复权, 'hfq'后复权, ''不复权
            start: 开始日期，如 '2024-01-01'
            end: 结束日期，如 '2024-12-31'
            
        Returns:
            DataFrame 分钟级数据
            
        示例:
            >>> # 获取1分钟数据
            >>> df = fetcher.get_minute_data('300751', period=1)
            >>> 
            >>> # 获取5分钟数据
            >>> df = fetcher.get_minute_data('300751', period=5)
            >>> 
            >>> # 获取指定日期范围的60分钟数据
            >>> df = fetcher.get_minute_data('300751', period=60, 
            ...                              start='2024-01-01', end='2024-01-31')
        """
        if not self.is_available():
            raise ImportError("EFinance 库未安装，请运行: pip install efinance")
        
        try:
            # 转换日期格式
            begin_date = start.replace('-', '') if start else None
            end_date = end.replace('-', '') if end else None
            
            df = self._efinance.stock.get_quote_history(
                symbol,
                klt=period,
                fqt=adjust,
                beg=begin_date,
                end=end_date
            )
            
            # 标准化列名
            df = self._standardize_history_columns(df)
            logger.info(f"获取分钟数据成功: {symbol}, {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取分钟数据失败 {symbol}: {e}")
            raise
    
    def get_tick_data(
        self,
        symbol: str,
        date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取分笔数据（tick级）
        
        Args:
            symbol: 股票代码，如 '300751'
            date: 日期，如 '2024-01-01'，None表示今天
            
        Returns:
            DataFrame 分笔成交数据
            
        示例:
            >>> # 获取今天分笔数据
            >>> df = fetcher.get_tick_data('300751')
            >>> 
            >>> # 获取指定日期分笔数据
            >>> df = fetcher.get_tick_data('300751', date='2024-01-15')
        """
        if not self.is_available():
            raise ImportError("EFinance 库未安装，请运行: pip install efinance")
        
        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')
            
            df = self._efinance.stock.get_deal_detail(symbol, date)
            
            # 标准化列名
            df = self._standardize_tick_columns(df)
            logger.info(f"获取分笔数据成功: {symbol}, {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取分笔数据失败 {symbol}: {e}")
            raise
    
    def _standardize_tick_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化分笔数据列名"""
        column_mapping = {
            '时间': 'time',
            '价格': 'price',
            '成交量': 'volume',
            '笔数': 'orders',
            '方向': 'direction',
            '主动买卖': 'active_side',
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        return df
    
    def get_daily_data(
        self,
        symbol: str,
        adjust: str = 'qfq',
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取日K线数据
        
        Args:
            symbol: 股票代码
            adjust: 复权类型
            start: 开始日期
            end: 结束日期
            
        Returns:
            DataFrame 日K数据
        """
        if not self.is_available():
            raise ImportError("EFinance 库未安装，请运行: pip install efinance")
        
        try:
            begin_date = start.replace('-', '') if start else None
            end_date = end.replace('-', '') if end else None
            
            df = self._efinance.stock.get_quote_history(
                symbol,
                klt=101,  # 日K
                fqt=adjust,
                beg=begin_date,
                end=end_date
            )
            
            df = self._standardize_history_columns(df)
            logger.info(f"获取日K数据成功: {symbol}, {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取日K数据失败 {symbol}: {e}")
            raise
    
    def _standardize_history_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化历史数据列名"""
        column_mapping = {
            '日期': 'date',
            '时间': 'datetime',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'change_percent',
            '涨跌额': 'change_amount',
            '换手率': 'turnover',
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # 确保有 datetime 列
        if 'datetime' in df.columns and 'date' not in df.columns:
            df['date'] = pd.to_datetime(df['datetime']).dt.date
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            
        return df
    
    def get_stock_list(self, market: str = 'all') -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: 市场类型，'all', 'sh', 'sz', 'bj'
            
        Returns:
            DataFrame 股票列表
        """
        if not self.is_available():
            raise ImportError("EFinance 库未安装，请运行: pip install efinance")
        
        try:
            df = self._efinance.stock.get_stock_list()
            
            # 根据市场过滤
            if market == 'sh':
                df = df[df['股票代码'].str.startswith(('60', '68', '51', '11'))]
            elif market == 'sz':
                df = df[df['股票代码'].str.startswith(('00', '30', '15', '12'))]
            elif market == 'bj':
                df = df[df['股票代码'].str.startswith(('8', '4', '92'))]
            
            # 标准化列名
            df = df.rename(columns={
                '股票代码': 'symbol',
                '股票名称': 'name',
            })
            
            logger.info(f"获取股票列表成功: {len(df)} 只")
            return df
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise
    
    def get_financial_data(
        self,
        symbol: str,
        report_type: str = 'quarterly'
    ) -> pd.DataFrame:
        """
        获取财务数据
        
        Args:
            symbol: 股票代码
            report_type: 报告类型，'quarterly'季报, 'annual'年报
            
        Returns:
            DataFrame 财务数据
        """
        if not self.is_available():
            raise ImportError("EFinance 库未安装，请运行: pip install efinance")
        
        try:
            if report_type == 'quarterly':
                df = self._efinance.stock.get_report_data(symbol)
            else:
                df = self._efinance.stock.get_report_data(symbol, data_type='annual')
            
            logger.info(f"获取财务数据成功: {symbol}, {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取财务数据失败 {symbol}: {e}")
            raise
    
    def get_sector_data(self, sector_type: str = 'industry') -> pd.DataFrame:
        """
        获取板块数据
        
        Args:
            sector_type: 板块类型，'industry'行业, 'concept'概念, 'area'地域
            
        Returns:
            DataFrame 板块数据
        """
        if not self.is_available():
            raise ImportError("EFinance 库未安装，请运行: pip install efinance")
        
        try:
            if sector_type == 'industry':
                df = self._efinance.stock.get_industry_plate()
            elif sector_type == 'concept':
                df = self._efinance.stock.get_concept_plate()
            elif sector_type == 'area':
                df = self._efinance.stock.get_area_plate()
            else:
                raise ValueError(f"不支持的板块类型: {sector_type}")
            
            logger.info(f"获取板块数据成功: {sector_type}, {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            raise
    
    def get_intraday_data(
        self,
        symbol: str,
        freq: str = '1min'
    ) -> pd.DataFrame:
        """
        获取当日分时数据
        
        Args:
            symbol: 股票代码
            freq: 频率，'1min', '5min'
            
        Returns:
            DataFrame 分时数据
        """
        if not self.is_available():
            raise ImportError("EFinance 库未安装，请运行: pip install efinance")
        
        try:
            period_map = {'1min': 1, '5min': 5}
            period = period_map.get(freq, 1)
            
            df = self._efinance.stock.get_quote_history(
                symbol,
                klt=period,
                beg=datetime.now().strftime('%Y%m%d'),
                end=datetime.now().strftime('%Y%m%d')
            )
            
            df = self._standardize_history_columns(df)
            logger.info(f"获取分时数据成功: {symbol}, {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取分时数据失败 {symbol}: {e}")
            raise
