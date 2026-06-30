# Quant Assistant - 个人量化研究助手

Quant Assistant 是一个面向 A 股研究的个人量化框架，聚焦数据获取、因子计算、策略构建、回测验证和终端可视化。项目当前定位为“研究与验证工具”，适合用于个人策略实验、行情数据整理、技术指标分析和回测复盘；实盘交易、Web 平台和生产级监控仍处于规划阶段。

> 风险提示：本项目仅供学习研究使用，不构成投资建议，也不提供实盘交易保证。

## 当前能力

| 能力域 | 状态 | 说明 |
|---|---:|---|
| 数据管理 | 已实现 | 支持 AKShare、EFinance、TickFlow 获取器，MySQL 存储，统一查询，数据校验和缓存基础设施。 |
| 因子与指标 | 已实现 | 支持 MA、EMA、MACD、RSI、BOLL、KDJ、ATR、OBV 等技术因子，并包含 V2 因子引擎。 |
| 策略研究 | 已实现 | 提供 `BaseStrategy`、信号生成、股票筛选、内置策略、策略组合和参数优化能力。 |
| 回测验证 | 已实现 | 支持事件驱动与向量化回测，包含模拟券商、真实撮合、投资组合、成本模型和绩效分析。 |
| 机器学习 | 已实现基础版 | 提供特征工程、模型封装、评估和股票预测器基础能力。 |
| 可视化 | 已实现终端版 | 支持 ASCII K 线、技术指标、数据表格和命令行图表工具。 |
| 风控 | 已实现基础版 | 提供仓位、回撤、集中度等风控管理基础能力。 |
| 实盘交易 | 未实现 | 尚无券商网关、订单状态机、账户同步和自动执行能力。 |
| Web 平台 | 未实现 | 尚无 Web UI、策略工作台、实时看板和多用户系统。 |

## 项目结构

```text
quant-assistant/
├── README.md
├── main.py
├── pyproject.toml
├── requirements.txt
├── config/
│   ├── default.yaml
│   └── production.yaml
├── docs/
│   ├── PRODUCT_DESCRIPTION.md
│   ├── architecture_design.md
│   ├── DATA_SOURCE_GUIDE.md
│   ├── FACTORS.md
│   ├── TICKFLOW_GUIDE.md
│   ├── USER_GUIDE.md
│   └── USAGE_GUIDE.md
└── quant_assistant/
    ├── api.py                  # 高层 API
    ├── cli.py                  # quant / qa 命令行入口
    ├── core/                   # 事件、上下文、依赖注入、异常和接口
    ├── data/                   # 数据源、存储、查询、缓存、校验
    ├── factors/                # 独立因子引擎
    ├── strategy/               # 策略基类、因子、信号、组合、优化、ML
    ├── backtest/               # 回测引擎、券商、组合、绩效、可视化
    ├── ml/                     # 机器学习基础模块
    ├── risk/                   # 风控管理
    ├── visualization/          # 终端图表和指标渲染
    └── utils/                  # 日志与配置工具
```

## 快速开始

### 环境要求

- Python 3.10+
- MySQL 8.0+，仅在需要持久化数据时使用

### 安装

```bash
git clone https://github.com/XiaoBai-learner/quant-assistant.git
cd quant-assistant
python -m venv venv
source venv/bin/activate
pip install -e .
```

也可以使用依赖文件：

```bash
pip install -r requirements.txt
```

### 验证安装

```bash
quant version
python -c "import quant_assistant; print(quant_assistant.__version__)"
```

### 基础示例

```python
from quant_assistant import QuantAPI

api = QuantAPI()

# 获取行情数据
data = api.data.get_stock_data("300751", start="2024-01-01")

# 计算指标
ma20 = api.factors.ma(data, window=20)
macd = api.factors.macd(data)

# 创建策略并运行回测
strategy = api.strategy.create("ma_cross", short_window=10, long_window=30)
result = api.backtest.run(strategy, data)
analysis = api.backtest.analyze(result)

print(f"总收益率: {analysis['total_return'] * 100:.2f}%")
```

### 命令行示例

```bash
quant data get 300751 --start 2024-01-01
quant data list --market all
quant factor ma 300751 --window 20
quant factor all 300751 --output factors.csv
quant backtest run ma_cross --symbol 300751 --capital 100000
quant ml train 300751 --model random_forest
```

## 数据源

项目当前包含三类主要数据源：

- `AKShareFetcher`：免费开源数据，覆盖面广，适合日线和基础数据研究。
- `EFinanceFetcher`：适合行情、分钟和实时数据场景。
- `TickFlowFetcher`：支持免费/付费模式，付费模式可扩展分钟级和实时行情。
- `UnifiedDataFetcher`：高层 API 默认使用的统一数据获取器，按 EFinance、AKShare、TickFlow 做主备尝试，支持故障切换、空结果 fallback 和基础字段标准化。

`api.data.get_stock_data()` 会把不同数据源返回的 `date`、`change_percent` 等字段统一为 `trade_date`、`pct_change` 等常用字段，并按用户传入的日期区间做最终裁剪。如果数据源返回了区间外数据，会给出明确错误，避免静默返回误导性的空结果。

更多细节见 [docs/DATA_SOURCE_GUIDE.md](docs/DATA_SOURCE_GUIDE.md) 和 [docs/TICKFLOW_GUIDE.md](docs/TICKFLOW_GUIDE.md)。

## 文档入口

| 文档 | 用途 |
|---|---|
| [docs/PRODUCT_DESCRIPTION.md](docs/PRODUCT_DESCRIPTION.md) | 产品定位、功能边界、当前状态和下一轮开发任务。 |
| [docs/architecture_design.md](docs/architecture_design.md) | 分层架构、模块关系和路线图。 |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | 面向使用者的完整手册。 |
| [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md) | 命令和 API 使用示例。 |
| [docs/DATA_SOURCE_GUIDE.md](docs/DATA_SOURCE_GUIDE.md) | 数据源配置和统一获取器说明。 |
| [docs/FACTORS.md](docs/FACTORS.md) | 因子体系说明。 |
| [quant_assistant/data/describe.md](quant_assistant/data/describe.md) | 数据模块说明。 |
| [quant_assistant/strategy/describe.md](quant_assistant/strategy/describe.md) | 策略模块说明。 |
| [quant_assistant/backtest/describe.md](quant_assistant/backtest/describe.md) | 回测模块说明。 |
| [quant_assistant/visualization/describe.md](quant_assistant/visualization/describe.md) | 可视化模块说明。 |


## 股票池多因子选股研究

第一阶段研究入口是 `SelectionResearch`，目标是围绕股票池做多因子排名、Top N 选股、等权组合和调仓回测。用户负责输入股票池、指标权重和调仓规则；系统负责指标计算、截面标准化、选股解释和组合回测。

```python
import pandas as pd
from quant_assistant import QuantAPI
from quant_assistant.research import DataBundleBuilder, FactorAnalyzer, FactorDefinition, SelectionResearch

api = QuantAPI()

# 先构建股票池数据包。单只股票获取失败会记录到 fetch_log，
# 可用股票仍会继续进入后续研究。
bundle = DataBundleBuilder(data_api=api.data).build(
    universe=["000001", "000002", "600000", "600519"],
    start="2024-01-01",
    end="2024-12-31",
)

print(bundle.quality.summary())

def close_to_open(df: pd.DataFrame) -> pd.Series:
    return df["close"] / df["open"] - 1

factor_analyzer = FactorAnalyzer()
factor_analyzer.factor_calculator.register_factor(FactorDefinition(
    name="close_to_open",
    direction="positive",
    min_periods=1,
    dependencies=["close", "open"],
    compute=close_to_open,
))
factor_analysis = factor_analyzer.analyze(
    data=bundle.panel,
    factors=["momentum_20", "momentum_60", "volatility_20", "close_to_open"],
    forward_returns=[5, 20],
    rebalance="M",
)
print(factor_analysis.summary_table)

research = SelectionResearch(
    universe=bundle.symbols,
    start=bundle.start,
    end=bundle.end,
    factors={
        "momentum_20": 1.0,
        "momentum_60": 1.0,
        "volatility_20": -0.7,
        "turnover_amount_20": 0.4,
        "close_to_open": 0.1,
    },
    top_n=10,
    rebalance="M",
    data=bundle.panel,
)

research.register_factor(FactorDefinition(
    name="close_to_open",
    direction="positive",
    min_periods=1,
    dependencies=["close", "open"],
    compute=close_to_open,
))

result = research.run()
print(result.metrics)
print(result.latest_selection)
print(result.factor_contributions.tail())
```

内置第一批指标包括 `momentum_20`、`momentum_60`、`ma_position_20`、`ma_position_60`、`volatility_20`、`turnover_amount_20`、`drawdown_20`、`atr_ratio_14`。后续可以通过 `FactorDefinition` 注册用户自定义指标，再由 `factors={...}` 配置权重组合成选股策略。

## 下一轮开发重点

1. 收敛数据层接口：统一 `get_daily_data`、`get_daily_quotes`、`get_price_data` 的命名和返回字段。
2. 扩展测试体系：当前已有最小烟雾测试，下一步为更多数据源适配、因子计算、策略生成和回测结果建立可重复测试。
3. 整理包导出：修正 `__init__.py` 中历史类名和实际实现不一致的问题。
4. 强化回测可信度：补充交易日处理、停牌/涨跌停、成交量约束和基准对比。
5. 规划实盘前置能力：先完成模拟交易、订单状态机、账户/持仓抽象和风控钩子。

详细任务见 [docs/PRODUCT_DESCRIPTION.md](docs/PRODUCT_DESCRIPTION.md)。

## 许可证

MIT License

## 作者

XiaoBai-learner
