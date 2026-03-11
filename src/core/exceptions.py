"""
自定义异常类
定义系统中使用的各种异常
"""


class QuantException(Exception):
    """量化系统基础异常"""
    
    def __init__(self, message: str = "", code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or "QUANT_ERROR"
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"[{self.code}] {self.message} - Details: {self.details}"
        return f"[{self.code}] {self.message}"


# 数据相关异常
class DataException(QuantException):
    """数据异常"""
    
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message, code="DATA_ERROR", details=details)


class DataFetchException(DataException):
    """数据获取异常"""
    
    def __init__(self, message: str = "", symbol: str = None, details: dict = None):
        details = details or {}
        if symbol:
            details['symbol'] = symbol
        super().__init__(message, details=details)
        self.code = "FETCH_ERROR"


class DataValidationException(DataException):
    """数据校验异常"""
    
    def __init__(self, message: str = "", validation_result=None, details: dict = None):
        details = details or {}
        if validation_result:
            details['validation'] = validation_result.to_dict() if hasattr(validation_result, 'to_dict') else str(validation_result)
        super().__init__(message, details=details)
        self.code = "VALIDATION_ERROR"


class DataStorageException(DataException):
    """数据存储异常"""
    
    def __init__(self, message: str = "", table: str = None, details: dict = None):
        details = details or {}
        if table:
            details['table'] = table
        super().__init__(message, details=details)
        self.code = "STORAGE_ERROR"


# 策略相关异常
class StrategyException(QuantException):
    """策略异常"""
    
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message, code="STRATEGY_ERROR", details=details)


class StrategyInitException(StrategyException):
    """策略初始化异常"""
    
    def __init__(self, message: str = "", strategy_name: str = None, details: dict = None):
        details = details or {}
        if strategy_name:
            details['strategy'] = strategy_name
        super().__init__(message, details=details)
        self.code = "STRATEGY_INIT_ERROR"


class StrategyExecutionException(StrategyException):
    """策略执行异常"""
    
    def __init__(self, message: str = "", strategy_name: str = None, bar=None, details: dict = None):
        details = details or {}
        if strategy_name:
            details['strategy'] = strategy_name
        if bar:
            details['bar'] = {
                'symbol': bar.symbol,
                'timestamp': bar.timestamp.isoformat() if hasattr(bar.timestamp, 'isoformat') else str(bar.timestamp)
            }
        super().__init__(message, details=details)
        self.code = "STRATEGY_EXEC_ERROR"


class FactorCalculationException(StrategyException):
    """因子计算异常"""
    
    def __init__(self, message: str = "", factor_name: str = None, details: dict = None):
        details = details or {}
        if factor_name:
            details['factor'] = factor_name
        super().__init__(message, details=details)
        self.code = "FACTOR_ERROR"


# 回测相关异常
class BacktestException(QuantException):
    """回测异常"""
    
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message, code="BACKTEST_ERROR", details=details)


class BacktestConfigException(BacktestException):
    """回测配置异常"""
    
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message, details=details)
        self.code = "BACKTEST_CONFIG_ERROR"


class BacktestExecutionException(BacktestException):
    """回测执行异常"""
    
    def __init__(self, message: str = "", date=None, details: dict = None):
        details = details or {}
        if date:
            details['date'] = date.isoformat() if hasattr(date, 'isoformat') else str(date)
        super().__init__(message, details=details)
        self.code = "BACKTEST_EXEC_ERROR"


class OrderExecutionException(BacktestException):
    """订单执行异常"""
    
    def __init__(self, message: str = "", order=None, details: dict = None):
        details = details or {}
        if order:
            details['order'] = {
                'symbol': getattr(order, 'symbol', None),
                'side': getattr(order, 'side', None),
                'volume': getattr(order, 'volume', None)
            }
        super().__init__(message, details=details)
        self.code = "ORDER_EXEC_ERROR"


# 风控相关异常
class RiskException(QuantException):
    """风控异常"""
    
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message, code="RISK_ERROR", details=details)


class RiskViolationException(RiskException):
    """风控违规异常"""
    
    def __init__(self, message: str = "", risk_result=None, details: dict = None):
        details = details or {}
        if risk_result:
            details['risk_checks'] = [
                {
                    'name': c.name,
                    'passed': c.passed,
                    'level': c.level.value if hasattr(c.level, 'value') else str(c.level),
                    'message': c.message
                }
                for c in risk_result.get_failed_checks()
            ] if hasattr(risk_result, 'get_failed_checks') else str(risk_result)
        super().__init__(message, details=details)
        self.code = "RISK_VIOLATION"


# 配置相关异常
class ConfigException(QuantException):
    """配置异常"""
    
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message, code="CONFIG_ERROR", details=details)


class ConfigLoadException(ConfigException):
    """配置加载异常"""
    
    def __init__(self, message: str = "", config_path: str = None, details: dict = None):
        details = details or {}
        if config_path:
            details['config_path'] = config_path
        super().__init__(message, details=details)
        self.code = "CONFIG_LOAD_ERROR"


class ConfigValidationException(ConfigException):
    """配置校验异常"""
    
    def __init__(self, message: str = "", missing_keys: list = None, details: dict = None):
        details = details or {}
        if missing_keys:
            details['missing_keys'] = missing_keys
        super().__init__(message, details=details)
        self.code = "CONFIG_VALIDATION_ERROR"


# 优化相关异常
class OptimizationException(QuantException):
    """优化异常"""
    
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message, code="OPTIMIZATION_ERROR", details=details)


class OptimizationConvergenceException(OptimizationException):
    """优化收敛异常"""
    
    def __init__(self, message: str = "", n_trials: int = None, details: dict = None):
        details = details or {}
        if n_trials:
            details['n_trials'] = n_trials
        super().__init__(message, details=details)
        self.code = "OPTIMIZATION_CONVERGENCE_ERROR"


# 交易相关异常
class TradingException(QuantException):
    """交易异常"""
    
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message, code="TRADING_ERROR", details=details)


class OrderSubmissionException(TradingException):
    """订单提交异常"""
    
    def __init__(self, message: str = "", order=None, details: dict = None):
        details = details or {}
        if order:
            details['order'] = str(order)
        super().__init__(message, details=details)
        self.code = "ORDER_SUBMISSION_ERROR"


class PositionException(TradingException):
    """持仓异常"""
    
    def __init__(self, message: str = "", symbol: str = None, details: dict = None):
        details = details or {}
        if symbol:
            details['symbol'] = symbol
        super().__init__(message, details=details)
        self.code = "POSITION_ERROR"


# 网络相关异常
class NetworkException(QuantException):
    """网络异常"""
    
    def __init__(self, message: str = "", url: str = None, details: dict = None):
        details = details or {}
        if url:
            details['url'] = url
        super().__init__(message, details=details)
        self.code = "NETWORK_ERROR"


class APIRateLimitException(NetworkException):
    """API限流异常"""
    
    def __init__(self, message: str = "", retry_after: int = None, details: dict = None):
        details = details or {}
        if retry_after:
            details['retry_after'] = retry_after
        super().__init__(message, details=details)
        self.code = "API_RATE_LIMIT"


# 数据库相关异常
class DatabaseException(QuantException):
    """数据库异常"""
    
    def __init__(self, message: str = "", details: dict = None):
        super().__init__(message, code="DATABASE_ERROR", details=details)


class ConnectionException(DatabaseException):
    """连接异常"""
    
    def __init__(self, message: str = "", host: str = None, details: dict = None):
        details = details or {}
        if host:
            details['host'] = host
        super().__init__(message, details=details)
        self.code = "CONNECTION_ERROR"


class QueryException(DatabaseException):
    """查询异常"""
    
    def __init__(self, message: str = "", query: str = None, details: dict = None):
        details = details or {}
        if query:
            details['query'] = query[:100]  # 只保留前100字符
        super().__init__(message, details=details)
        self.code = "QUERY_ERROR"
