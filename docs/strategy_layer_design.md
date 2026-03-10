# 策略研究层设计文档

## 文档信息
- **版本**: v1.0.0
- **日期": 2026-03-10
- **模块": Strategy Layer (策略研究层)
- **依赖**: 数据管理层 (Phase 1 ✅), 用户界面层 (Phase 2 ✅)

---

## 一、架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    策略研究层 (Strategy Layer)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Factor     │  │  Machine     │  │  Evolution   │          │
│  │   Mining     │  │  Learning    │  │  Algorithm   │          │
│  │  (因子挖掘)   │  │  (机器学习)   │  │  (进化算法)   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           │                                    │
│                           ▼                                    │
│              ┌─────────────────────┐                          │
│  ┌───────────┤   Signal Synthesis  ├───────────┐              │
│  │           │   (信号合成)         │           │              │
│  │           └─────────────────────┘           │              │
│  │                                             │              │
│  │  ┌──────────────┐  ┌──────────────┐        │              │
│  │  │   Factor     │  │   Model      │        │              │
│  │  │   Library    │  │   Registry   │        │              │
│  │  │  (因子库)     │  │  (模型库)     │        │              │
│  │  └──────────────┘  └──────────────┘        │              │
│  │                                             │              │
│  └─────────────────────────────────────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Data Manager      │
                    │   (Phase 1 ✅)      │
                    └─────────────────────┘
```

### 1.2 工作包划分

| 工作包 | 模块 | 职责 | 输出 |
|--------|------|------|------|
| WP1 | Factor Mining | 因子挖掘与计算 | factor_mining/ |
| WP2 | ML Prediction | 机器学习预测 | ml_prediction/ |
| WP3 | Evolution Algorithm | 进化算法策略挖掘 | evolution/ |
| WP4 | Signal Synthesis | 信号合成 | signal_synthesis/ |
| WP5 | Strategy Base | 策略基类与框架 | strategy/ |

### 1.3 模块依赖关系

```
WP5 (Strategy Base)
    ├── WP1 (Factor Mining)
    │       └── Data Manager
    ├── WP2 (ML Prediction)
    │       └── WP1
    ├── WP3 (Evolution Algorithm)
    │       └── WP1
    └── WP4 (Signal Synthesis)
            ├── WP2
            ├── WP3
            └── WP1
```

---

## 二、核心设计

### 2.1 因子挖掘模块

#### 因子定义
```python
@dataclass
class Factor:
    name: str              # 因子名称
    description: str       # 因子描述
    formula: str          # 计算公式
    dependencies: List[str] # 依赖字段
    frequency: str        # 计算频率
    factor_type: str      # 因子类型
    category: str         # 因子分类
    author: str           # 作者
    version: str          # 版本
```

#### 因子分类
- **价格因子**: 基于OHLCV计算
- **成交量因子**: 量能相关
- **波动率因子**: 价格波动
- **趋势因子**: 趋势强度
- **情绪因子**: 市场情绪
- **财务因子**: 基本面数据

### 2.2 技术指标库

#### 已实现指标
| 指标 | 类别 | 说明 |
|------|------|------|
| MA | 趋势 | 移动平均线 |
| MACD | 趋势 | 指数平滑异同平均线 |
| RSI | 动量 | 相对强弱指数 |
| BOLL | 波动 | 布林带 |
| KDJ | 动量 | 随机指标 |
| ATR | 波动 | 真实波动幅度 |
| OBV | 量能 | 能量潮 |

### 2.3 策略基类

```python
class BaseStrategy(ABC):
    """策略基类"""
    
    @abstractmethod
    def on_init(self, context: Context):
        """初始化"""
        pass
    
    @abstractmethod
    def on_bar(self, context: Context, bar: Bar):
        """K线处理"""
        pass
    
    @abstractmethod
    def on_signal(self, context: Context, signal: Signal):
        """信号处理"""
        pass
```

---

## 三、数据流设计

```
数据管理层
    │
    ├──> 基础行情数据
    │       │
    │       ├──> WP1: 因子挖掘
    │       │       │
    │       │       ├──> 因子库 (factor_values)
    │       │       │
    │       │       └──> 因子元数据 (factor_metadata)
    │       │
    │       └──> WP2: 机器学习
    │               │
    │               ├──> 特征矩阵
    │               ├──> 模型训练
    │               └──> 预测结果
    │
    └──> WP3: 进化算法
            │
            ├──> 策略基因编码
            ├──> 适应度评估
            └──> 策略库

WP4: 信号合成
    │
    ├──> 多源信号融合
    ├──> 规则引擎
    └──> 交易信号
```

---

## 四、数据库设计

### 4.1 因子值表

```sql
CREATE TABLE factor_values (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    factor_name VARCHAR(50) NOT NULL,
    value DECIMAL(20, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_symbol_date_factor (symbol, trade_date, factor_name),
    KEY idx_factor_date (factor_name, trade_date),
    KEY idx_symbol_date (symbol, trade_date)
) ENGINE=InnoDB COMMENT='因子值表';
```

### 4.2 因子元数据表

```sql
CREATE TABLE factor_metadata (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    factor_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    formula TEXT,
    dependencies JSON,
    frequency VARCHAR(10),
    factor_type VARCHAR(20),
    category VARCHAR(30),
    author VARCHAR(50),
    version VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    KEY idx_category (category),
    KEY idx_factor_type (factor_type)
) ENGINE=InnoDB COMMENT='因子元数据表';
```

### 4.3 策略表

```sql
CREATE TABLE strategies (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    strategy_name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(20),  -- 'manual', 'evolution', 'ml'
    description TEXT,
    code TEXT,  -- 策略代码或表达式
    parameters JSON,  -- 策略参数
    performance JSON,  -- 绩效指标
    status TINYINT DEFAULT 1,  -- 0: disabled, 1: enabled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_strategy_name (strategy_name),
    KEY idx_strategy_type (strategy_type),
    KEY idx_status (status)
) ENGINE=InnoDB COMMENT='策略表';
```

---

## 五、开发计划

### Phase 1: 因子挖掘基础 (当前)
- [ ] 因子定义与管理
- [ ] 技术指标库扩展
- [ ] 因子计算引擎
- [ ] 因子存储实现

### Phase 2: 策略框架
- [ ] 策略基类设计
- [ ] 事件系统
- [ ] 简单策略示例

### Phase 3: 机器学习 (未来)
- [ ] 特征工程
- [ ] 模型训练
- [ ] 预测模块

### Phase 4: 进化算法 (未来)
- [ ] 策略编码
- [ ] 适应度函数
- [ ] 进化过程

### Phase 5: 信号合成 (未来)
- [ ] 多信号融合
- [ ] 规则引擎
- [ ] 实时信号

---

## 六、文件结构

```
src/
├── strategy/                   # 策略研究层
│   ├── __init__.py
│   ├── base.py                # 策略基类
│   ├── context.py             # 策略上下文
│   ├── factors/               # WP1: 因子挖掘
│   │   ├── __init__.py
│   │   ├── base.py           # 因子基类
│   │   ├── registry.py       # 因子注册表
│   │   ├── engine.py         # 因子计算引擎
│   │   ├── technical.py      # 技术指标因子
│   │   └── fundamental.py    # 基本面因子
│   ├── ml/                    # WP2: 机器学习
│   │   ├── __init__.py
│   │   ├── features.py       # 特征工程
│   │   ├── models.py         # 模型管理
│   │   └── trainer.py        # 训练器
│   ├── evolution/             # WP3: 进化算法
│   │   ├── __init__.py
│   │   ├── encoding.py       # 策略编码
│   │   ├── fitness.py        # 适应度函数
│   │   └── ga.py             # 遗传算法
│   └── signals/               # WP4: 信号合成
│       ├── __init__.py
│       ├── synthesis.py      # 信号合成
│       └── rules.py          # 规则引擎
```

---

**设计完成，开始开发**
