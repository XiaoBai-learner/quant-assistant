# Quant Assistant 使用手册

> 本手册涵盖数据管理、策略开发、回测验证等核心功能  
> 不包含实盘交易和可视化功能（请参考其他文档）

---

## 目录

1. [快速开始](#1-快速开始)
2. [数据管理](#2-数据管理)
3. [策略开发](#3-策略开发)
4. [回测验证](#4-回测验证)
5. [高级功能](#5-高级功能)
6. [API参考](#6-api参考)
7. [常见问题](#7-常见问题)

---

## 1. 快速开始

### 1.1 环境准备

```bash
# 克隆项目
git clone https://github.com/XiaoBai-learner/quant-assistant.git
cd quant-assistant

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 1.2 数据库配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
DB_HOST=localhost
DB_PORT=3306
DB_USER=quant_user
DB_PASSWORD=your_password
DB_NAME=quant_data
```

```bash
# 创建数据库
mysql -u root -p
```

```sql
CREATE DATABASE quant_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'quant_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON quant_data.* TO 'quant_user'@'localhost';
FLUSH PRIVILEGES;
```

### 1.3 初始化系统

```python
from src.data import DataQueryEngine
from src.config_manager import get_config

# 初始化配置
config = get_config()
print(f"数据库: {config.database.connection_string}")

# 测试数据库连接
from src.data.database import db_manager
if db_manager.test_connection():
    print("✅ 数据库连接成功")
else:
    print("❌ 数据库连接失败")
```

---

## 2. 数据管理

### 2.1 数据获取

```python
from src.data import AKShareFetcher

# 创建获取器
fetcher = AKShareFetcher()

# 获取股票列表
stocks = fetcher.get_stock_list()
print(f"获取到 {len(stocks)} 只股票")

# 获取日线数据
df = fetcher.get_daily_quotes(
    symbol='000001',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
print(f"获取到 {len(df)} 条数据")
```

### 2.2 增量更新（推荐）

```python
from src.data import AKShareFetcher, MySQLStorage

fetcher = AKShareFetcher()
storage = MySQLStorage()

# 获取最后更新日期
last_date = storage.get_last_update_date('000001')

# 增量获取新数据
new_data = fetcher.get_daily_quotes_incremental(
    symbol='000001',
    last_date=last_date
)

if not new_data.empty:
    storage.save_daily_quotes(new_data)
    print(f"新增 {len(new_data)} 条数据")
else:
    print("数据已是最新")
```

### 2.3 数据校验

```python
from src.data import DataValidator

validator = DataValidator()

# 校验价格数据
result = validator.validate_price_data(df)

if result.is_valid:
    print("✅ 数据校验通过")
else:
    print(f"❌ 发现 {result.failed_count} 个问题:")
    for check in result.get_failed_checks():
        print(f"  - {check.name}: {check.message}")
```

### 2.4 数据查询（带缓存）

```python
from src.data import DataQueryEngine, DataCache

# 创建带缓存的查询引擎
cache = DataCache(memory_ttl=60, redis_ttl=300)
query = DataQueryEngine(cache=cache)

# 查询价格数据（自动缓存）
df = query.get_price_data(
    symbol='000001',
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 查询最新价格（短缓存）
latest = query.get_latest_price('000001')
print(f"最新价格: {latest['close']}")

# 查看缓存统计
stats = cache.get_stats()
print(f"L1命中率: {stats['l1']['hit_rate']:.2%}")
```

### 2.5 批量数据更新

```python
from src.data import AKShareFetcher, MySQLStorage

fetcher = AKShareFetcher()
storage = MySQLStorage()

# 股票列表
symbols = ['000001', '000002', '600000', '600519']

# 批量更新
for symbol in symbols:
    try:
        df = fetcher.get_daily_quotes_incremental(symbol)
        if not df.empty:
            storage.save_daily_quotes(df, validate=True)
            print(f"✅ {symbol}: 更新 {len(df)} 条")
    except Exception as e:
        print(f"❌ {symbol}: {e}")
```

---

## 3. 策略开发

### 3.1 创建简单策略

```python
from src.strategy.base import BaseStrategy, Bar, Signal, SignalType
from typing import Optional

class MAStrategy(BaseStrategy):
    """
    双均线策略
    短期均线上穿长期均线买入，下穿卖出
    """
    
    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        super().__init__(name="MA_Cross")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prices = []
    
    def on_init(self, context):
        """初始化"""
        print(f"策略初始化: 快MA={self.fast_period}, 慢MA={self.slow_period}")
    
    def on_bar(self, bar: Bar) -> Optional[Signal]:
        """处理K线"""
        self.prices.append(bar.close)
        
        # 数据不足
        if len(self.prices) < self.slow_period:
            return None
        
        # 计算均线
        fast_ma = sum(self.prices[-self.fast_period:]) / self.fast_period
        slow_ma = sum(self.prices[-self.slow_period:]) / self.slow_period
        
        # 判断交叉
        if len(self.prices) > self.slow_period:
            prev_fast = sum(self.prices[-self.fast_period-1:-1]) / self.fast_period
            prev_slow = sum(self.prices[-self.slow_period-1:-1]) / self.slow_period
            
            # 金叉
            if prev_fast <= prev_slow and fast_ma > slow_ma:
                return self.buy(bar.symbol, bar.close, 100)
            
            # 死叉
            if prev_fast >= prev_slow and fast_ma < slow_ma:
                position = self.context.get_position(bar.symbol)
                if position > 0:
                    return self.sell(bar.symbol, bar.close, position)
        
        return None
```

### 3.2 使用因子引擎

```python
from src.strategy.factors import FactorEngine

# 创建因子引擎
engine = FactorEngine()

# 计算技术指标
factors = engine.calculate(df, ['MA5', 'MA10', 'MACD', 'RSI'])

# 获取因子值
ma5 = factors['MA5'].values
macd = factors['MACD'].values

print(f"MA5: {ma5.iloc[-1]:.2f}")
print(f"MACD: {macd.iloc[-1]:.2f}")
```

### 3.3 策略组合

```python
from src.strategy.composite import CompositeStrategy
from src.strategy.examples.ma_strategy import MAStrategy

# 创建子策略
strategy1 = MAStrategy(fast_period=5, slow_period=20)
strategy2 = MAStrategy(fast_period=10, slow_period=30)

# 创建组合策略
composite = CompositeStrategy(
    name="MA_Composite",
    strategies=[
        CompositeStrategy.StrategyWeight(strategy1, weight=0.6),
        CompositeStrategy.StrategyWeight(strategy2, weight=0.4)
    ],
    combination_method='weighted_sum'  # 加权求和
)

# 使用组合策略回测
engine.set_strategy(composite)
```

### 3.4 策略参数优化

```python
from src.strategy.optimizer import StrategyOptimizer
from src.backtest.engine import BacktestConfig

# 准备数据
query = DataQueryEngine()
df = query.get_price_data('000001', '2024-01-01', '2024-06-30')

# 回测配置
config = BacktestConfig(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 6, 30)
)

# 创建优化器
optimizer = StrategyOptimizer(
    strategy_class=MAStrategy,
    data=df,
    config=config,
    objective='sharpe_ratio'
)

# 网格搜索
param_grid = {
    'fast_period': [5, 10, 15],
    'slow_period': [20, 30, 60]
}

result = optimizer.grid_search(param_grid, n_jobs=4)

print(f"最佳参数: {result.best_params}")
print(f"最佳夏普比率: {result.best_score:.2f}")
```

### 3.5 前向优化（避免过拟合）

```python
from src.strategy.optimizer import WalkForwardOptimizer

# 创建前向优化器
wf_optimizer = WalkForwardOptimizer(
    strategy_class=MAStrategy,
    data=df,
    config=config,
    train_size=252,  # 训练期：1年
    test_size=63,    # 测试期：1季度
    objective='sharpe_ratio'
)

# 执行前向优化
result = wf_optimizer.optimize(param_grid, n_splits=5)

print(f"最佳参数: {result['best_params']}")
print(f"平均测试得分: {result['avg_test_score']:.2f}")
```

---

## 4. 回测验证

### 4.1 事件驱动回测

```python
from src.backtest import BacktestEngine, BacktestConfig
from datetime import date

# 回测配置
config = BacktestConfig(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31),
    initial_cash=100000.0,
    commission_rate=0.00025,  # 万2.5
    slippage=0.001,           # 0.1%
    stamp_duty=0.001          # 0.1%
)

# 创建引擎
engine = BacktestEngine(config)

# 设置策略
strategy = MAStrategy(fast_period=5, slow_period=20)
engine.set_strategy(strategy)

# 加载数据
engine.load_data('000001', df)

# 运行回测
result = engine.run()

# 查看结果
metrics = result['metrics']
print(f"总收益: {metrics['total_return']:.2%}")
print(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
print(f"最大回撤: {metrics['max_drawdown']:.2%}")
```

### 4.2 向量化回测（快速）

```python
from src.backtest import VectorizedBacktestEngine

# 创建向量化引擎
engine = VectorizedBacktestEngine(config)

# 生成信号（示例：双均线）
df['ma_fast'] = df['close'].rolling(window=5).mean()
df['ma_slow'] = df['close'].rolling(window=20).mean()
signals = pd.Series(0, index=df.index)
signals[df['ma_fast'] > df['ma_slow']] = 1
signals[df['ma_fast'] < df['ma_slow']] = -1

# 运行回测
result = engine.run(df, signals)

print(f"总收益: {result.metrics['total_return']:.2%}")
print(f"夏普比率: {result.metrics['sharpe_ratio']:.2f}")
```

### 4.3 使用真实撮合引擎

```python
from src.backtest import BacktestEngine
from src.backtest.realistic_broker import RealisticBroker

# 创建真实撮合引擎
broker = RealisticBroker(config, market_impact=0.0001)

# 创建回测引擎（注入真实撮合）
engine = BacktestEngine(
    config=config,
    broker=broker
)

# 运行回测
result = engine.run()

# 查看订单簿
order_book = broker.get_order_book('000001')
print(f"买一: {order_book.best_bid().price}")
print(f"卖一: {order_book.best_ask().price}")
```

### 4.4 风控管理

```python
from src.risk import RiskManager

# 创建风控管理器
risk_manager = RiskManager(
    max_position_pct=0.8,      # 最大仓位80%
    max_single_position_pct=0.3,  # 单股最大30%
    max_daily_loss_pct=0.05,   # 单日最大亏损5%
    max_drawdown_pct=0.2,      # 最大回撤20%
    min_cash_reserve=0.1       # 最小现金储备10%
)

# 在回测引擎中使用
engine = BacktestEngine(
    config=config,
    risk_manager=risk_manager
)

# 风控会自动检查每笔订单
```

### 4.5 绩效分析

```python
from src.backtest import PerformanceAnalyzer

# 创建分析器
analyzer = PerformanceAnalyzer()

# 计算指标
metrics = analyzer.calculate_metrics(
    daily_records=daily_df,
    trade_records=trade_df
)

# 打印关键指标
print("【收益指标】")
print(f"  总收益率: {metrics['total_return']:.2%}")
print(f"  年化收益率: {metrics['annual_return']:.2%}")
print(f"  年化波动率: {metrics['volatility']:.2%}")

print("【风险指标】")
print(f"  最大回撤: {metrics['max_drawdown']:.2%}")
print(f"  最大回撤持续时间: {metrics['max_drawdown_duration']} 天")
print(f"  VaR(95%): {metrics['var_95']:.2%}")

print("【风险调整收益】")
print(f"  夏普比率: {metrics['sharpe_ratio']:.2f}")
print(f"  索提诺比率: {metrics['sortino_ratio']:.2f}")
print(f"  卡玛比率: {metrics['calmar_ratio']:.2f}")
print(f"  信息比率: {metrics['information_ratio']:.2f}")

# 生成报告
report = analyzer.generate_report(metrics, output_path='report.txt')
print(report)
```

---

## 5. 高级功能

### 5.1 依赖注入

```python
from src.core import get_container, register_type, resolve
from src.core.interfaces import IBroker, IPortfolio

# 注册自定义实现
from my_broker import MyBroker
register_type(IBroker, MyBroker)

# 自动解析依赖
broker = resolve(IBroker)

# 创建引擎
engine = BacktestEngine(
    config=config,
    broker=broker
)
```

### 5.2 事件系统

```python
from src.core import EventBus, EventType, Event

# 获取事件总线
bus = EventBus()

# 订阅事件
def on_signal(event):
    print(f"收到信号: {event.data}")

bus.subscribe(EventType.SIGNAL_GENERATED, on_signal)

# 发送事件
event = Event(
    type=EventType.SIGNAL_GENERATED,
    data={'symbol': '000001', 'signal': 'BUY'},
    source='MyStrategy'
)
bus.emit(event)
```

### 5.3 自定义异常处理

```python
from src.core.exceptions import DataException, StrategyException

try:
    df = fetcher.get_daily_quotes('000001')
    if df.empty:
        raise DataException("数据为空", symbol='000001')
except DataException as e:
    print(f"数据错误 [{e.code}]: {e.message}")
    print(f"详情: {e.details}")
```

---

## 6. API参考

### 6.1 数据管理API

| 类/函数 | 说明 | 示例 |
|---------|------|------|
| `AKShareFetcher` | 数据获取器 | `fetcher = AKShareFetcher()` |
| `MySQLStorage` | 数据存储 | `storage = MySQLStorage()` |
| `DataQueryEngine` | 数据查询 | `query = DataQueryEngine()` |
| `DataValidator` | 数据校验 | `validator = DataValidator()` |
| `DataCache` | 数据缓存 | `cache = DataCache()` |

### 6.2 策略API

| 类/函数 | 说明 | 示例 |
|---------|------|------|
| `BaseStrategy` | 策略基类 | `class MyStrategy(BaseStrategy)` |
| `CompositeStrategy` | 组合策略 | `composite = CompositeStrategy(...)` |
| `StrategyOptimizer` | 参数优化 | `optimizer = StrategyOptimizer(...)` |
| `FactorEngine` | 因子引擎 | `engine = FactorEngine()` |

### 6.3 回测API

| 类/函数 | 说明 | 示例 |
|---------|------|------|
| `BacktestEngine` | 事件驱动回测 | `engine = BacktestEngine(config)` |
| `VectorizedBacktestEngine` | 向量化回测 | `engine = VectorizedBacktestEngine(config)` |
| `RealisticBroker` | 真实撮合 | `broker = RealisticBroker(config)` |
| `RiskManager` | 风控管理 | `risk = RiskManager(...)` |
| `PerformanceAnalyzer` | 绩效分析 | `analyzer = PerformanceAnalyzer()` |

---

## 7. 常见问题

### Q1: 数据库连接失败？

```python
# 检查配置
from src.config_manager import get_config
config = get_config()
print(config.database.connection_string)

# 测试连接
from src.data.database import db_manager
print(db_manager.test_connection())
```

### Q2: 如何添加新的数据源？

```python
from src.data.fetcher.base_fetcher import BaseDataFetcher

class MyFetcher(BaseDataFetcher):
    def get_daily_quotes(self, symbol, start_date, end_date):
        # 实现数据获取逻辑
        pass

# 注册到容器
from src.core import register_type
from src.core.interfaces import IDataFetcher
register_type(IDataFetcher, MyFetcher)
```

### Q3: 如何保存回测结果？

```python
import json

# 保存结果
with open('backtest_result.json', 'w') as f:
    json.dump(result['metrics'], f, indent=2)

# 保存交易记录
result['trades'].to_csv('trades.csv', index=False)
```

### Q4: 如何调试策略？

```python
# 使用小数据集测试
df_small = df.head(100)

# 打印调试信息
class DebugStrategy(BaseStrategy):
    def on_bar(self, bar):
        print(f"Bar: {bar.timestamp}, Close: {bar.close}")
        # ... 策略逻辑
```

---

## 附录：不支持的功能

以下功能在复盘报告中提到，但**当前版本不支持**：

| 功能 | 说明 | 计划版本 |
|------|------|----------|
| 实盘交易接口 | 连接真实券商API | v3.0 |
| 实时监控面板 | Web界面实时显示 | v3.0 |
| 自动交易执行 | 自动化订单执行 | v3.0 |
| 分布式回测 | 多机器并行回测 | v4.0 |
| 强化学习策略 | RL-based策略 | v4.0 |

---

**文档版本**: v1.5  
**最后更新**: 2026-03-11  
**作者**: XiaoBai-learner
