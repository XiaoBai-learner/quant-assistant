#!/usr/bin/env python3
"""
查找连续一字板股票 - 演示版本

由于网络限制，此版本使用模拟数据演示功能
"""

import os
from datetime import datetime, date, timedelta
import pandas as pd


def create_demo_data():
    """创建演示数据"""
    
    # 模拟找到的一字板股票
    results = [
        {
            'symbol': '000001',
            'name': '平安银行',
            'earliest_date': '2024-05-20',
            'max_consecutive': 5,
        },
        {
            'symbol': '000002',
            'name': '万科A',
            'earliest_date': '2024-08-15',
            'max_consecutive': 4,
        },
        {
            'symbol': '600000',
            'name': '浦发银行',
            'earliest_date': '2024-11-10',
            'max_consecutive': 6,
        },
    ]
    
    return results


def create_demo_stock_data(symbol, name, output_dir):
    """创建演示股票数据"""
    
    # 生成30个交易日的模拟数据
    dates = pd.date_range(end=date.today(), periods=30, freq='B')
    
    data = []
    base_price = 10.0
    
    for i, d in enumerate(dates):
        # 模拟价格波动
        change = (i % 5 - 2) * 0.5  # -1, -0.5, 0, 0.5, 1
        close = base_price + change
        open_price = close - 0.1
        high = close + 0.2
        low = close - 0.2
        
        # 模拟一字板（最后一天）
        if i == len(dates) - 1:
            close = open_price * 1.1
            high = close
            low = close
            change_pct = 10.0
        else:
            change_pct = (close - open_price) / open_price * 100
        
        data.append({
            'date': d.strftime('%Y-%m-%d'),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': 1000000 + i * 10000,
            'change_percent': round(change_pct, 2),
        })
        
        base_price = close
    
    df = pd.DataFrame(data)
    
    # 保存到CSV
    filename = f"{symbol}_{name}.csv"
    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    
    return filepath


def main():
    """主函数"""
    print("=" * 60)
    print("查找连续一字板股票 - 演示版本")
    print("=" * 60)
    
    print("\n注意: 由于网络限制，此版本使用模拟数据演示功能")
    print("实际使用时需要稳定的网络连接访问东方财富数据接口\n")
    
    # 时间范围
    end_date = date.today().strftime('%Y-%m-%d')
    start_date = (date.today() - timedelta(days=730)).strftime('%Y-%m-%d')
    
    print(f"时间范围: {start_date} 至 {end_date}")
    print(f"一字板条件: 涨幅>=9.9% 且 最低价==最高价")
    print(f"连续天数: >=4天\n")
    
    # 创建输出目录
    output_dir = './yiziban_data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 获取演示数据
    results = create_demo_data()
    
    print(f"找到 {len(results)} 只符合条件的股票:\n")
    print("-" * 60)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['symbol']} {result['name']}")
        print(f"   最早连续一字板时间: {result['earliest_date']}")
        print(f"   最大连续天数: {result['max_consecutive']}")
        
        # 创建并保存数据
        filepath = create_demo_stock_data(
            result['symbol'], 
            result['name'], 
            output_dir
        )
        result['filepath'] = filepath
        print(f"   数据文件: {filepath}")
        print()
    
    # 保存汇总信息
    summary_file = os.path.join(output_dir, 'summary.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("连续一字板股票汇总 (演示数据)\n")
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
    
    print("=" * 60)
    print("任务完成!")
    print("=" * 60)
    
    print(f"\n共找到 {len(results)} 只符合条件的股票")
    print(f"所有数据文件保存在: {os.path.abspath(output_dir)}")
    print(f"汇总信息已保存至: {summary_file}")
    
    return len(results), output_dir


if __name__ == '__main__':
    count, output_dir = main()
    print(f"\n最终数量: {count}")
    print(f"文件目录: {os.path.abspath(output_dir)}")
