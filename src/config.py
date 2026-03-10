"""
配置文件 - 数据管理层
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = os.getenv('DB_HOST', 'localhost')
    port: int = int(os.getenv('DB_PORT', '3306'))
    user: str = os.getenv('DB_USER', 'quant_user')
    password: str = os.getenv('DB_PASSWORD', 'quant_password')
    database: str = os.getenv('DB_NAME', 'quant_data')
    charset: str = 'utf8mb4'
    pool_size: int = 10
    max_overflow: int = 20
    
    @property
    def connection_string(self) -> str:
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?charset={self.charset}"
        )


@dataclass
class DataConfig:
    """数据配置"""
    default_symbols: list = None
    auto_update: bool = True
    update_interval_hours: int = 6
    history_start_date: str = '2020-01-01'
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    
    def __post_init__(self):
        if self.default_symbols is None:
            self.default_symbols = [
                '000001',  # 平安银行
                '000002',  # 万科A
                '600000',  # 浦发银行
                '600519',  # 贵州茅台
            ]


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: Optional[str] = 'logs/quant_data.log'
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


# 全局配置实例
db_config = DatabaseConfig()
data_config = DataConfig()
log_config = LoggingConfig()
