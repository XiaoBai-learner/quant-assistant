-- 量化数据管理系统 - 数据库结构
-- Phase 1 基础版

-- 创建数据库
CREATE DATABASE IF NOT EXISTS quant_data 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE quant_data;

-- 股票基础信息表
CREATE TABLE IF NOT EXISTS stocks (
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

-- 日线行情数据表
CREATE TABLE IF NOT EXISTS daily_quotes (
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

-- 分钟线数据表
CREATE TABLE IF NOT EXISTS minute_quotes (
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

-- 财务指标表
CREATE TABLE IF NOT EXISTS financial_indicators (
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

-- 交易日历表
CREATE TABLE IF NOT EXISTS trade_calendar (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    trade_date      DATE NOT NULL COMMENT '日期',
    is_trading_day  TINYINT DEFAULT 1 COMMENT '是否交易日: 1-是, 0-否',
    exchange        VARCHAR(10) COMMENT '交易所',
    week_day        TINYINT COMMENT '星期几 (1-7)',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_date_exchange (trade_date, exchange),
    KEY idx_trade_date (trade_date)
) ENGINE=InnoDB COMMENT='交易日历表';

-- 数据更新日志表
CREATE TABLE IF NOT EXISTS update_logs (
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
