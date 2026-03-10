"""
配置管理 - 支持YAML配置文件和环境变量
"""
import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


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
    default_symbols: list = field(default_factory=lambda: [
        '000001', '000002', '600000', '600519'
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
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


@dataclass
class Config:
    """全局配置"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    data: DataConfig = field(default_factory=DataConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        """从YAML文件加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        config = cls()
        if data:
            if 'database' in data:
                config.database = DatabaseConfig(**data['database'])
            if 'data' in data:
                config.data = DataConfig(**data['data'])
            if 'logging' in data:
                config.logging = LoggingConfig(**data['logging'])
        
        return config
    
    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量加载配置"""
        config = cls()
        
        # 数据库配置
        config.database.host = os.getenv('DB_HOST', config.database.host)
        config.database.port = int(os.getenv('DB_PORT', config.database.port))
        config.database.user = os.getenv('DB_USER', config.database.user)
        config.database.password = os.getenv('DB_PASSWORD', config.database.password)
        config.database.database = os.getenv('DB_NAME', config.database.database)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'database': self.database.__dict__,
            'data': self.data.__dict__,
            'logging': self.logging.__dict__
        }


def load_config(env: str = None) -> Config:
    """
    加载配置
    优先级: 环境变量 > 环境配置文件 > 默认配置
    """
    env = env or os.getenv('QUANT_ENV', 'development')
    
    # 基础配置
    config = Config()
    
    # 加载环境配置文件
    config_dir = Path(__file__).parent.parent.parent / 'config'
    config_file = config_dir / f'{env}.yaml'
    
    if config_file.exists():
        config = Config.from_yaml(str(config_file))
    
    # 环境变量覆盖
    env_config = Config.from_env()
    config.database = env_config.database
    
    return config


# 全局配置实例
config = load_config()
