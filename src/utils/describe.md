# Utils 工具模块

## 模块概述

工具模块提供系统通用的辅助功能，包括日志管理、配置加载等。采用简洁设计，为其他模块提供统一的基础设施支持。

## 子模块说明

### logger.py - 日志管理

**功能**: 统一日志管理和配置

**核心类**:
- `LoggerConfig`: 日志配置
  - 属性: level, format, file_path, max_bytes, backup_count

- `setup_logging()`: 配置日志
  - 设置日志级别
  - 配置日志格式
  - 添加文件处理器
  - 添加控制台处理器

- `get_logger(name)`: 获取日志器
  - 返回配置好的 logger 实例
  - 支持模块级日志记录

**日志级别**:
- DEBUG: 调试信息
- INFO: 一般信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

**日志格式**:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**使用示例**:
```python
from src.utils.logger import setup_logging, get_logger

# 初始化日志
setup_logging()

# 获取logger
logger = get_logger(__name__)

# 记录日志
logger.info("系统启动")
logger.debug(f"数据加载完成: {len(df)} 条")
logger.warning("数据缺失")
logger.error("连接失败")
```

### config.py - 配置管理

**功能**: 系统配置管理

**核心类**:
- `DatabaseConfig`: 数据库配置
  - 属性: host, port, user, password, database, charset, pool_size, max_overflow
  - `connection_string`: 生成SQLAlchemy连接字符串

- `DataConfig`: 数据配置
  - 属性: default_symbols, auto_update, update_interval_hours, history_start_date
  - 默认股票: 000001, 000002, 600000, 600519

- `LoggingConfig`: 日志配置
  - 属性: level, format, file_path, max_bytes, backup_count

**全局配置实例**:
- `db_config`: 数据库配置实例
- `data_config`: 数据配置实例
- `log_config`: 日志配置实例

**配置来源**:
1. 环境变量 (优先级最高)
2. 配置文件
3. 默认值

**环境变量**:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=quant_user
DB_PASSWORD=your_password
DB_NAME=quant_data
```

**使用示例**:
```python
from src.utils.config import db_config, data_config

# 数据库连接
conn_string = db_config.connection_string

# 默认股票
symbols = data_config.default_symbols

# 历史数据起始日期
start_date = data_config.history_start_date
```

## 接口汇总

| 接口 | 输入 | 输出 | 说明 |
|------|------|------|------|
| setup_logging | - | - | 配置日志系统 |
| get_logger | name | Logger | 获取日志器 |
| db_config.connection_string | - | str | 数据库连接字符串 |
| data_config.default_symbols | - | list | 默认股票列表 |

## 设计原则

- **简洁**: 只提供必要功能
- **统一**: 全系统使用相同日志格式
- **灵活**: 支持环境变量覆盖配置
