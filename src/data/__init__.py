"""
数据管理层 - Phase 1
提供数据获取、存储、查询的统一接口
"""
from .fetcher import AKShareFetcher, BaseDataFetcher
from .storage import MySQLStorage, BaseStorage
from .query import DataQueryEngine
from .database import db_manager, Stock, DailyQuote, FinancialIndicator

__version__ = "1.0.0"
__all__ = [
    # Fetcher
    'AKShareFetcher', 'BaseDataFetcher',
    # Storage
    'MySQLStorage', 'BaseStorage',
    # Query
    'DataQueryEngine',
    # Database
    'db_manager', 'Stock', 'DailyQuote', 'FinancialIndicator'
]
