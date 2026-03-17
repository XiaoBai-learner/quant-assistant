"""数据获取模块"""
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

__all__ = ['BaseDataFetcher', 'AKShareFetcher', 'EFinanceFetcher', 'TickFlowFetcher']
