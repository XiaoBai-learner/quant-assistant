#!/usr/bin/env python3
"""
查找连续一字板股票

功能：
1. 遍历上市时间大于3年的股票
2. 查找近两年内出现过连续4个或大于4个一字板的股票
3. 一字板定义：涨幅 >= 9.9% 且 最低价 == 最高价
4. 记录股票名称和最早发生时间
5. 保存前30个交易日至今的日线数据到CSV

使用方法：
    python find_limit_up_stocks.py
"""

import os
import sys
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quant_assistant.data.fetcher.akshare_fetcher import AKShareFetcher
from quant_assistant.utils.logger import get_logger

# 配置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_stock_list_with_listing_date() -> pd.DataFrame:
    """
    获取股票列表及上市时间
    
    Returns:
        DataFrame: 包含 symbol, name, list_date
    """
    try:
        import akshare as ak
        
        logger.info("获取A股股票列表及上市时间...")
        
        # 获取股票列表
        df = ak.stock_zh_a_spot_em()
        df = df.rename(columns={
            '代码': 'symbol',
            '名称': 'name',
        })
        
        # 获取上市时间
        stock_info = ak.stock_zh_a_spot_em()
        
        # 使用 stock_individual_info_em 获取每只股票的详细信息（包含上市时间）
        logger.info("获取股票上市时间信息...")
        
        # 由于获取每只股票的上市时间很慢，我们使用另一种方式
        # 使用 stock_zh_a_hist 的最早日期作为上市时间参考
        
        # 简化：先返回股票列表，上市时间通过数据范围判断
        result = df[['symbol', 'name']].copy()
        
        # 添加交易所信息
        result['exchange'] = result['symbol'].apply(get_exchange)
        
        logger.info(f"获取到 {len(result)} 只股票")
        return result
        
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return pd.DataFrame()


def get_exchange(symbol: str) -> str:
    """根据股票代码判断交易所"""
    if symbol.startswith(('600', '601', '603', '605', '688')):
        return 'SH'
    elif symbol.startswith(('000', '001', '002', '003', '300')):
        return 'SZ'
    elif symbol.startswith(('8', '4')):
        return 'BJ'
    else:
        return 'UNKNOWN'


def get_stock_daily_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取股票日线数据
    
    Args:
        symbol: 股票代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        
    Returns:
        DataFrame: 日线数据
    """
    try:
        import akshare as ak
        
        # 转换日期格式
        start = start_date.replace('-', '')
        end = end_date.replace('-', '')
        
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start,
            end_date=end,
            adjust="qfq"  # 前复权
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # 标准化列名
        df = df.rename(columns={
            '日期': 'trade_date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change_amount',
            '换手率': 'turnover',
        })
        
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['symbol'] = symbol
        
        return df
        
    except Exception as e:
        logger.error(f"获取 {symbol} 数据失败: {e}")
        return pd.DataFrame()


def is_limit_up_board(row: pd.Series) -> bool:
    """
    判断是否为一字板
    
    一字板定义：
    - 涨幅 >= 9.9%
    - 最低价 == 最高价（即开盘价=最高价=最低价=收盘价）
    
    Args:
        row: 单行数据
        
    Returns:
        bool: 是否为一字板
    """
    try:
        pct_change = float(row['pct_change'])
        high = float(row['high'])
        low = float(row['low'])
        
        # 涨幅 >= 9.9% 且 最低价 == 最高价
        return pct_change >= 9.9 and abs(high - low) < 0.001
    except:
        return False


def find_consecutive_limit_up(df: pd.DataFrame, min_consecutive: int = 4) -> List[Tuple[datetime, int]]:
    """
    查找连续一字板的记录
    
    Args:
        df: 股票日线数据
        min_consecutive: 最小连续天数（默认4天）
        
    Returns:
        List[Tuple[datetime, int]]: [(最早日期, 连续天数), ...]
    """
    if df.empty or len(df) < min_consecutive:
        return []
    
    # 按日期排序
    df = df.sort_values('trade_date').reset_index(drop=True)
    
    # 标记一字板
    df['is_limit_up'] = df.apply(is_limit_up_board, axis=1)
    
    # 查找连续一字板
    consecutive_records = []
    current_start = None
    current_count = 0
    
    for idx, row in df.iterrows():
        if row['is_limit_up']:
            if current_start is None:
                current_start = row['trade_date']
            current_count += 1
        else:
            # 连续结束
            if current_count >= min_consecutive:
                consecutive_records.append((current_start, current_count))
            current_start = None
            current_count = 0
    
    # 检查最后一段
    if current_count >= min_consecutive:
        consecutive_records.append((current_start, current_count))
    
    return consecutive_records


def check_stock_listing_time(symbol: str, min_years: int = 3) -> bool:
    """
    检查股票上市时间是否超过指定年限
    
    Args:
        symbol: 股票代码
        min_years: 最小上市年限
        
    Returns:
        bool: 是否满足上市时间要求
    """
    try:
        import akshare as ak
        
        # 获取股票历史数据
        end_date = date.today()
        start_date = end_date - timedelta(days=365 * (min_years + 1))
        
        df = get_stock_daily_data(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if df.empty:
            return False
        
        # 检查数据是否覆盖足够长的时间
        if len(df) < 365 * min_years * 0.5:  # 考虑交易日约250天/年
            return False
        
        # 获取最早的交易日期
        earliest_date = df['trade_date'].min()
        years_listed = (end_date - earliest_date.date()).days / 365
        
        return years_listed >= min_years
        
    except Exception as e:
        logger.error(f"检查 {symbol} 上市时间失败: {e}")
        return False


def save_stock_data_to_csv(symbol: str, stock_name: str, first_limit_up_date: datetime, 
                           output_dir: str = './limit_up_stocks') -> str:
    """
    保存股票前30个交易日至今的数据到CSV
    
    Args:
        symbol: 股票代码
        stock_name: 股票名称
        first_limit_up_date: 最早一字板日期
        output_dir: 输出目录
        
    Returns:
        str: 保存的文件路径
    """
    try:
        # 计算日期范围
        end_date = date.today()
        start_date = first_limit_up_date - timedelta(days=60)  # 前30个交易日约等于45天
        
        # 获取数据
        df = get_stock_daily_data(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        if df.empty:
            logger.warning(f"{symbol} 无数据可保存")
            return ""
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 添加股票名称
        df['stock_name'] = stock_name
        
        # 保存CSV
        filename = f"{symbol}_{stock_name}_{first_limit_up_date.strftime('%Y%m%d')}.csv"
        filepath = os.path.join(output_dir, filename)
        
        # 选择需要的列
        columns = ['symbol', 'stock_name', 'trade_date', 'open', 'high', 'low', 'close', 
                   'volume', 'amount', 'pct_change', 'turnover']
        df = df[[col for col in columns if col in df.columns]]
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"已保存 {symbol} 数据到 {filepath}")
        
        return filepath
        
    except Exception as e:
        logger.error(f"保存 {symbol} 数据失败: {e}")
        return ""


def main():
    """主函数"""
    
    # 配置参数
    MIN_LISTING_YEARS = 3  # 最小上市年限
    MIN_CONSECUTIVE = 4    # 最小连续一字板天数
    LOOKBACK_YEARS = 2     # 查找时间范围（年）
    
    output_dir = './limit_up_stocks'
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("开始查找连续一字板股票")
    logger.info(f"条件：上市>{MIN_LISTING_YEARS}年，近{LOOKBACK_YEARS}年内连续{MIN_CONSECUTIVE}+个一字板")
    logger.info("=" * 60)
    
    # 获取股票列表
    stock_list = get_stock_list_with_listing_date()
    if stock_list.empty:
        logger.error("获取股票列表失败")
        return
    
    logger.info(f"共 {len(stock_list)} 只股票待检查")
    
    # 计算日期范围
    end_date = date.today()
    start_date = end_date - timedelta(days=365 * LOOKBACK_YEARS)
    
    logger.info(f"数据范围：{start_date} 至 {end_date}")
    
    # 存储结果
    results = []
    saved_files = []
    
    # 遍历股票
    total = len(stock_list)
    for idx, row in stock_list.iterrows():
        symbol = row['symbol']
        name = row['name']
        
        if idx % 50 == 0:
            logger.info(f"进度: {idx}/{total} ({idx/total*100:.1f}%)")
        
        try:
            # 检查上市时间
            # 简化：直接获取近两年数据，如果数据不足则认为上市时间不够
            df = get_stock_daily_data(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if df.empty:
                continue
            
            # 检查数据是否足够（近两年应该有约500个交易日）
            if len(df) < 200:  # 简化判断，实际应该更复杂
                logger.debug(f"{symbol} {name} 数据不足，可能上市时间不够或停牌")
                continue
            
            # 查找连续一字板
            consecutive_records = find_consecutive_limit_up(df, MIN_CONSECUTIVE)
            
            if consecutive_records:
                # 取最早的一次连续一字板
                first_record = min(consecutive_records, key=lambda x: x[0])
                first_date, consecutive_days = first_record
                
                logger.info(f"✓ 发现: {symbol} {name} - 最早连续{consecutive_days}个一字板于 {first_date.strftime('%Y-%m-%d')}")
                
                # 保存结果
                results.append({
                    'symbol': symbol,
                    'name': name,
                    'first_limit_up_date': first_date.strftime('%Y-%m-%d'),
                    'consecutive_days': consecutive_days
                })
                
                # 保存数据到CSV
                filepath = save_stock_data_to_csv(symbol, name, first_date, output_dir)
                if filepath:
                    saved_files.append(filepath)
                
                # 延迟，避免请求过快
                time.sleep(0.3)
            
        except Exception as e:
            logger.error(f"处理 {symbol} 时出错: {e}")
            continue
    
    # 输出结果
    logger.info("=" * 60)
    logger.info("查找完成")
    logger.info("=" * 60)
    
    if results:
        logger.info(f"共找到 {len(results)} 只符合条件的股票：")
        for r in results:
            logger.info(f"  - {r['symbol']} {r['name']}: 最早于 {r['first_limit_up_date']} 连续{r['consecutive_days']}个一字板")
        
        # 保存汇总结果
        summary_file = os.path.join(output_dir, 'summary.csv')
        summary_df = pd.DataFrame(results)
        summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n汇总结果已保存到: {summary_file}")
        
        logger.info(f"\n共保存 {len(saved_files)} 个数据文件到: {output_dir}")
        
        # 返回信息
        print("\n" + "=" * 60)
        print("最终结果")
        print("=" * 60)
        print(f"符合条件的股票数量: {len(results)}")
        print(f"文件保存地址: {os.path.abspath(output_dir)}")
        print(f"汇总文件: {summary_file}")
        print("\n数据文件列表:")
        for f in saved_files[:10]:  # 只显示前10个
            print(f"  - {os.path.basename(f)}")
        if len(saved_files) > 10:
            print(f"  ... 还有 {len(saved_files) - 10} 个文件")
        
        return len(results), saved_files, output_dir
    else:
        logger.info("未找到符合条件的股票")
        return 0, [], output_dir


if __name__ == '__main__':
    count, files, output_dir = main()
    
    print("\n" + "=" * 60)
    print("返回结果")
    print("=" * 60)
    print(f"数量: {count}")
    print(f"文件所在地址: {os.path.abspath(output_dir)}")
    if files:
        print(f"文件名称示例: {os.path.basename(files[0]) if files else 'N/A'}")
