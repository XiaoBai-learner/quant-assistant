# Quant Assistant 策略因子手册

> 完整记录所有策略因子的计算方法、适用场景和时间粒度

## 目录

1. [因子分类概览](#因子分类概览)
2. [时间粒度说明](#时间粒度说明)
3. [趋势类因子](#趋势类因子)
4. [动量类因子](#动量类因子)
5. [波动率类因子](#波动率类因子)
6. [量价类因子](#量价类因子)
7. [形态类因子](#形态类因子)
8. [统计类因子](#统计类因子)
9. [信号类因子](#信号类因子)
10. [实时因子](#实时因子)
11. [日内因子](#日内因子)
12. [使用示例](#使用示例)

---

## 因子分类概览

Quant Assistant 提供 **150+** 个策略因子，分为以下类别：

| 类别 | 数量 | 说明 | 适用场景 |
|------|------|------|----------|
| 趋势类 | 25+ | 均线、MACD、ADX等 | 趋势跟踪策略 |
| 动量类 | 20+ | RSI、KDJ、CCI、WR等 | 反转/突破策略 |
| 波动率类 | 20+ | 布林带、ATR、唐奇安通道等 | 波动率策略 |
| 量价类 | 20+ | 成交量、OBV、MFI等 | 量价分析 |
| 形态类 | 10+ | 影线、K线形态等 | 技术分析 |
| 统计类 | 15+ | 收益率统计、最大回撤等 | 风险评估 |
| 信号类 | 10+ | 金叉死叉、均线排列等 | 交易信号 |
| 实时因子 | 10+ | 换手率、涨速、量比等 | 实时交易 |
| 日内因子 | 10+ | VWAP、日内位置等 | 日内交易 |

---

## 时间粒度说明

不同因子适用于不同时间粒度的数据：

| 粒度 | 标识 | 说明 | 适用因子 |
|------|------|------|----------|
| 日线 | `daily` | 日K线数据 | 所有中长期因子 |
| 1分钟 | `1min` | 1分钟K线 | 超短周期因子 |
| 5分钟 | `5min` | 5分钟K线 | 短周期因子 |
| 15分钟 | `15min` | 15分钟K线 | 短周期因子 |
| 30分钟 | `30min` | 30分钟K线 | 中短周期因子 |
| 60分钟 | `60min` | 60分钟K线 | 中短周期因子 |
| 实时 | `realtime` | Tick级/实时行情 | 实时因子 |

### 粒度自适应计算

```python
from quant_assistant import QuantAPI

api = QuantAPI()

# 自动检测数据粒度并计算适合的因子
df = api.factors.compute_factors_v2(data)
```

---

## 趋势类因子

### 移动平均线 (MA)

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `ma5` | 5日 | MA = mean(close, 5) | 5日均线 |
| `ma10` | 10日 | MA = mean(close, 10) | 10日均线 |
| `ma20` | 20日 | MA = mean(close, 20) | 20日均线 |
| `ma30` | 30日 | MA = mean(close, 30) | 30日均线 |
| `ma60` | 60日 | MA = mean(close, 60) | 60日均线 |
| `ma120` | 120日 | MA = mean(close, 120) | 120日均线 |

**适用粒度**: 日线、60分钟、30分钟

### 指数移动平均线 (EMA)

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `ema5` | 5日 | EMA = EMA(close, 5) | 5日指数均线 |
| `ema10` | 10日 | EMA = EMA(close, 10) | 10日指数均线 |
| `ema20` | 20日 | EMA = EMA(close, 20) | 20日指数均线 |
| `ema60` | 60日 | EMA = EMA(close, 60) | 60日指数均线 |
| `ema120` | 120日 | EMA = EMA(close, 120) | 120日指数均线 |

**适用粒度**: 日线、60分钟、30分钟

### 均线衍生因子

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `ma5_10_diff` | ma5 - ma10 | 5日与10日均线差值 |
| `ma10_20_diff` | ma10 - ma20 | 10日与20日均线差值 |
| `ma20_60_diff` | ma20 - ma60 | 20日与60日均线差值 |
| `ma5_10_ratio` | ma5 / ma10 | 5日与10日均线比值 |
| `ma10_20_ratio` | ma10 / ma20 | 10日与20日均线比值 |

### MACD 指标

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `macd` | EMA(12) - EMA(26) | MACD线 |
| `macd_signal` | EMA(macd, 9) | 信号线 |
| `macd_hist` | macd - macd_signal | MACD柱状图 |

**参数**: 快线=12, 慢线=26, 信号=9

**适用粒度**: 日线、分钟级

### ADX 平均趋向指数

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `adx14` | mean(\|+DI - -DI\| / (+DI + -DI), 14) | 趋势强度 |
| `plus_di14` | 100 * mean(+DM, 14) / ATR | 正向指标 |
| `minus_di14` | 100 * mean(-DM, 14) / ATR | 负向指标 |

**说明**: ADX > 25 表示强趋势，ADX < 20 表示弱趋势

**适用粒度**: 日线、60分钟

### 一目均衡表

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `tenkan_sen` | (HH(9) + LL(9)) / 2 | 转换线 |
| `kijun_sen` | (HH(26) + LL(26)) / 2 | 基准线 |
| `ichimoku_cloud` | \|tenkan_sen - kijun_sen\| | 云图厚度 |
| `ichimoku_golden_cross` | tenkan_sen > kijun_sen 且 前一日 <= | 一目金叉 |

**适用粒度**: 日线

---

## 动量类因子

### RSI 相对强弱指数

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `rsi6` | 6日 | RSI = 100 - 100/(1+RS) | 短周期RSI |
| `rsi12` | 12日 | RSI = 100 - 100/(1+RS) | 中周期RSI |
| `rsi14` | 14日 | RSI = 100 - 100/(1+RS) | 标准RSI |
| `rsi24` | 24日 | RSI = 100 - 100/(1+RS) | 长周期RSI |

**其中**: RS = mean(gain, n) / mean(loss, n)

**适用粒度**: 日线、分钟级

### KDJ 随机指标

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `kdj_k` | EMA(RSV, 3) | K值 |
| `kdj_d` | EMA(K, 3) | D值 |
| `kdj_j` | 3*K - 2*D | J值 |
| `kdj_golden_cross` | K > D 且 前一日 K <= D | KDJ金叉 |

**其中**: RSV = (close - LL(9)) / (HH(9) - LL(9)) * 100

**适用粒度**: 日线、分钟级

### CCI 商品通道指数

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `cci20` | 20日 | (TP - MA) / (0.015 * MD) | CCI指标 |

**其中**: 
- TP = (high + low + close) / 3
- MA = mean(TP, 20)
- MD = mean(\|TP - MA\|, 20)

**适用粒度**: 日线

### 威廉指标 (WR)

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `wr14` | 14日 | -100 * (HH - close) / (HH - LL) | 威廉指标 |

**适用粒度**: 日线、分钟级

### 动量与变化率

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `mom10` | 10日 | close - close(10日前) | 动量 |
| `mom20` | 20日 | close - close(20日前) | 动量 |
| `roc10` | 10日 | (close/close(10日前) - 1) * 100 | 变化率 |
| `roc20` | 20日 | (close/close(20日前) - 1) * 100 | 变化率 |
| `momentum5` | 5日 | close/close(5日前) - 1 | 价格动量 |
| `momentum10` | 10日 | close/close(10日前) - 1 | 价格动量 |
| `momentum20` | 20日 | close/close(20日前) - 1 | 价格动量 |
| `momentum60` | 60日 | close/close(60日前) - 1 | 价格动量 |

**适用粒度**: 日线

---

## 波动率类因子

### 布林带 (BOLL)

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `boll_upper_20` | 20日 | MA + 2*STD | 上轨 |
| `boll_middle_20` | 20日 | MA | 中轨 |
| `boll_lower_20` | 20日 | MA - 2*STD | 下轨 |
| `boll_width_20` | 20日 | (上轨-下轨)/中轨 | 带宽 |
| `boll_position_20` | 20日 | (close-下轨)/(上轨-下轨) | 位置 |
| `boll_upper_60` | 60日 | MA + 2*STD | 上轨 |
| `boll_middle_60` | 60日 | MA | 中轨 |
| `boll_lower_60` | 60日 | MA - 2*STD | 下轨 |
| `boll_width_60` | 60日 | (上轨-下轨)/中轨 | 带宽 |
| `boll_position_60` | 60日 | (close-下轨)/(上轨-下轨) | 位置 |

**适用粒度**: 日线

### ATR 平均真实波幅

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `atr14` | mean(TR, 14) | 14日ATR |
| `atr20` | mean(TR, 20) | 20日ATR |
| `atr_ratio_14` | ATR14 / close | ATR比率 |
| `atr_ratio_20` | ATR20 / close | ATR比率 |

**其中**: TR = max(high-low, \|high-close_prev\|, \|low-close_prev\|)

**适用粒度**: 日线、分钟级

### 历史波动率

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `volatility_5` | 5日 | std(returns, 5) * sqrt(252) | 5日波动率 |
| `volatility_10` | 10日 | std(returns, 10) * sqrt(252) | 10日波动率 |
| `volatility_20` | 20日 | std(returns, 20) * sqrt(252) | 20日波动率 |
| `volatility_60` | 60日 | std(returns, 60) * sqrt(252) | 60日波动率 |
| `intraday_volatility` | 20根 | std(returns, 20) | 日内波动率 |

**适用粒度**: 日线、分钟级

### 唐奇安通道

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `dc_upper_20` | max(high, 20) | 上轨 |
| `dc_lower_20` | min(low, 20) | 下轨 |
| `dc_middle_20` | (上轨+下轨)/2 | 中轨 |
| `dc_width_20` | (上轨-下轨)/中轨 | 通道宽度 |

**适用粒度**: 日线

### 振幅因子

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `amplitude` | (high - low) / low | 当日振幅 |
| `amplitude_ma5` | mean(amplitude, 5) | 5日平均振幅 |
| `amplitude_ma10` | mean(amplitude, 10) | 10日平均振幅 |
| `amplitude_ma20` | mean(amplitude, 20) | 20日平均振幅 |

**适用粒度**: 日线

---

## 量价类因子

### 成交量移动平均

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `volume_ma5` | 5日 | mean(volume, 5) | 5日成交量均线 |
| `volume_ma10` | 10日 | mean(volume, 10) | 10日成交量均线 |
| `volume_ma20` | 20日 | mean(volume, 20) | 20日成交量均线 |

### 量比与换手率

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `volume_ratio` | volume / volume_ma20 | 量比 |
| `volume_change` | pct_change(volume) | 成交量变化率 |
| `turnover` | volume / float_shares | 换手率 |

### 成交额

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `amount` | close * volume | 成交额 |
| `amount_ma5` | mean(amount, 5) | 5日成交额均线 |
| `amount_ma10` | mean(amount, 10) | 10日成交额均线 |
| `amount_ma20` | mean(amount, 20) | 20日成交额均线 |
| `amount_change` | pct_change(amount) | 成交额变化率 |

### OBV 能量潮

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `obv` | cumsum(sign(close_diff) * volume) | OBV |

**适用粒度**: 日线、分钟级

### MFI 资金流量指标

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `mfi14` | 100 - 100/(1+PMF/NMF) | 资金流量指标 |

**其中**:
- TP = (high + low + close) / 3
- PMF = sum(TP > TP_prev ? TP*volume : 0, 14)
- NMF = sum(TP < TP_prev ? TP*volume : 0, 14)

**适用粒度**: 日线

### 量价相关性

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `price_volume_corr` | corr(close, volume, 20) | 价量相关性 |

### PVT 价量趋势

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `pvt` | cumsum(pct_change(close) * volume) | 价量趋势 |

---

## 形态类因子

### K线形态

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `upper_shadow` | (high - max(open, close)) / close | 上影线 |
| `lower_shadow` | (min(open, close) - low) / close | 下影线 |
| `body` | abs(close - open) / close | K线实体 |

### 价格位置

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `price_position_20` | 20日 | (close - LL) / (HH - LL) | 20日价格位置 |
| `price_position_60` | 60日 | (close - LL) / (HH - LL) | 60日价格位置 |

**其中**: HH = max(high, n), LL = min(low, n)

---

## 统计类因子

### 收益率

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `returns` | pct_change(close) | 收益率 |
| `log_returns` | log(close / close_prev) | 对数收益率 |

### 收益率统计量

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `returns_mean_5` | 5日 | mean(returns, 5) | 5日收益均值 |
| `returns_mean_10` | 10日 | mean(returns, 10) | 10日收益均值 |
| `returns_mean_20` | 20日 | mean(returns, 20) | 20日收益均值 |
| `returns_std_5` | 5日 | std(returns, 5) | 5日收益标准差 |
| `returns_std_10` | 10日 | std(returns, 10) | 10日收益标准差 |
| `returns_std_20` | 20日 | std(returns, 20) | 20日收益标准差 |
| `returns_skew_5` | 5日 | skew(returns, 5) | 5日收益偏度 |
| `returns_skew_10` | 10日 | skew(returns, 10) | 10日收益偏度 |
| `returns_skew_20` | 20日 | skew(returns, 20) | 20日收益偏度 |
| `returns_kurt_5` | 5日 | kurt(returns, 5) | 5日收益峰度 |
| `returns_kurt_10` | 10日 | kurt(returns, 10) | 10日收益峰度 |
| `returns_kurt_20` | 20日 | kurt(returns, 20) | 20日收益峰度 |

### 最大回撤

| 因子名 | 周期 | 公式 | 说明 |
|--------|------|------|------|
| `drawdown_20` | 20日 | (close - max(close, 20)) / max(close, 20) | 20日最大回撤 |
| `drawdown_60` | 60日 | (close - max(close, 60)) / max(close, 60) | 60日最大回撤 |

---

## 信号类因子

### MACD信号

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `macd_golden_cross` | MACD > Signal 且 前一日 MACD <= Signal | MACD金叉 |
| `macd_dead_cross` | MACD < Signal 且 前一日 MACD >= Signal | MACD死叉 |

### KDJ信号

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `kdj_golden_cross` | K > D 且 前一日 K <= D | KDJ金叉 |

### 均线排列

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `ma_bull` | ma5 > ma10 > ma20 > ma60 | 均线多头排列 |
| `ma_bear` | ma5 < ma10 < ma20 < ma60 | 均线空头排列 |
| `trend_strength` | (ma5_10_ratio + ma10_20_ratio) / 2 | 趋势强度 |

---

## 实时因子

实时因子适用于实时行情数据，提供即时交易信号。

### 基础实时因子

| 因子名 | 数据来源 | 说明 | 交易意义 |
|--------|----------|------|----------|
| `realtime_turnover` | 实时行情 | 实时换手率 | 判断活跃度 |
| `realtime_rise_speed` | 实时行情 | 实时涨速(%) | 捕捉快速上涨 |
| `realtime_volume_ratio` | 实时行情 | 实时量比 | 成交量异常 |
| `realtime_order_ratio` | 实时行情 | 实时委比(%) | 买卖盘力量 |
| `realtime_amplitude` | 实时行情 | 实时振幅(%) | 波动率评估 |
| `realtime_price_position` | 实时行情 | 相对昨收位置(%) | 价格位置 |

### 资金流向因子

| 因子名 | 数据来源 | 公式 | 说明 |
|--------|----------|------|------|
| `realtime_inflow` | 实时行情 | 外盘 - 内盘 | 实时资金流向 |
| `buying_power` | 实时行情 | (close-low)/(high-low) | 买入力度 |
| `selling_pressure` | 实时行情 | (high-close)/(high-low) | 卖出压力 |

### 实时因子计算示例

```python
from quant_assistant.data import EFinanceFetcher
from quant_assistant import QuantAPI

ef = EFinanceFetcher()
api = QuantAPI()

# 获取实时行情
realtime = ef.get_realtime_quotes(['300751'])

# 计算实时因子
df = api.factors.compute_factors_v2(realtime)

print(df[['realtime_turnover', 'realtime_rise_speed', 
          'realtime_volume_ratio', 'buying_power']])
```

---

## 日内因子

日内因子适用于分钟级数据，提供日内交易参考。

### 日内价格因子

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `intraday_change` | (close - first_close) / first_close * 100 | 日内涨跌幅 |
| `intraday_position` | (close - day_low) / (day_high - day_low) | 日内位置 |
| `intraday_high_pos` | expanding_max(high) | 日内最高位置 |
| `intraday_low_pos` | expanding_min(low) | 日内最低位置 |

### VWAP 因子

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `vwap` | cumsum(close * volume) / cumsum(volume) | 成交量加权均价 |
| `vwap_deviation` | (close - vwap) / vwap | VWAP偏离度 |

### 成交量分布

| 因子名 | 公式 | 说明 |
|--------|------|------|
| `volume_cumsum` | cumsum(volume) | 累计成交量 |
| `volume_pct` | volume / sum(volume) | 成交量占比 |

### 日内因子计算示例

```python
from quant_assistant.data import EFinanceFetcher
from quant_assistant import QuantAPI

ef = EFinanceFetcher()
api = QuantAPI()

# 获取当日分时数据
intraday = ef.get_intraday_data('300751', freq='1min')

# 计算日内因子
df = api.factors.compute_factors_v2(intraday)

print(df[['intraday_change', 'intraday_position', 'vwap', 'vwap_deviation']])
```

---

## 使用示例

### 基础使用

```python
from quant_assistant import QuantAPI

api = QuantAPI()

# 获取数据
data = api.data.get_stock_data('300751', start='2024-01-01')

# 计算所有因子
df = api.factors.compute_all_factors(data)

print(f"共计算 {len(df.columns)} 个因子")
```

### 多粒度因子计算

```python
from quant_assistant import QuantAPI, TimeGranularity, FactorCategory

api = QuantAPI()

# 1. 日线数据 - 计算中长期因子
daily_data = api.data.get_stock_data('300751', start='2024-01-01')
df_daily = api.factors.compute_factors_v2(daily_data)

# 2. 分钟数据 - 计算短周期因子
from quant_assistant.data import EFinanceFetcher
ef = EFinanceFetcher()
minute_data = ef.get_minute_data('300751', period=5)
df_minute = api.factors.compute_factors_v2(minute_data)

# 3. 实时数据 - 计算实时因子
realtime = ef.get_realtime_quotes(['300751'])
df_realtime = api.factors.compute_factors_v2(realtime)

# 4. 指定类别
from quant_assistant import FactorCategory
df = api.factors.compute_factors_v2(
    data,
    categories=[FactorCategory.TREND, FactorCategory.MOMENTUM]
)
```

### 因子信息查询

```python
from quant_assistant.factors import FactorEngineV2

engine = FactorEngineV2()

# 获取所有因子信息
info = engine.get_factor_info()
print(info[info['category'] == 'realtime'])
```

---

## 因子选择建议

### 按策略类型选择

| 策略类型 | 推荐因子类别 | 示例因子 |
|----------|--------------|----------|
| 趋势跟踪 | 趋势类、信号类 | ma20, macd, adx14, ma_bull |
| 均值回归 | 动量类、波动率类 | rsi14, boll_position, cci20 |
| 突破策略 | 形态类、波动率类 | price_position, dc_width, amplitude |
| 量价策略 | 量价类 | volume_ratio, obv, mfi14 |
| 日内交易 | 实时类、日内类 | realtime_rise_speed, vwap, intraday_position |
| 高频交易 | 实时类 | realtime_turnover, buying_power |

### 按数据粒度选择

| 数据粒度 | 推荐因子 | 说明 |
|----------|----------|------|
| 日线 | ma5-120, rsi14, macd, boll | 中长期趋势 |
| 5分钟 | ma5-48, rsi6, atr14 | 短周期波动 |
| 1分钟 | ma5-30, rsi5, intraday_volatility | 超短周期 |
| 实时 | realtime_*, buying_power | 即时信号 |

---

## 更新日志

- **2024-03-12**: 初始版本，包含 150+ 个因子
  - 支持多时间粒度（日线/分钟级/实时）
  - 新增实时因子和日内因子
  - 因子元数据管理

---

*文档版本: 1.0*
*最后更新: 2024-03-12*
