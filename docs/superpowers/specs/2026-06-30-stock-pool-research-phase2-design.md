# 股票池多因子研究框架阶段二设计

## 1. 背景

第一阶段已经建立了 `quant_assistant.research.SelectionResearch` 主流程，能够完成多股票日线数据输入、内置或自定义因子计算、截面标准化、权重评分、Top N 选股、等权组合调仓回测和结果输出。

下一阶段的目标不是横向增加更多策略，而是把研究链路中最影响可信度和使用体验的部分做深：股票池数据集、数据健康检查、因子有效性评价和研究报告。项目定位继续保持为 A 股股票池多因子选股研究框架，不转向单股择时、实盘交易、分钟级交易或 Web 平台。

## 2. 核心问题

阶段二要帮助用户回答四个问题：

1. 当前股票池的数据是否足够完整、稳定、可用于研究？
2. 某个因子是否真的在股票池截面上有选股能力？
3. 用户组合出来的多因子策略，收益来自哪些因子，风险暴露在哪里？
4. 一次研究实验能否被清楚复现、比较和沉淀？

## 3. 目标用户与使用方式

目标用户是会使用 Python 做数据分析的个人投资者、量化学习者和策略研究者。他们不一定想维护完整交易系统，但需要一个本地 Python 库来快速验证股票池选股想法。

典型使用方式：

```python
from quant_assistant.research import (
    DataBundleBuilder,
    FactorAnalyzer,
    ResearchReport,
    SelectionResearch,
)

bundle = DataBundleBuilder(api=api).build(
    universe=["000001", "000002", "600000", "600519"],
    start="2020-01-01",
    end="2025-12-31",
)

factor_report = FactorAnalyzer().analyze(
    data=bundle.panel,
    factors=["momentum_60", "volatility_20", "turnover_amount_20"],
    forward_returns=[5, 20, 60],
)

research = SelectionResearch(
    universe=bundle.universe.symbols,
    start=bundle.start,
    end=bundle.end,
    data=bundle.panel,
    factors={
        "momentum_60": 1.0,
        "volatility_20": -0.7,
        "turnover_amount_20": 0.3,
    },
    top_n=30,
    rebalance="M",
)

result = research.run()
ResearchReport().write_markdown(result, factor_report, "reports/momentum_quality.md")
```

## 4. 成功标准

阶段二完成后，项目应达到以下标准：

1. 用户可以用一行 API 构建多股票日线面板，并获得明确的数据健康报告。
2. 单个股票数据失败不会直接中断整个股票池研究，系统会记录失败原因并继续处理可用股票。
3. 因子不仅能计算，还能输出覆盖率、分布、Rank IC、ICIR、分组收益、换手和因子相关性。
4. 一次选股研究可以导出 Markdown 报告，报告包含配置、数据质量、因子评价、回测指标、最新选股和风险提示。
5. 阶段二新增能力必须服务股票池选股，不新增实盘、Web、分钟策略和复杂机器学习能力。

## 5. 范围

### 5.1 包含

- 股票池对象：标准化股票代码、去重、保留来源和过滤记录。
- 多股票数据构建器：批量拉取日线行情、字段标准化、本地缓存入口、部分失败容错。
- 数据健康报告：覆盖率、起止日期、缺失 OHLCV、重复行、异常价格、疑似停牌、不可用股票列表。
- 因子有效性评价：Rank IC、ICIR、分组收益、Top-Bottom 收益、因子相关性、因子覆盖率。
- 策略研究报告：Markdown 输出，聚合配置、数据质量、因子评价、组合回测和最新选股。
- 实验元数据：记录 universe、时间区间、因子权重、调仓频率、成本参数和生成时间。

### 5.2 不包含

- 实盘交易、自动下单、券商接口。
- 分钟级和实时行情研究。
- 行业中性、风格暴露和组合优化器。
- 机器学习模型训练。
- Web UI 和多用户协作。
- 对外投资建议或自动推荐股票。

## 6. 模块设计

阶段二继续放在 `quant_assistant/research/` 下，保持这一产品线边界清晰。

```text
quant_assistant/research/
├── universe.py         # 股票池定义、标准化、过滤记录
├── panel.py            # 多股票数据面板构建与缓存入口
├── data_quality.py     # 数据健康报告
├── factor_analysis.py  # 因子 IC、分组收益、相关性评价
├── report.py           # Markdown 研究报告
└── experiment.py       # 实验元数据与可复现配置
```

现有模块继续保留：

```text
config.py
factors.py
preprocessing.py
scoring.py
selector.py
portfolio.py
backtest.py
evaluation.py
result.py
workflow.py
```

## 7. 数据集设计

### 7.1 `Universe`

职责：表示一次研究使用的股票池，并记录它是如何得到的。

核心字段：

- `symbols`: 标准化后的股票代码列表。
- `name`: 可选股票池名称，例如 `custom`、`hs300`。
- `source`: 来源描述，例如 `manual`、`csv`、`index_constituents`。
- `filters`: 已执行过滤记录。
- `metadata`: 额外信息。

第一阶段只要求支持手工列表，阶段二在对象层预留指数成分和文件导入空间。

### 7.2 `DataBundle`

职责：封装股票池、行情面板、数据质量和获取日志。

核心字段：

- `universe`: `Universe` 对象。
- `panel`: 标准日线长表。
- `start`, `end`: 实际研究区间。
- `quality`: `DataQualityReport`。
- `fetch_log`: 每只股票的数据获取状态。

标准 `panel` 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `symbol` | str | 股票代码 |
| `trade_date` | datetime64 | 交易日期 |
| `open` | float | 开盘价 |
| `high` | float | 最高价 |
| `low` | float | 最低价 |
| `close` | float | 收盘价 |
| `volume` | float | 成交量 |
| `amount` | float | 成交额 |

### 7.3 `DataBundleBuilder`

职责：从 `QuantAPI.data` 或自定义 loader 构建股票池面板。

接口草案：

```python
bundle = DataBundleBuilder(api=api).build(
    universe=["000001", "600000"],
    start="2020-01-01",
    end="2025-12-31",
    adjust="qfq",
    cache=True,
    min_coverage=0.8,
)
```

规则：

- 每只股票独立获取，单只失败记录到 `fetch_log`。
- 只有当可用股票数为 0 时才抛出中断异常。
- 字段统一由数据层完成，研究层再次校验必要字段。
- 输出按 `symbol, trade_date` 排序并去重。
- 默认不填充价格缺失，避免制造虚假行情。

## 8. 数据健康设计

`DataQualityReport` 应该从股票维度和整体维度同时评价数据。

股票维度字段：

- `rows`: 有效行数。
- `start`: 第一条数据日期。
- `end`: 最后一条数据日期。
- `coverage`: 实际交易日覆盖率。
- `missing_ohlcv`: OHLCV 缺失数量。
- `duplicate_rows`: 重复日期行数。
- `invalid_price_rows`: `high < low`、`close <= 0` 等异常行数。
- `zero_volume_rows`: 零成交量行数。
- `status`: `ok`、`warning`、`failed`。
- `reason`: 异常原因。

整体维度字段：

- 股票池数量。
- 可用股票数量。
- 失败股票数量。
- 平均覆盖率。
- 严重缺失股票列表。
- 数据质量 warnings。

使用体验要求：

- 报告要能直接 `summary()` 成字典。
- 报告要能导出 CSV。
- `SelectionResearchResult.data_quality` 后续可以兼容并升级为该对象的摘要。

## 9. 因子有效性评价设计

阶段二新增 `FactorAnalyzer`，它不负责选股，只负责判断因子是否值得进入策略。

输入：

- 标准行情面板。
- 因子定义或因子名称。
- 远期收益窗口，例如 5、20、60 个交易日。
- 可选调仓频率，例如 `M`。

输出：

- 因子覆盖率。
- 因子分布统计。
- Rank IC 时间序列。
- IC 均值、标准差、ICIR、胜率。
- 分组收益。
- Top-Bottom 收益。
- 因子相关性矩阵。

接口草案：

```python
analysis = FactorAnalyzer().analyze(
    data=panel,
    factors=["momentum_60", "volatility_20"],
    forward_returns=[5, 20],
    quantiles=5,
    rebalance="M",
)

print(analysis.summary())
print(analysis.ic_table)
print(analysis.group_returns)
```

关键规则：

- 因子值必须来自调仓日当日或之前的数据。
- 远期收益从调仓日之后开始计算，避免未来函数。
- 每个截面有效样本低于阈值时，该期 IC 不参与汇总。
- 负向因子仍按原始因子值计算 IC，报告中明确方向，不在分析阶段偷偷翻转。
- 因子相关性用于发现重复因子，默认基于调仓日截面合并后的样本计算。

## 10. 报告设计

阶段二先做 Markdown 报告，不做复杂 HTML 和图表。

`ResearchReport.write_markdown()` 输出章节：

1. 研究配置。
2. 数据质量摘要。
3. 因子有效性摘要。
4. 因子相关性摘要。
5. 回测绩效摘要。
6. 最新一期选股。
7. 因子贡献摘要。
8. 风险提示和 warnings。

报告原则：

- 数值表格优先，不堆长文字。
- 明确区分“已计算结果”和“风险提示”。
- 不生成确定性投资建议。
- 任何缺失数据、禁用因子、失败股票都必须进入报告。

## 11. 实验元数据设计

`ExperimentConfig` 和 `ExperimentRecord` 用于沉淀可复现实验。

应记录：

- 研究名称。
- 运行时间。
- 股票池来源和股票数量。
- 起止日期。
- 因子权重。
- 调仓频率。
- Top N。
- 成本参数。
- 数据质量摘要。
- 代码版本，优先使用 git commit hash。

第一阶段不需要数据库管理实验，先以 JSON 文件导出即可。

## 12. 与现有代码的关系

现有 `SelectionResearch` 保持主入口，但阶段二完成后可以接受 `DataBundle`：

```python
research = SelectionResearch.from_bundle(
    bundle,
    factors={"momentum_60": 1.0, "volatility_20": -0.7},
    top_n=30,
    rebalance="M",
)
```

短期内也可以不新增构造器，只把 `bundle.panel` 和 `bundle.universe.symbols` 传入现有构造函数。新增模块应避免破坏第一阶段 API。

`FactorCalculator.quality_report()` 当前只提供基础统计，阶段二的 `FactorAnalyzer` 会成为因子研究主入口。

`SelectionResearchResult.export_csv()` 继续保留，`ResearchReport` 只消费结果对象和因子分析对象，不直接重跑研究。

## 13. 测试策略

新增测试应覆盖：

1. `Universe` 标准化、去重和非法输入处理。
2. `DataBundleBuilder` 在部分股票失败时仍返回可用面板。
3. `DataQualityReport` 能识别缺失、重复、异常价格和零成交量。
4. `FactorAnalyzer` 能正确计算远期收益、Rank IC 和分组收益。
5. 因子评价不使用未来数据。
6. `ResearchReport` 能生成包含关键章节的 Markdown 文件。
7. 现有 `SelectionResearch` 测试继续通过。

测试数据使用小型合成面板，不依赖真实网络数据源。

## 14. 实施顺序

推荐按以下顺序实现：

1. `Universe`、`DataBundle`、`DataQualityReport` 数据对象。
2. `DataBundleBuilder` 批量获取和部分失败容错。
3. `FactorAnalyzer` 的远期收益、Rank IC、ICIR。
4. `FactorAnalyzer` 的分组收益和因子相关性。
5. `ResearchReport` Markdown 输出。
6. `SelectionResearch.from_bundle()` 便利入口。
7. 文档和 README 示例更新。

这个顺序优先保障数据获取环节和因子评价环节，再补报告与易用性。

## 15. 验收清单

- `python -m pytest tests -q` 全部通过。
- 新增模块不需要联网即可完成单元测试。
- 用三只股票的合成数据可以完整跑出数据健康报告、因子分析和研究报告。
- 部分股票数据获取失败时，用户能看到失败股票和失败原因。
- 报告中能看到至少一个因子的 IC/ICIR、分组收益和覆盖率。
- 阶段二功能没有引入实盘、Web、分钟策略或机器学习训练依赖。

