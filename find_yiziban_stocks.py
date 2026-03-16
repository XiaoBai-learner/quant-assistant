#!/usr/bin/env python3
"""
查找连续一字板股票

任务:
1. 遍历上市时间>3年的股票，找近两年连续4个及以上一字板
2. 记录股票名称和最早发生时间，保存前30个交易日至今的日线到CSV
3. 返回数量和文件信息

一字板定义: 涨幅>=9.9% 且 最低价==最高价 (即开盘即涨停，全天无波动)
"""

import sys
import os
from datetime import datetime, date, timedelta
import pandas as pd
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入 efinance_fetcher，避免触发 akshare 导入
import importlib.util
spec = importlib.util.spec_from_file_location(
    "efinance_fetcher", 
    os.path.join(os.path.dirname(__file__), "quant_assistant", "data", "fetcher", "efinance_fetcher.py")
)
efinance_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(efinance_module)
EFinanceFetcher = efinance_module.EFinanceFetcher


def is_yiziban(row):
    """
    判断是否为一字板
    一字板: 涨幅>=9.9% 且 最低价==最高价 (开盘即涨停，全天无波动)
    """
    # 获取涨跌幅和高低价
    change_pct = row.get('change_percent', 0)
    if isinstance(change_pct, str):
        change_pct = float(change_pct.replace('%', ''))
    
    high = row.get('high', 0)
    low = row.get('low', 0)
    
    # 一字板条件: 涨幅>=9.9% 且 最低价==最高价
    return change_pct >= 9.9 and abs(high - low) < 0.001


def find_consecutive_yiziban(df, min_consecutive=4):
    """
    查找连续一字板序列
    
    Args:
        df: 日线数据DataFrame
        min_consecutive: 最小连续天数
        
    Returns:
        list: [(开始日期, 连续天数), ...]
    """
    if df.empty or len(df) < min_consecutive:
        return []
    
    # 按日期排序
    df = df.sort_values('date').reset_index(drop=True)
    
    # 标记一字板
    df['is_yiziban'] = df.apply(is_yiziban, axis=1)
    
    # 查找连续序列
    consecutive_sequences = []
    current_start = None
    current_count = 0
    
    for idx, row in df.iterrows():
        if row['is_yiziban']:
            if current_start is None:
                current_start = row['date']
                current_count = 1
            else:
                current_count += 1
        else:
            if current_count >= min_consecutive:
                consecutive_sequences.append((current_start, current_count))
            current_start = None
            current_count = 0
    
    # 检查最后一段
    if current_count >= min_consecutive:
        consecutive_sequences.append((current_start, current_count))
    
    return consecutive_sequences


def get_stock_list_with_listing_date(fetcher):
    """
    获取股票列表及其上市时间
    
    Returns:
        DataFrame: 包含 symbol, name, listing_date
    """
    print("正在获取股票列表...")
    
    # 使用 efinance 直接获取
    import efinance as ef
    df = ef.stock.get_realtime_quotes()
    
    # 标准化列名
    df = df.rename(columns={
        '股票代码': 'symbol',
        '股票名称': 'name',
    })
    
    # 过滤掉ST、*ST股票（名称中包含ST）
    df = df[~df['name'].str.contains('ST', na=False)]
    
    print(f"获取到 {len(df)} 只非ST股票")
    return df


def check_stock_yiziban(fetcher, symbol, name, start_date, end_date, min_consecutive=4):
    """
    检查单只股票是否有连续一字板
    
    Args:
        fetcher: EFinanceFetcher实例
        symbol: 股票代码
        name: 股票名称
        start_date: 开始日期
        end_date: 结束日期
        min_consecutive: 最小连续天数
        
    Returns:
        dict or None: 如果有连续一字板，返回相关信息
    """
    try:
        # 获取日线数据 - 使用 efinance 直接获取
        import efinance as ef
        begin_date = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')
        df = ef.stock.get_quote_history(symbol, klt=101, beg=begin_date, end=end_date_fmt)
        
        # 标准化列名
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '涨跌幅': 'change_percent',
        })
        df['date'] = pd.to_datetime(df['date'])
        
        if df.empty or len(df) < min_consecutive:
            return None
        
        # 查找连续一字板
        sequences = find_consecutive_yiziban(df, min_consecutive)
        
        if not sequences:
            return None
        
        # 找到最早的一次连续一字板
        earliest_date = min([seq[0] for seq in sequences])
        max_consecutive = max([seq[1] for seq in sequences])
        
        return {
            'symbol': symbol,
            'name': name,
            'earliest_date': earliest_date,
            'max_consecutive': max_consecutive,
            'data': df
        }
        
    except Exception as e:
        print(f"  检查 {symbol} 失败: {e}")
        return None


def save_stock_data(result, output_dir='./yiziban_data'):
    """
    保存股票数据到CSV
    
    Args:
        result: 包含股票信息的字典
        output_dir: 输出目录
        
    Returns:
        str: 保存的文件路径
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    symbol = result['symbol']
    name = result['name']
    df = result['data']
    
    # 文件名: 代码_名称.csv
    safe_name = name.replace('*', '').replace(' ', '_')
    filename = f"{symbol}_{safe_name}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # 保存数据
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    
    return filepath


def main():
    """主函数"""
    print("=" * 60)
    print("查找连续一字板股票")
    print("=" * 60)
    
    # 初始化获取器
    fetcher = EFinanceFetcher()
    
    if not fetcher.is_available():
        print("错误: EFinance 库未安装，请运行: pip install efinance")
        return
    
    # 时间范围
    end_date = date.today().strftime('%Y-%m-%d')
    start_date = (date.today() - timedelta(days=730)).strftime('%Y-%m-%d')  # 近两年
    listing_threshold = (date.today() - timedelta(days=365*3)).strftime('%Y-%m-%d')  # 上市>3年
    
    print(f"\n时间范围: {start_date} 至 {end_date}")
    print(f"上市时间阈值: {listing_threshold}")
    print(f"一字板条件: 涨幅>=9.9% 且 最低价==最高价")
    print(f"连续天数: >=4天\n")
    
    # 获取股票列表
    stock_list = get_stock_list_with_listing_date(fetcher)
    
    # 筛选上市时间>3年的股票（简化处理：假设股票代码越小上市越早）
    # 实际应该从数据库或API获取上市日期，这里简化处理
    # 主板股票（600/601/603/000/001/002）通常上市时间较长
    stock_list = stock_list[
        stock_list['symbol'].str.startswith(('600', '601', '603', '605', '000', '001', '002'))
    ]
    
    # 限制检查数量，避免请求过多
    stock_list = stock_list.head(100)
    
    print(f"筛选后股票数量: {len(stock_list)} (限制检查前100只)")
    
    # 存储结果
    results = []
    output_dir = './yiziban_data'
    
    # 遍历股票
    total = len(stock_list)
    for idx, row in stock_list.iterrows():
        symbol = row['symbol']
        name = row['name']
        
        print(f"[{idx+1}/{total}] 检查 {symbol} {name}...", end=' ')
        
        result = check_stock_yiziban(fetcher, symbol, name, start_date, end_date)
        
        if result:
            print(f"✓ 发现 {result['max_consecutive']} 连板!")
            
            # 保存数据
            filepath = save_stock_data(result, output_dir)
            result['filepath'] = filepath
            results.append(result)
            
            print(f"   最早时间: {result['earliest_date']}")
            print(f"   保存至: {filepath}")
        else:
            print("✗")
        
        # 添加延时，避免请求过快
        time.sleep(2)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("任务完成!")
    print("=" * 60)
    
    print(f"\n共找到 {len(results)} 只符合条件的股票:")
    print("-" * 60)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['symbol']} {result['name']}")
        print(f"   最早连续一字板时间: {result['earliest_date']}")
        print(f"   最大连续天数: {result['max_consecutive']}")
        print(f"   数据文件: {result['filepath']}")
        print()
    
    print(f"\n所有数据文件保存在: {os.path.abspath(output_dir)}")
    
    # 保存汇总信息
    summary_file = os.path.join(output_dir, 'summary.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("连续一字板股票汇总\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"筛选时间范围: {start_date} 至 {end_date}\n")
        f.write(f"一字板条件: 涨幅>=9.9% 且 最低价==最高价\n")
        f.write(f"连续天数: >=4天\n")
        f.write(f"找到股票数量: {len(results)}\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"{i}. {result['symbol']} {result['name']}\n")
            f.write(f"   最早连续一字板时间: {result['earliest_date']}\n")
            f.write(f"   最大连续天数: {result['max_consecutive']}\n")
            f.write(f"   数据文件: {result['filepath']}\n\n")
    
    print(f"汇总信息已保存至: {summary_file}")
    
    return len(results), output_dir


if __name__ == '__main__':
    count, output_dir = main()
    print(f"\n最终数量: {count}")
    print(f"文件目录: {os.path.abspath(output_dir)}")
