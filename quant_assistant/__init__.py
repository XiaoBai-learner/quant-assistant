"""
Quant Assistant - 个人量化交易框架

一个模块化、可扩展的量化交易框架，支持数据获取、因子计算、
机器学习预测、策略开发和回测验证。

快速开始:
    >>> import quant_assistant as qa
    >>> 
    >>> # 获取迈为股份数据
    >>> data = qa.data.get_stock_data('300751', start='2024-01-01')
    >>> 
    >>> # 计算技术指标
    >>> ma20 = qa.factors.ma(data, window=20)
    >>> macd = qa.factors.macd(data)
    >>> 
    >>> # 运行回测
    >>> result = qa.backtest.run(strategy, data)

完整文档: https://github.com/XiaoBai-learner/quant-assistant/blob/main/docs/USAGE_GUIDE.md
"""

__version__ = "1.0.0"
__author__ = "XiaoBai-learner"
__email__ = "185890339@qq.com"

# 尝试导入核心模块
try:
    from quant_assistant.core import (
        Context,
        Event,
        EventBus,
        Container,
        QuantException,
    )
except ImportError:
    pass

# 尝试导入数据模块
try:
    from quant_assistant.data import (
        DataFetcher,
        MySQLStorage,
        DataQuery,
        CacheManager,
    )
except ImportError:
    pass

# 尝试导入因子模块
try:
    from quant_assistant.factors import (
        FactorEngine,
        TechnicalFactor,
        CompositeFactor,
    )
    # 便捷函数：一次性计算所有因子
    from quant_assistant.api import QuantAPI
    _default_api = QuantAPI()
    compute_factors = _default_api.factors.compute_all_factors
except ImportError:
    pass

# 尝试导入策略模块
try:
    from quant_assistant.strategy import (
        BaseStrategy,
        SignalGenerator,
        StockSelector,
        StrategyOptimizer,
    )
except ImportError:
    pass

# 尝试导入回测模块
try:
    from quant_assistant.backtest import (
        BacktestEngine,
        Portfolio,
        PerformanceAnalyzer,
    )
except ImportError:
    pass

# 尝试导入机器学习模块
try:
    from quant_assistant.ml import (
        MLPredictor,
        FeatureEngineer,
        ModelEvaluator,
    )
except ImportError:
    pass

# 尝试导入可视化模块
try:
    from quant_assistant.visualization import (
        ChartRenderer,
        IndicatorPlotter,
    )
except ImportError:
    pass

# 尝试导入便捷 API
try:
    from quant_assistant.api import QuantAPI
    
    # 创建默认 API 实例
    _default_api = QuantAPI()
    
    # 提供便捷的模块级访问
    data = _default_api.data
    factors = _default_api.factors
    strategy = _default_api.strategy
    backtest = _default_api.backtest
    ml = _default_api.ml
except ImportError:
    pass

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    
    # 核心
    "Context",
    "Event",
    "EventBus",
    "Container",
    "QuantException",
    
    # 数据
    "DataFetcher",
    "MySQLStorage",
    "DataQuery",
    "CacheManager",
    
    # 因子
    "FactorEngine",
    "TechnicalFactor",
    "CompositeFactor",
    
    # 策略
    "BaseStrategy",
    "SignalGenerator",
    "StockSelector",
    "StrategyOptimizer",
    
    # 回测
    "BacktestEngine",
    "Portfolio",
    "PerformanceAnalyzer",
    
    # 机器学习
    "MLPredictor",
    "FeatureEngineer",
    "ModelEvaluator",
    
    # 可视化
    "ChartRenderer",
    "IndicatorPlotter",
    
    # API
    "QuantAPI",
]
