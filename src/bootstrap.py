"""
服务注册和启动模块
配置依赖注入容器，注册所有服务
"""
from src.core.container import get_container, register_type, register_instance
from src.core.interfaces import (
    IBroker, IPortfolio, IPerformanceAnalyzer,
    IDataFetcher, IDataStorage, IDataValidator,
    IStrategy, IRiskManager
)

# 导入具体实现
from src.backtest.broker import Broker
from src.backtest.portfolio import Portfolio
from src.backtest.performance import PerformanceAnalyzer
from src.backtest.engine import BacktestConfig
from src.data.fetcher.akshare_fetcher import AKShareFetcher
from src.data.storage.mysql_storage import MySQLStorage
from src.data.validator import DataValidator
from src.risk.manager import RiskManager
from src.config_manager import Config, get_config


def register_services():
    """
    注册所有服务到依赖注入容器
    
    在应用启动时调用一次
    """
    container = get_container()
    
    # 1. 注册配置
    config = get_config()
    container.set_config('config', config)
    container.set_config('db_config', config.database)
    container.set_config('data_config', config.data)
    
    # 2. 注册数据层服务
    register_type(IDataFetcher, AKShareFetcher)
    register_type(IDataStorage, MySQLStorage)
    register_type(IDataValidator, DataValidator)
    
    # 3. 注册回测层服务
    register_type(IBroker, Broker)
    register_type(IPortfolio, Portfolio)
    register_type(IPerformanceAnalyzer, PerformanceAnalyzer)
    
    # 4. 注册风控服务
    register_type(IRiskManager, RiskManager)
    
    print("✅ 服务注册完成")


def create_backtest_engine(config: BacktestConfig) -> 'BacktestEngine':
    """
    创建回测引擎（使用依赖注入）
    
    Args:
        config: 回测配置
        
    Returns:
        BacktestEngine: 配置好的回测引擎
    """
    from src.backtest.engine import BacktestEngine
    
    container = get_container()
    
    # 解析依赖
    broker = container.resolve(IBroker)
    portfolio = container.resolve(IPortfolio)
    analyzer = container.resolve(IPerformanceAnalyzer)
    risk_manager = container.resolve(IRiskManager)
    
    # 创建引擎
    engine = BacktestEngine(
        config=config,
        broker=broker,
        portfolio=portfolio,
        analyzer=analyzer,
        risk_manager=risk_manager
    )
    
    return engine


def create_data_fetcher() -> 'AKShareFetcher':
    """创建数据获取器"""
    container = get_container()
    return container.resolve(IDataFetcher)


def create_data_storage() -> 'MySQLStorage':
    """创建数据存储"""
    container = get_container()
    return container.resolve(IDataStorage)


def create_risk_manager(**kwargs) -> 'RiskManager':
    """创建风险管理器"""
    return RiskManager(**kwargs)


# 启动时自动注册
register_services()
