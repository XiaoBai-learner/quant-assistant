"""数据存储模块"""
from .base_storage import BaseStorage
from .mysql_storage import MySQLStorage

__all__ = ['BaseStorage', 'MySQLStorage']
