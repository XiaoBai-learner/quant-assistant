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
