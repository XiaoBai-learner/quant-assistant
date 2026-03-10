"""
异常定义 - 量化系统专用异常类
"""


class QuantException(Exception):
    """量化系统基础异常"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or "QUANT_ERROR"
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"[{self.code}] {self.message} - Details: {self.details}"
        return f"[{self.code}] {self.message}"


class DataException(QuantException):
    """数据层异常"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "DATA_ERROR", details)


class DataFetchException(DataException):
    """数据获取异常"""
    def __init__(self, message: str, source: str = None, details: dict = None):
        details = details or {}
        details['source'] = source
        super().__init__(message, details)


class DataStorageException(DataException):
    """数据存储异常"""
    def __init__(self, message: str, operation: str = None, details: dict = None):
        details = details or {}
        details['operation'] = operation
        super().__init__(message, details)


class StrategyException(QuantException):
    """策略层异常"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "STRATEGY_ERROR", details)


class TradingException(QuantException):
    """交易层异常"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "TRADING_ERROR", details)


class OrderException(TradingException):
    """订单异常"""
    def __init__(self, message: str, order_id: str = None, details: dict = None):
        details = details or {}
        details['order_id'] = order_id
        super().__init__(message, details)


class RiskException(QuantException):
    """风控异常"""
    def __init__(self, message: str, rule: str = None, details: dict = None):
        details = details or {}
        details['rule'] = rule
        super().__init__(message, "RISK_ERROR", details)


class ValidationException(QuantException):
    """校验异常"""
    def __init__(self, message: str, field: str = None, details: dict = None):
        details = details or {}
        details['field'] = field
        super().__init__(message, "VALIDATION_ERROR", details)
