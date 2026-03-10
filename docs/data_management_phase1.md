# 数据管理层实施文档 - Phase 1 (基础版)

## 文档信息
- **版本**: v1.0.0
- **日期**: 2026-03-10
- **状态**: 实施中
- **技术栈**: Python + MySQL + AKShare

---

## 1. 架构概述

### 1.1 设计目标
构建一个稳定、可扩展的量化数据管理层，实现：
- 从 AKShare 获取 A 股市场数据
- 使用 MySQL 进行结构化数据存储
- 提供统一的数据访问接口
- 支持历史数据回测和实时数据更新

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    数据管理层 (Data Manager)                  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  DataFetcher │  │ DataStorage  │  │ DataQuery    │      │
│  │  (数据获取)   │  │  (数据存储)   │  │  (数据查询)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │              │
│         ▼                 ▼                 ▼              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              MySQL Database                          │  │
│  │  ┌──────────┬──────────┬──────────┬──────────┐     │  │
│  │  │  stocks  │  daily   │  factors │  calendar│     │  │
│  │  │ (股票信息)│ (日线数据)│ (因子数据)│ (交易日历)│     │  │
│  │  └──────────┴──────────┴──────────┴──────────┘     │  │
│  └─────────────────────────────────────────────────────┘  │
│                           ▲                                │
│                           │                                │
│  ┌────────────────────────┴────────────────────────┐      │
│  │                    AKShare API                   │      │
│  │  (股票列表/历史行情/财务数据/实时行情)              │      │
│  └─────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 核心模块

| 模块 | 职责 | 关键类 |
|------|------|--------|
| DataFetcher | 从 AKShare 获取数据 | `StockDataFetcher`, `MarketDataFetcher` |
| DataStorage | 数据持久化到 MySQL | `MySQLStorage`, `DataInserter` |
| DataQuery | 提供数据查询接口 | `DataQueryEngine`, `CacheManager` |
| DataValidator | 数据质量校验 | `DataValidator`, `DataCleaner` |

---

## 2. 数据库设计

### 2.1 数据库架构

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS quant_data 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE quant_data;
```

### 2.2 表结构设计

#### 2.2.1 股票基础信息表 (stocks)

```sql
CREATE TABLE stocks (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL COMMENT '股票代码',
    name            VARCHAR(100) NOT NULL COMMENT '股票名称',
    exchange        VARCHAR(10) NOT NULL COMMENT '交易所 (SH/SZ/BJ)',
    industry        VARCHAR(50) COMMENT '所属行业',
    list_date       DATE COMMENT '上市日期',
    delist_date     DATE COMMENT '退市日期',
    status          TINYINT DEFAULT 1 COMMENT '状态: 1-正常, 0-退市',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_symbol (symbol),
    KEY idx_industry (industry),
    KEY idx_status (status)
) ENGINE=InnoDB COMMENT='股票基础信息表';
```

#### 2.2.2 日线行情数据表 (daily_quotes)

```sql
CREATE TABLE daily_quotes (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL COMMENT '股票代码',
    trade_date      DATE NOT NULL COMMENT '交易日期',
    open            DECIMAL(10,4) COMMENT '开盘价',
    high            DECIMAL(10,4) COMMENT '最高价',
    low             DECIMAL(10,4) COMMENT '最低价',
    close           DECIMAL(10,4) COMMENT '收盘价',
    volume          BIGINT COMMENT '成交量(股)',
    amount          DECIMAL(20,4) COMMENT '成交额(元)',
    amplitude       DECIMAL(6,4) COMMENT '振幅',
    pct_change      DECIMAL(6,4) COMMENT '涨跌幅',
    change_amount   DECIMAL(10,4) COMMENT '涨跌额',
    turnover        DECIMAL(6,4) COMMENT '换手率',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_symbol_date (symbol, trade_date),
    KEY idx_trade_date (trade_date),
    KEY idx_symbol (symbol)
) ENGINE=InnoDB COMMENT='日线行情数据表';
```

#### 2.2.3 分钟线数据表 (minute_quotes)

```sql
CREATE TABLE minute_quotes (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL COMMENT '股票代码',
    trade_datetime  DATETIME NOT NULL COMMENT '交易时间',
    open            DECIMAL(10,4) COMMENT '开盘价',
    high            DECIMAL(10,4) COMMENT '最高价',
    low             DECIMAL(10,4) COMMENT '最低价',
    close           DECIMAL(10,4) COMMENT '收盘价',
    volume          BIGINT COMMENT '成交量',
    amount          DECIMAL(20,4) COMMENT '成交额',
    period          VARCHAR(5) DEFAULT '1min' COMMENT '周期: 1min/5min/15min/30min/60min',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_symbol_datetime_period (symbol, trade_datetime, period),
    KEY idx_trade_datetime (trade_datetime),
    KEY idx_symbol (symbol)
) ENGINE=InnoDB COMMENT='分钟线行情数据表';
```

#### 2.2.4 财务指标表 (financial_indicators)

```sql
CREATE TABLE financial_indicators (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL COMMENT '股票代码',
    report_date     DATE NOT NULL COMMENT '报告期',
    report_type     VARCHAR(10) COMMENT '报告类型 (年报/季报)',
    eps             DECIMAL(10,4) COMMENT '每股收益',
    bvps            DECIMAL(10,4) COMMENT '每股净资产',
    roe             DECIMAL(6,4) COMMENT '净资产收益率',
    roa             DECIMAL(6,4) COMMENT '总资产收益率',
    gross_margin    DECIMAL(6,4) COMMENT '毛利率',
    net_margin      DECIMAL(6,4) COMMENT '净利率',
    debt_ratio      DECIMAL(6,4) COMMENT '资产负债率',
    revenue         DECIMAL(20,4) COMMENT '营业收入',
    net_profit      DECIMAL(20,4) COMMENT '净利润',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_symbol_date (symbol, report_date),
    KEY idx_report_date (report_date)
) ENGINE=InnoDB COMMENT='财务指标表';
```

#### 2.2.5 交易日历表 (trade_calendar)

```sql
CREATE TABLE trade_calendar (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date      DATE NOT NULL COMMENT '日期',
    is_trading_day  TINYINT DEFAULT 1 COMMENT '是否交易日: 1-是, 0-否',
    exchange        VARCHAR(10) COMMENT '交易所',
    week_day        TINYINT COMMENT '星期几 (1-7)',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_date_exchange (trade_date, exchange),
    KEY idx_trade_date (trade_date)
) ENGINE=InnoDB COMMENT='交易日历表';
```

#### 2.2.6 数据更新日志表 (update_logs)

```sql
CREATE TABLE update_logs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name      VARCHAR(50) NOT NULL COMMENT '表名',
    symbol          VARCHAR(20) COMMENT '股票代码',
    start_date      DATE COMMENT '数据起始日期',
    end_date        DATE COMMENT '数据结束日期',
    record_count    INT COMMENT '记录数',
    status          VARCHAR(20) COMMENT '状态: success/failed',
    message         TEXT COMMENT '日志信息',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    KEY idx_table_name (table_name),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB COMMENT='数据更新日志表';
```

---

## 3. 代码实现

### 3.1 项目结构

```
quant_project/
├── docs/                           # 文档
│   └── data_management_phase1.md  # 本实施文档
├── src/                           # 源代码
│   ├── __init__.py
│   ├── config.py                  # 配置文件
│   ├── database/                  # 数据库模块
│   │   ├── __init__.py
│   │   ├── connection.py          # 数据库连接管理
│   │   ├── models.py              # 数据模型
│   │   └── schema.sql             # 数据库结构
│   ├── fetcher/                   # 数据获取模块
│   │   ├── __init__.py
│   │   ├── akshare_fetcher.py     # AKShare 数据获取
│   │   └── base_fetcher.py        # 获取器基类
│   ├── storage/                   # 数据存储模块
│   │   ├── __init__.py
│   │   ├── mysql_storage.py       # MySQL 存储实现
│   │   └── base_storage.py        # 存储基类
│   ├── query/                     # 数据查询模块
│   │   ├── __init__.py
│   │   ├── data_query.py          # 查询接口
│   │   └── cache.py               # 缓存管理
│   └── utils/                     # 工具模块
│       ├── __init__.py
│       ├── logger.py              # 日志工具
│       └── validator.py           # 数据校验
├── tests/                         # 测试代码
│   └── test_data_manager.py
├── data/                          # 本地数据缓存
├── requirements.txt               # 依赖包
└── main.py                        # 入口程序
```

### 3.2 配置文件 (src/config.py)

```python
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
    # 默认股票列表
    default_symbols: list = None
    
    # 数据更新设置
    auto_update: bool = True
    update_interval_hours: int = 6
    
    # 历史数据起始日期
    history_start_date: str = '2020-01-01'
    
    # 缓存设置
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
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


# 全局配置实例
db_config = DatabaseConfig()
data_config = DataConfig()
log_config = LoggingConfig()
```

### 3.3 数据库连接管理 (src/database/connection.py)

```python
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
            pool_pre_ping=True,  # 连接前ping检测
            pool_recycle=3600,   # 1小时回收连接
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
```

### 3.4 数据模型 (src/database/models.py)

```python
"""
SQLAlchemy 数据模型定义
"""
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column, BigInteger, String, Date, DateTime, 
    Decimal, Integer, Text, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Stock(Base):
    """股票基础信息表"""
    __tablename__ = 'stocks'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    exchange = Column(String(10), nullable=False, comment='交易所')
    industry = Column(String(50), comment='所属行业')
    list_date = Column(Date, comment='上市日期')
    delist_date = Column(Date, comment='退市日期')
    status = Column(Integer, default=1, comment='状态')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_industry', 'industry'),
        Index('idx_status', 'status'),
        {'comment': '股票基础信息表'}
    )


class DailyQuote(Base):
    """日线行情数据表"""
    __tablename__ = 'daily_quotes'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    open = Column(Decimal(10, 4), comment='开盘价')
    high = Column(Decimal(10, 4), comment='最高价')
    low = Column(Decimal(10, 4), comment='最低价')
    close = Column(Decimal(10, 4), comment='收盘价')
    volume = Column(BigInteger, comment='成交量')
    amount = Column(Decimal(20, 4), comment='成交额')
    amplitude = Column(Decimal(6, 4), comment='振幅')
    pct_change = Column(Decimal(6, 4), comment='涨跌幅')
    change_amount = Column(Decimal(10, 4), comment='涨跌额')
    turnover = Column(Decimal(6, 4), comment='换手率')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('symbol', 'trade_date', name='uk_symbol_date'),
        Index('idx_trade_date', 'trade_date'),
        Index('idx_symbol', 'symbol'),
        {'comment': '日线行情数据表'}
    )


class FinancialIndicator(Base):
    """财务指标表"""
    __tablename__ = 'financial_indicators'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, comment='股票代码')
    report_date = Column(Date, nullable=False, comment='报告期')
    report_type = Column(String(10), comment='报告类型')
    eps = Column(Decimal(10, 4), comment='每股收益')
    bvps = Column(Decimal(10, 4), comment='每股净资产')
    roe = Column(Decimal(6, 4), comment='净资产收益率')
    roa = Column(Decimal(6, 4), comment='总资产收益率')
    gross_margin = Column(Decimal(6, 4), comment='毛利率')
    net_margin = Column(Decimal(6, 4), comment='净利率')
    debt_ratio = Column(Decimal(6, 4), comment='资产负债率')
    revenue = Column(Decimal(20, 4), comment='营业收入')
    net_profit = Column(Decimal(20, 4), comment='净利润')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('symbol', 'report_date', name='uk_symbol_report'),
        Index('idx_report_date', 'report_date'),
        {'comment': '财务指标表'}
    )


class UpdateLog(Base):
    """数据更新日志表"""
    __tablename__ = 'update_logs'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False, comment='表名')
    symbol = Column(String(20), comment='股票代码')
    start_date = Column(Date, comment='数据起始日期')
    end_date = Column(Date, comment='数据结束日期')
    record_count = Column(Integer, comment='记录数')
    status = Column(String(20), comment='状态')
    message = Column(Text, comment='日志信息')
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_table_name', 'table_name'),
        Index('idx_created_at', 'created_at'),
        {'comment': '数据更新日志表'}
    )
```

### 3.5 AKShare 数据获取器 (src/fetcher/akshare_fetcher.py)

```python
"""
AKShare 数据获取实现
"""
import akshare as ak
import pandas as pd
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import time

from src.fetcher.base_fetcher import BaseDataFetcher
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AKShareFetcher(BaseDataFetcher):
    """AKShare 数据获取器"""
    
    def __init__(self):
        self.name = "AKShare"
        self.rate_limit_delay = 0.5  # API 调用间隔(秒)
    
    def _rate_limit(self):
        """速率限制"""
        time.sleep(self.rate_limit_delay)
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表
        
        Returns:
            DataFrame: 包含 symbol, name, exchange 等字段
        """
        try:
            logger.info("获取A股股票列表...")
            df = ak.stock_zh_a_spot_em()
            
            # 标准化列名
            df = df.rename(columns={
                '代码': 'symbol',
                '名称': 'name',
            })
            
            # 提取交易所信息
            df['exchange'] = df['symbol'].apply(self._get_exchange)
            
            # 选择需要的列
            result = df[['symbol', 'name', 'exchange']].copy()
            
            logger.info(f"获取到 {len(result)} 只股票")
            return result
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise
    
    def get_daily_quotes(
        self, 
        symbol: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取日线行情数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            DataFrame: 日线数据
        """
        try:
            self._rate_limit()
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = '20200101'
            
            # 转换日期格式
            start = start_date.replace('-', '')
            end = end_date.replace('-', '')
            
            logger.info(f"获取 {symbol} 日线数据: {start_date} ~ {end_date}")
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                logger.warning(f"{symbol} 在指定日期范围内无数据")
                return pd.DataFrame()
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change_amount',
                '换手率': 'turnover',
            })
            
            df['symbol'] = symbol
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            
            logger.info(f"获取到 {len(df)} 条日线数据")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 日线数据失败: {e}")
            raise
    
    def get_financial_indicators(self, symbol: str) -> pd.DataFrame:
        """
        获取财务指标数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame: 财务指标数据
        """
        try:
            self._rate_limit()
            
            logger.info(f"获取 {symbol} 财务指标...")
            
            # 主要财务指标
            df = ak.stock_financial_report_sina(
                stock=symbol, 
                symbol="主要财务指标"
            )
            
            if df.empty:
                return pd.DataFrame()
            
            # 标准化处理
            df['symbol'] = symbol
            
            logger.info(f"获取到 {len(df)} 条财务指标")
            return df
            
        except Exception as e:
            logger.error(f"获取 {symbol} 财务指标失败: {e}")
            # 财务数据可能不存在，返回空DataFrame
            return pd.DataFrame()
    
    def get_trade_calendar(self, year: int) -> pd.DataFrame:
        """
        获取交易日历
        
        Args:
            year: 年份
            
        Returns:
            DataFrame: 交易日历
        """
        try:
            logger.info(f"获取 {year} 年交易日历...")
            
            df = ak.tool_trade_date_hist_sina()
            
            df = df.rename(columns={
                'trade_date': 'trade_date'
            })
            
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
            df['is_trading_day'] = 1
            df['exchange'] = 'SH/SZ'
            df['week_day'] = pd.to_datetime(df['trade_date']).dt.dayofweek + 1
            
            # 筛选指定年份
            df = df[df['trade_date'].apply(lambda x: x.year) == year]
            
            logger.info(f"获取到 {len(df)} 个交易日")
            return df
            
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            raise
    
    def _get_exchange(self, symbol: str) -> str:
        """根据股票代码判断交易所"""
        if symbol.startswith(('600', '601', '603', '605', '688')):
            return 'SH'
        elif symbol.startswith(('000', '001', '002', '003', '300')):
            return 'SZ'
        elif symbol.startswith(('8', '4')):
            return 'BJ'
        else:
            return 'UNKNOWN'
```

### 3.6 MySQL 存储实现 (src/storage/mysql_storage.py)

```python
"""
MySQL 数据存储实现
"""
import pandas as pd
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from sqlalchemy import insert, update, delete
from sqlalchemy.dialects.mysql import insert as mysql_insert

from src.storage.base_storage import BaseStorage
from src.database.connection import db_manager
from src.database.models import (
    Stock, DailyQuote, FinancialIndicator, 
    UpdateLog, Base
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MySQLStorage(BaseStorage):
    """MySQL 数据存储实现"""
    
    def __init__(self):
        self.db = db_manager
        self._ensure_tables()
    
    def _ensure_tables(self):
        """确保数据库表已创建"""
        Base.metadata.create_all(self.db.engine)
        logger.info("数据库表结构已确认")
    
    def save_stocks(self, df: pd.DataFrame) -> int:
        """
        保存股票列表
        
        Args:
            df: 包含股票信息的DataFrame
            
        Returns:
            int: 保存的记录数
        """
        if df.empty:
            return 0
        
        records = df.to_dict('records')
        count = 0
        
        with self.db.session() as session:
            for record in records:
                # 使用 UPSERT 语义
                stmt = mysql_insert(Stock).values(**record)
                stmt = stmt.on_duplicate_key_update(
                    name=stmt.inserted.name,
                    exchange=stmt.inserted.exchange,
                    updated_at=datetime.now()
                )
                session.execute(stmt)
                count += 1
        
        logger.info(f"保存/更新 {count} 只股票信息")
        self._log_update('stocks', None, None, None, count, 'success')
        return count
    
    def save_daily_quotes(self, df: pd.DataFrame) -> int:
        """
        保存日线行情数据
        
        Args:
            df: 日线数据DataFrame
            
        Returns:
            int: 保存的记录数
        """
        if df.empty:
            return 0
        
        # 确保数据类型正确
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date
        
        records = df.to_dict('records')
        count = 0
        symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else None
        
        with self.db.session() as session:
            for record in records:
                stmt = mysql_insert(DailyQuote).values(**record)
                stmt = stmt.on_duplicate_key_update(
                    open=stmt.inserted.open,
                    high=stmt.inserted.high,
                    low=stmt.inserted.low,
                    close=stmt.inserted.close,
                    volume=stmt.inserted.volume,
                    amount=stmt.inserted.amount,
                    amplitude=stmt.inserted.amplitude,
                    pct_change=stmt.inserted.pct_change,
                    change_amount=stmt.inserted.change_amount,
                    turnover=stmt.inserted.turnover,
                )
                session.execute(stmt)
                count += 1
        
        start_date = df['trade_date'].min()
        end_date = df['trade_date'].max()
        
        logger.info(f"保存 {count} 条日线数据 [{symbol}: {start_date} ~ {end_date}]")
        self._log_update('daily_quotes', symbol, start_date, end_date, count, 'success')
        return count
    
    def save_financial_indicators(self, df: pd.DataFrame) -> int:
        """保存财务指标"""
        if df.empty:
            return 0
        
        records = df.to_dict('records')
        count = 0
        
        with self.db.session() as session:
            for record in records:
                stmt = mysql_insert(FinancialIndicator).values(**record)
                stmt = stmt.on_duplicate_key_update(**record)
                session.execute(stmt)
                count += 1
        
        logger.info(f"保存 {count} 条财务指标")
        self._log_update('financial_indicators', None, None, None, count, 'success')
        return count
    
    def save_trade_calendar(self, df: pd.DataFrame) -> int:
        """保存交易日历"""
        if df.empty:
            return 0
        
        records = df.to_dict('records')
        count = 0
        
        with self.db.session() as session:
            for record in records:
                stmt = mysql_insert(TradeCalendar).values(**record)
                stmt = stmt.on_duplicate_key_update(
                    is_trading_day=stmt.inserted.is_trading_day
                )
                session.execute(stmt)
                count += 1
        
        logger.info(f"保存 {count} 条交易日历")
        return count
    
    def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        查询日线数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 日线数据
        """
        from sqlalchemy import select, and_
        
        stmt = select(DailyQuote).where(DailyQuote.symbol == symbol)
        
        if start_date:
            stmt = stmt.where(DailyQuote.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(DailyQuote.trade_date <= end_date)
        
        stmt = stmt.order_by(DailyQuote.trade_date)
        
        with self.db.session() as session:
            result = session.execute(stmt)
            rows = result.scalars().all()
            
            if not rows:
                return pd.DataFrame()
            
            data = [{
                'symbol': r.symbol,
                'trade_date': r.trade_date,
                'open': float(r.open) if r.open else None,
                'high': float(r.high) if r.high else None,
                'low': float(r.low) if r.low else None,
                'close': float(r.close) if r.close else None,
                'volume': r.volume,
                'amount': float(r.amount) if r.amount else None,
                'amplitude': float(r.amplitude) if r.amplitude else None,
                'pct_change': float(r.pct_change) if r.pct_change else None,
                'change_amount': float(r.change_amount) if r.change_amount else None,
                'turnover': float(r.turnover) if r.turnover else None,
            } for r in rows]
            
            return pd.DataFrame(data)
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        from sqlalchemy import select
        
        stmt = select(Stock).where(Stock.status == 1)
        
        with self.db.session() as session:
            result = session.execute(stmt)
            rows = result.scalars().all()
            
            data = [{
                'symbol': r.symbol,
                'name': r.name,
                'exchange': r.exchange,
                'industry': r.industry,
            } for r in rows]
            
            return pd.DataFrame(data)
    
    def get_last_update_date(self, symbol: str, table: str = 'daily_quotes') -> Optional[date]:
        """获取某只股票的最后更新日期"""
        from sqlalchemy import select, func
        
        if table == 'daily_quotes':
            stmt = select(func.max(DailyQuote.trade_date)).where(
                DailyQuote.symbol == symbol
            )
        else:
            return None
        
        with self.db.session() as session:
            result = session.execute(stmt)
            last_date = result.scalar()
            return last_date
    
    def _log_update(
        self,
        table_name: str,
        symbol: Optional[str],
        start_date: Optional[date],
        end_date: Optional[date],
        record_count: int,
        status: str,
        message: str = ''
    ):
        """记录更新日志"""
        log = UpdateLog(
            table_name=table_name,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            record_count=record_count,
            status=status,
            message=message
        )
        
        with self.db.session() as session:
            session.add(log)
```

### 3.7 数据查询接口 (src/query/data_query.py)

```python
"""
数据查询接口 - 提供统一的数据访问
"""
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Union
from functools import lru_cache

from src.storage.mysql_storage import MySQLStorage
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataQueryEngine:
    """数据查询引擎"""
    
    def __init__(self):
        self.storage = MySQLStorage()
        self._cache = {}
    
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 股票信息
        """
        df = self.storage.get_stock_list()
        stock = df[df['symbol'] == symbol]
        
        if stock.empty:
            return None
        
        return stock.iloc[0].to_dict()
    
    def get_price_data(
        self,
        symbol: str,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        fields: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取价格数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            fields: 指定字段列表，None表示全部
            
        Returns:
            DataFrame: 价格数据
        """
        # 转换日期格式
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        df = self.storage.get_daily_quotes(symbol, start_date, end_date)
        
        if df.empty:
            logger.warning(f"未找到 {symbol} 的价格数据")
            return pd.DataFrame()
        
        # 选择指定字段
        if fields:
            available_fields = ['symbol', 'trade_date'] + fields
            df = df[[col for col in available_fields if col in df.columns]]
        
        return df
    
    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取最新价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 最新价格信息
        """
        df = self.get_price_data(symbol)
        
        if df.empty:
            return None
        
        latest = df.iloc[-1]
        return {
            'symbol': symbol,
            'date': latest['trade_date'],
            'close': latest['close'],
            'change_pct': latest['pct_change'],
            'volume': latest['volume'],
            'turnover': latest['turnover']
        }
    
    def get_multiple_stocks(
        self,
        symbols: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            dict: {symbol: DataFrame}
        """
        result = {}
        for symbol in symbols:
            df = self.get_price_data(symbol, start_date, end_date)
            if not df.empty:
                result[symbol] = df
        return result
    
    def calculate_returns(
        self,
        symbol: str,
        periods: List[int] = [1, 5, 20, 60]
    ) -> pd.DataFrame:
        """
        计算收益率
        
        Args:
            symbol: 股票代码
            periods: 计算周期列表（交易日）
            
        Returns:
            DataFrame: 包含收益率的数据
        """
        df = self.get_price_data(symbol)
        
        if df.empty:
            return pd.DataFrame()
        
        df = df.sort_values('trade_date')
        
        for period in periods:
            df[f'return_{period}d'] = df['close'].pct_change(period) * 100
        
        return df
    
    def get_trading_days(
        self,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """
        获取交易日列表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            list: 交易日列表
        """
        # 简化实现：假设所有工作日都是交易日
        days = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # 周一到周五
                days.append(current)
            current += timedelta(days=1)
        return days
    
    def resample_data(
        self,
        df: pd.DataFrame,
        rule: str = 'W',
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        重采样数据
        
        Args:
            df: 原始数据
            rule: 重采样规则 ('W'=周, 'M'=月)
            price_col: 价格列名
            
        Returns:
            DataFrame: 重采样后的数据
        """
        if df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.set_index('trade_date', inplace=True)
        
        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum'
        })
        
        resampled.reset_index(inplace=True)
        return resampled
```

### 3.8 主程序入口 (main.py)

```python
#!/usr/bin/env python3
"""
数据管理层主程序 - Phase 1
"""
import os
import sys
import argparse
from datetime import datetime, date, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.fetcher.akshare_fetcher import AKShareFetcher
from src.storage.mysql_storage import MySQLStorage
from src.query.data_query import DataQueryEngine
from src.database.connection import db_manager
from src.utils.logger import setup_logging


def init_database():
    """初始化数据库"""
    print("初始化数据库...")
    
    # 测试连接
    if not db_manager.test_connection():
        print("数据库连接失败，请检查配置")
        return False
    
    # 创建表结构
    storage = MySQLStorage()
    print("数据库初始化完成")
    return True


def update_stock_list():
    """更新股票列表"""
    print("更新股票列表...")
    
    fetcher = AKShareFetcher()
    storage = MySQLStorage()
    
    df = fetcher.get_stock_list()
    count = storage.save_stocks(df)
    
    print(f"成功更新 {count} 只股票")


def update_daily_data(symbol: str = None, start_date: str = None, end_date: str = None):
    """
    更新日线数据
    
    Args:
        symbol: 股票代码，None表示更新默认列表
        start_date: 开始日期
        end_date: 结束日期
    """
    fetcher = AKShareFetcher()
    storage = MySQLStorage()
    query = DataQueryEngine()
    
    if end_date is None:
        end_date = date.today().strftime('%Y-%m-%d')
    
    if symbol:
        symbols = [symbol]
    else:
        # 获取默认股票列表
        from src.config import data_config
        symbols = data_config.default_symbols
    
    for sym in symbols:
        try:
            # 检查最后更新日期
            last_date = storage.get_last_update_date(sym)
            
            if start_date is None:
                if last_date:
                    # 从上次更新日期的下一天开始
                    start = last_date + timedelta(days=1)
                    start_date = start.strftime('%Y-%m-%d')
                else:
                    # 使用默认起始日期
                    from src.config import data_config
                    start_date = data_config.history_start_date
            
            # 获取数据
            df = fetcher.get_daily_quotes(sym, start_date, end_date)
            
            if not df.empty:
                storage.save_daily_quotes(df)
                print(f"[{sym}] 更新完成: {len(df)} 条数据")
            else:
                print(f"[{sym}] 无新数据")
                
        except Exception as e:
            print(f"[{sym}] 更新失败: {e}")


def query_data(symbol: str, days: int = 30):
    """查询数据示例"""
    query = DataQueryEngine()
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    df = query.get_price_data(symbol, start_date, end_date)
    
    if df.empty:
        print(f"未找到 {symbol} 的数据")
        return
    
    print(f"\n{symbol} 最近 {days} 天数据:")
    print(df.tail(10).to_string(index=False))
    
    # 显示最新价格
    latest = query.get_latest_price(symbol)
    if latest:
        print(f"\n最新价格: {latest['close']}, 涨跌幅: {latest['change_pct']}%")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='量化数据管理工具')
    parser.add_argument(
        'command',
        choices=['init', 'update-stocks', 'update-daily', 'query'],
        help='要执行的命令'
    )
    parser.add_argument('--symbol', '-s', help='股票代码')
    parser.add_argument('--start-date', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--days', '-d', type=int, default=30, help='查询天数')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    if args.command == 'init':
        init_database()
    
    elif args.command == 'update-stocks':
        update_stock_list()
    
    elif args.command == 'update-daily':
        update_daily_data(args.symbol, args.start_date, args.end_date)
    
    elif args.command == 'query':
        if not args.symbol:
            print("请指定股票代码: --symbol 000001")
            return
        query_data(args.symbol, args.days)


if __name__ == '__main__':
    main()
```

### 3.9 依赖文件 (requirements.txt)

```
# 核心依赖
akshare>=1.11.0
pandas>=2.0.0
numpy>=1.24.0

# 数据库
sqlalchemy>=2.0.0
pymysql>=1.1.0
cryptography>=41.0.0  # 用于MySQL密码加密

# 工具
python-dotenv>=1.0.0
loguru>=0.7.0

# 开发依赖
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.0.0
```

---

## 4. 部署与使用

### 4.1 环境准备

```bash
# 1. 安装 MySQL
sudo apt-get install mysql-server  # Ubuntu/Debian
# 或
brew install mysql  # macOS

# 2. 创建数据库和用户
mysql -u root -p
```

```sql
-- 创建数据库
CREATE DATABASE quant_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'quant_user'@'localhost' IDENTIFIED BY 'quant_password';
GRANT ALL PRIVILEGES ON quant_data.* TO 'quant_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4.2 项目初始化

```bash
# 1. 克隆/创建项目目录
cd /home/admin/.openclaw/workspace/quant_project

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
python main.py init
```

### 4.3 日常使用

```bash
# 更新股票列表
python main.py update-stocks

# 更新日线数据（默认股票列表）
python main.py update-daily

# 更新指定股票数据
python main.py update-daily --symbol 000001

# 更新指定日期范围
python main.py update-daily --symbol 000001 --start-date 2024-01-01 --end-date 2024-12-31

# 查询数据
python main.py query --symbol 000001 --days 30
```

---

## 5. Phase 1 功能清单

### 5.1 已实现功能

| 功能模块 | 功能点 | 状态 |
|---------|--------|------|
| 数据获取 | A股股票列表获取 | ✅ |
| 数据获取 | 日线行情数据获取 | ✅ |
| 数据获取 | 财务指标数据获取 | ✅ |
| 数据存储 | MySQL数据库连接池 | ✅ |
| 数据存储 | 股票信息表 | ✅ |
| 数据存储 | 日线数据表 | ✅ |
| 数据存储 | 财务指标表 | ✅ |
| 数据存储 | 交易日历表 | ✅ |
| 数据存储 | 更新日志表 | ✅ |
| 数据查询 | 单只股票价格查询 | ✅ |
| 数据查询 | 多只股票批量查询 | ✅ |
| 数据查询 | 最新价格获取 | ✅ |
| 数据查询 | 收益率计算 | ✅ |
| 数据查询 | 数据重采样 | ✅ |
| 工具 | 日志记录 | ✅ |
| 工具 | 数据校验 | ✅ |
| 工具 | 命令行接口 | ✅ |

### 5.2 Phase 2 规划（未来版本）

- [ ] 分钟级数据支持
- [ ] 实时行情数据接入
- [ ] 数据缓存层 (Redis)
- [ ] 多数据源支持 (Tushare, JoinQuant)
- [ ] 数据质量监控
- [ ] 自动更新调度
- [ ] 数据导出功能 (CSV, Parquet)
- [ ] 数据可视化接口

---

## 6. 附录

### 6.1 数据库 ERD

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│     stocks      │     │  daily_quotes    │     │financial_indicators│
├─────────────────┤     ├──────────────────┤     ├───────────────────┤
│ PK id           │◄────┤ FK symbol        │     │ FK symbol         │
│    symbol (UQ)  │     │    trade_date    │     │    report_date    │
│    name         │     │    open          │     │    eps            │
│    exchange     │     │    high          │     │    roe            │
│    industry     │     │    low           │     │    revenue        │
│    list_date    │     │    close         │     └───────────────────┘
│    status       │     │    volume        │
└─────────────────┘     │    amount        │
                        │    pct_change    │
                        └──────────────────┘
```

### 6.2 AKShare 接口参考

| 数据类型 | AKShare 函数 | 说明 |
|---------|-------------|------|
| 股票列表 | `stock_zh_a_spot_em()` | A股实时行情（含列表） |
| 日线数据 | `stock_zh_a_hist()` | 历史日线数据 |
| 分钟数据 | `stock_zh_a_minute()` | 分钟级数据 |
| 财务数据 | `stock_financial_report_sina()` | 财务报表 |
| 交易日历 | `tool_trade_date_hist_sina()` | 交易日历 |

---

**文档版本**: v1.0.0  
**最后更新**: 2026-03-10  
**作者**: AI Assistant
