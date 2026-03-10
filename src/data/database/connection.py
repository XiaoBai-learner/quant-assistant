"""
数据库连接管理
"""
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.config import db_config


class DatabaseManager:
    """数据库连接管理器"""
    
    _instance: Optional['DatabaseManager'] = None
    _engine = None
    _session_factory = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化数据库引擎"""
        self._engine = create_engine(
            db_config.connection_string,
            poolclass=QueuePool,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        self._session_factory = sessionmaker(bind=self._engine)
    
    @property
    def engine(self):
        return self._engine
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """提供事务性数据库会话上下文"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def execute(self, sql: str, params: dict = None):
        """执行原始SQL"""
        with self.engine.connect() as conn:
            result = conn.execute(sql, params or {})
            return result
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False


# 全局数据库管理器实例
db_manager = DatabaseManager()
