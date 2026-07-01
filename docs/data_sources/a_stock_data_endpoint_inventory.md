# a-stock-data Endpoint Inventory

来源仓库：`simonlin1212/a-stock-data`

版本参考：`SKILL.md` V3.3.0

许可证：Apache License 2.0

## 优先级定义

- P0：直接影响股票池策略和交易可执行性，第一轮实现。
- P1：能增强因子和风险过滤，第二轮实现。
- P2：解释层、报告层或专项研究，后续实现。
- Optional：需要 key、网络条件或与当前股票池目标关系较远。

## 行情层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| mootdx K 线 | mootdx | 日/分钟/周/月 K 线 | P0 | `market/daily`, `market/minute` | `symbol, trade_date, open, high, low, close, volume, amount` |
| mootdx 五档盘口 | mootdx | 买卖五档盘口 | P0 | `market/order_book/date=...` | `symbol, bid_px, bid_qty, ask_px, ask_qty, fetch_time` |
| mootdx 逐笔成交 | mootdx | 分笔成交 | P1 | `market/ticks/{symbol}` | `symbol, datetime, price, volume, side` |
| 腾讯实时行情 | 腾讯财经 | 实时价、涨跌幅、换手 | P0 | `market/realtime/date=...` | `symbol, price, pct_change, volume, amount, turnover` |
| 腾讯估值市值 | 腾讯财经 | PE/PB/市值/涨跌停价 | P0 | `market/valuation/date=...` | `symbol, pe_ttm, pb, market_cap, float_market_cap, limit_up, limit_down` |
| 腾讯指数/ETF | 腾讯财经 | 指数、ETF 行情 | P1 | `market/index`, `market/etf` | `symbol, trade_date, price, pct_change, amount` |
| 百度 K 线 | 百度股市通 | K 线和 MA5/10/20 | P1 | `market/baidu_kline/{symbol}` | `symbol, trade_date, open, high, low, close, ma5, ma10, ma20` |

## 研报层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| 东财个股研报 | 东财 reportapi | 个股研报、评级、EPS | P2 | `reports/stock/{symbol}` | `symbol, publish_date, title, org, rating, eps_forecast, pdf_url` |
| 东财行业研报 | 东财 reportapi | 行业研报 | P2 | `reports/industry/{industry}` | `industry_code, publish_date, title, org, rating, pdf_url` |
| 东财 PDF 下载 | 东财 | 研报 PDF | P2 | `reports/pdf` | `pdf_path, source_url, info_code` |
| 同花顺一致预期 | 同花顺 | EPS 一致预期 | P1 | `reports/eps_forecast/{symbol}` | `symbol, report_period, eps_avg, eps_high, eps_low` |
| iwencai 研报搜索 | iwencai | 自然语言研报搜索 | Optional | `reports/iwencai` | `query, title, url, publish_date, score` |

## 信号层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| 同花顺热点 | 同花顺 | 强势股、题材归因 | P1 | `signals/ths_hot/date=...` | `trade_date, symbol, name, reason, tags` |
| 同花顺北向实时 | 同花顺 | 北向分钟流向 | P1 | `signals/northbound/minute/date=...` | `datetime, hgt_flow, sgt_flow, total_flow` |
| 同花顺北向历史 | 本地自缓存 | 北向日级历史 | P1 | `signals/northbound/daily` | `trade_date, hgt_flow, sgt_flow, total_flow` |
| 东财概念归属 | 东财 slist | 行业/概念/地域归属 | P0 | `signals/concept_blocks/date=...` | `symbol, block_code, block_name, block_type, leader` |
| 东财资金流分钟 | 东财 push2 | 主力/大单/中单/小单分钟净流入 | P1 | `capital_flow/minute/{symbol}` | `symbol, datetime, main_net_inflow, large_net_inflow` |
| 龙虎榜席位 | 东财 datacenter | 个股上榜记录和席位 | P0 | `signals/dragon_tiger/{symbol}` | `trade_date, symbol, reason, net_buy, buy_seats, sell_seats` |
| 全市场龙虎榜 | 东财 datacenter | 每日全市场龙虎榜 | P0 | `signals/dragon_tiger/date=...` | `trade_date, symbol, reason, net_buy, amount` |
| 限售解禁 | 东财 datacenter | 历史和未来解禁 | P1 | `events/lockup/{symbol}` | `symbol, unlock_date, unlock_amount, unlock_ratio` |
| 行业板块排名 | 东财 | 行业涨跌和涨跌家数 | P0 | `signals/industry_rank/date=...` | `trade_date, industry, pct_change, rising_count, falling_count` |

## 资金面 / 筹码层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| 融资融券 | 东财 datacenter | 两融余额和买偿 | P1 | `fundamentals/margin/{symbol}` | `trade_date, symbol, margin_balance, financing_buy, financing_repay` |
| 大宗交易 | 东财 datacenter | 大宗交易明细 | P1 | `events/block_trade/{symbol}` | `trade_date, symbol, price, volume, premium_rate, buyer, seller` |
| 股东户数 | 东财 datacenter | 股东数和户均持股 | P1 | `fundamentals/shareholders/{symbol}` | `report_date, symbol, holder_count, change_rate, avg_holding` |
| 分红送转 | 东财 datacenter | 分红送转历史 | P2 | `fundamentals/dividend/{symbol}` | `ex_date, symbol, cash_dividend, bonus_share, transfer_share` |
| 个股资金流 120 日 | 东财 push2his | 日级资金流 | P0 | `capital_flow/stock_120d/{symbol}` | `trade_date, symbol, main_net_inflow, large_net_inflow, retail_net_inflow` |

## 新闻层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| 东财个股新闻 | 东财 search-api | 个股新闻 | P2 | `news/stock/{symbol}` | `publish_time, symbol, title, url, source` |
| 财联社快讯 | cls.cn | 已下线 | 不接入 | 不缓存 | 不实现 |
| 东财全球资讯 | 东财 np-weblist | 7x24 资讯 | P2 | `news/global/date=...` | `publish_time, title, url, source` |

## 基础数据层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| mootdx 财务快照 | mootdx | 季报快照 37 字段 | P1 | `fundamentals/snapshot/{symbol}` | `report_date, symbol, eps, roe, revenue, net_profit` |
| mootdx F10 | mootdx | 公司资料文本 | P2 | `fundamentals/f10/{symbol}` | `symbol, section, content, fetch_time` |
| 东财个股信息 | 东财 push2 | 行业、股本、市值、上市日期 | P1 | `fundamentals/stock_info/{symbol}` | `symbol, industry, total_share, float_share, list_date` |
| 新浪财报三表 | 新浪 | 资产负债表/利润表/现金流量表 | P1 | `fundamentals/statements/{symbol}` | `report_date, symbol, statement_type, item, value` |

## 公告层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| 巨潮公告 | cninfo | 公告检索和下载 | P1 | `announcements/cninfo/{symbol}` | `publish_date, symbol, title, url, announcement_type` |
| mootdx 公告摘要 | mootdx F10 | 最新公告摘要 | P2 | `announcements/tdx/{symbol}` | `publish_date, symbol, title, summary` |

## 打板层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| 东财涨停池 | 东财 push2ex | 涨停池、连板、封单 | P0 | `limit_board/limit_up/date=...` | `trade_date, symbol, boards, sealed_amount, first_time, last_time` |
| 东财炸板池 | 东财 push2ex | 炸板池 | P0 | `limit_board/broken/date=...` | `trade_date, symbol, amplitude, open_count, max_pct` |
| 东财跌停池 | 东财 push2ex | 跌停池 | P0 | `limit_board/limit_down/date=...` | `trade_date, symbol, sealed_amount, open_count` |
| 东财昨涨停池 | 东财 push2ex | 昨涨停今表现 | P1 | `limit_board/yesterday_limit_up/date=...` | `trade_date, symbol, today_pct, promoted` |
| 同花顺涨停揭秘 | 同花顺 | 涨停原因、封板成功率 | P0 | `limit_board/reason/date=...` | `trade_date, symbol, reason, theme, success_rate, board_type` |
| 打板情绪速算 | 派生 | 炸板率、连板梯队 | P0 | `limit_board/sentiment/date=...` | `trade_date, limit_up_count, broken_rate, max_boards` |

## ETF 期权层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| 期权合约清单 | 新浪 | ETF 期权合约 | Optional | `options/contracts/date=...` | `underlying, month, option_code, call_put, strike` |
| T 型报价 | 新浪 | 期权报价 | Optional | `options/quotes/date=...` | `option_code, bid, ask, volume, open_interest, price` |
| 希腊字母和 IV | 新浪 | Delta/Gamma/Theta/Vega/IV | Optional | `options/greeks/date=...` | `option_code, delta, gamma, theta, vega, iv` |

## 舆情互动层

| 端点 | 来源 | 能力 | 优先级 | 缓存 | 标准化目标 |
|---|---|---|---|---|---|
| 互动易问答 | 巨潮 | 投资者问答 | P2 | `sentiment/irm/{symbol}` | `publish_time, symbol, question, answer` |
| 同花顺热榜 | 同花顺 | 热榜、人气、概念 | P1 | `sentiment/ths_hot_rank/date=...` | `trade_date, symbol, rank, heat, tags` |
| 东财人气榜 | 东财 | 人气排名 | P1 | `sentiment/em_hot_rank/date=...` | `trade_date, symbol, rank, rank_change` |
| 东财概念命中 | 东财 | 个股概念热度 | P1 | `sentiment/em_hot_concept/{symbol}` | `trade_date, symbol, concept, heat` |

## MVP 12 个端点

| 顺序 | 端点 | 原因 |
|---:|---|---|
| 1 | 腾讯实时行情 | 增强当前行情可用性 |
| 2 | 腾讯估值/市值/涨跌停价 | 支持真实交易约束和估值过滤 |
| 3 | mootdx 日 K | 降低对 akshare/efinance 依赖 |
| 4 | mootdx 五档盘口 | 后续支持成交可行性 |
| 5 | 东财涨停池 | 短线强势因子 |
| 6 | 东财炸板池 | 风险和情绪因子 |
| 7 | 东财跌停池 | 风险过滤 |
| 8 | 同花顺涨停揭秘 | 题材解释和封板质量 |
| 9 | 东财龙虎榜 | 资金行为因子 |
| 10 | 东财资金流 120 日 | 主力资金因子 |
| 11 | 东财行业排名 | 行业动量因子 |
| 12 | 东财概念归属 | 题材归因和概念热度 |
