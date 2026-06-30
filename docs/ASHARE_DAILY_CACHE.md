# A 股日线本地缓存

本地缓存用于把 A 股日线行情保存为 Parquet 文件，服务股票池因子研究、选股回测和实验复现。

## 缓存范围

- 市场：默认全 A，可通过 `--market all/sh/sz/bj` 控制。
- 粒度：日线。
- 默认区间：初始化时获取近一年。
- 默认复权：`qfq` 前复权。
- 标准字段：`symbol`, `trade_date`, `open`, `high`, `low`, `close`, `volume`, `amount`。
- 默认目录：`~/.quant_assistant/cache/ashare_daily/`。
- 存储格式：每只股票一个 Parquet 文件。

## 数据源选择

脚本把“股票列表”和“日线行情”拆成两条数据链路：

- 股票列表：默认 `--stock-list-source tickflow`。当前本机试跑中，TickFlow 能稳定返回全 A 列表，可避免 `auto` 模式先尝试 EFinance/AKShare 产生前置报错日志。
- 日线行情：默认 `--source auto`，继续使用统一数据获取器做行情源故障切换。

也可以显式指定：

```bash
python scripts/cache_ashare_daily.py --init-one-year --source akshare
python scripts/cache_ashare_daily.py --update-latest --source efinance
python scripts/cache_ashare_daily.py --update-latest --source tickflow
python scripts/cache_ashare_daily.py --init-one-year --stock-list-source tickflow --source auto
```

## 初始化近一年全 A 日线缓存

建议先用 `--limit` 小批量试跑：

```bash
python scripts/cache_ashare_daily.py --init-one-year --limit 20
```

确认数据源和缓存目录正常后，执行全量初始化：

```bash
python scripts/cache_ashare_daily.py --init-one-year
```

指定缓存目录：

```bash
python scripts/cache_ashare_daily.py \
  --init-one-year \
  --cache-dir ~/.quant_assistant/cache/ashare_daily
```

## 每天 8 点更新上一工作日

当前项目只提供可手动执行的任务代码，不直接创建系统定时任务。

手动执行：

```bash
python scripts/cache_ashare_daily.py --update-latest
```

该命令会计算运行日的上一工作日，拉取全 A 日线数据并追加到本地 Parquet 缓存。单只股票失败不会中断整体更新，失败原因会写入报告。后续可以接入交易所交易日历，把“上一工作日”升级为严格的“上一交易日”。

试跑：

```bash
python scripts/cache_ashare_daily.py --update-latest --limit 20
```

指定运行日期，用于手动补数据：

```bash
python scripts/cache_ashare_daily.py --update-latest --run-date 2026-06-30
```

## 更新报告

默认报告输出到：

```text
reports/ashare_cache_update.json
```

可以指定：

```bash
python scripts/cache_ashare_daily.py \
  --update-latest \
  --report reports/ashare_cache_update_2026-06-30.json
```

报告包含：

- 更新区间。
- 数据源。
- 股票数量。
- 成功数量。
- 空结果数量。
- 失败数量。
- 每只股票的状态。
- 缓存目录和缓存统计。

## 后续定时任务示例

macOS/Linux 可自行配置 cron，每天 8 点执行：

```cron
0 8 * * 1-5 cd /path/to/quant-assistant && python scripts/cache_ashare_daily.py --update-latest
```
