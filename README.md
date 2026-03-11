# Quant Assistant - 个人量化交易软件

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个模块化、可扩展的个人量化交易软件，支持策略研究、回测验证和实盘交易。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    量化交易系统架构                          │
├─────────────────────────────────────────────────────────────┤
│  用户界面层  │  监控面板  │  告警中心                         │
├─────────────────────────────────────────────────────────────┤
│                    API Gateway                              │
├─────────────────────────────────────────────────────────────┤
│  策略研究层  │  回测模拟层  │  实盘交易层                      │
├─────────────────────────────────────────────────────────────┤
│                      风控中心                                │
├─────────────────────────────────────────────────────────────┤
│  数据管理层 (Data Manager) ✅ Phase 1 已完成                  │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │  Fetcher │ Storage  │  Query   │  Cache   │             │
│  │ (AKShare)│ (MySQL)  │ (Engine) │ (Redis)  │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
└─────────────────────────────────────────────────────────────┘
```

## 📦 功能模块

### Phase 1: 数据管理层 ✅ (已完成)
- [x] 多数据源接入 (AKShare)
- [x] MySQL 数据存储
- [x] 统一查询接口
- [x] 数据质量校验
- [x] 命令行工具

**文档**: [src/data/describe.md](src/data/describe.md)

### Phase 2: 策略研究层 ✅ (已完成)
- [x] 策略框架 (BaseStrategy)
- [x] 技术指标库 (MA, MACD, RSI, BOLL, KDJ等)
- [x] 因子计算引擎
- [x] 信号生成器
- [x] 股票筛选器
- [x] 机器学习集成

**文档**: [src/strategy/describe.md](src/strategy/describe.md)

### Phase 2: 回测模拟层 ✅ (已完成)
- [x] 事件驱动回测引擎
- [x] 券商模拟 (订单撮合)
- [x] 投资组合管理
- [x] 绩效分析 (夏普比率、最大回撤等)
- [x] 成本模型 (手续费、滑点、印花税)

**文档**: [src/backtest/describe.md](src/backtest/describe.md)

### Phase 2: 可视化层 ✅ (已完成)
- [x] ASCII K线图
- [x] 技术指标显示
- [x] 数据表格渲染
- [x] 命令行图表工具

**文档**: [src/visualization/describe.md](src/visualization/describe.md)

### Phase 3: 实盘交易层 (规划中)
- [ ] 交易接口
- [ ] 订单管理
- [ ] 风控系统
- [ ] 监控告警

## 🚀 快速开始

### 环境要求
- Python 3.10+
- MySQL 8.0+

### 安装

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

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置数据库连接
DB_HOST=localhost
DB_PORT=3306
DB_USER=quant_user
DB_PASSWORD=your_password
DB_NAME=quant_data
```

### 初始化数据库

```bash
# 创建数据库和用户 (MySQL)
mysql -u root -p
```

```sql
CREATE DATABASE quant_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'quant_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON quant_data.* TO 'quant_user'@'localhost';
FLUSH PRIVILEGES;
```

```bash
# 初始化数据表
python main.py init
```

### 使用

```bash
# 更新股票列表
python main.py update-stocks

# 更新日线数据
python main.py update-daily

# 查询数据
python main.py query --symbol 000001 --days 30

# 显示K线图
python main.py chart --symbol 000001

# 显示周线
python main.py chart --symbol 000001 --period W

# 显示带MACD
python main.py chart --symbol 000001 --macd
```

## 📁 项目结构

```
quant-assistant/
├── README.md                 # 项目说明
├── main.py                   # 主程序入口
├── requirements.txt          # Python依赖
├── .env.example             # 环境变量模板
├── config/                  # 配置文件
│   ├── default.yaml
│   └── production.yaml
├── docs/                    # 文档
│   ├── architecture_design.md
│   ├── data_management_phase1.md
│   ├── strategy_layer_design.md
│   └── ui_layer_design.md
├── src/                     # 源代码
│   ├── core/                # 核心框架
│   │   ├── events.py        # 事件系统
│   │   ├── context.py       # 上下文管理
│   │   └── describe.md      # 模块说明
│   ├── data/                # 数据管理层
│   │   ├── fetcher/         # 数据获取
│   │   ├── storage/         # 数据存储
│   │   ├── query/           # 数据查询
│   │   ├── database/        # 数据库连接
│   │   └── describe.md      # 模块说明
│   ├── strategy/            # 策略层
│   │   ├── base.py          # 策略基类
│   │   ├── factors/         # 因子引擎
│   │   ├── signal_synthesis/# 信号合成
│   │   ├── ml/              # 机器学习
│   │   └── describe.md      # 模块说明
│   ├── backtest/            # 回测层
│   │   ├── engine.py        # 回测引擎
│   │   ├── broker.py        # 券商模拟
│   │   ├── portfolio.py     # 投资组合
│   │   ├── performance.py   # 绩效分析
│   │   └── describe.md      # 模块说明
│   ├── visualization/       # 可视化层
│   │   ├── indicators/      # 技术指标
│   │   ├── layouts/         # 图表布局
│   │   ├── renderers/       # 渲染器
│   │   ├── adapters/        # 数据适配
│   │   └── describe.md      # 模块说明
│   ├── utils/               # 工具模块
│   │   ├── logger.py        # 日志管理
│   │   ├── config.py        # 配置管理
│   │   └── describe.md      # 模块说明
│   └── config.py            # 主配置
└── tests/                   # 测试代码
    ├── test_integration.py  # 集成测试
    ├── test_backtest.py     # 回测测试
    ├── test_strategy.py     # 策略测试
    └── ...
```

## 📊 数据库设计

### 核心表

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| stocks | 股票基础信息 | symbol, name, exchange, industry |
| daily_quotes | 日线行情 | open, high, low, close, volume |
| financial_indicators | 财务指标 | eps, roe, revenue, net_profit |
| trade_calendar | 交易日历 | trade_date, is_trading_day |
| update_logs | 更新日志 | table_name, record_count, status |

## 📚 文档

### 使用手册

📖 **[使用手册 (USER_GUIDE.md)](docs/USER_GUIDE.md)** - 完整的使用指南，包含：
- 快速开始
- 数据管理（获取、存储、查询、校验、缓存）
- 策略开发（创建策略、因子、组合、优化）
- 回测验证（事件驱动、向量化、风控、绩效分析）
- 高级功能（依赖注入、事件系统）
- API参考
- 常见问题

### 模块文档

| 模块 | 文档 | 说明 |
|------|------|------|
| Core | [src/core/describe.md](src/core/describe.md) | 事件系统、上下文管理、依赖注入 |
| Data | [src/data/describe.md](src/data/describe.md) | 数据获取、存储、查询 |
| Strategy | [src/strategy/describe.md](src/strategy/describe.md) | 策略框架、因子、信号 |
| Backtest | [src/backtest/describe.md](src/backtest/describe.md) | 回测引擎、绩效分析 |
| Visualization | [src/visualization/describe.md](src/visualization/describe.md) | 图表渲染、技术指标 |
| Utils | [src/utils/describe.md](src/utils/describe.md) | 日志、配置 |

## 🛠️ 开发路线图

### Phase 1: 基础版 ✅
- [x] 数据管理层
- [x] CLI 工具
- [x] 基础架构

### Phase 2: 策略版 ✅
- [x] 策略框架
- [x] 技术指标
- [x] 回测引擎（事件驱动 + 向量化）
- [x] 真实撮合引擎
- [x] 风控管理
- [x] 绩效分析
- [x] 策略参数优化
- [x] 策略组合
- [x] 多级缓存
- [x] 依赖注入

### Phase 3: 实盘版 (规划中)
- [ ] 交易接口（⚠️ 当前不支持）
- [ ] 自动订单执行（⚠️ 当前不支持）
- [ ] 实时监控（⚠️ 当前不支持）

### Phase 4: 平台版 (规划中)
- [ ] Web 前端（⚠️ 当前不支持）
- [ ] 分布式回测（⚠️ 当前不支持）
- [ ] 强化学习策略（⚠️ 当前不支持）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

[MIT License](LICENSE)

## 👤 作者

**XiaoBai-learner**
- GitHub: [@XiaoBai-learner](https://github.com/XiaoBai-learner)
- Email: 185890339@qq.com

---

> ⚠️ **风险提示**: 量化交易涉及金融风险，本软件仅供学习研究使用，不构成投资建议。
