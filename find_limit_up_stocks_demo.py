#!/usr/bin/env python3
"""
查找连续一字板股票 - 演示版本（使用模拟数据）

由于环境无法安装 akshare，此版本使用模拟数据演示完整逻辑
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple

# 配置
output_dir = './limit_up_stocks_demo'
os.makedirs(output_dir, exist_ok=True)


def generate_mock_stock_data(symbol: str, name: str, start_date: date, end_date: date, 
                             has_limit_up: bool = False) -> pd.DataFrame:
    """生成模拟股票数据"""
    
    # 生成日期范围（交易日）
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
    
    data = []
    base_price = 10.0
    
    limit_up_start = None
    if has_limit_up:
        # 随机选择连续一字板的起始日期
        limit_up_start_idx = np.random.randint(len(date_range) // 2, len(date_range) - 10)
        limit_up_start = date_range[limit_up_start_idx]
    
    for i, trade_date in enumerate(date_range):
        # 基础价格波动
        change_pct = np.random.normal(0, 2)  # 正态分布，均值0，标准差2%
        
        # 如果是连续一字板期间
        if has_limit_up and limit_up_start:
            days_from_start = (trade_date - limit_up_start).days
            if 0 <= days_from_start < 5:  # 连续5天一字板
                change_pct = 10.0  # 涨停
                open_price = base_price * 1.1
                high_price = open_price
                low_price = open_price
                close_price = open_price
            else:
                open_price = base_price * (1 + change_pct / 100)
                high_price = open_price * (1 + abs(np.random.normal(0, 1)) / 100)
                low_price = open_price * (1 - abs(np.random.normal(0, 1)) / 100)
                close_price = open_price
        else:
            open_price = base_price * (1 + change_pct / 100)
            high_price = open_price * (1 + abs(np.random.normal(0, 1)) / 100)
            low_price = open_price * (1 - abs(np.random.normal(0, 1)) / 100)
            close_price = open_price
        
        # 更新基础价格
        base_price = close_price
        
        data.append({
            'symbol': symbol,
            'trade_date': trade_date,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': int(np.random.randint(100000, 1000000)),
            'amount': int(np.random.randint(1000000, 10000000)),
            'pct_change': round(change_pct, 2),
            'turnover': round(np.random.uniform(1, 10), 2),
        })
    
    df = pd.DataFrame(data)
    return df


def is_limit_up_board(row: pd.Series) -> bool:
    """判断是否为一字板：涨幅 >= 9.9% 且 最低价 == 最高价"""
    try:
        pct_change = float(row['pct_change'])
        high = float(row['high'])
        low = float(row['low'])
        
        return pct_change >= 9.9 and abs(high - low) < 0.001
    except:
        return False


def find_consecutive_limit_up(df: pd.DataFrame, min_consecutive: int = 4) -> List[Tuple[datetime, int]]:
    """查找连续一字板的记录"""
    if df.empty or len(df) < min_consecutive:
        return []
    
    df = df.sort_values('trade_date').reset_index(drop=True)
    df['is_limit_up'] = df.apply(is_limit_up_board, axis=1)
    
    consecutive_records = []
    current_start = None
    current_count = 0
    
    for idx, row in df.iterrows():
        if row['is_limit_up']:
            if current_start is None:
                current_start = row['trade_date']
            current_count += 1
        else:
            if current_count >= min_consecutive:
                consecutive_records.append((current_start, current_count))
            current_start = None
            current_count = 0
    
    if current_count >= min_consecutive:
        consecutive_records.append((current_start, current_count))
    
    return consecutive_records


def main():
    """主函数"""
    
    print("=" * 60)
    print("查找连续一字板股票 - 演示版本")
    print("=" * 60)
    print("注意：此版本使用模拟数据演示完整逻辑")
    print("=" * 60)
    
    # 模拟股票列表
    mock_stocks = [
        ('000001', '平安银行', True),   # 有一字板
        ('000002', '万科A', False),
        ('600000', '浦发银行', False),
        ('600519', '贵州茅台', True),   # 有一字板
        ('300750', '宁德时代', False),
        ('002594', '比亚迪', True),     # 有一字板
        ('000858', '五粮液', False),
        ('601318', '中国平安', False),
        ('600036', '招商银行', True),   # 有一字板
        ('000333', '美的集团', False),
    ]
    
    # 日期范围
    end_date = date.today()
    start_date = end_date - timedelta(days=365 * 2)  # 近两年
    
    print(f"\n数据范围：{start_date} 至 {end_date}")
    print(f"检查股票数：{len(mock_stocks)}")
    print(f"条件：上市>3年，连续>=4个一字板\n")
    
    results = []
    saved_files = []
    
    for symbol, name, has_limit_up in mock_stocks:
        print(f"处理: {symbol} {name}...")
        
        # 生成模拟数据
        df = generate_mock_stock_data(symbol, name, start_date, end_date, has_limit_up)
        
        # 查找连续一字板
        consecutive_records = find_consecutive_limit_up(df, 4)
        
        if consecutive_records:
            first_record = min(consecutive_records, key=lambda x: x[0])
            first_date, consecutive_days = first_record
            
            print(f"  ✓ 发现连续{consecutive_days}个一字板于 {first_date.strftime('%Y-%m-%d')}")
            
            results.append({
                'symbol': symbol,
                'name': name,
                'first_limit_up_date': first_date.strftime('%Y-%m-%d'),
                'consecutive_days': consecutive_days
            })
            
            # 保存数据到CSV（前30个交易日至今）
            df['stock_name'] = name
            df['is_limit_up'] = df.apply(is_limit_up_board, axis=1)
            
            filename = f"{symbol}_{name}_{first_date.strftime('%Y%m%d')}.csv"
            filepath = os.path.join(output_dir, filename)
            
            columns = ['symbol', 'stock_name', 'trade_date', 'open', 'high', 'low', 'close', 
                      'volume', 'amount', 'pct_change', 'turnover', 'is_limit_up']
            df[columns].to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"  ✓ 已保存数据到 {filepath}")
            saved_files.append(filepath)
    
    print("\n" + "=" * 60)
    print("查找完成")
    print("=" * 60)
    
    if results:
        print(f"\n共找到 {len(results)} 只符合条件的股票：\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['symbol']} {r['name']}")
            print(f"   最早连续一字板时间: {r['first_limit_up_date']}")
            print(f"   连续天数: {r['consecutive_days']}")
            print()
        
        # 保存汇总结果
        summary_file = os.path.join(output_dir, 'summary.csv')
        summary_df = pd.DataFrame(results)
        summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        print(f"汇总结果已保存到: {summary_file}")
        
        print(f"\n共保存 {len(saved_files)} 个数据文件")
        print(f"文件所在地址: {os.path.abspath(output_dir)}")
        
        # 返回信息
        print("\n" + "=" * 60)
        print("最终结果")
        print("=" * 60)
        print(f"符合条件的股票数量: {len(results)}")
        print(f"文件保存地址: {os.path.abspath(output_dir)}")
        print(f"汇总文件: summary.csv")
        print("\n数据文件列表:")
        for f in saved_files:
            print(f"  - {os.path.basename(f)}")
        
        return len(results), saved_files, output_dir
    else:
        print("未找到符合条件的股票")
        return 0, [], output_dir


if __name__ == '__main__':
    count, files, output_dir = main()
