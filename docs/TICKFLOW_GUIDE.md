# TickFlow 主数据源接入与测试

更新时间：2026-11-18。官方参考：[Python 快速开始](https://docs.tickflow.org/zh-Hans/sdk/python-quickstart)。

## 设计与入口

取数链路统一为：

```text
QuantAPI.data / DataHub.market / quant CLI / 日线缓存任务
    → UnifiedDataFetcher
    → TickFlow 官方 SDK → EFinance → AKShare
```

TickFlow 是默认主源，`auto` 也使用相同优先级。因子、研究、回测仍接收原有 pandas DataFrame，不需要重写。

- `TickFlowFetcher` 只负责 TickFlow 的端点、参数、权限和标准化。
- `UnifiedDataFetcher` 负责统一主备策略，失败或空结果时切换；所有接口遵守 `fallback_enabled`。
- `DataHub.market.daily()`、默认 `DataHub.market.realtime()` 共用这套取数策略。
- 估值快照 `DataHub.market.valuation()` 仍使用腾讯；资金流、行业、事件仍使用已有东方财富 provider；财务面板仍保留现有渠道。当前 TickFlow Key 没有财务权限，不假装所有扩展数据已经迁移。
- 显式注入的 fetcher、腾讯 provider 继续按调用者选择运行。

## 配置

在项目根目录 `.env` 中配置（该文件被 Git 忽略）：

```dotenv
TICKFLOW_API_KEY=your-key
TICKFLOW_MODE=authenticated
```

环境变量优先于本地文件；不会覆盖已有 shell 配置。

| mode | 端点 | 含义 |
|---|---|---|
| `free` | `https://free-api.tickflow.org` | 匿名免费历史服务；不发送 Key |
| `authenticated` | `https://api.tickflow.org` | 使用 Key，权限由账户决定，不等于已付费 |

不指定模式时，有 Key 自动选择认证服务，否则选择匿名免费服务。旧构造参数 `use_paid=True/False` 保留兼容；新代码使用 `mode`。

API Key 仅用于官方认证端点，不写入源码、报告或日志。默认 15 秒超时，SDK 对连接、限流和服务端临时错误最多重试 2 次，401/403 不重试。适配器串行调用间隔默认至少 1.1 秒；该间隔是保守客户端设置，不是账户配额承诺。

## 使用

```python
from quant_assistant import QuantAPI
from quant_assistant.data import UnifiedDataFetcher, TickFlowFetcher, DataHub

api = QuantAPI()
bars = api.data.get_stock_data("600000.SH", start="2026-10-01", end="2026-11-17")
print(bars.tail())
print(bars.attrs)  # source、mode、复权、单位及主备尝试

# 严格测试 TickFlow，禁止使用其他渠道掩盖失败
fetcher = UnifiedDataFetcher(primary_source="tickflow", fallback_enabled=False)
bars = fetcher.get_daily_quotes("000001.SZ", "2026-10-01", "2026-11-17")
quotes = fetcher.get_realtime_quotes(["600000.SH"])
print(fetcher.last_source, fetcher.last_attempts)
fetcher.close()

# 显式体验匿名服务；即使本地有 Key，也不会发送
free = TickFlowFetcher(mode="free")
try:
    bars = free.get_daily_quotes("600000.SH", "2026-10-01", "2026-11-17")
finally:
    free.close()

hub = DataHub()
bars = hub.market.daily("600000.SH", start="2026-10-01", end="2026-11-17")
```

### 日线口径

- 输入支持六位代码、`600000.SH`、`sh600000`；保留显式交易所，避免将 `000001.SH` 指数误识别为深圳股票。
- 股票列表只保留沪深北 A 股，不把 ETF、指数或 B 股混入股票池。
- 输出：`symbol` 为六位代码，`trade_date` 为上海时区对应交易日的无时区 Timestamp，附带 OHLCV 与 `amount`。
- 日期转换成 API 所需的 `start_time` / `end_time` 毫秒时间戳，结束日包含全天；返回后再次裁剪、排序、去重。
- 每页最多 10000 根；历史超过上限会向前分页，若服务端不推进分页则明确报错，拒绝静默截断。
- `qfq` → `forward_additive`，`hfq` → `backward_additive`，保持与原东方财富渠道的差值复权口径一致。
- 比例复权可直接在 `TickFlowFetcher` 传 `forward` / `backward`，不会默认为另一种复权。
- `volume` 保留 A 股源数据的“手”，`amount` 为人民币元。使用复权价格时，不应期望 `close × volume × 100` 严格等于原始成交额。
- 日线 `symbol` 兼容旧研究模块使用六位代码；实时行情保留 `代码.交易所`，以区分 `000001.SH` 指数与 `000001.SZ` 股票。实时批量结果若缺少请求标的则报错，不把部分返回标为整批成功。
- 来源、模式、复权等保存在 `DataFrame.attrs`；缓存任务的 JSON 报告逐股票记录实际来源与主备尝试。后续 DataFrame 操作不一定保留 attrs，审计时应保留报告。

## 可重复诊断

安装依赖后，从项目根目录运行：

```bash
python scripts/diagnose_tickflow.py --mode both
```

只用匿名服务：

```bash
python scripts/diagnose_tickflow.py --mode free
```

脚本直接调用 TickFlow，不启用备用渠道，检查股票列表、沪深北样本日线、三种复权、标的信息、实时快照、分钟线及财务权限。报告默认写入 `reports/tickflow_diagnostics.json`，包含耗时、行数、最新日期、字段和错误状态。权限拒绝与空数据分别记录。

小范围写入独立缓存，避免与旧行情混合：

```bash
python scripts/cache_ashare_daily.py \
  --update-range --start 2026-10-01 --end 2026-11-17 \
  --symbols 600000.SH,000001.SZ,920662.BJ \
  --source tickflow --no-fallback \
  --cache-dir reports/tickflow_sample_cache \
  --report reports/tickflow_sample_cache_report.json
```

## 2026-11-18 账户实测

| 检查 | 匿名免费服务 | 本地 Key 认证服务 |
|---|---|---|
| 沪深北 A 股列表 | 成功，5892 只 | 成功，5892 只 |
| 沪深北三只样本日线 | 成功，最新 2026-11-17 | 成功，最新 2026-11-18 |
| 差值前复权、后复权、不复权 | 成功 | 成功 |
| 标的信息 | 成功 | 成功 |
| 实时快照 | 免费模式不支持 | 成功 |
| 5 分钟 K 线 | 免费模式不支持 | HTTP 403：无分钟 K 线查询权限 |
| 核心财务指标 | 免费模式不支持 | HTTP 403：无公司财务数据查询权限 |

这是该 Key 在本次测试时的能力，不是所有免费账户的统一承诺。仅以日线用于当前研究已经可行；分钟级策略和 TickFlow 财务数据目前不可用。历史长度、大规模稳定性与限流阈值应分开测试，不能从几次成功请求推断。认证日线可能包含尚未完成的当日 K 线，历史研究建议显式指定已收盘的结束日。

已额外跑通 2025-01-02 至 2026-11-17 共 453 条浦发银行日线 → MA20 → 原事件回测，及三只股票共 87 条独立 Parquet 缓存。结果见 `reports/tickflow_pipeline_smoke.json`、`reports/tickflow_sample_cache_report.json`。该回测用于验证接口兼容性，不用于评价策略收益。

回归验证：`python -m pytest -q`，209 项通过（保留项目已有的弃用与性能警告）。
