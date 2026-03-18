# 数据源使用指南

> 本指南详细介绍 Quant Assistant 的数据源配置和使用方法

---

## 目录

1. [概述](#1-概述)
2. [统一数据获取器](#2-统一数据获取器)
3. [AKShare 数据源](#3-akshare-数据源)
4. [TickFlow 数据源](#4-tickflow-数据源)
5. [EFinance 数据源](#5-efinance-数据源)
6. [数据源对比](#6-数据源对比)
7. [配置参考](#7-配置参考)
8. [常见问题](#8-常见问题)

---

## 1. 概述

Quant Assistant 支持多个数据源，通过统一接口对外提供服务：

| 数据源 | 类型 | 特点 |
|--------|------|------|
| **AKShare** | 免费开源 | 数据丰富、更新及时、无需注册 |
| **TickFlow** | 免费/付费 | API 稳定、分钟级数据、实时行情 |
| **EFinance** | 免费 | 细粒度实时数据、支持分钟级/分笔级 |

推荐使用 **统一数据获取器 (UnifiedDataFetcher)**，它会自动管理多个数据源，支持故障切换。

---

## 2. 统一数据获取器

### 2.1 基本使用

```python
from quant_assistant.data import UnifiedDataFetcher

# 创建统一数据获取器（默认 AKShare 为主，其他为备用）
fetcher = UnifiedDataFetcher()

# 获取股票列表
stocks = fetcher.get_stock_list()
print(f"获取到 {len(stocks)} 只股票")

# 获取日线数据
df = fetcher.get_daily_quotes(
    symbol='600000',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

### 2.2 配置数据源优先级

```python
# 使用 TickFlow 为主数据源
fetcher = UnifiedDataFetcher(primary_source='tickflow')

# 使用 AKShare 为主数据源（默认）
fetcher = UnifiedDataFetcher(primary_source='akshare')

# 自动选择（根据接口智能选择最优数据源）
fetcher = UnifiedDataFetcher(primary_source='auto')
```

### 2.3 故障自动切换

```python
# 启用故障切换（默认）
fetcher = UnifiedDataFetcher(fallback_enabled=True)

# 禁用故障切换（只使用主数据源）
fetcher = UnifiedDataFetcher(fallback_enabled=False)
```

当主数据源失败时，会自动尝试备用数据源，无需手动处理。

### 2.4 完整配置示例

```python
from quant_assistant.data import UnifiedDataFetcher

fetcher = UnifiedDataFetcher(
    primary_source='tickflow',        # 主数据源
    fallback_enabled=True,            # 启用故障切换
    tickflow_api_key='your-key',      # TickFlow API Key（付费版需要）
    tickflow_use_paid=True            # 使用 TickFlow 付费版
)
```

---

## 3. AKShare 数据源

### 3.1 特点

- **免费开源**：无需注册，直接使用
- **数据丰富**：A股、港股、美股、期货、期权、基金等
- **更新及时**：日线数据通常 T+1 更新
- **社区活跃**：持续维护和更新

### 3.2 直接使用

```python
from quant_assistant.data import AKShareFetcher

fetcher = AKShareFetcher()

# 获取股票列表
stocks = fetcher.get_stock_list()

# 获取日线数据
df = fetcher.get_daily_quotes('600000', start_date='2024-01-01')

# 获取财务指标
df = fetcher.get_financial_indicators('600000')
```

### 3.3 支持的接口

| 接口 | 支持情况 |
|------|----------|
| `get_stock_list()` | ✅ 完整支持 |
| `get_daily_quotes()` | ✅ 完整支持 |
| `get_financial_indicators()` | ✅ 完整支持 |
| `get_minute_quotes()` | ⚠️ 支持有限 |
| `get_realtime_quotes()` | ⚠️ 支持有限 |

---

## 4. TickFlow 数据源

### 4.1 特点

- **API 稳定**：RESTful API，响应稳定
- **分钟级数据**：支持 1m/5m/15m/30m/60m K线
- **实时行情**：付费版支持实时行情推送
- **免费可用**：免费版无需注册即可使用基础功能

### 4.2 免费版 vs 付费版

| 功能 | 免费版 | 付费版 |
|------|--------|--------|
| 日K线数据 | ✅ | ✅ |
| 股票列表 | ✅ | ✅ |
| 财务数据 | ✅ | ✅ |
| 分钟级K线 | ❌ | ✅ |
| 实时行情 | ❌ | ✅ |
| 访问频率 | 较低 | 较高 |

### 4.3 直接使用

```python
from quant_assistant.data import TickFlowFetcher

# 免费版（无需 API Key）
fetcher = TickFlowFetcher()

# 付费版（需要 API Key）
fetcher = TickFlowFetcher(
    api_key='your-api-key',
    use_paid=True
)

# 获取日线数据
df = fetcher.get_daily_quotes('600000.SH', start_date='2024-01-01')

# 获取分钟数据（需要付费版）
df = fetcher.get_minute_quotes('600000.SH', period='5m')

# 获取实时行情（需要付费版）
df = fetcher.get_realtime_quotes(['600000.SH', '000001.SZ'])
```

---

## 5. EFinance 数据源

### 5.1 特点

- **细粒度数据**：支持分钟级、分笔级数据
- **实时数据**：提供实时行情数据
- **免费使用**：无需 API Key

### 5.2 直接使用

```python
from quant_assistant.data import EFinanceFetcher

fetcher = EFinanceFetcher()

# 获取实时行情
realtime = fetcher.get_realtime_quotes(['300751'])

# 获取分钟级数据
minute_data = fetcher.get_minute_data('300751', period=5)

# 获取分笔数据
tick_data = fetcher.get_tick_data('300751')
```

---

## 6. 数据源对比

### 6.1 日线数据

```python
from quant_assistant.data import UnifiedDataFetcher

fetcher = UnifiedDataFetcher()

# 两种数据源都能获取日线数据
df = fetcher.get_daily_quotes('600000', start_date='2024-01-01')

# 内部逻辑：
# 1. 优先使用主数据源（默认 AKShare）
# 2. 如果失败，自动切换到备用数据源（TickFlow）
```

### 6.2 分钟数据

```python
from quant_assistant.data import UnifiedDataFetcher

fetcher = UnifiedDataFetcher()

# 分钟数据优先使用 TickFlow 或 EFinance
df = fetcher.get_minute_quotes('600000', period='5m')
```

### 6.3 实时行情

```python
from quant_assistant.data import UnifiedDataFetcher

fetcher = UnifiedDataFetcher()

# 实时行情优先使用 EFinance 或 TickFlow
df = fetcher.get_realtime_quotes(['600000', '000001'])
```

---

## 7. 配置参考

### 7.1 统一数据获取器参数

```python
UnifiedDataFetcher(
    primary_source='akshare',      # 主数据源: 'akshare' | 'tickflow' | 'efinance' | 'auto'
    fallback_enabled=True,         # 是否启用故障切换: True | False
    tickflow_api_key=None,         # TickFlow API Key（付费版需要）
    tickflow_use_paid=False        # 是否使用 TickFlow 付费版: True | False
)
```

### 7.2 股票代码格式

统一数据获取器支持多种股票代码格式：

```python
# 以下格式都支持
fetcher.get_daily_quotes('600000')        # 纯代码（推荐）
fetcher.get_daily_quotes('600000.SH')     # 带交易所后缀
fetcher.get_daily_quotes('SH600000')      # 带交易所前缀

# 统一数据获取器会自动标准化为纯代码格式
```

---

## 8. 常见问题

### Q1: 为什么推荐使用统一数据获取器？

**A**: 统一数据获取器提供以下优势：
- **统一接口**：无论底层使用哪个数据源，调用方式完全一致
- **故障切换**：主数据源失败时自动切换到备用数据源
- **智能选择**：根据数据类型自动选择最优数据源
- **代码简洁**：无需关心底层实现细节

### Q2: 如何切换主数据源？

**A**: 通过 `primary_source` 参数切换：

```python
# 使用 AKShare 为主
fetcher = UnifiedDataFetcher(primary_source='akshare')

# 使用 TickFlow 为主
fetcher = UnifiedDataFetcher(primary_source='tickflow')
```

### Q3: 故障切换是如何工作的？

**A**: 当主数据源请求失败时，会自动尝试备用数据源。

### Q4: 如何获取分钟级数据？

**A**: 分钟级数据需要 TickFlow 付费版或 EFinance：

```python
from quant_assistant.data import UnifiedDataFetcher

fetcher = UnifiedDataFetcher()
df = fetcher.get_minute_quotes('600000', period='5m')
```

### Q5: 如何检查数据源是否可用？

**A**: 使用 `is_available()` 方法：

```python
from quant_assistant.data import UnifiedDataFetcher, DataSourceType

fetcher = UnifiedDataFetcher()

# 检查主数据源
if fetcher.is_available():
    print("主数据源可用")

# 获取所有可用数据源
sources = fetcher.get_available_sources()
print(f"可用数据源: {sources}")
```

---

## 参考链接

- [AKShare 文档](https://www.akshare.xyz/)
- [TickFlow 文档](https://docs.tickflow.org/zh-Hans)
- [Quant Assistant GitHub](https://github.com/XiaoBai-learner/quant-assistant)
