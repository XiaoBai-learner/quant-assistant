# Data 数据管理层

## 模块概述

数据管理层负责量化数据的完整生命周期管理，包括数据获取、清洗、存储、查询和缓存。采用分层架构设计，支持多数据源接入和统一查询接口。

## 架构图

```
外部数据源 (AKShare/Tushare)
    ↓
Fetcher (数据获取)
    ↓
Validator (数据校验)
    ↓
Storage (数据存储)
    ↓
Cache (缓存层)
    ↓
Query Engine (查询引擎)
    ↓
上层模块 (策略/回测)
```

## 子模块说明

### fetcher/ - 数据获取

**功能**: 从外部数据源获取原始数据

**核心类**:
- `BaseDataFetcher`: 数据获取器基类
  - `get_stock_list()`: 获取股票列表
  - `get_daily_quotes(symbol, start_date, end_date)`: 获取日线数据
  - `get_financial_indicators(symbol)`: 获取财务指标

- `AKShareFetcher`: AKShare 数据获取实现
  - 支持A股实时/历史行情
  - 自动速率限制 (0.5秒间隔)
  - 数据字段自动映射

**使用示例**:
```python
from src.data import AKShareFetcher

fetcher = AKShareFetcher()
stocks = fetcher.get_stock_list()
df = fetcher.get_daily_quotes('000001', '2024-01-01', '2024-12-31')
```

### storage/ - 数据存储

**功能**: 数据持久化存储

**核心类**:
- `BaseStorage`: 存储基类
  - `save_stocks(df)`: 保存股票列表
  - `save_daily_quotes(df)`: 保存日线数据
  - `get_daily_quotes(symbol, start_date, end_date)`: 查询日线数据

- `MySQLStorage`: MySQL 存储实现
  - 使用 SQLAlchemy ORM
  - 支持 upsert 操作 (ON DUPLICATE KEY UPDATE)
  - 自动记录更新日志

**数据表**:
- `stocks`: 股票基础信息 (symbol, name, exchange, industry)
- `daily_quotes`: 日线行情 (open, high, low, close, volume, amount)
- `financial_indicators`: 财务指标
- `trade_calendar`: 交易日历
- `update_logs`: 更新日志

### query/ - 数据查询

**功能**: 统一数据查询接口

**核心类**:
- `DataQueryEngine`: 数据查询引擎
  - `get_stock_info(symbol)`: 获取股票信息
  - `get_price_data(symbol, start_date, end_date, fields)`: 获取价格数据
  - `get_latest_price(symbol)`: 获取最新价格
  - `get_multiple_stocks(symbols, start_date, end_date)`: 批量获取
  - `calculate_returns(symbol, periods)`: 计算收益率
  - `resample_data(df, rule)`: 数据重采样

**使用示例**:
```python
from src.data import DataQueryEngine

query = DataQueryEngine()
df = query.get_price_data('000001', '2024-01-01', '2024-12-31')
returns = query.calculate_returns('000001', [1, 5, 20, 60])
```

### database/ - 数据库连接

**功能**: 数据库连接管理和模型定义

**核心类**:
- `db_manager`: 数据库管理器（单例）
  - `engine`: SQLAlchemy 引擎
  - `session()`: 上下文管理器会话
  - `test_connection()`: 测试连接

- `Stock`: 股票模型
- `DailyQuote`: 日线数据模型
- `FinancialIndicator`: 财务指标模型

## 配置

环境变量配置 (`.env`):
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=quant_user
DB_PASSWORD=your_password
DB_NAME=quant_data
```

## 接口汇总

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| AKShareFetcher.get_stock_list | - | DataFrame | 获取A股列表 |
| AKShareFetcher.get_daily_quotes | symbol, start, end | DataFrame | 获取日线数据 |
| MySQLStorage.save_daily_quotes | DataFrame | int | 保存日线数据 |
| MySQLStorage.get_daily_quotes | symbol, start, end | DataFrame | 查询日线数据 |
| DataQueryEngine.get_price_data | symbol, start, end | DataFrame | 统一查询接口 |
| DataQueryEngine.get_latest_price | symbol | dict | 获取最新价格 |
