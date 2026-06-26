# Quant Assistant 架构设计

## 文档信息

- 版本: v1.1.0
- 更新日期: 2026-06-26
- 状态: 当前架构梳理
- 适用范围: 本地量化研究、策略开发、回测验证

## 1. 总体定位

Quant Assistant 当前是一个 Python 本地量化研究框架。系统围绕“数据 -> 因子 -> 策略 -> 回测 -> 分析”的研究闭环组织，先服务个人研究和开发验证，再逐步向模拟交易、实盘前置抽象和 Web 平台演进。

当前版本不提供真实券商交易能力，也不应被描述为已具备生产级实盘系统。

## 2. 分层架构

```text
┌─────────────────────────────────────────────────────────────┐
│ CLI / Python API                                             │
│ quant / qa / QuantAPI                                        │
├─────────────────────────────────────────────────────────────┤
│ Research Layer                                               │
│ Strategy / Factors / ML / Visualization                      │
├─────────────────────────────────────────────────────────────┤
│ Backtest Layer                                               │
│ Event-driven Engine / Vectorized Engine / Broker / Portfolio │
├─────────────────────────────────────────────────────────────┤
│ Risk Layer                                                   │
│ Position / Drawdown / Concentration / Trade Rules            │
├─────────────────────────────────────────────────────────────┤
│ Core Layer                                                   │
│ Event Bus / Context / Container / Interfaces / Exceptions    │
├─────────────────────────────────────────────────────────────┤
│ Data Layer                                                   │
│ Fetcher / Validator / Storage / Query / Cache                │
├─────────────────────────────────────────────────────────────┤
│ External Systems                                             │
│ AKShare / EFinance / TickFlow / MySQL                        │
└─────────────────────────────────────────────────────────────┘
```

## 3. 模块职责

### 3.1 CLI 与高层 API

- `quant_assistant/api.py` 提供 `QuantAPI`，作为数据、因子、策略、回测和机器学习的高层入口。
- `quant_assistant/cli.py` 提供 `quant` / `qa` 命令，覆盖数据获取、数据查询、股票列表、因子计算、回测和模型训练。
- 当前风险：高层 API 与底层 fetcher 的方法命名存在历史差异，需要下一轮优先收敛。

### 3.2 Core 核心层

- `events.py`：事件总线和事件类型。
- `context.py`：全局上下文。
- `container.py`：依赖注入容器。
- `interfaces.py`：核心接口抽象。
- `exceptions.py`：统一异常层级。

核心层为其他模块提供解耦通信、上下文和基础抽象。

### 3.3 Data 数据层

- `fetcher/`：AKShare、EFinance、TickFlow、UnifiedDataFetcher。
- `storage/`：MySQL 存储和基础存储接口。
- `query/`：统一查询引擎。
- `database/`：SQLAlchemy 连接、模型和 schema。
- `cache.py`：缓存基础设施。
- `validator.py`：数据质量校验。

数据层已经具备多数据源和持久化基础能力。下一步重点是统一 schema、方法名、异常和 fallback 语义。

### 3.4 Factors 因子层

项目当前有两处因子相关实现：

- `quant_assistant/factors/`：顶层通用因子引擎，包含 `FactorEngine` 和 `FactorEngineV2`。
- `quant_assistant/strategy/factors/`：策略层内部因子体系，包含因子注册、技术因子和组合因子。

下一轮需要明确二者关系，避免同名概念在不同路径下产生维护成本。

### 3.5 Strategy 策略层

策略层包含：

- `base.py`：策略基类、信号、K 线和策略上下文。
- `signal_synthesis/`：规则信号生成、股票筛选、策略构建、内置策略和遗传算法优化。
- `composite.py`：组合策略。
- `optimizer.py`：参数优化。
- `examples/`：MA、MACD 示例策略。
- `ml/`：策略层机器学习辅助模块。

策略层当前已具备研究能力，后续应补齐模板、示例和策略运行结果标准化。

### 3.6 Backtest 回测层

回测层包含：

- `engine.py`：事件驱动回测引擎。
- `vectorized_engine.py`：向量化回测引擎。
- `broker.py` 与 `realistic_broker.py`：订单、成交和模拟撮合。
- `portfolio.py`：投资组合和资金持仓。
- `performance.py`：绩效指标。
- `visualization.py`：回测结果可视化辅助。

回测主流程已经具备，但需要增强交易日历、停牌、涨跌停、成交量约束、基准对比和结果可重复性。

### 3.7 Risk 风控层

`quant_assistant/risk/manager.py` 提供基础风控管理能力，适合在回测或未来模拟交易中校验仓位、回撤、集中度和交易规则。

当前风控仍是基础模块，尚未与真实订单生命周期和实时账户同步打通。

### 3.8 Visualization 可视化层

可视化层面向终端输出，包含数据适配、指标计算、ASCII 渲染、布局管理和 CLI 工具。当前适合本地复盘和快速查看，不是 Web 看板。

## 4. 关键数据流

### 4.1 研究数据流

```text
外部数据源
  -> Fetcher
  -> Validator
  -> Storage / Cache
  -> Query Engine
  -> Factors / Strategy / ML
  -> Backtest
  -> Performance / Visualization
```

### 4.2 回测执行流

```text
历史行情
  -> BacktestEngine
  -> BaseStrategy.on_bar
  -> Signal
  -> Broker / RealisticBroker
  -> Portfolio
  -> PerformanceAnalyzer
  -> Report
```

### 4.3 CLI 调用流

```text
quant 命令
  -> argparse 子命令
  -> QuantAPI
  -> Data / Factor / Strategy / Backtest / ML 子 API
  -> 终端输出或文件输出
```

## 5. 当前状态

| 模块 | 状态 | 下一步 |
|---|---:|---|
| Core | 已实现 | 对外接口和异常层级补测试。 |
| Data | 已实现 | 统一数据 schema、方法名和异常。 |
| Factors | 已实现 | 合并或明确双因子体系边界。 |
| Strategy | 已实现 | 增加模板、示例和策略结果标准格式。 |
| Backtest | 已实现 | 强化真实市场约束和基准分析。 |
| Risk | 基础版 | 与回测和未来模拟交易流程打通。 |
| ML | 基础版 | 加强特征泄漏检查和模型评估规范。 |
| Visualization | 终端版 | 修正文档示例，增加常用图表回归测试。 |
| Trading | 未实现 | 先设计模拟交易、订单状态机和账户抽象。 |
| Web UI | 未实现 | 待核心研究闭环稳定后规划。 |

## 6. 路线图

### Phase 1：研究闭环稳定化

目标：让本地研究流程稳定、可测、可复现。

- 修复包导出和文档路径。
- 建立最小自动化测试套件。
- 统一数据源 schema。
- 保证 README 示例和 CLI 常用命令可运行。

### Phase 2：回测可信度增强

目标：提升回测结果和真实市场约束的一致性。

- 交易日历。
- 停牌和涨跌停处理。
- 成交量约束。
- 手续费、印花税、滑点、冲击成本模型。
- 基准收益和超额收益。

### Phase 3：模拟交易与风控闭环

目标：在实盘前先完成可控的交易生命周期抽象。

- 订单状态机。
- 账户和持仓同步抽象。
- 模拟交易 broker。
- 事前、事中、事后风控钩子。
- 交易日志和回放能力。

### Phase 4：实盘和平台化

目标：在核心模块稳定后，再扩展真实券商接口和 Web 工作台。

- 券商网关适配。
- 实时行情和订单回报。
- Web 策略工作台。
- 监控和告警。
- 多策略管理。

## 7. 架构原则

- 研究优先：先保证数据、因子、策略、回测的本地闭环稳定。
- 接口统一：上层策略不应感知具体数据源字段差异。
- 可验证：核心流程必须有自动化测试和可重复样例。
- 实盘克制：没有模拟交易和风控闭环前，不直接推进真实下单。
- 文档诚实：明确区分已实现、基础版、规划中和不支持能力。
