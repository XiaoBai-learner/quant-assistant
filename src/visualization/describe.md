# Visualization 可视化层

## 模块概述

可视化层提供终端图表展示功能，支持K线图、技术指标和绩效报告的ASCII渲染。采用模块化设计，支持多种指标和灵活的布局配置。

## 架构图

```
原始数据
    ↓
数据适配器 (DataAdapter)
    ↓
指标计算 (IndicatorEngine)
    ↓
图表渲染 (ASCIIRenderer)
    ↓
布局管理 (ChartLayout)
    ↓
终端输出
```

## 子模块说明

### indicators/ - 技术指标

**功能**: 技术指标计算和管理

**核心类**:
- `IndicatorResult`: 指标计算结果
  - 属性: name, values, params, metadata

- `BaseIndicator`: 指标基类
  - `calculate(df)`: 计算指标（抽象方法）
  - `_validate_params()`: 验证参数

- `IndicatorEngine`: 指标计算引擎
  - `register(indicator)`: 注册指标
  - `calculate(df, indicator_names)`: 批量计算指标
  - `list_indicators()`: 列出所有指标
  - `clear_cache()`: 清空缓存

**内置指标**:

1. **MAIndicator** (moving_average.py)
   - 功能: 移动平均线
   - 参数: period, ma_type ('sma', 'ema'), price_col
   - 计算: SMA = mean(close, period), EMA = ewm(close, span=period)

2. **MA5Indicator / MA10Indicator / MA20Indicator**
   - 预定义的MA指标

3. **MACDIndicator** (macd.py)
   - 功能: MACD指标
   - 参数: fast_period=12, slow_period=26, signal_period=9
   - 计算:
     - DIF = EMA(12) - EMA(26)
     - DEA = EMA(DIF, 9)
     - MACD = 2 * (DIF - DEA)
   - `get_signal(df)`: 获取交易信号（金叉/死叉）

**使用示例**:
```python
from src.visualization.indicators import IndicatorEngine, MAIndicator

engine = IndicatorEngine()
result = engine.calculate(df, ['MA5', 'MA10', 'MACD'])
ma5_values = result['MA5'].values
macd_values = result['MACD'].values
```

### renderers/ - 渲染器

**功能**: ASCII图表渲染

**核心类**:
- `BaseRenderer`: 渲染器基类
  - `render_candlestick(df)`: 渲染K线图
  - `render_volume(df)`: 渲染成交量
  - `render_indicator(df, indicator)`: 渲染指标

- `ASCIIRenderer`: ASCII渲染器
  - `render_candlestick(df, width=80, height=20)`: 渲染K线图
    - 使用不同字符表示涨跌
    - 自动缩放价格范围
    - 显示OHLC信息
  - `render_volume(df, width=80)`: 渲染成交量柱状图
  - `render_indicator(df, indicator, width=80, height=10)`: 渲染指标

- `SimpleTableRenderer`: 简单表格渲染器
  - `render(df)`: 渲染数据表格
  - 显示日期、开盘、最高、最低、收盘、成交量

**K线图字符**:
- `█`: 实体部分（涨）
- `░`: 实体部分（跌）
- `│`: 影线
- `┬`: 上影线顶部
- `┴`: 下影线底部

**使用示例**:
```python
from src.visualization.renderers import ASCIIRenderer

renderer = ASCIIRenderer()
chart = renderer.render_candlestick(df, width=80, height=20)
print(chart)
```

### layouts/ - 布局管理

**功能**: 图表布局管理器

**核心类**:
- `ChartLayout`: 图表布局管理器
  - `__init__(renderer)`: 初始化
  - `display(df, symbol, period, indicators, show_table, show_chart)`: 显示完整图表
  - 整合数据适配、指标计算和图表渲染

**布局组件**:
1. 标题: 股票代码 + 周期
2. 数据表格: 最近N条数据
3. K线图: 价格走势
4. 指标图: MA/MACD等

**使用示例**:
```python
from src.visualization.layouts import ChartLayout

layout = ChartLayout()
output = layout.display(
    df=df,
    symbol='000001',
    period='D',
    indicators=['MA5', 'MA10', 'MACD'],
    show_table=True,
    show_chart=True
)
print(output)
```

### adapters/ - 数据适配

**功能**: 数据预处理和适配

**核心类**:
- `DataAdapter`: 数据适配器
  - `prepare_for_chart(df, period)`: 准备图表数据
    - 重采样 (日线/周线)
    - 计算涨跌幅
    - 格式化数据
  - `resample_to_weekly(df)`: 转换为周线
  - `calculate_change(df)`: 计算涨跌幅

**使用示例**:
```python
from src.visualization.adapters import DataAdapter

adapter = DataAdapter()
df_prepared = adapter.prepare_for_chart(df, period='W')
```

### cli.py - 命令行界面

**功能**: 命令行交互界面

**核心类**:
- `ChartCLI`: 图表命令行工具
  - `show_chart(symbol, period, days, indicators)`: 显示图表
  - `interactive_mode()`: 交互模式
  - `batch_mode(symbols, config)`: 批量模式

## 接口汇总

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| IndicatorEngine.calculate | df, indicator_names | Dict[str, IndicatorResult] | 计算指标 |
| ASCIIRenderer.render_candlestick | df, width, height | str | 渲染K线图 |
| ASCIIRenderer.render_volume | df, width | str | 渲染成交量 |
| ChartLayout.display | df, symbol, period, indicators | str | 显示完整图表 |
| DataAdapter.prepare_for_chart | df, period | DataFrame | 准备数据 |

## 使用示例

### 完整示例
```python
from src.visualization import ChartLayout
from src.data import DataQueryEngine

# 查询数据
query = DataQueryEngine()
df = query.get_price_data('000001', '2024-01-01', '2024-12-31')

# 显示图表
layout = ChartLayout()
output = layout.display(
    df=df,
    symbol='000001',
    period='D',
    indicators=['MA5', 'MA10', 'MACD'],
    show_table=True,
    show_chart=True
)
print(output)
```

### 命令行使用
```bash
# 显示K线图
python main.py chart --symbol 000001

# 显示周线
python main.py chart --symbol 000001 --period W

# 显示带MACD
python main.py chart --symbol 000001 --macd

# 指定MA周期
python main.py chart --symbol 000001 --ma 5 10 20
```

## 支持的指标

| 指标 | 说明 | 参数 |
|------|------|------|
| MA5 | 5日移动平均 | period=5 |
| MA10 | 10日移动平均 | period=10 |
| MA20 | 20日移动平均 | period=20 |
| MACD | MACD指标 | fast=12, slow=26, signal=9 |

## 渲染限制

- 终端宽度: 建议80-120字符
- 图表高度: 默认20行
- 数据条数: 自动适配终端大小
