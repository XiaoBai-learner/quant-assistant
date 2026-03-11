# Strategy 策略层

## 模块概述

策略层提供完整的量化策略开发框架，包括策略基类、因子计算、信号生成和机器学习集成。支持事件驱动的策略执行和灵活的规则配置。

## 架构图

```
行情数据
    ↓
因子计算 (FactorEngine)
    ↓
信号生成 (SignalGenerator)
    ↓
策略执行 (BaseStrategy)
    ↓
交易信号 (Signal)
```

## 子模块说明

### base.py - 策略基类

**功能**: 定义策略开发的基础框架

**核心类**:
- `SignalType`: 信号类型枚举 (BUY=1, SELL=-1, HOLD=0)

- `Signal`: 交易信号
  - 属性: symbol, signal_type, price, volume, timestamp, strength, source, metadata

- `Bar`: K线数据
  - 属性: symbol, timestamp, open, high, low, close, volume, amount

- `StrategyContext`: 策略上下文
  - 属性: cash, positions, current_time, current_symbol, user_data, signals, trades
  - `get_position(symbol)`: 获取持仓
  - `set_position(symbol, volume)`: 设置持仓
  - `add_signal(signal)`: 添加信号

- `BaseStrategy`: 策略基类（抽象类）
  - `__init__(name, params)`: 初始化
  - `init(context)`: 初始化策略
  - `on_init(context)`: 策略初始化（子类实现）
  - `on_bar(bar)`: K线处理（子类实现）
  - `on_signal(signal)`: 信号处理
  - `buy(symbol, price, volume, **kwargs)`: 生成买入信号
  - `sell(symbol, price, volume, **kwargs)`: 生成卖出信号
  - `get_param(key, default)`: 获取参数
  - `set_param(key, value)`: 设置参数

**使用示例**:
```python
from src.strategy import BaseStrategy, Bar, Signal

class MyStrategy(BaseStrategy):
    def on_init(self, context):
        self.ma_period = self.get_param('ma_period', 20)
    
    def on_bar(self, bar: Bar) -> Signal:
        # 策略逻辑
        if bar.close > bar.open:
            return self.buy(bar.symbol, bar.close, 100)
        return None
```

### factors/ - 因子引擎

**功能**: 因子计算、管理和质量检查

**核心类**:
- `Factor`: 因子基类
  - `calculate(df)`: 计算因子值
  - `name`: 因子名称
  - `params`: 因子参数

- `FactorResult`: 因子计算结果
  - 属性: name, values, params, metadata

- `FactorEngine`: 因子计算引擎
  - `calculate(df, factor_names)`: 批量计算因子
  - `calculate_single(df, factor_name, params)`: 计算单个因子
  - `quality_check(result)`: 因子质量检查
  - `get_factor_values(results)`: 合并因子结果为DataFrame
  - `register_builtin_factors()`: 注册内置因子

**内置因子** (technical.py):
- `MAFactor`: 移动平均线
- `EMAFactor`: 指数移动平均
- `MACDFactor`: MACD指标
- `RSIFactor`: 相对强弱指数
- `BOLLFactor`: 布林带
- `KDJFactor`: KDJ指标
- `ATRFactor`: 平均真实波幅
- `OBVFactor`: 能量潮

**使用示例**:
```python
from src.strategy.factors import FactorEngine

engine = FactorEngine()
engine.register_builtin_factors()
results = engine.calculate(df, ['MA5', 'MA10', 'MACD'])
```

### signal_synthesis/ - 信号合成

**功能**: 基于规则生成交易信号

**核心类**:
- `SignalType`: 信号类型 (BUY, SELL, HOLD, STRONG_BUY, STRONG_SELL)

- `TradeSignal`: 交易信号
  - 属性: symbol, signal_type, timestamp, price, confidence, strategy_name, metadata
  - `to_dict()`: 转换为字典

- `SignalGenerator`: 信号生成器
  - `add_buy_rule(rule)`: 添加买入规则
  - `add_sell_rule(rule)`: 添加卖出规则
  - `generate_signals(symbol, factor_data, price_data, timestamp)`: 生成信号
  - `evaluate_signals(signals, price_data)`: 评估信号质量

- `StrategyRule`: 策略规则
  - 属性: name, condition, weight, logic_op
  - `evaluate(factor_data)`: 评估规则

- `StockSelector`: 股票筛选器
  - `add_filter(name, condition)`: 添加筛选条件
  - `select(factor_data)`: 执行筛选
  - `rank(factor_data, factor_name, ascending)`: 排序

**使用示例**:
```python
from src.strategy.signal_synthesis import SignalGenerator, StrategyRule

generator = SignalGenerator()
generator.add_buy_rule(StrategyRule('MA金叉', lambda d: d['MA5'] > d['MA10']))
signals = generator.generate_signals('000001', factor_data, price_data)
```

### ml/ - 机器学习

**功能**: 机器学习预测集成

**核心类**:
- `FeatureEngineer`: 特征工程
  - `create_features(df)`: 创建特征
  - `create_lag_features(df, lags)`: 创建滞后特征
  - `create_rolling_features(df, windows)`: 创建滚动特征

- `MLModel`: ML模型包装器
  - `train(X, y)`: 训练模型
  - `predict(X)`: 预测
  - `evaluate(X, y)`: 评估
  - `save(path)`: 保存模型
  - `load(path)`: 加载模型

- `StockPredictor`: 股票预测器
  - `prepare_data(symbol, start, end)`: 准备数据
  - `train(lookback, horizon)`: 训练
  - `predict(symbol)`: 预测
  - `backtest(start, end)`: 回测

## 接口汇总

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| BaseStrategy.on_bar | Bar | Signal/None | K线处理 |
| BaseStrategy.buy | symbol, price, volume | Signal | 买入信号 |
| FactorEngine.calculate | df, factor_names | Dict[str, FactorResult] | 批量计算因子 |
| SignalGenerator.generate_signals | symbol, factor_data, price_data | List[TradeSignal] | 生成信号 |
| StockSelector.select | factor_data | List[str] | 股票筛选 |
| StockPredictor.predict | symbol | dict | 价格预测 |
