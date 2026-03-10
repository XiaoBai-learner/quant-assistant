"""
日志工具
"""
import os
import sys
from loguru import logger

from src.config import log_config


def setup_logging():
    """配置日志"""
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        level=log_config.level,
        format=log_config.format,
        colorize=True
    )
    
    # 添加文件输出
    if log_config.file_path:
        os.makedirs(os.path.dirname(log_config.file_path), exist_ok=True)
        logger.add(
            log_config.file_path,
            level=log_config.level,
            format=log_config.format,
            rotation=f"{log_config.max_bytes} bytes",
            retention=log_config.backup_count,
            encoding='utf-8'
        )


def get_logger(name: str = None):
    """获取logger实例"""
    return logger.bind(name=name) if name else logger
