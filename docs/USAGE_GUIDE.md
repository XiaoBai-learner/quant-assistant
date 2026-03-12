# Quant Assistant 使用手册

> 以迈为股份 (300751) 为例的完整使用指南

## 目录

1. [安装](#安装)
2. [快速开始](#快速开始)
3. [数据获取](#数据获取)
4. [因子计算](#因子计算)
5. [策略开发](#策略开发)
6. [回测验证](#回测验证)
7. [机器学习预测](#机器学习预测)
8. [命令行工具](#命令行工具)
9. [API 参考](#api-参考)

---

## 安装

### 从源码安装

```bash
# 克隆仓库
git clone https://github.com/XiaoBai-learner/quant-assistant.git
cd quant-assistant

# 安装依赖
pip install -e .

# 验证安装
quant version
```

### 依赖要求

- Python >= 3.10
- MySQL >= 8.0 (可选，用于数据存储)

---

## 快速开始

### 1. 导入包

```python
import quant_assistant as qa
from quant_assistant import QuantAPI

# 创建 API 实例
api = QuantAPI()
```

### 2. 获取迈为股份数据

```python
# 获取日线数据
data = api.data.get_stock_data(
    symbol='300751',      # 迈为股份
    start='2024-01-01',
    end='2024-12-31'
)

print(data.head())
```

输出：
```
            open   high    low  close   volume
2024-01-02  85.5   87.2   84.8   86.5   125000
2024-01-03  86.5   88.0   85.2   87.8   132000
...
```

---

## 数据源选择

Quant Assistant 支持多种数据源：

| 数据源 | 特点 | 适用场景 |
|--------|------|----------|
| **AKShare** | 免费开源，数据全面 | 历史数据获取、批量下载 |
| **EFinance** | 细粒度、实时性强 | 实时行情、分钟级数据、分笔数据 |

### 使用 EFinance 获取细粒度数据 ⭐

```python
from quant_assistant.data import EFinanceFetcher

# 创建 EFinance 获取器
ef = EFinanceFetcher()

# 检查是否可用
if ef.is_available():
    # 获取实时行情
    realtime = ef.get_realtime_quotes(['300751'])
    print(realtime[['symbol', 'close', 'change_percent', 'volume_ratio']])
    
    # 获取分钟级数据（1分钟）
    minute_data = ef.get_minute_data('300751', period=1)
    print(minute_data.head())
    
    # 获取5分钟数据
    df_5min = ef.get_minute_data('300751', period=5, start='2024-01-01')
    
    # 获取分笔数据（tick级）
    tick_data = ef.get_tick_data('300751')
    print(f"今日分笔数据: {len(tick_data)} 笔")
    
    # 获取当日分时数据
    intraday = ef.get_intraday_data('300751', freq='1min')
```

---

## EFinance 详细使用指南 ⭐

EFinance 数据源提供细粒度、高时效性的股票数据，适合实时交易和短线策略。

### 安装依赖

```bash
pip install efinance
```

### 实时行情数据

```python
from quant_assistant.data import EFinanceFetcher

ef = EFinanceFetcher()

# 获取全市场实时行情（约5000+股票）
all_stocks = ef.get_realtime_quotes()
print(f"全市场股票: {len(all_stocks)} 只")

# 获取指定股票实时行情
realtime = ef.get_realtime_quotes(['300751', '000001', '600519'])
print(realtime[['symbol', 'name', 'close', 'change_percent', 
                'volume', 'turnover', 'pe', 'volume_ratio']])

# 筛选涨幅超过5%的股票
rising = realtime[realtime['change_percent'] > 5]
print(f"涨幅超过5%: {len(rising)} 只")
```

### 分钟级历史数据

```python
# 获取1分钟数据（适合日内策略）
df_1min = ef.get_minute_data('300751', period=1, 
                              start='2024-01-01', end='2024-01-31')
print(f"1分钟数据: {len(df_1min)} 条")

# 获取5分钟数据
df_5min = ef.get_minute_data('300751', period=5)

# 获取15分钟数据
df_15min = ef.get_minute_data('300751', period=15)

# 获取30分钟数据
df_30min = ef.get_minute_data('300751', period=30)

# 获取60分钟数据
df_60min = ef.get_minute_data('300751', period=60)

# 计算分钟级因子
from quant_assistant import QuantAPI
api = QuantAPI()
df_5min_with_factors = api.factors.compute_all_factors(df_5min)
```

### 分笔数据（Tick级）

```python
# 获取今日分笔数据
tick_today = ef.get_tick_data('300751')
print(f"今日分笔: {len(tick_today)} 笔")

# 获取指定日期分笔数据
tick_history = ef.get_tick_data('300751', date='2024-01-15')

# 分析大单
big_orders = tick_history[tick_history['volume'] >= 100000]  # 10万股以上
print(f"大单数量: {len(big_orders)}")

# 计算资金流向
buy_volume = tick_history[tick_history['direction'] == '买盘']['volume'].sum()
sell_volume = tick_history[tick_history['direction'] == '卖盘']['volume'].sum()
net_inflow = buy_volume - sell_volume
print(f"净流入: {net_inflow} 股")
```

### 当日分时数据

```python
# 获取当日1分钟分时数据
intraday_1min = ef.get_intraday_data('300751', freq='1min')

# 获取当日5分钟分时数据
intraday_5min = ef.get_intraday_data('300751', freq='5min')

# 实时监控
import time
while True:
    latest = ef.get_intraday_data('300751', freq='1min')
    current = latest.iloc[-1]
    print(f"时间: {current['datetime']}, 价格: {current['close']}, "
          f"成交量: {current['volume']}")
    time.sleep(60)  # 每分钟更新
```

### 财务数据

```python
# 获取财务报表（季报）
financial = ef.get_financial_data('300751', report_type='quarterly')
print(financial[['report_date', 'eps', 'roe', 'revenue', 'net_profit']])

# 获取年报
annual = ef.get_financial_data('300751', report_type='annual')
```

### 板块数据

```python
# 获取行业板块
industry = ef.get_sector_data('industry')
print(industry[['name', 'change_percent', 'volume']].head(10))

# 获取概念板块
concept = ef.get_sector_data('concept')

# 获取地域板块
area = ef.get_sector_data('area')
```

---

## 数据获取

### 获取股票列表

```python
# 获取全部A股
stocks = api.data.get_stock_list(market='all')

# 获取创业板股票
cy_stocks = api.data.get_stock_list(market='sz')

# 查找迈为股份
maiwei = stocks[stocks['symbol'] == '300751']
print(maiwei[['symbol', 'name', 'industry']])
```

### 获取历史行情

```python
# 获取不同周期数据
daily = api.data.get_stock_data('300751', period='daily')    # 日线
weekly = api.data.get_stock_data('300751', period='weekly')  # 周线

# 获取不复权数据
raw = api.data.get_stock_data('300751', adjust='')

# 获取后复权数据
hfq = api.data.get_stock_data('300751', adjust='hfq')
```

### 获取财务数据

```python
# 获取财务报表
financial = api.data.get_financial_data('300751', report_type='quarterly')
print(financial[['report_date', 'eps', 'roe', 'revenue']])
```

### 数据存储与查询

```python
# 保存到数据库
api.data.save(data, 'daily_quotes')

# 从数据库查询
result = api.data.query(
    table='daily_quotes',
    symbol='300751',
    start='2024-01-01',
    end='2024-12-31'
)
```

---

## 因子计算

### 计算单个指标

```python
# 获取数据
data = api.data.get_stock_data('300751', start='2024-01-01')

# 计算移动平均线
ma20 = api.factors.ma(data, window=20)
ma60 = api.factors.ma(data, window=60)

# 计算MACD
macd = api.factors.macd(data)
print(f"MACD: {macd['macd'].iloc[-1]:.2f}")
print(f"Signal: {macd['signal'].iloc[-1]:.2f}")

# 计算RSI
rsi = api.factors.rsi(data, window=14)
print(f"RSI(14): {rsi.iloc[-1]:.2f}")

# 计算布林带
bb = api.factors.bollinger(data)
print(f"上轨: {bb['upper'].iloc[-1]:.2f}")
print(f"中轨: {bb['middle'].iloc[-1]:.2f}")
print(f"下轨: {bb['lower'].iloc[-1]:.2f}")

# 计算KDJ
kdj = api.factors.kdj(data)
print(f"K: {kdj['k'].iloc[-1]:.2f}, D: {kdj['d'].iloc[-1]:.2f}, J: {kdj['j'].iloc[-1]:.2f}")
```

### 计算所有指标（基础版）

```python
# 一键计算所有技术指标（约30个）
data_with_factors = api.factors.compute_all(data)

print(data_with_factors.columns)
# 输出: ['open', 'high', 'low', 'close', 'volume', 
#        'ma5', 'ma10', 'ma20', 'ma60', 
#        'ema12', 'ema26', 'macd', 'macd_signal', ...]
```

### 计算所有策略因子（完整版）⭐

```python
# 一次性计算120+个策略因子，包含趋势、动量、波动率、量价、形态、统计、复合信号等
# 适合策略开发和机器学习特征工程
df = api.factors.compute_all_factors(data)

print(f"共计算 {len(df.columns)} 个因子")
print(df.columns.tolist())
```

#### 因子分类说明

| 类别 | 因子示例 | 数量 |
|------|---------|------|
| **趋势类** | ma5/10/20/30/60/120, ema, MACD, 均线差值/比值, 金叉死叉信号 | 25+ |
| **动量类** | rsi6/12/14/24, KDJ, 威廉指标WR, CCI, MOM, ROC | 15+ |
| **波动率类** | 布林带, ATR, 唐奇安通道, 历史波动率, 振幅 | 20+ |
| **量价类** | 成交量MA, 量价相关性, OBV, MFI, PVT, 换手率 | 15+ |
| **形态类** | 影线, 价格位置, 实体大小, 连涨连跌天数 | 10+ |
| **统计类** | 收益率统计, 最大回撤, 偏度峰度 | 20+ |
| **复合信号** | 均线多头排列/空头排列, 趋势强度, 一目金叉 | 10+ |

#### 常用扩展因子示例

```python
# 获取完整因子数据
df = api.factors.compute_all_factors(data)

# 趋势强度因子
print(f"ADX(14): {df['adx14'].iloc[-1]:.2f}")  # 平均趋向指数
print(f"+DI(14): {df['plus_di14'].iloc[-1]:.2f}")
print(f"-DI(14): {df['minus_di14'].iloc[-1]:.2f}")

# 动量因子
print(f"CCI(20): {df['cci20'].iloc[-1]:.2f}")  # 商品通道指数
print(f"WR(14): {df['wr14'].iloc[-1]:.2f}")    # 威廉指标
print(f"MOM(10): {df['mom10'].iloc[-1]:.2f}")  # 动量
print(f"ROC(10): {df['roc10'].iloc[-1]:.2f}")  # 变化率

# 通道因子
print(f"唐奇安通道宽度: {df['dc_width_20'].iloc[-1]:.4f}")
print(f"一目均衡表云厚: {df['ichimoku_cloud'].iloc[-1]:.2f}")

# 量价因子
print(f"MFI(14): {df['mfi14'].iloc[-1]:.2f}")  # 资金流量指标
print(f"换手率: {df['turnover'].iloc[-1]:.2f}")
print(f"连涨天数: {df['consecutive_up'].iloc[-1]}")
```

---

## 策略开发

### 使用内置策略

```python
# 创建MACD策略
macd_strategy = api.strategy.create('macd', 
    fast=12, slow=26, signal=9
)

# 创建均线交叉策略
ma_strategy = api.strategy.create('ma_cross',
    short_window=10, long_window=30
)

# 生成交易信号
signals = api.strategy.generate_signals(ma_strategy, data)
print(signals[['close', 'signal', 'position']].tail(20))
```

### 自定义策略

```python
from quant_assistant.strategy import BaseStrategy

class MaiWeiStrategy(BaseStrategy):
    """迈为股份专用策略"""
    
    def __init__(self, ma_short=10, ma_long=30, rsi_threshold=30):
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.rsi_threshold = rsi_threshold
    
    def generate_signals(self, data):
        df = data.copy()
        
        # 计算指标
        df['ma_short'] = df['close'].rolling(self.ma_short).mean()
        df['ma_long'] = df['close'].rolling(self.ma_long).mean()
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 生成信号
        df['signal'] = 0
        # 金叉 + RSI超卖
        buy_condition = (df['ma_short'] > df['ma_long']) & \
                       (df['ma_short'].shift(1) <= df['ma_long'].shift(1)) & \
                       (df['rsi'] < self.rsi_threshold + 20)
        # 死叉
        sell_condition = (df['ma_short'] < df['ma_long']) & \
                        (df['ma_short'].shift(1) >= df['ma_long'].shift(1))
        
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        
        return df

# 使用自定义策略
my_strategy = MaiWeiStrategy(ma_short=5, ma_long=20)
signals = my_strategy.generate_signals(data)
```

---

## 回测验证

### 运行回测

```python
# 创建策略
strategy = api.strategy.create('ma_cross', short_window=10, long_window=30)

# 获取数据
data = api.data.get_stock_data('300751', start='2024-01-01', end='2024-12-31')

# 运行回测
result = api.backtest.run(
    strategy=strategy,
    data=data,
    initial_capital=100000,  # 初始资金10万
    commission=0.0003,       # 手续费万3
    slippage=0.001           # 滑点千1
)

# 分析结果
analysis = api.backtest.analyze(result)

print(f"总收益率: {analysis['total_return']*100:.2f}%")
print(f"年化收益率: {analysis['annual_return']*100:.2f}%")
print(f"最大回撤: {analysis['max_drawdown']*100:.2f}%")
print(f"夏普比率: {analysis['sharpe_ratio']:.2f}")
print(f"交易次数: {analysis['total_trades']}")
print(f"胜率: {analysis['win_rate']*100:.2f}%")
```

### 多策略对比

```python
strategies = {
    'MA10/30': api.strategy.create('ma_cross', 10, 30),
    'MA5/20': api.strategy.create('ma_cross', 5, 20),
    'MACD': api.strategy.create('macd'),
}

results = {}
for name, strategy in strategies.items():
    result = api.backtest.run(strategy, data)
    analysis = api.backtest.analyze(result)
    results[name] = analysis

# 对比结果
import pandas as pd
comparison = pd.DataFrame(results).T
print(comparison[['total_return', 'max_drawdown', 'sharpe_ratio']])
```

---

## 机器学习预测

### 训练预测模型

```python
# 获取数据
data = api.data.get_stock_data('300751', start='2023-01-01', end='2024-12-31')

# 计算特征
data = api.factors.compute_all(data)

# 划分训练测试集
train_data = data[data.index < '2024-06-01']
test_data = data[data.index >= '2024-06-01']

# 训练模型
predictor = api.ml.train(
    train_data,
    target='close',
    features=['ma5', 'ma20', 'rsi6', 'macd', 'volume_ratio'],
    model_type='random_forest'
)

# 查看特征重要性
importance = predictor.feature_importance()
print(importance)
```

### 预测与评估

```python
# 预测
predictions = api.ml.predict(predictor, test_data)

# 评估
metrics = api.ml.evaluate(predictor, test_data)
print(f"MSE: {metrics['mse']:.4f}")
print(f"RMSE: {metrics['rmse']:.4f}")
print(f"MAE: {metrics['mae']:.4f}")
print(f"R²: {metrics['r2']:.4f}")

# 可视化预测结果
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(test_data.index, test_data['close'], label='Actual')
plt.plot(test_data.index, predictions, label='Predicted')
plt.title('迈为股份价格预测')
plt.legend()
plt.show()
```

---

## 命令行工具

### 安装后使用

安装完成后，可以使用 `quant` 或 `qa` 命令：

```bash
# 查看版本
quant version

# 获取迈为股份数据
quant data get 300751 --start 2024-01-01 --end 2024-12-31

# 计算技术指标
quant factor ma 300751 --window 20
quant factor macd 300751
quant factor all 300751 --output maiwei_factors.csv

# 运行回测
quant backtest run ma_cross --symbol 300751 --start 2024-01-01 --capital 100000

# 训练ML模型
quant ml train 300751 --model random_forest --days 252
```

### 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `quant data get` | 获取股票数据 | `quant data get 300751 --start 2024-01-01` |
| `quant data query` | 查询数据 | `quant data query 300751 --days 30` |
| `quant data list` | 股票列表 | `quant data list --market sz` |
| `quant factor ma` | 移动平均线 | `quant factor ma 300751 --window 20` |
| `quant factor macd` | MACD指标 | `quant factor macd 300751` |
| `quant factor rsi` | RSI指标 | `quant factor rsi 300751 --window 14` |
| `quant factor all` | 所有指标 | `quant factor all 300751` |
| `quant backtest run` | 运行回测 | `quant backtest run ma_cross --symbol 300751` |
| `quant ml train` | 训练模型 | `quant ml train 300751 --model random_forest` |

---

## API 参考

### QuantAPI

主 API 类，提供所有功能的访问入口。

```python
api = QuantAPI()

# 子模块
api.data      # 数据操作
api.factors   # 因子计算
api.strategy  # 策略开发
api.backtest  # 回测验证
api.ml        # 机器学习
```

### DataAPI

| 方法 | 说明 | 参数 |
|------|------|------|
| `get_stock_data()` | 获取股票数据 | symbol, start, end, period, adjust |
| `get_stock_list()` | 获取股票列表 | market |
| `get_financial_data()` | 获取财务数据 | symbol, report_type |
| `save()` | 保存数据 | data, table |
| `query()` | 查询数据 | table, symbol, start, end |

### FactorAPI

| 方法 | 说明 | 参数 |
|------|------|------|
| `ma()` | 移动平均线 | data, window |
| `ema()` | 指数移动平均 | data, window |
| `macd()` | MACD指标 | data, fast, slow, signal |
| `rsi()` | RSI指标 | data, window |
| `bollinger()` | 布林带 | data, window, std |
| `kdj()` | KDJ指标 | data, n, m1, m2 |
| `compute_all()` | 所有指标（基础版，约30个） | data |
| `compute_all_factors()` | 所有因子（完整版，120+个）⭐ | data |

#### compute_all_factors() 包含的因子

**趋势类因子**
- `ma5/10/20/30/60/120` - 多周期移动平均线
- `ema5/10/20/30/60/120` - 指数移动平均
- `ma5_10_diff`, `ma10_20_diff` - 均线差值
- `ma5_10_ratio`, `ma10_20_ratio` - 均线比值
- `macd`, `macd_signal`, `macd_hist` - MACD指标
- `macd_golden_cross`, `macd_dead_cross` - MACD金叉/死叉信号
- `adx14`, `plus_di14`, `minus_di14` - ADX平均趋向指数
- `tenkan_sen`, `kijun_sen`, `ichimoku_cloud` - 一目均衡表
- `ichimoku_golden_cross` - 一目金叉信号

**动量类因子**
- `rsi6/12/14/24` - 多周期RSI
- `kdj_k`, `kdj_d`, `kdj_j` - KDJ指标
- `kdj_golden_cross` - KDJ金叉信号
- `cci20` - 商品通道指数
- `wr14` - 威廉指标
- `mom10/20` - 动量因子
- `roc10/20` - 变化率

**波动率类因子**
- `boll_upper_20/60`, `boll_middle_20/60`, `boll_lower_20/60` - 布林带
- `boll_width_20/60` - 布林带宽度
- `boll_position_20/60` - 布林带位置
- `atr14/20` - 平均真实波幅
- `atr_ratio_14/20` - ATR比率
- `volatility_5/10/20/60` - 历史波动率
- `dc_upper_20`, `dc_lower_20`, `dc_middle_20`, `dc_width_20` - 唐奇安通道
- `tr` - 真实波幅
- `amplitude`, `amplitude_ma5/10/20` - 振幅因子

**量价类因子**
- `volume_ma5/10/20` - 成交量移动平均
- `volume_ratio` - 量比
- `volume_change` - 成交量变化率
- `price_volume_corr` - 价格成交量相关性
- `obv` - 能量潮
- `mfi14` - 资金流量指标
- `pvt` - 价量趋势
- `turnover` - 换手率
- `amount`, `amount_ma5/10/20` - 成交额
- `amount_change` - 成交额变化率

**形态类因子**
- `upper_shadow`, `lower_shadow` - 上下影线
- `body` - K线实体
- `price_position_20/60` - 价格位置
- `consecutive_up`, `consecutive_down` - 连涨连跌天数

**统计类因子**
- `returns`, `log_returns` - 收益率
- `returns_mean_5/10/20` - 收益率均值
- `returns_std_5/10/20` - 收益率标准差
- `returns_skew_5/10/20` - 收益率偏度
- `returns_kurt_5/10/20` - 收益率峰度
- `drawdown_20/60` - 最大回撤

**复合信号因子**
- `ma_bull` - 均线多头排列
- `ma_bear` - 均线空头排列
- `trend_strength` - 趋势强度
- `momentum5/10/20/60` - 价格动量
- `price_change_5/10/20/60` - 价格变化率

### EFinanceFetcher ⭐

EFinance 数据源，提供细粒度、高时效性数据。

| 方法 | 说明 | 参数 |
|------|------|------|
| `is_available()` | 检查是否可用 | - |
| `get_realtime_quotes()` | 实时行情 | symbols |
| `get_minute_data()` | 分钟级数据 | symbol, period, adjust, start, end |
| `get_tick_data()` | 分笔数据 | symbol, date |
| `get_daily_data()` | 日K数据 | symbol, adjust, start, end |
| `get_intraday_data()` | 当日分时 | symbol, freq |
| `get_stock_list()` | 股票列表 | market |
| `get_financial_data()` | 财务数据 | symbol, report_type |
| `get_sector_data()` | 板块数据 | sector_type |

### BacktestAPI

| 方法 | 说明 | 参数 |
|------|------|------|
| `run()` | 运行回测 | strategy, data, initial_capital, commission, slippage |
| `analyze()` | 分析结果 | result |

### MLAPI

| 方法 | 说明 | 参数 |
|------|------|------|
| `train()` | 训练模型 | data, target, features, model_type |
| `predict()` | 预测 | predictor, data |
| `evaluate()` | 评估模型 | predictor, data, target |

---

## 完整示例：迈为股份策略研究

```python
import quant_assistant as qa
from quant_assistant import QuantAPI
import pandas as pd
import matplotlib.pyplot as plt

# 1. 初始化
api = QuantAPI()

# 2. 获取数据
print("=== 获取迈为股份数据 ===")
data = api.data.get_stock_data(
    symbol='300751',
    start='2024-01-01',
    end='2024-12-31'
)
print(f"获取到 {len(data)} 条数据")

# 3. 计算因子（使用完整版，120+个因子）
print("\n=== 计算所有策略因子 ===")
data = api.factors.compute_all_factors(data)
print(f"共计算 {len(data.columns)} 个因子")

# 查看部分因子
print("\n部分因子预览:")
print(data[['ma5', 'ma20', 'rsi14', 'macd', 'boll_width_20', 'adx14', 'cci20', 'mfi14']].tail())

# 4. 创建策略
print("\n=== 创建策略 ===")
strategy = api.strategy.create('ma_cross', short_window=10, long_window=30)

# 5. 回测
print("\n=== 运行回测 ===")
result = api.backtest.run(
    strategy=strategy,
    data=data,
    initial_capital=100000,
    commission=0.0003
)

# 6. 分析结果
analysis = api.backtest.analyze(result)
print(f"\n回测结果:")
print(f"  总收益率: {analysis['total_return']*100:.2f}%")
print(f"  年化收益: {analysis['annual_return']*100:.2f}%")
print(f"  最大回撤: {analysis['max_drawdown']*100:.2f}%")
print(f"  夏普比率: {analysis['sharpe_ratio']:.2f}")

# 7. 机器学习预测
print("\n=== 训练预测模型 ===")
train_data = data[data.index < '2024-09-01']
test_data = data[data.index >= '2024-09-01']

# 使用更多因子进行机器学习训练
predictor = api.ml.train(
    train_data,
    target='close',
    features=[
        'ma5', 'ma20', 'ma60',
        'rsi6', 'rsi14',
        'macd', 'macd_hist',
        'boll_width_20', 'boll_position_20',
        'adx14', 'cci20',
        'volume_ratio', 'turnover', 'mfi14',
        'mom10', 'roc10'
    ],
    model_type='random_forest'
)

predictions = api.ml.predict(predictor, test_data)
metrics = api.ml.evaluate(predictor, test_data)

print(f"预测结果:")
print(f"  R²: {metrics['r2']:.4f}")
print(f"  RMSE: {metrics['rmse']:.4f}")

# 8. 可视化
plt.figure(figsize=(14, 10))

# 价格和均线
plt.subplot(3, 1, 1)
plt.plot(data.index, data['close'], label='Close')
plt.plot(data.index, data['ma10'], label='MA10', alpha=0.7)
plt.plot(data.index, data['ma30'], label='MA30', alpha=0.7)
plt.title('迈为股份 (300751) - 价格和均线')
plt.legend()

# MACD
plt.subplot(3, 1, 2)
plt.plot(data.index, data['macd'], label='MACD')
plt.plot(data.index, data['macd_signal'], label='Signal')
plt.bar(data.index, data['macd_hist'], label='Histogram', alpha=0.3)
plt.title('MACD')
plt.legend()

# 预测结果
plt.subplot(3, 1, 3)
plt.plot(test_data.index, test_data['close'], label='Actual')
plt.plot(test_data.index, predictions, label='Predicted')
plt.title('机器学习预测')
plt.legend()

plt.tight_layout()
plt.savefig('maiwei_analysis.png', dpi=150)
print("\n分析图表已保存到 maiwei_analysis.png")
```

---

## 常见问题

### Q: 如何获取实时数据？
A: 使用 `api.data.get_stock_data()` 获取最新数据，支持日线、周线、月线。

### Q: 支持哪些技术指标？
A: 支持 MA、EMA、MACD、RSI、布林带、KDJ 等常用指标，可通过 `api.factors.compute_all()` 一键计算。

### Q: 如何保存自定义策略？
A: 继承 `BaseStrategy` 类，实现 `generate_signals()` 方法即可。

### Q: 机器学习模型支持哪些？
A: 支持 Random Forest、Gradient Boosting、Linear Regression 等 sklearn 模型。

### Q: 数据存储在哪里？
A: 默认使用 MySQL 存储，可通过配置修改存储方式。

---

## 更多信息

- GitHub: https://github.com/XiaoBai-learner/quant-assistant
- 问题反馈: https://github.com/XiaoBai-learner/quant-assistant/issues
- 作者: XiaoBai-learner (185890339@qq.com)
