"""
统一配置管理器
整合所有配置来源，提供统一的配置访问接口
"""
import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
import yaml


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 3306
    user: str = "quant_user"
    password: str = "quant_password"
    database: str = "quant_data"
    charset: str = "utf8mb4"
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
    default_symbols: List[str] = field(default_factory=lambda: [
        '000001',  # 平安银行
        '000002',  # 万科A
        '600000',  # 浦发银行
        '600519',  # 贵州茅台
    ])
    auto_update: bool = True
    update_interval_hours: int = 6
    history_start_date: str = '2020-01-01'
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: Optional[str] = 'logs/quant.log'
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class BacktestConfig:
    """回测配置"""
    initial_cash: float = 100000.0
    commission_rate: float = 0.00025  # 万2.5
    slippage: float = 0.001  # 0.1%
    stamp_duty: float = 0.001  # 0.1%
    max_position_pct: float = 1.0
    max_drawdown_limit: float = 0.2


@dataclass
class Config:
    """统一配置类"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    data: DataConfig = field(default_factory=DataConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    
    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """从YAML文件加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls(
            database=DatabaseConfig(**data.get('database', {})),
            data=DataConfig(**data.get('data', {})),
            logging=LoggingConfig(**data.get('logging', {})),
            backtest=BacktestConfig(**data.get('backtest', {}))
        )
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        config = cls()
        
        # 数据库配置
        if os.getenv('DB_HOST'):
            config.database.host = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            config.database.port = int(os.getenv('DB_PORT'))
        if os.getenv('DB_USER'):
            config.database.user = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            config.database.password = os.getenv('DB_PASSWORD')
        if os.getenv('DB_NAME'):
            config.database.database = os.getenv('DB_NAME')
        
        return config
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        加载配置，优先级：环境变量 > YAML文件 > 默认值
        
        Args:
            config_path: YAML配置文件路径，默认查找 config/default.yaml
        """
        # 1. 从默认或指定路径加载YAML
        if config_path is None:
            # 查找默认配置
            possible_paths = [
                Path('config/default.yaml'),
                Path('../config/default.yaml'),
                Path('/app/config/default.yaml'),
            ]
            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break
        
        if config_path and Path(config_path).exists():
            config = cls.from_yaml(config_path)
        else:
            config = cls()
        
        # 2. 环境变量覆盖
        env_config = cls.from_env()
        config.database = env_config.database
        
        return config


# 全局配置实例（延迟加载）
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config.load()
    return _config
