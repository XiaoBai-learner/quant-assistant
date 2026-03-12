# Backtest 回测层

## 模块概述

回测层提供完整的策略回测验证功能，支持事件驱动和向量化两种回测模式。包含券商模拟、订单撮合、持仓管理和绩效分析，能够真实模拟交易环境。

## 架构图

```
历史数据
    ↓
回测引擎 (BacktestEngine)
    ↓
策略执行 (BaseStrategy.on_bar)
    ↓
信号生成 (Signal)
    ↓
订单提交 (Broker.submit_order)
    ↓
订单撮合 (Broker.execute_order)
    ↓
持仓更新 (Portfolio)
    ↓
绩效分析 (PerformanceAnalyzer)
```

## 子模块说明

### engine.py - 回测引擎

**功能**: 事件驱动的回测核心

**核心类**:
- `BacktestMode`: 回测模式枚举
  - `EVENT_DRIVEN`: 事件驱动模式
  - `VECTORIZED`: 向量化模式

- `BacktestConfig`: 回测配置
  - 属性: start_date, end_date, initial_cash
  - 成本: commission_rate (万2.5), slippage (0.1%), stamp_duty (0.1%)
  - 风控: max_position_pct, max_drawdown_limit
  - 模式: mode, benchmark, log_level

- `BacktestEngine`: 回测引擎
  - `__init__(config)`: 初始化
  - `set_strategy(strategy)`: 设置策略
  - `load_data(symbol, data)`: 加载历史数据
  - `run()`: 运行回测
  - `get_results()`: 获取回测结果
  - `get_trades()`: 获取交易记录
  - `get_daily_records()`: 获取每日记录

**回测流程**:
1. 加载历史数据
2. 设置策略
3. 逐日推进
4. 处理每根K线
5. 执行策略逻辑
6. 撮合订单
7. 更新持仓
8. 生成绩效报告

**使用示例**:
```python
from src.backtest import BacktestEngine, BacktestConfig
from src.strategy import MyStrategy

config = BacktestConfig(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31),
    initial_cash=100000.0
)

engine = BacktestEngine(config)
engine.set_strategy(MyStrategy())
engine.load_data('000001', df)
results = engine.run()

print(f"总收益: {results['total_return']:.2%}")
print(f"夏普比率: {results['sharpe_ratio']:.2f}")
```

### broker.py - 券商模拟

**功能**: 订单管理和撮合执行

**核心类**:
- `OrderType`: 订单类型
  - `MARKET`: 市价单
  - `LIMIT`: 限价单
  - `STOP`: 止损单
  - `STOP_LIMIT`: 止损限价单

- `OrderSide`: 订单方向
  - `BUY`: 买入
  - `SELL`: 卖出

- `OrderStatus`: 订单状态
  - `PENDING`: 待提交
  - `SUBMITTED`: 已提交
  - `PARTIAL_FILLED`: 部分成交
  - `FILLED`: 全部成交
  - `CANCELLED`: 已撤销
  - `REJECTED`: 已拒绝

- `Order`: 订单对象
  - 属性: symbol, side, order_type, volume, price, stop_price, limit_price
  - 状态: order_id, status, filled_volume, filled_amount, created_at
  - `remaining_volume()`: 剩余未成交数量
  - `is_filled()`: 是否全部成交

- `Trade`: 成交记录
  - 属性: symbol, side, volume, price, amount, timestamp, order_id, trade_id

- `Broker`: 券商模拟
  - `submit_order(order)`: 提交订单
  - `execute_order(order, bar)`: 执行订单撮合
  - `cancel_order(order_id)`: 撤销订单
  - `get_orders()`: 获取所有订单
  - `get_trades()`: 获取所有成交

**撮合规则**:
- 市价单: 以当前bar的close价格成交
- 限价单: 价格在low-high范围内成交
- 考虑滑点: 买入+滑点，卖出-滑点
- 考虑手续费: 买入时扣除

### portfolio.py - 投资组合

**功能**: 持仓和资金管理

**核心类**:
- `Portfolio`: 投资组合
  - 属性: initial_cash, cash, positions, trades
  - `update_position(symbol, volume, price)`: 更新持仓
  - `get_position(symbol)`: 获取持仓
  - `get_position_value(symbol, price)`: 获取持仓市值
  - `get_total_value(prices)`: 获取总资产
  - `get_returns()`: 获取收益率
  - `can_trade(symbol, volume, price)`: 检查是否可交易

**持仓计算**:
- 多头持仓: volume > 0
- 空头持仓: volume < 0
- 持仓市值: position * price
- 总资产: cash + sum(持仓市值)

### performance.py - 绩效分析

**功能**: 回测结果分析和指标计算

**核心类**:
- `PerformanceAnalyzer`: 绩效分析器
  - `calculate_returns(daily_records)`: 计算收益率
  - `calculate_sharpe(returns, risk_free_rate)`: 计算夏普比率
  - `calculate_max_drawdown(returns)`: 计算最大回撤
  - `calculate_volatility(returns)`: 计算波动率
  - `calculate_win_rate(trades)`: 计算胜率
  - `generate_report(results)`: 生成完整报告

**绩效指标**:
- 总收益率: (最终价值 - 初始资金) / 初始资金
- 年化收益率: 总收益率 / 年数
- 夏普比率: (年化收益 - 无风险收益) / 年化波动率
- 最大回撤: 峰值到谷底的最大跌幅
- 胜率: 盈利交易数 / 总交易数
- 盈亏比: 平均盈利 / 平均亏损
- 卡尔玛比率: 年化收益 / 最大回撤

**报告内容**:
```python
{
    'total_return': 0.25,        # 总收益率 25%
    'annual_return': 0.25,       # 年化收益率
    'sharpe_ratio': 1.5,         # 夏普比率
    'max_drawdown': -0.15,       # 最大回撤 -15%
    'volatility': 0.20,          # 波动率 20%
    'win_rate': 0.55,            # 胜率 55%
    'profit_factor': 1.8,        # 盈亏比
    'total_trades': 100,         # 总交易次数
    'avg_trade_return': 0.002    # 单次平均收益
}
```

## 接口汇总

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| BacktestEngine.set_strategy | strategy | - | 设置策略 |
| BacktestEngine.load_data | symbol, df | - | 加载数据 |
| BacktestEngine.run | - | dict | 运行回测 |
| Broker.submit_order | Order | bool | 提交订单 |
| Broker.execute_order | Order, bar | List[Trade] | 撮合订单 |
| Portfolio.update_position | symbol, volume, price | - | 更新持仓 |
| Portfolio.get_total_value | prices | float | 总资产 |
| PerformanceAnalyzer.generate_report | results | dict | 生成报告 |

## 成本模型

默认交易成本:
- 手续费: 万2.5 (买入卖出都收)
- 滑点: 0.1% (买入+滑点，卖出-滑点)
- 印花税: 0.1% (仅卖出)

## 风控配置

- 最大仓位比例: 默认100%
- 最大回撤限制: 默认20%
