#!/usr/bin/env python3
"""
数据管理层主程序 - Phase 1
"""
import os
import sys
import argparse
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.fetcher.akshare_fetcher import AKShareFetcher
from src.storage.mysql_storage import MySQLStorage
from src.query.data_query import DataQueryEngine
from src.database.connection import db_manager
from src.utils.logger import setup_logging


def init_database():
    """初始化数据库"""
    print("初始化数据库...")
    
    if not db_manager.test_connection():
        print("数据库连接失败，请检查配置")
        return False
    
    storage = MySQLStorage()
    print("数据库初始化完成")
    return True


def update_stock_list():
    """更新股票列表"""
    print("更新股票列表...")
    
    fetcher = AKShareFetcher()
    storage = MySQLStorage()
    
    df = fetcher.get_stock_list()
    count = storage.save_stocks(df)
    
    print(f"成功更新 {count} 只股票")


def update_daily_data(symbol: str = None, start_date: str = None, end_date: str = None):
    """更新日线数据"""
    fetcher = AKShareFetcher()
    storage = MySQLStorage()
    
    if end_date is None:
        end_date = date.today().strftime('%Y-%m-%d')
    
    if symbol:
        symbols = [symbol]
    else:
        from src.config import data_config
        symbols = data_config.default_symbols
    
    for sym in symbols:
        try:
            last_date = storage.get_last_update_date(sym)
            
            if start_date is None:
                if last_date:
                    start = last_date + timedelta(days=1)
                    start_date = start.strftime('%Y-%m-%d')
                else:
                    from src.config import data_config
                    start_date = data_config.history_start_date
            
            df = fetcher.get_daily_quotes(sym, start_date, end_date)
            
            if not df.empty:
                storage.save_daily_quotes(df)
                print(f"[{sym}] 更新完成: {len(df)} 条数据")
            else:
                print(f"[{sym}] 无新数据")
                
        except Exception as e:
            print(f"[{sym}] 更新失败: {e}")


def query_data(symbol: str, days: int = 30):
    """查询数据示例"""
    query = DataQueryEngine()
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    df = query.get_price_data(symbol, start_date, end_date)
    
    if df.empty:
        print(f"未找到 {symbol} 的数据")
        return
    
    print(f"\n{symbol} 最近 {days} 天数据:")
    print(df.tail(10).to_string(index=False))
    
    latest = query.get_latest_price(symbol)
    if latest:
        print(f"\n最新价格: {latest['close']}, 涨跌幅: {latest['change_pct']}%")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='量化数据管理工具')
    parser.add_argument(
        'command',
        choices=['init', 'update-stocks', 'update-daily', 'query'],
        help='要执行的命令'
    )
    parser.add_argument('--symbol', '-s', help='股票代码')
    parser.add_argument('--start-date', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--days', '-d', type=int, default=30, help='查询天数')
    
    args = parser.parse_args()
    
    setup_logging()
    
    if args.command == 'init':
        init_database()
    
    elif args.command == 'update-stocks':
        update_stock_list()
    
    elif args.command == 'update-daily':
        update_daily_data(args.symbol, args.start_date, args.end_date)
    
    elif args.command == 'query':
        if not args.symbol:
            print("请指定股票代码: --symbol 000001")
            return
        query_data(args.symbol, args.days)


if __name__ == '__main__':
    main()
