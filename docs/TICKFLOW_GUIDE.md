# TickFlow 数据源使用指南

本文档介绍如何在 Quant Assistant 中使用 TickFlow 数据源。

## 概述

TickFlow 是一个稳定、易用的行情数据服务，提供实时行情和历史 K 线数据。

- **免费版**: https://free-api.tickflow.org (无需 API Key)
- **付费版**: https://api.tickflow.org (需要 API Key)

## 免费版 vs 付费版

| 功能 | 免费版 | 付费版 |
|------|--------|--------|
| 日K线数据 (1d, 1w, 1M, 1Q, 1Y) | ✅ | ✅ |
| 标的信息查询 | ✅ | ✅ |
| 财务数据 (资产负债表/利润表/现金流量表) | ✅ | ✅ |
| 核心财务指标 | ✅ | ✅ |
| 交易所列表 | ✅ | ✅ |
| 分钟级K线 (1m, 5m, 15m, 30m, 60m) | ❌ | ✅ |
| 实时行情 | ❌ | ✅ |
| 更高频率访问 | ❌ | ✅ |

## 快速开始

### 安装依赖

TickFlow 数据获取器使用标准库 `requests`，无需额外安装依赖。

### 基本使用

```python
from quant_assistant.data import TickFlowFetcher

# 创建免费版获取器
fetcher = TickFlowFetcher()

# 检查服务可用性
if fetcher.is_available():
    print("TickFlow 服务可用")
```

## API 参考

### 获取交易所列表

```python
exchanges = fetcher.get_exchanges()
print(exchanges)
# 输出: DataFrame 包含 exchange, region, count 列
```

### 获取股票列表

```python
# 获取全部A股
stocks = fetcher.get_stock_list()

# 获取指定交易所
sh_stocks = fetcher.get_stock_list('SH')  # 上交所
sz_stocks = fetcher.get_stock_list('SZ')  # 深交所
bj_stocks = fetcher.get_stock_list('BJ')  # 北交所
```

### 获取日线数据

```python
# 获取日线数据
df = fetcher.get_daily_quotes(
    '600000',  # 股票代码
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 返回 DataFrame 包含:
# - trade_date: 交易日期
# - open: 开盘价
# - high: 最高价
# - low: 最低价
# - close: 收盘价
# - volume: 成交量
# - amount: 成交额
# - symbol: 股票代码
```

### 获取财务数据

```python
# 获取财务指标
metrics = fetcher.get_financial_indicators('600000.SH')

# 获取利润表
income = fetcher.get_income_statement('600000.SH')

# 获取资产负债表
balance = fetcher.get_balance_sheet('600000.SH')

# 获取现金流量表
cashflow = fetcher.get_cash_flow('600000.SH')
```

### 获取标的信息

```python
info = fetcher.get_instrument_info('600000.SH')
print(info)
# 输出: 包含 symbol, name, exchange, type, listing_date 等
```

## 付费版功能

### 初始化付费版

```python
from quant_assistant.data import TickFlowFetcher

# 使用 API Key 初始化付费版
fetcher = TickFlowFetcher(
    api_key='your-api-key',
    use_paid=True
)
```

### 获取分钟级数据

```python
# 获取5分钟K线
df = fetcher.get_minute_quotes(
    '600000.SH',
    period='5m',  # 支持 '1m', '5m', '15m', '30m', '60m'
    start_date='2024-01-01',
    end_date='2024-01-31'
)
```

### 获取实时行情

```python
# 获取实时行情
quotes = fetcher.get_realtime_quotes(['600000.SH', '000001.SZ'])
```

## 完整示例

```python
from quant_assistant.data import TickFlowFetcher
import pandas as pd

# 创建获取器
fetcher = TickFlowFetcher()

# 获取浦发银行数据
df = fetcher.get_daily_quotes('600000.SH', start_date='2024-01-01')

# 计算简单指标
latest = df.iloc[-1]
print(f"最新价格: {latest['close']}")
print(f"涨跌幅: {(latest['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close'] * 100:.2f}%")

# 获取财务数据
financials = fetcher.get_financial_indicators('600000.SH')
if not financials.empty:
    print(f"最新财务指标: {financials.iloc[0].to_dict()}")
```

## 错误处理

```python
from quant_assistant.core.exceptions import DataFetchException

try:
    df = fetcher.get_daily_quotes('600000.SH')
except DataFetchException as e:
    print(f"数据获取失败: {e}")
```

## 注意事项

1. **免费版限制**: 免费版不提供分钟级数据和实时行情
2. **速率限制**: 请合理控制请求频率，避免触发限流
3. **数据格式**: 股票代码格式支持 `600000` 或 `600000.SH`
4. **日期格式**: 支持 `YYYY-MM-DD` 格式

## 获取 API Key

如需使用付费版功能，请访问 [tickflow.org](https://tickflow.org) 注册并获取 API Key。

## 文档

- TickFlow 官方文档: https://docs.tickflow.org/zh-Hans
- OpenAPI 规范: https://free-api.tickflow.org/openapi.json
