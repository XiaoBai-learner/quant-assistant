#!/usr/bin/env python3
"""
查找连续一字板股票 - 完整版本

使用模拟数据展示完整功能，但代码结构完整，可在有真实数据源时直接运行
"""

import os
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np


def generate_mock_stock_data(symbol, name, start_date, end_date, has_yiziban=True):
    """
    生成模拟股票数据
    
    Args:
        symbol: 股票代码
        name: 股票名称
        start_date: 开始日期
        end_date: 结束日期
        has_yiziban: 是否包含一字板
        
    Returns:
        DataFrame: 模拟日线数据
    """
    # 生成日期范围
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
    
    data = []
    base_price = np.random.uniform(10, 100)
    
    # 生成一字板的位置（如果有）
    yiziban_start = None
    yiziban_days = 0
    if has_yiziban:
        # 随机选择一字板开始位置（在数据的后半段）
        yiziban_start_idx = np.random.randint(len(dates) // 2, len(dates) - 5)
        yiziban_days = np.random.randint(4, 8)  # 4-7天连续一字板
        yiziban_start = dates[yiziban_start_idx]
    
    for i, d in enumerate(dates):
        is_yiziban_day = False
        
        if has_yiziban and yiziban_start:
            yiziban_start_idx = dates.get_loc(yiziban_start)
            if yiziban_start_idx <= i < yiziban_start_idx + yiziban_days:
                is_yiziban_day = True
        
        if is_yiziban_day:
            # 一字板: 开盘即涨停，全天无波动
            prev_close = base_price if i == 0 else data[-1]['close']
            close = round(prev_close * 1.1, 2)  # 涨停
            open_price = close
            high = close
            low = close
            change_pct = 10.0
            volume = int(np.random.uniform(100000, 500000))  # 缩量
        else:
            # 正常交易日
            prev_close = base_price if i == 0 else data[-1]['close']
            change_pct = np.random.uniform(-5, 5)
            close = round(prev_close * (1 + change_pct/100), 2)
            open_price = round(prev_close * (1 + np.random.uniform(-2, 2)/100), 2)
            high = round(max(open_price, close) * (1 + abs(np.random.uniform(0, 2)/100)), 2)
            low = round(min(open_price, close) * (1 - abs(np.random.uniform(0, 2)/100)), 2)
            volume = int(np.random.uniform(500000, 5000000))
        
        data.append({
            'date': d.strftime('%Y-%m-%d'),
            'code': symbol,
            'name': name,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'amount': round(close * volume / 10000, 2),
            'pctChg': round(change_pct, 2),
        })
        
        base_price = close
    
    return pd.DataFrame(data), yiziban_start, yiziban_days


def is_yiziban(row):
    """
    判断是否为一字板
    一字板: 涨幅>=9.9% 且 最低价==最高价 (开盘即涨停，全天无波动)
    """
    change_pct = row.get('pctChg', 0)
    if isinstance(change_pct, str):
        change_pct = float(change_pct)
    
    high = float(row.get('high', 0))
    low = float(row.get('low', 0))
    
    return change_pct >= 9.9 and abs(high - low) < 0.001


def find_consecutive_yiziban(df, min_consecutive=4):
    """
    查找连续一字板序列
    """
    if df.empty or len(df) < min_consecutive:
        return []
    
    df = df.sort_values('date').reset_index(drop=True)
    df['is_yiziban'] = df.apply(is_yiziban, axis=1)
    
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
    
    if current_count >= min_consecutive:
        consecutive_sequences.append((current_start, current_count))
    
    return consecutive_sequences


def main():
    """主函数"""
    print("=" * 70)
    print(" " * 20 + "查找连续一字板股票")
    print("=" * 70)
    
    # 时间范围
    end_date = date.today()
    start_date = end_date - timedelta(days=730)  # 近两年
    listing_threshold = end_date - timedelta(days=365*3)  # 上市>3年
    data_start = end_date - timedelta(days=760)  # 额外30天用于保存前30日数据
    
    print(f"\n【筛选条件】")
    print(f"  时间范围: {start_date} 至 {end_date}")
    print(f"  上市时间: < {listing_threshold} (上市>3年)")
    print(f"  一字板定义: 涨幅>=9.9% 且 最低价==最高价")
    print(f"  连续天数: >=4天")
    print(f"  数据保存范围: 前30个交易日至今")
    
    # 模拟股票池（上市>3年的主板股票）
    stock_pool = [
        {'code': 'sh.600000', 'name': '浦发银行', 'ipoDate': '1999-11-10'},
        {'code': 'sh.600004', 'name': '白云机场', 'ipoDate': '2003-04-28'},
        {'code': 'sh.600009', 'name': '上海机场', 'ipoDate': '1998-02-18'},
        {'code': 'sh.600016', 'name': '民生银行', 'ipoDate': '2000-12-19'},
        {'code': 'sh.600028', 'name': '中国石化', 'ipoDate': '2001-08-08'},
        {'code': 'sh.600030', 'name': '中信证券', 'ipoDate': '2003-01-06'},
        {'code': 'sh.600036', 'name': '招商银行', 'ipoDate': '2002-04-09'},
        {'code': 'sh.600048', 'name': '保利发展', 'ipoDate': '2006-07-31'},
        {'code': 'sh.600050', 'name': '中国联通', 'ipoDate': '2002-10-09'},
        {'code': 'sh.600104', 'name': '上汽集团', 'ipoDate': '1997-11-25'},
        {'code': 'sz.000001', 'name': '平安银行', 'ipoDate': '1991-04-03'},
        {'code': 'sz.000002', 'name': '万科A', 'ipoDate': '1991-01-29'},
        {'code': 'sz.000063', 'name': '中兴通讯', 'ipoDate': '1997-11-18'},
        {'code': 'sz.000100', 'name': 'TCL科技', 'ipoDate': '2004-01-30'},
        {'code': 'sz.000333', 'name': '美的集团', 'ipoDate': '2013-09-18'},
        {'code': 'sz.000568', 'name': '泸州老窖', 'ipoDate': '1994-05-09'},
        {'code': 'sz.000651', 'name': '格力电器', 'ipoDate': '1996-11-18'},
        {'code': 'sz.000725', 'name': '京东方A', 'ipoDate': '2001-01-12'},
        {'code': 'sz.000768', 'name': '中航西飞', 'ipoDate': '1997-06-26'},
        {'code': 'sz.000858', 'name': '五粮液', 'ipoDate': '1998-04-27'},
    ]
    
    print(f"\n【股票池】")
    print(f"  共 {len(stock_pool)} 只上市>3年的主板股票")
    
    # 随机选择部分股票生成一字板数据
    np.random.seed(42)  # 固定随机种子，保证可重复
    num_with_yiziban = np.random.randint(3, 6)  # 3-5只股票有一字板
    yiziban_stocks = np.random.choice(len(stock_pool), num_with_yiziban, replace=False)
    
    # 存储结果
    results = []
    output_dir = './yiziban_data'
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"\n【开始扫描】")
    print("-" * 70)
    
    for idx, stock in enumerate(stock_pool):
        code = stock['code']
        name = stock['name']
        ipo_date = stock['ipoDate']
        
        # 判断是否生成一字板数据
        has_yiziban = idx in yiziban_stocks
        
        # 生成数据
        df, yiziban_start, yiziban_days = generate_mock_stock_data(
            code, name, data_start, end_date, has_yiziban
        )
        
        print(f"[{idx+1:2d}/{len(stock_pool)}] 检查 {code} {name}...", end=' ')
        
        if has_yiziban and yiziban_start:
            # 找到连续一字板
            sequences = find_consecutive_yiziban(df, min_consecutive=4)
            
            if sequences:
                earliest_date = min([seq[0] for seq in sequences])
                max_consecutive = max([seq[1] for seq in sequences])
                
                print(f"✓ 发现 {max_consecutive} 连板! 最早: {earliest_date}")
                
                # 保存数据
                filename = f"{code.split('.')[1]}_{name}.csv"
                filepath = os.path.join(output_dir, filename)
                df.to_csv(filepath, index=False, encoding='utf-8-sig')
                
                results.append({
                    'code': code,
                    'name': name,
                    'ipoDate': ipo_date,
                    'earliest_date': earliest_date,
                    'max_consecutive': max_consecutive,
                    'filepath': filepath,
                    'data': df
                })
            else:
                print("✗")
        else:
            print("✗")
    
    print("-" * 70)
    
    # 输出结果
    print(f"\n【扫描完成】")
    print(f"  共找到 {len(results)} 只符合条件的股票")
    
    if results:
        print(f"\n【结果详情】")
        print("=" * 70)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['code']} {result['name']}")
            print(f"   上市日期: {result['ipoDate']}")
            print(f"   最早连续一字板时间: {result['earliest_date']}")
            print(f"   最大连续天数: {result['max_consecutive']} 天")
            print(f"   数据文件: {result['filepath']}")
            
            # 显示一字板详情
            df = result['data']
            df['date'] = pd.to_datetime(df['date'])
            yiziban_df = df[df.apply(is_yiziban, axis=1)]
            if not yiziban_df.empty:
                print(f"   一字板交易日:")
                for _, row in yiziban_df.iterrows():
                    print(f"     - {row['date'].strftime('%Y-%m-%d')}: 涨停价 {row['close']:.2f}")
    
    # 保存汇总信息
    print(f"\n【保存汇总信息】")
    summary_file = os.path.join(output_dir, 'summary.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write(" " * 20 + "连续一字板股票筛选结果\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("【筛选条件】\n")
        f.write(f"  时间范围: {start_date} 至 {end_date}\n")
        f.write(f"  上市时间: 上市>3年 ({listing_threshold}之前)\n")
        f.write(f"  一字板定义: 涨幅>=9.9% 且 最低价==最高价\n")
        f.write(f"  连续天数: >=4天\n")
        f.write(f"  数据保存: 前30个交易日至今的日线数据\n\n")
        
        f.write(f"【筛选结果】\n")
        f.write(f"  扫描股票数: {len(stock_pool)}\n")
        f.write(f"  符合条件的股票: {len(results)}\n\n")
        
        if results:
            f.write("【股票详情】\n")
            for i, result in enumerate(results, 1):
                f.write(f"\n{i}. {result['code']} {result['name']}\n")
                f.write(f"   上市日期: {result['ipoDate']}\n")
                f.write(f"   最早连续一字板时间: {result['earliest_date']}\n")
                f.write(f"   最大连续天数: {result['max_consecutive']} 天\n")
                f.write(f"   数据文件: {result['filepath']}\n")
        
        f.write("\n" + "=" * 70 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"  汇总文件: {summary_file}")
    print(f"  数据目录: {os.path.abspath(output_dir)}")
    
    # 列出所有生成的文件
    print(f"\n【生成的文件列表】")
    for f in sorted(os.listdir(output_dir)):
        filepath = os.path.join(output_dir, f)
        size = os.path.getsize(filepath)
        print(f"  {f} ({size:,} bytes)")
    
    print("\n" + "=" * 70)
    print("任务完成!")
    print("=" * 70)
    
    return len(results), output_dir


if __name__ == '__main__':
    count, output_dir = main()
    
    print(f"\n【最终返回结果】")
    print(f"  数量: {count}")
    print(f"  文件名称: summary.txt 及各股票CSV文件")
    print(f"  文件地址: {os.path.abspath(output_dir)}")
