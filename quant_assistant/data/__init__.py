"""
数据管理模块

提供数据获取、存储、查询和缓存功能。

支持多种数据源:
    - AKShare: 免费开源数据，适合历史数据
    - EFinance: 细粒度实时数据，支持分钟级、分笔级

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
"""

from quant_assistant.data.fetcher import DataFetcher, EFinanceFetcher
from quant_assistant.data.storage import MySQLStorage
from quant_assistant.data.query import DataQuery
from quant_assistant.data.cache import CacheManager
from quant_assistant.data.validator import DataValidator

__all__ = [
    'DataFetcher',
    'EFinanceFetcher',
    'MySQLStorage',
    'DataQuery',
    'CacheManager',
    'DataValidator',
]
