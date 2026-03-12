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

### 计算所有指标

```python
# 一键计算所有技术指标
data_with_factors = api.factors.compute_all(data)

print(data_with_factors.columns)
# 输出: ['open', 'high', 'low', 'close', 'volume', 
#        'ma5', 'ma10', 'ma20', 'ma60', 
#        'ema12', 'ema26', 'macd', 'macd_signal', ...]
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
| `compute_all()` | 所有指标 | data |

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

# 3. 计算因子
print("\n=== 计算技术指标 ===")
data = api.factors.compute_all(data)
print("指标计算完成")

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

predictor = api.ml.train(
    train_data,
    target='close',
    features=['ma5', 'ma20', 'rsi6', 'macd', 'volume_ratio'],
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
