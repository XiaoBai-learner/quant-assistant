# 用户界面层设计文档

## 文档信息
- **版本**: v1.0.0
- **日期**: 2026-03-10
- **模块**: UI Layer (用户界面层)
- **依赖**: 数据管理层 (Phase 1 ✅)

---

## 一、架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户界面层 (UI Layer)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Chart      │  │  Indicator   │  │   Layout     │          │
│  │   Renderer   │  │   Engine     │  │   Manager    │          │
│  │  (图表渲染)   │  │  (指标计算)   │  │  (布局管理)   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           │                                    │
│                           ▼                                    │
│              ┌─────────────────────┐                          │
│              │    Data Adapter     │                          │
│              │   (数据适配器)       │                          │
│              └──────────┬──────────┘                          │
│                         │                                      │
└─────────────────────────┼──────────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │   Data Manager      │
              │   (Phase 1 ✅)      │
              └─────────────────────┘
```

### 1.2 工作包划分

| 工作包 | 模块 | 职责 | 输出 |
|--------|------|------|------|
| WP1 | Data Adapter | 数据格式转换、重采样 | data_adapter.py |
| WP2 | Indicator Engine | 技术指标计算 (MA/MACD) | indicators.py |
| WP3 | Chart Renderer | K线图表渲染 | chart_renderer.py |
| WP4 | Layout Manager | 多图表布局 | layout_manager.py |
| WP5 | CLI Interface | 命令行交互界面 | cli.py |

### 1.3 模块依赖关系

```
WP5 (CLI Interface)
    ├── WP4 (Layout Manager)
    │       └── WP3 (Chart Renderer)
    │               ├── WP2 (Indicator Engine)
    │               └── WP1 (Data Adapter)
    └── WP1 (Data Adapter)
            └── Data Manager
```

---

## 二、接口设计

### 2.1 Data Adapter 接口

```python
class DataAdapter:
    """数据适配器 - 将原始数据转换为图表所需格式"""
    
    def resample(df: pd.DataFrame, period: str) -> pd.DataFrame
        """数据重采样 (日线 -> 周线/月线)"""
    
    def normalize(df: pd.DataFrame) -> pd.DataFrame
        """数据标准化处理"""
    
    def fill_missing(df: pd.DataFrame) -> pd.DataFrame
        """缺失值填充"""
```

### 2.2 Indicator Engine 接口

```python
class IndicatorEngine:
    """指标计算引擎"""
    
    def ma(df: pd.DataFrame, period: int) -> pd.Series
        """简单移动平均线"""
    
    def ema(df: pd.DataFrame, period: int) -> pd.Series
        """指数移动平均线"""
    
    def macd(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]
        """MACD指标 (DIF, DEA, MACD)"""
```

### 2.3 Chart Renderer 接口

```python
class ChartRenderer:
    """图表渲染器"""
    
    def render_candlestick(df: pd.DataFrame, title: str) -> str
        """渲染K线图 (返回HTML或ASCII)"""
    
    def render_with_indicators(
        df: pd.DataFrame, 
        indicators: List[Indicator],
        title: str
    ) -> str
        """渲染带指标的K线图"""
```

---

## 三、技术指标规格

### 3.1 支持的指标

| 指标 | 参数 | 说明 |
|------|------|------|
| MA5 | period=5 | 5日简单移动平均线 |
| MA10 | period=10 | 10日简单移动平均线 |
| MA20 | period=20 | 20日简单移动平均线 |
| MACD | fast=12, slow=26, signal=9 | MACD指标 |

### 3.2 计算公式

**MA (简单移动平均线)**:
```
MA_n = (Close_1 + Close_2 + ... + Close_n) / n
```

**MACD**:
```
EMA_12 = 12日指数移动平均
EMA_26 = 26日指数移动平均
DIF = EMA_12 - EMA_26
DEA = DIF的9日EMA
MACD = 2 * (DIF - DEA)
```

---

## 四、UI 展示规格

### 4.1 命令行界面 (Phase 1)

使用 ASCII 图表或纯文本表格展示：

```
┌────────────────────────────────────────────────────────────┐
│ 股票: 000001 平安银行                                       │
│ 周期: 日线  时间范围: 2024-01-01 ~ 2024-03-10              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  12.00 ┤                                          ╭─╮     │
│  11.50 ┤                              ╭─╮    ╭───╯  │     │
│  11.00 ┤          ╭─╮    ╭──╮    ╭───╯  ╰────╯      │     │
│  10.50 ┤    ╭────╯  ╰────╯  ╰────╯                  │     │
│  10.00 ┤────╯                                       ╰──   │
│                                                            │
│  MA5:  11.20  ▲                                          │
│  MA10: 11.05  ▲                                          │
│  MA20: 10.85  ▲                                          │
├────────────────────────────────────────────────────────────┤
│ MACD:                                                      │
│  DIF:  0.25  DEA: 0.15  MACD: 0.20  ████████              │
└────────────────────────────────────────────────────────────┘
```

### 4.2 Web 界面 (Phase 2 预留)

使用 ECharts 或 Plotly 实现交互式图表

---

## 五、开发计划

### 5.1 工作包开发顺序

1. **WP1 - Data Adapter** (30分钟)
   - 数据重采样功能
   - 数据清洗功能

2. **WP2 - Indicator Engine** (45分钟)
   - MA 指标实现
   - MACD 指标实现
   - 指标验证

3. **WP3 - Chart Renderer** (45分钟)
   - ASCII K线图渲染
   - 指标叠加显示

4. **WP4 - Layout Manager** (30分钟)
   - 多图表布局
   - 信息面板

5. **WP5 - CLI Interface** (30分钟)
   - 命令行参数
   - 交互界面

### 5.2 验收标准

- [ ] 可展示指定股票的K线图
- [ ] 可切换日线/周线视图
- [ ] 可显示 MA5/MA10/MA20
- [ ] 可显示 MACD 指标
- [ ] 命令行交互流畅

---

## 六、文件结构

```
src/
├── visualization/              # 新增: 可视化模块
│   ├── __init__.py
│   ├── adapters/              # WP1: Data Adapter
│   │   ├── __init__.py
│   │   └── data_adapter.py
│   ├── indicators/            # WP2: Indicator Engine
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── moving_average.py
│   │   └── macd.py
│   ├── renderers/             # WP3: Chart Renderer
│   │   ├── __init__.py
│   │   ├── base_renderer.py
│   │   └── ascii_renderer.py
│   ├── layouts/               # WP4: Layout Manager
│   │   ├── __init__.py
│   │   └── chart_layout.py
│   └── cli.py                 # WP5: CLI Interface
```

---

**设计完成，开始开发**
