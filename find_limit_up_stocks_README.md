# 查找连续一字板股票脚本

## 功能说明

本脚本用于查找A股市场中满足以下条件的股票：

1. **上市时间大于3年**
2. **近两年内出现过连续4个或大于4个一字板**
3. **一字板定义**：涨幅 >= 9.9% 且 最低价 == 最高价（即开盘价=最高价=最低价=收盘价）

## 文件说明

| 文件 | 说明 |
|------|------|
| `find_limit_up_stocks.py` | 完整版本（需要 akshare 数据） |
| `find_limit_up_stocks_demo.py` | 演示版本（使用模拟数据） |
| `find_limit_up_stocks_README.md` | 本说明文档 |

## 使用方法

### 演示版本（无需 akshare）

```bash
python find_limit_up_stocks_demo.py
```

此版本使用模拟数据演示完整逻辑，适合测试和学习。

### 完整版本（需要 akshare）

```bash
# 安装依赖
pip install akshare pandas

# 运行脚本
python find_limit_up_stocks.py
```

## 输出结果

脚本会生成以下输出：

### 1. 汇总文件
- **路径**: `./limit_up_stocks/summary.csv`
- **内容**: 符合条件的股票列表，包含股票代码、名称、最早一字板日期、连续天数

### 2. 个股数据文件
- **路径**: `./limit_up_stocks/{代码}_{名称}_{日期}.csv`
- **内容**: 每只股票前30个交易日至今的日线行情数据

### 3. 控制台输出
- 符合条件的股票数量
- 文件保存地址
- 汇总文件路径
- 数据文件列表

## 输出示例

```
============================================================
最终结果
============================================================
符合条件的股票数量: 3
文件保存地址: /home/admin/.openclaw/workspace/quant-assistant-github/limit_up_stocks
汇总文件: summary.csv

数据文件列表:
  - 000001_平安银行_20250407.csv
  - 600519_贵州茅台_20251014.csv
  - 600036_招商银行_20250414.csv
```

## 数据结构

### summary.csv
```csv
symbol,name,first_limit_up_date,consecutive_days
000001,平安银行,2025-04-07,5
600519,贵州茅台,2025-10-14,4
```

### 个股数据文件
```csv
symbol,stock_name,trade_date,open,high,low,close,volume,amount,pct_change,turnover,is_limit_up
000001,平安银行,2024-03-18,9.83,9.91,9.67,9.83,324805,9769782,-1.67,7.33,False
```

## 核心算法

### 一字板判断
```python
def is_limit_up_board(row):
    pct_change = float(row['pct_change'])
    high = float(row['high'])
    low = float(row['low'])
    
    # 涨幅 >= 9.9% 且 最低价 == 最高价
    return pct_change >= 9.9 and abs(high - low) < 0.001
```

### 连续一字板查找
```python
def find_consecutive_limit_up(df, min_consecutive=4):
    consecutive_records = []
    current_start = None
    current_count = 0
    
    for idx, row in df.iterrows():
        if is_limit_up_board(row):
            if current_start is None:
                current_start = row['trade_date']
            current_count += 1
        else:
            if current_count >= min_consecutive:
                consecutive_records.append((current_start, current_count))
            current_start = None
            current_count = 0
    
    return consecutive_records
```

## 注意事项

1. **数据获取限制**: 完整版本依赖 akshare 数据源，可能受限于网络和数据源限制
2. **运行时间**: 遍历全部A股（约5000+只）可能需要较长时间（预计1-2小时）
3. **数据准确性**: 一字板判断基于日线数据，实际交易中可能存在细微差异
4. **上市时间判断**: 通过数据覆盖范围间接判断上市时间，可能存在误差

## 自定义配置

可以在脚本中修改以下参数：

```python
MIN_LISTING_YEARS = 3      # 最小上市年限
MIN_CONSECUTIVE = 4        # 最小连续一字板天数
LOOKBACK_YEARS = 2         # 查找时间范围（年）
output_dir = './limit_up_stocks'  # 输出目录
```

## 依赖

- Python >= 3.6
- pandas
- numpy
- akshare (仅完整版本需要)
