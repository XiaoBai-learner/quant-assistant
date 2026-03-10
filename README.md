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

### Phase 2: 策略研究层 (开发中)
- [ ] 策略框架
- [ ] 技术指标库
- [ ] 回测引擎
- [ ] 绩效分析

### Phase 3: 实盘交易层 (规划中)
- [ ] 交易接口
- [ ] 订单管理
- [ ] 风控系统
- [ ] 监控告警

## 🚀 快速开始

### 环境要求
- Python 3.10+
- MySQL 8.0+
- Redis 7.0+ (可选)

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
```

## 📁 项目结构

```
quant-assistant/
├── README.md
├── docs/                      # 文档
│   ├── architecture_design.md # 架构设计
│   └── data_management_phase1.md
├── config/                    # 配置文件
│   ├── default.yaml
│   └── production.yaml
├── src/                       # 源代码
│   ├── core/                  # 核心框架
│   ├── data/                  # 数据管理层 ✅
│   ├── strategy/              # 策略层
│   ├── backtest/              # 回测层
│   ├── trading/               # 交易层
│   ├── risk/                  # 风控层
│   └── utils/                 # 工具模块
├── tests/                     # 测试代码
├── scripts/                   # 脚本工具
└── requirements.txt           # 依赖包
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

## 🛠️ 开发路线图

### Phase 1: 基础版 ✅
- [x] 数据管理层
- [x] CLI 工具
- [x] 基础架构

### Phase 2: 策略版
- [ ] 策略框架
- [ ] 技术指标
- [ ] 回测引擎
- [ ] 绩效分析

### Phase 3: 实盘版
- [ ] 交易接口
- [ ] 风控系统
- [ ] 订单管理
- [ ] 监控告警

### Phase 4: 平台版
- [ ] Web 前端
- [ ] 多策略管理
- [ ] 用户系统
- [ ] 可视化面板

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
