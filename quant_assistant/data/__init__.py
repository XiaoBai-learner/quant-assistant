"""
数据管理模块

提供数据获取、存储、查询和缓存功能。

支持多种数据源:
    - AKShare: 免费开源数据，适合历史数据
    - EFinance: 细粒度实时数据，支持分钟级、分笔级
    - TickFlow: 稳定行情数据服务，支持免费/付费版
      * 免费版: 日K线、财务数据、标的信息（无需API Key）
      * 付费版: 分钟级K线、实时行情（需要API Key）
    
推荐使用 UnifiedDataFetcher（统一数据获取器）:
    - 整合 AKShare、EFinance、TickFlow 多个数据源
    - 支持配置化数据源选择
    - 支持故障自动切换
    - 统一对外接口

示例:
    >>> from quant_assistant.data import UnifiedDataFetcher, DataSourceType
    >>> 
    >>> # 使用统一数据获取器（推荐）
    >>> fetcher = UnifiedDataFetcher()  # 默认 AKShare 为主
    >>> df = fetcher.get_daily_quotes('600000', start_date='2024-01-01')
    >>> 
    >>> # 指定 TickFlow 为主数据源
    >>> fetcher = UnifiedDataFetcher(primary_source='tickflow')
    >>> 
    >>> # 使用 EFinance 获取实时数据
    >>> from quant_assistant.data import EFinanceFetcher
    >>> ef = EFinanceFetcher()
    >>> realtime = ef.get_realtime_quotes(['300751'])
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

from quant_assistant.data.fetcher import (
    BaseDataFetcher,
    AKShareFetcher,
    EFinanceFetcher,
    TickFlowFetcher,
    UnifiedDataFetcher,  # 统一数据获取器（推荐）
    DataSourceType,
)
from quant_assistant.data.storage import MySQLStorage
from quant_assistant.data.query import DataQueryEngine
from quant_assistant.data.cache import DataCache, MemoryCache, CacheEntry
from quant_assistant.data.local_cache import AshareCacheUpdater, AshareDailyCache
from quant_assistant.data.hub import DataHub

# 为向后兼容保留别名
DataFetcher = UnifiedDataFetcher

__all__ = [
    # 数据获取器 - 统一数据获取器（推荐）
    'UnifiedDataFetcher',
    'DataFetcher',  # 别名，向后兼容
    'DataSourceType',
    
    # 数据获取器 - 特定数据源
    'BaseDataFetcher',
    'AKShareFetcher',
    'EFinanceFetcher',
    'TickFlowFetcher',
    
    # 存储和查询
    'DataHub',
    'MySQLStorage',
    'DataQueryEngine',
    
    # 缓存
    'AshareCacheUpdater',
    'AshareDailyCache',
    'DataCache',
    'MemoryCache',
    'CacheEntry',
]
