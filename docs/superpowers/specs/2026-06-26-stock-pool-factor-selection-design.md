# 股票池多因子选股研究系统设计

## 1. 背景与目标

Quant Assistant 下一阶段的核心目标是从“可用的量化模块集合”升级为“系统化股票池选股研究工具”。本系统不以单一股票择时为主线，而是围绕多股票样本、指标计算、截面排名、组合构建和组合回测建立完整闭环。

目标是帮助用户回答一个核心问题：一套选股逻辑是否能在股票池中稳定选出更优组合，并通过收益、风险、换手、回撤、超额收益和因子贡献等指标提供证据。

## 2. 产品原则

1. 多股票优先：所有流程默认服务股票池，不以单票策略为中心。
2. 指标可信优先：指标计算必须可解释、可复现、可检查，不允许黑箱式“算出一个分数”。
3. 化繁为简：第一阶段只做最关键闭环，不做实时交易、分钟策略和复杂机器学习。
4. 每次选股留痕：任何股票入选都必须能追溯到原始因子值、标准化分数、权重和综合排名。
5. 样本外意识：避免通过单票或单阶段调参造成过拟合，后续必须支持分阶段评估和稳定性分析。

## 3. 第一阶段范围

### 3.1 包含

- 股票池定义：手工股票列表，预留指数成分和全 A 入口。
- 多股票日线数据面板：OHLCV 数据获取、字段标准化、日期对齐、缺失检查。
- 指标/因子计算：按股票逐只计算时间序列因子，再在调仓日生成截面因子表。
- 因子预处理：缺失处理、去极值、标准化、方向调整。
- 因子评分：按配置权重合成综合分。
- 选股：每个调仓日选 Top N，并保留完整解释明细。
- 组合构建：等权组合，支持单票最大权重和最小可交易过滤。
- 组合回测：周频/月频调仓，计算组合净值、收益、回撤、换手和超额收益。
- 结果导出：选股明细、持仓明细、调仓记录、绩效指标、因子贡献。

### 3.2 不包含

- 实盘交易和自动下单。
- 分钟级或实时选股。
- 机器学习预测模型。
- 复杂行业中性和风险模型优化。
- 分布式任务调度。

## 4. 用户工作流

```text
定义股票池
  -> 获取多股票日线数据
  -> 检查数据质量
  -> 计算时间序列因子
  -> 在调仓日生成截面因子矩阵
  -> 因子预处理与综合评分
  -> 选出 Top N 股票
  -> 构建等权组合
  -> 执行组合回测
  -> 输出指标、明细和解释报告
```

目标 API：

```python
from quant_assistant.research import SelectionResearch

research = SelectionResearch(
    universe=["000001", "000002", "600000", "600519"],
    start="2024-01-01",
    end="2024-12-31",
    factors={
        "momentum_20": 1.0,
        "momentum_60": 1.0,
        "volatility_20": -0.7,
        "turnover_20": 0.5,
        "drawdown_20": -0.5,
    },
    top_n=10,
    rebalance="M",
)

result = research.run()

print(result.metrics)
print(result.latest_selection)
print(result.holdings)
```

## 5. 模块设计

新增 `quant_assistant/research/` 作为股票池研究产品线。

```text
quant_assistant/research/
├── __init__.py
├── config.py          # 研究配置对象
├── universe.py        # 股票池定义与过滤
├── panel.py           # 多股票行情面板
├── factors.py         # 指标与因子计算
├── preprocessing.py   # 缺失、去极值、标准化、方向处理
├── scoring.py         # 因子权重与综合评分
├── selector.py        # Top N 选股
├── portfolio.py       # 组合构建与权重约束
├── backtest.py        # 调仓型组合回测
├── evaluation.py      # 绩效与稳定性评估
└── result.py          # 结果对象与导出
```

### 5.1 `SelectionResearchConfig`

职责：集中定义一次研究任务的输入参数。

关键字段：

- `universe`: 股票列表或股票池名称。
- `start`, `end`: 研究区间。
- `factors`: `{factor_name: weight}`。
- `top_n`: 每期入选股票数量。
- `rebalance`: 调仓频率，第一阶段支持 `W` 和 `M`。
- `min_history`: 指标计算所需最短历史，默认 120 个交易日。
- `max_weight`: 单票最大权重，默认等权且不超过 20%。
- `benchmark`: 基准代码，第一阶段可选。
- `cost`: 交易成本配置。

### 5.2 `UniverseBuilder`

职责：生成研究股票池，并执行基础过滤。

第一阶段支持：

- 手工列表。
- 去除空代码、重复代码、格式不规范代码。
- 可选过滤：上市不足 N 天、低成交额、数据缺失过高。

输出：

```python
Universe(symbols=[...], metadata={...})
```

### 5.3 `MarketDataPanel`

职责：管理多股票行情数据。

输入：股票池、日期区间、数据源。

输出长表：

| symbol | trade_date | open | high | low | close | volume | amount |
|---|---|---:|---:|---:|---:|---:|---:|

关键要求：

- 统一字段名。
- `trade_date` 必须为日期类型。
- 每只股票按日期升序。
- 保留数据质量报告：缺失天数、起止日期、重复行、异常 OHLC。
- 如果个股数据不足，不直接中断整次研究，而是记录为不可用并继续处理其他股票。

### 5.4 `FactorCalculator`

指标计算是系统核心，必须单独设计，不依赖临时 DataFrame 拼接。

第一阶段内置因子：

| 因子 | 方向 | 公式 | 用途 |
|---|---:|---|---|
| `momentum_20` | + | `close / close.shift(20) - 1` | 中短期动量 |
| `momentum_60` | + | `close / close.shift(60) - 1` | 中期趋势 |
| `ma_position_20` | + | `close / MA(close, 20) - 1` | 价格相对趋势 |
| `ma_position_60` | + | `close / MA(close, 60) - 1` | 中期趋势位置 |
| `volatility_20` | - | `std(daily_return, 20)` | 风险控制 |
| `turnover_amount_20` | + | `mean(amount, 20)` | 流动性过滤与加分 |
| `drawdown_20` | - | `close / rolling_max(close, 20) - 1` | 短期回撤风险 |
| `atr_ratio_14` | - | `ATR(14) / close` | 波动风险 |

计算流程：

1. 按 `symbol` 分组。
2. 按 `trade_date` 排序。
3. 计算日收益 `return_1d`。
4. 计算滚动指标。
5. 只在调仓日抽取截面因子。
6. 记录每个因子的有效样本数、缺失率、极值范围。

输出长表：

| trade_date | symbol | factor | raw_value |
|---|---|---|---:|

以及宽表：

| trade_date | symbol | momentum_20 | volatility_20 | score |
|---|---|---:|---:|---:|

关键规则：

- 指标计算不得使用未来数据。
- 调仓日使用当日收盘后可得数据，组合收益从下一交易日开始计算。
- 每个因子必须声明 `min_periods`、方向、依赖字段和是否适合排序。
- 缺失率过高的调仓截面应给出 warning。

### 5.5 `FactorPreprocessor`

职责：将原始因子转成可比较的截面分数。

第一阶段处理顺序：

1. 缺失处理：缺失值不参与排名；如果某因子当期有效样本低于 50%，该因子当期禁用。
2. 去极值：按 1% / 99% 分位数 winsorize。
3. 标准化：默认使用截面 z-score。
4. 方向调整：正向因子保留，负向因子乘以 `-1`。
5. 分数裁剪：标准化分数裁剪到 `[-3, 3]`，避免单因子极端主导。

输出：

| trade_date | symbol | factor | raw_value | processed_value | valid |
|---|---|---|---:|---:|---|

### 5.6 `FactorScorer`

职责：根据因子权重合成综合分。

公式：

```text
score(symbol, date) = sum(processed_factor_i * weight_i) / sum(abs(weight_i))
```

规则：

- 因子权重必须显式配置。
- 当期禁用因子不参与分母。
- 如果某股票有效因子数低于配置因子数的 60%，该股票不可入选。
- 输出单因子贡献：`contribution_i = processed_factor_i * weight_i`。

### 5.7 `StockPoolSelector`

职责：根据综合分选股。

规则：

- 每个调仓日按 `score` 降序排序。
- 选取 Top N。
- 支持最低分数阈值。
- 支持流动性硬过滤：如 `turnover_amount_20` 低于阈值不可入选。
- 输出排名、分数、原始因子、处理后因子、贡献。

输出：

| rebalance_date | symbol | rank | score | selected | reason |
|---|---|---:|---:|---|---|

### 5.8 `PortfolioConstructor`

职责：将选股结果转换成持仓权重。

第一阶段只支持等权：

```text
weight = min(1 / selected_count, max_weight)
```

如果因为 `max_weight` 导致权重和小于 1，剩余部分保留现金。

输出：

| rebalance_date | symbol | target_weight |
|---|---|---:|

### 5.9 `SelectionBacktester`

职责：执行调仓型组合回测。

回测规则：

- 调仓日生成目标组合。
- 持仓收益从下一交易日开始计入，避免使用未来收益。
- 持有到下一个调仓日前一交易日。
- 组合每日收益为持仓股票收益按权重加权。
- 调仓时计算换手率和交易成本。
- 个股缺失下一日收益时，该股票当日收益按 0 或剔除并重归一，第一阶段默认按 0 并记录 warning。

输出：

- daily portfolio value
- daily return
- holdings by date
- rebalance trades
- turnover by rebalance date

### 5.10 `SelectionEvaluator`

职责：输出可用于判断选股系统是否有效的指标。

第一阶段核心指标：

- 总收益率。
- 年化收益率。
- 年化波动率。
- Sharpe。
- 最大回撤。
- Calmar。
- 月度胜率。
- 调仓期胜率。
- 平均换手率。
- 最大单期亏损。
- 相对基准收益与超额收益。
- 信息比率，基准存在时计算。

选股解释指标：

- 每期入选股票平均分。
- 入选股票因子贡献均值。
- 每个因子与下一期收益的 Spearman IC。
- IC 均值、IC 标准差、ICIR。
- Top 分组与 Bottom 分组收益差，第一阶段可选。

## 6. 数据结构

### 6.1 `SelectionResearchResult`

字段：

- `metrics`: 绩效指标字典。
- `daily_returns`: 每日组合收益。
- `equity_curve`: 净值曲线。
- `selections`: 每期选股结果。
- `holdings`: 每日持仓。
- `rebalance_trades`: 调仓交易明细。
- `factor_values`: 原始因子值。
- `factor_scores`: 处理后因子分数。
- `factor_contributions`: 因子贡献。
- `data_quality`: 数据质量报告。
- `warnings`: 研究过程中的非致命问题。

方法：

- `to_dict()`。
- `export_csv(output_dir)`。
- `summary()`。

## 7. 错误处理与卡点记录

系统遇到卡点时不应整段停止，除非无法继续产生可信结果。

非致命卡点：

- 单只股票数据获取失败：记录到 `data_quality`，继续其他股票。
- 单只股票历史不足：标记不可用，继续。
- 某期某因子缺失率过高：禁用该因子当期评分，记录 warning。
- 某期入选股票不足 Top N：按实际数量建仓，剩余现金保留。

致命错误：

- 股票池为空。
- 所有股票都无可用数据。
- 所有因子在所有调仓日都无有效值。
- 回测期间没有任何可交易调仓日。

所有 warning 必须进入 `SelectionResearchResult.warnings`。

## 8. 测试策略

第一阶段必须覆盖：

1. 因子计算不使用未来数据。
2. 因子方向调整正确。
3. 去极值与 z-score 输出稳定。
4. 缺失率过高时禁用因子。
5. Top N 选股排序正确。
6. 等权组合权重合计不超过 1。
7. 调仓收益从下一交易日开始计算。
8. 换手率计算正确。
9. 单只股票数据失败不影响其他股票。
10. 完整 `SelectionResearch.run()` 可用小样本跑通。

## 9. 第一阶段验收标准

代码层：

- 新增 `quant_assistant.research` 产品线。
- 提供 `SelectionResearch` 一个主入口。
- 使用 4 到 10 只股票的小样本可在本地稳定跑通。
- 所有核心步骤有单元测试。
- 不依赖外部网络的测试必须通过。

产品层：

- 用户可以看到每期入选股票及其因子贡献。
- 用户可以看到组合净值和核心绩效指标。
- 用户可以看到数据质量问题和非致命卡点。
- 用户可以导出选股明细、持仓明细和绩效指标。

研究层：

- 能计算至少 5 个有效因子。
- 能报告每个因子的 IC 或下一期收益相关性。
- 能避免单票过拟合，将评价对象转为组合与股票池。

## 10. 后续扩展

第二阶段：

- 指数成分股票池。
- 行业/市值中性处理。
- 分组回测。
- 因子 IC 时间序列和分层收益。
- 样本内/样本外分段评估。

第三阶段：

- 因子组合优化。
- 机器学习排序模型。
- 多策略组合。
- Web 研究报告。

## 11. 实施顺序建议

1. 定义 `SelectionResearchConfig` 和 `SelectionResearchResult`。
2. 实现多股票数据面板和数据质量报告。
3. 实现第一批内置因子和因子元数据。
4. 实现预处理、打分和 Top N 选股。
5. 实现等权组合和调仓型回测。
6. 实现绩效与因子评价。
7. 增加 CSV 导出和 README 示例。

第一轮实现不追求因子数量，而追求流程可信、指标准确、解释清楚。
