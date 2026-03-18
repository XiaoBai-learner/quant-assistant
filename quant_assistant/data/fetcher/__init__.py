"""数据获取模块

提供多种数据获取器的实现:
    - BaseDataFetcher: 数据获取器基类
    - AKShareFetcher: AKShare 数据源实现
    - EFinanceFetcher: EFinance 数据源实现
    - TickFlowFetcher: TickFlow 数据源实现
    - UnifiedDataFetcher: 统一数据获取器（推荐）

推荐使用 UnifiedDataFetcher，它整合了多个数据源并支持故障自动切换。
"""
from .base_fetcher import BaseDataFetcher

# 延迟导入，避免未安装依赖时出错
try:
    from .akshare_fetcher import AKShareFetcher
except ImportError:
    AKShareFetcher = None

try:
    from .efinance_fetcher import EFinanceFetcher
except ImportError:
    EFinanceFetcher = None

# TickFlow 数据获取器（无需额外依赖，使用标准库 requests）
from .tickflow_fetcher import TickFlowFetcher

# 统一数据获取器（推荐）
from .unified_fetcher import UnifiedDataFetcher, DataSourceType

__all__ = [
    'BaseDataFetcher',
    'AKShareFetcher',
    'EFinanceFetcher',
    'TickFlowFetcher',
    'UnifiedDataFetcher',  # 统一数据获取器（推荐）
    'DataSourceType',
]
