"""
数据缓存层
提供多级缓存支持：内存缓存 + Redis缓存
"""
import pickle
import hashlib
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    data: Any
    timestamp: datetime
    ttl: int  # 秒
    
    def is_expired(self) -> bool:
        """是否过期"""
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl)


class MemoryCache:
    """
    内存缓存
    
    基于字典的本地缓存，适合单进程使用
    """
    
    def __init__(self, default_ttl: int = 300):
        """
        初始化内存缓存
        
        Args:
            default_ttl: 默认过期时间（秒）
        """
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self._hit_count = 0
        self._miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存数据或None
        """
        entry = self._cache.get(key)
        
        if entry is None:
            self._miss_count += 1
            return None
        
        if entry.is_expired():
            del self._cache[key]
            self._miss_count += 1
            return None
        
        self._hit_count += 1
        return entry.data
    
    def set(self, key: str, data: Any, ttl: int = None) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            data: 缓存数据
            ttl: 过期时间（秒），默认使用初始化值
        """
        ttl = ttl or self.default_ttl
        entry = CacheEntry(
            data=data,
            timestamp=datetime.now(),
            ttl=ttl
        )
        self._cache[key] = entry
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("内存缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0
        
        return {
            'size': len(self._cache),
            'hit_count': self._hit_count,
            'miss_count': self._miss_count,
            'hit_rate': hit_rate,
            'default_ttl': self.default_ttl
        }
    
    def clean_expired(self) -> int:
        """清理过期缓存，返回清理数量"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)


class RedisCache:
    """
    Redis缓存
    
    分布式缓存，适合多进程/多机器环境
    """
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: str = None, default_ttl: int = 300):
        """
        初始化Redis缓存
        
        Args:
            host: Redis主机
            port: Redis端口
            db: 数据库编号
            password: 密码
            default_ttl: 默认过期时间（秒）
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self._client = None
        self._hit_count = 0
        self._miss_count = 0
        
        self._connect()
    
    def _connect(self):
        """连接Redis"""
        try:
            import redis
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False  # 二进制数据
            )
            self._client.ping()
            logger.info(f"Redis缓存连接成功: {self.host}:{self.port}")
        except ImportError:
            logger.warning("redis模块未安装，Redis缓存不可用")
            self._client = None
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self._client = None
    
    def _is_connected(self) -> bool:
        """检查是否已连接"""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self._is_connected():
            self._miss_count += 1
            return None
        
        try:
            data = self._client.get(key)
            if data is None:
                self._miss_count += 1
                return None
            
            self._hit_count += 1
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Redis获取失败: {e}")
            self._miss_count += 1
            return None
    
    def set(self, key: str, data: Any, ttl: int = None) -> bool:
        """设置缓存"""
        if not self._is_connected():
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized = pickle.dumps(data)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis设置失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self._is_connected():
            return False
        
        try:
            return self._client.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis删除失败: {e}")
            return False
    
    def clear(self) -> bool:
        """清空缓存"""
        if not self._is_connected():
            return False
        
        try:
            self._client.flushdb()
            logger.info("Redis缓存已清空")
            return True
        except Exception as e:
            logger.error(f"Redis清空失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0
        
        stats = {
            'hit_count': self._hit_count,
            'miss_count': self._miss_count,
            'hit_rate': hit_rate,
            'default_ttl': self.default_ttl,
            'connected': self._is_connected()
        }
        
        if self._is_connected():
            try:
                info = self._client.info()
                stats['used_memory'] = info.get('used_memory_human', 'N/A')
                stats['keys'] = self._client.dbsize()
            except:
                pass
        
        return stats


class DataCache:
    """
    数据缓存（多级缓存）
    
    L1: 内存缓存（快）
    L2: Redis缓存（分布式）
    """
    
    def __init__(self, 
                 memory_ttl: int = 60,
                 redis_ttl: int = 300,
                 use_redis: bool = True):
        """
        初始化数据缓存
        
        Args:
            memory_ttl: 内存缓存过期时间
            redis_ttl: Redis缓存过期时间
            use_redis: 是否使用Redis
        """
        self.l1_cache = MemoryCache(default_ttl=memory_ttl)
        self.l2_cache = RedisCache(default_ttl=redis_ttl) if use_redis else None
        
        logger.info(f"数据缓存初始化: L1={memory_ttl}s, L2={'enabled' if use_redis else 'disabled'}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存（L1 -> L2）
        
        Args:
            key: 缓存键
            
        Returns:
            缓存数据或None
        """
        # 先查L1
        data = self.l1_cache.get(key)
        if data is not None:
            return data
        
        # 再查L2
        if self.l2_cache:
            data = self.l2_cache.get(key)
            if data is not None:
                # 回填L1
                self.l1_cache.set(key, data)
                return data
        
        return None
    
    def set(self, key: str, data: Any, l1_ttl: int = None, l2_ttl: int = None) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            data: 缓存数据
            l1_ttl: L1缓存时间
            l2_ttl: L2缓存时间
        """
        self.l1_cache.set(key, data, l1_ttl)
        
        if self.l2_cache:
            self.l2_cache.set(key, data, l2_ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        l1_result = self.l1_cache.delete(key)
        l2_result = self.l2_cache.delete(key) if self.l2_cache else False
        return l1_result or l2_result
    
    def clear(self) -> None:
        """清空缓存"""
        self.l1_cache.clear()
        if self.l2_cache:
            self.l2_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            'l1': self.l1_cache.get_stats(),
            'l2': self.l2_cache.get_stats() if self.l2_cache else None
        }


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    缓存装饰器
    
    自动缓存函数结果
    
    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
        
    Example:
        @cached(ttl=300)
        def get_stock_data(symbol: str) -> pd.DataFrame:
            return fetch_data(symbol)
    """
    def decorator(func: Callable) -> Callable:
        cache = MemoryCache(default_ttl=ttl)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # 尝试从缓存获取
            result = cache.get(key)
            if result is not None:
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache.set(key, result)
            
            return result
        
        # 附加缓存操作方法
        wrapper.cache = cache
        wrapper.cache_clear = cache.clear
        wrapper.cache_stats = cache.get_stats
        
        return wrapper
    return decorator


class CachedDataQuery:
    """
    带缓存的数据查询
    
    包装 DataQueryEngine，添加缓存层
    """
    
    def __init__(self, query_engine, cache: DataCache = None):
        """
        初始化
        
        Args:
            query_engine: 数据查询引擎
            cache: 数据缓存实例
        """
        self.query_engine = query_engine
        self.cache = cache or DataCache()
    
    def _make_key(self, method: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = ["data_query", method]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()
    
    def get_price_data(self, symbol: str, start_date=None, end_date=None, **kwargs):
        """获取价格数据（带缓存）"""
        key = self._make_key("price", symbol, start_date, end_date)
        
        # 尝试缓存
        result = self.cache.get(key)
        if result is not None:
            return result
        
        # 查询数据
        result = self.query_engine.get_price_data(symbol, start_date, end_date, **kwargs)
        
        # 存入缓存
        if not result.empty:
            self.cache.set(key, result, l1_ttl=60, l2_ttl=300)
        
        return result
    
    def get_latest_price(self, symbol: str):
        """获取最新价格（短缓存）"""
        key = self._make_key("latest", symbol)
        
        result = self.cache.get(key)
        if result is not None:
            return result
        
        result = self.query_engine.get_latest_price(symbol)
        
        if result:
            self.cache.set(key, result, l1_ttl=10, l2_ttl=60)
        
        return result
    
    def invalidate_symbol(self, symbol: str):
        """使某股票的缓存失效"""
        # 清理包含该symbol的缓存
        self.cache.l1_cache.clear()
        logger.info(f"股票 {symbol} 的缓存已清理")
    
    def get_stats(self):
        """获取缓存统计"""
        return self.cache.get_stats()
