"""
数据管理模块

提供数据获取、存储、查询和缓存功能。

支持多种数据源:
    - AKShare: 免费开源数据，适合历史数据
    - EFinance: 细粒度实时数据，支持分钟级、分笔级
    - TickFlow: 稳定行情数据服务，支持免费/付费版
      * 免费版: 日K线、财务数据、标的信息（无需API Key）
      * 付费版: 分钟级K线、实时行情（需要API Key）

示例:
    >>> from quant_assistant.data import DataFetcher, EFinanceFetcher, MySQLStorage
    >>> 
    >>> # 使用 EFinance 获取实时数据
    >>> fetcher = EFinanceFetcher()
    >>> realtime = fetcher.get_realtime_quotes(['300751'])
    >>> 
    >>> # 获取分钟级数据
    >>> minute_data = fetcher.get_minute_data('300751', period=5)
    >>> 
    >>> # 获取分笔数据
    >>> tick_data = fetcher.get_tick_data('300751')
    >>> 
    >>> # 使用 TickFlow 免费版获取日K线
    >>> from quant_assistant.data import TickFlowFetcher
    >>> tickflow = TickFlowFetcher()  # 免费版，无需API Key
    >>> daily = tickflow.get_daily_quotes('600000.SH', start_date='2024-01-01')
    >>> 
    >>> # 使用 TickFlow 付费版获取分钟数据
    >>> tickflow_paid = TickFlowFetcher(api_key='your-key', use_paid=True)
    >>> minute = tickflow_paid.get_minute_quotes('600000.SH', period='5m')
"""

from quant_assistant.data.fetcher import BaseDataFetcher, AKShareFetcher, EFinanceFetcher, TickFlowFetcher
from quant_assistant.data.storage import MySQLStorage
from quant_assistant.data.query import DataQueryEngine
from quant_assistant.data.cache import DataCache, MemoryCache, CacheEntry

__all__ = [
    'BaseDataFetcher',
    'AKShareFetcher',
    'EFinanceFetcher',
    'TickFlowFetcher',
    'MySQLStorage',
    'DataQueryEngine',
    'DataCache',
    'MemoryCache',
    'CacheEntry',
]
