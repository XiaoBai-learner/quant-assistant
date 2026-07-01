# A Stock Data Integration Plan

## 背景

`simonlin1212/a-stock-data` 是一个以 `SKILL.md` 形式发布的 A 股全栈数据工具包，覆盖行情、研报、信号、资金、新闻、基础数据、公告、打板、ETF 期权和舆情互动等数据源。它的价值不在于提供一个可直接安装的 Python 包，而在于沉淀了大量直连数据源的端点、参数、限流经验和接口修复记录。

本项目的目标不是复制一个 Skill 文件，而是把这些数据源工程化吸纳为 `quant_assistant` 的数据资产层，让股票池选股研究可以稳定使用更多因子、风险事件和解释性数据。

## 集成目标

- 接入 `a-stock-data` 覆盖的核心数据源，并保留来源和许可证说明。
- 将外部接口封装为可测试、可缓存、可降级的 provider。
- 将数据统一标准化为 `DataFrame + metadata`，避免研究层直接依赖外部字段名。
- 优先服务股票池选股研究：多股票数据、因子排名、筛选、组合回测。
- 建立每日可运行的缓存任务，把行情、涨停、龙虎榜、资金流、题材、公告等数据落到本地 Parquet。

## 不做什么

- 不把 `SKILL.md` 原样塞进项目。
- 不让研究层直接调用裸 HTTP URL。
- 不在东财接口上做并发批量请求。
- 不把所有 40 个端点一次性做成生产级能力。
- 不把新闻、舆情、互动易直接作为交易信号，先进入解释层和人工复核层。

## 目标架构

```text
quant_assistant/data/
├── providers/
│   ├── __init__.py
│   ├── base.py
│   ├── errors.py
│   ├── http_client.py
│   ├── rate_limiter.py
│   ├── registry.py
│   ├── symbol.py
│   ├── tdx_provider.py
│   ├── tencent_provider.py
│   ├── eastmoney_provider.py
│   ├── ths_provider.py
│   ├── sina_provider.py
│   ├── cninfo_provider.py
│   ├── baidu_provider.py
│   └── iwencai_provider.py
├── datasets/
│   ├── __init__.py
│   ├── market.py
│   ├── reports.py
│   ├── signals.py
│   ├── capital_flow.py
│   ├── fundamentals.py
│   ├── news.py
│   ├── announcements.py
│   ├── limit_board.py
│   ├── options.py
│   └── sentiment.py
└── hub.py
```

### Provider 层

Provider 只负责一件事：稳定地从外部数据源取回原始数据，并附带可追踪 metadata。

统一返回：

```python
ProviderResult(
    data=frame_or_dict,
    source="eastmoney",
    endpoint="limit_up_pool",
    fetched_at="2026-07-01T08:00:00+08:00",
    params={"date": "2026-07-01"},
    raw_hash="sha256:4b7c1f0a",
)
```

### Dataset 层

Dataset 负责把 provider 返回内容转成项目标准表。

例如涨停池标准字段：

```text
trade_date
symbol
name
limit_up_type
consecutive_boards
sealed_amount
first_limit_time
last_limit_time
open_count
industry
source
fetch_time
```

### Hub 层

Hub 是用户和研究模块的入口：

```python
hub.market.daily("000001.SZ")
hub.market.realtime(["000001.SZ", "600519.SH"])
hub.signals.limit_up_pool("2026-07-01")
hub.capital_flow.stock_fund_flow_120d("000858.SZ")
hub.announcements.cninfo("601318.SH")
```

## 数据源优先级

### 行情类

1. `mootdx`：K 线、盘口、逐笔、财务快照、F10，低封禁风险。
2. 腾讯财经：实时价、PE/PB、市值、换手率、涨跌停价、指数、ETF。
3. 百度股市通：带 MA 的 K 线，作为补充。
4. 东财：仅用于其独有数据。

### 东财类

东财接口只用于独有数据：

- 龙虎榜
- 全市场龙虎榜
- 限售解禁
- 融资融券
- 大宗交易
- 股东户数
- 分红送转
- 资金流
- 行业排名
- 研报/PDF
- 新闻/全球资讯
- 涨停/炸板/跌停池
- 概念归属/人气榜

必须串行限流，默认最小间隔 `1.2s + jitter`。

## 本地缓存设计

统一使用 Parquet：

```text
~/.quant_assistant/cache/
├── market/daily/{symbol}.parquet
├── market/realtime/date=YYYY-MM-DD.parquet
├── signals/limit_up/date=YYYY-MM-DD.parquet
├── signals/dragon_tiger/date=YYYY-MM-DD.parquet
├── signals/concept_blocks/date=YYYY-MM-DD.parquet
├── capital_flow/stock_120d/{symbol}.parquet
├── fundamentals/shareholder_count/{symbol}.parquet
├── fundamentals/margin_trading/{symbol}.parquet
├── announcements/cninfo/date=YYYY-MM-DD.parquet
├── news/stock/{symbol}.parquet
└── sentiment/hot_rank/date=YYYY-MM-DD.parquet
```

所有缓存表必须有：

```text
source
endpoint
fetch_time
raw_hash
```

股票级表还必须有：

```text
symbol
trade_date 或 publish_time
```

## 分阶段实施

### Phase 0：盘点和合规

产出：

- `docs/data_sources/a_stock_data_endpoint_inventory.md`
- `docs/third_party/A_STOCK_DATA_NOTICE.md`

完成标准：

- 40 个端点按层级、来源、优先级、缓存策略整理完成。
- 明确 Apache 2.0 来源说明。

### Phase 1：公共基础设施

新增：

- `quant_assistant/data/providers/base.py`
- `quant_assistant/data/providers/http_client.py`
- `quant_assistant/data/providers/rate_limiter.py`
- `quant_assistant/data/providers/symbol.py`
- `quant_assistant/data/providers/registry.py`

完成标准：

- 所有 provider 有统一返回结构。
- HTTP 请求有超时、重试、headers、metadata。
- 东财请求强制走限流客户端。
- 单元测试覆盖限流、metadata、错误封装。

### Phase 2：行情源增强

优先接入：

- 腾讯实时行情
- 腾讯估值/市值/涨跌停价
- mootdx 日 K
- mootdx 盘口
- 百度 K 线

完成标准：

- 能替换或补强当前 `UnifiedDataFetcher.get_daily_quotes`。
- 能给交易回测提供涨跌停价、开盘价、是否可交易辅助字段。

### Phase 3：选股信号源

优先接入：

- 东财涨停池
- 东财炸板池
- 东财跌停池
- 同花顺涨停揭秘
- 东财龙虎榜
- 全市场龙虎榜
- 东财资金流 120 日
- 东财概念归属
- 东财行业排名

完成标准：

- 每日可缓存信号表。
- 研究层可生成以下因子：
  - `limit_up_strength`
  - `limit_board_height`
  - `theme_heat`
  - `dragon_tiger_net_buy`
  - `main_fund_inflow_20d`
  - `industry_rank_score`
  - `concept_heat_score`

### Phase 4：基本面和事件层

接入：

- 融资融券
- 大宗交易
- 股东户数
- 分红送转
- 限售解禁
- 新浪财报三表
- 东财个股信息

完成标准：

- 可作为风险过滤和中期因子。
- 支持在股票池策略里排除高解禁压力、筹码恶化、异常大宗交易标的。

### Phase 5：新闻、公告、舆情层

接入：

- 巨潮公告
- 个股新闻
- 全球资讯
- 互动易问答
- 同花顺热榜
- 东财人气榜
- 概念命中

完成标准：

- 先进入研究报告和人工复核，不直接进入交易信号。
- 可为策略选股结果输出解释：
  - 为什么这只股票在涨
  - 是否有公告风险
  - 是否有概念热度
  - 公司如何回应市场关注

### Phase 6：ETF 期权层

接入：

- 期权合约清单
- T 型报价
- 希腊字母
- 隐含波动率

完成标准：

- 独立于股票池策略，作为后续 ETF/期权研究模块。

## MVP 端点

第一轮只做 12 个最有价值端点：

1. 腾讯实时行情
2. 腾讯估值/市值/涨跌停价
3. mootdx 日 K
4. mootdx 五档盘口
5. 东财涨停池
6. 东财炸板池
7. 东财跌停池
8. 同花顺涨停揭秘
9. 东财龙虎榜
10. 东财资金流 120 日
11. 东财行业排名
12. 东财概念归属

## 测试策略

### 单元测试

- symbol 规范化。
- URL 和参数构造。
- JSONP 解析。
- 字段标准化。
- 东财限流器不会并发。
- 缓存写入和去重。

### Smoke Test

每个 provider 至少有一个小样本：

```bash
python scripts/smoke_data_provider.py --provider eastmoney --endpoint limit_up_pool --date 2026-07-01
```

Smoke test 默认不进 CI，以免网络波动导致 CI 不稳定。

### 数据质量测试

- 必要字段非空。
- 股票代码可标准化。
- 日期可解析。
- 金额/价格字段可转数值。
- 空数据必须带原因。

## 研究层接入

新增：

```text
quant_assistant/research/alternative_factors.py
```

将扩展数据转成可排名因子：

```text
theme_heat_score
limit_up_score
dragon_tiger_score
fund_flow_score
unlock_risk_score
sentiment_rank_score
```

现有 `SelectionResearch` 不需要一次性重写，只需要允许加载外部因子表，并按 `symbol, trade_date` 合并。

## 风险

- 东财有风控，必须限流。
- 同花顺部分接口可能变化，需要明确降级。
- `iwencai` 需要 API Key，默认 optional。
- `mootdx` 对网络环境敏感，需要服务器探测和 fallback。
- 外部接口字段可能随时变化，必须有 schema test。
- 新闻和舆情数据不应直接进交易，防止噪音和过拟合。

## 成功标准

- 能稳定缓存 MVP 12 个端点。
- 能用扩展数据生成至少 5 个新因子。
- 能在股票池策略报告中解释入选股票的题材、资金、龙虎榜或风险事件。
- 回测流水能使用更真实的可交易字段：开盘价、涨跌停、停牌、不可成交。
- 任一数据源失败不会中断整个研究任务。
