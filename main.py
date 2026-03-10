#!/usr/bin/env python3
"""
Quant Assistant - 主程序入口
支持数据管理和图表展示
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
from src.visualization.layouts.chart_layout import ChartLayout
from src.visualization.indicators.moving_average import MAIndicator
from src.visualization.indicators.macd import MACDIndicator


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


def show_chart(
    symbol: str,
    period: str = 'D',
    days: int = 30,
    ma_periods: list = None,
    show_macd: bool = False
):
    """
    显示图表
    
    Args:
        symbol: 股票代码
        period: 周期 D=日线 W=周线
        days: 显示天数
        ma_periods: MA周期列表
        show_macd: 是否显示MACD
    """
    print(f"正在加载 {symbol} 的数据...")
    
    # 查询数据
    query = DataQueryEngine()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    df = query.get_price_data(symbol, start_date, end_date)
    
    if df.empty:
        print(f"错误: 未找到 {symbol} 的数据")
        return
    
    # 创建布局管理器
    layout = ChartLayout()
    
    # 准备指标
    indicators = []
    
    # 添加MA指标
    if ma_periods:
        for p in ma_periods:
            layout.indicator_engine.register(MAIndicator(period=p))
            indicators.append(f"MA{p}")
    else:
        # 默认MA
        indicators = ['MA5', 'MA10', 'MA20']
    
    # 添加MACD
    if show_macd:
        indicators.append('MACD')
    
    # 显示图表
    print("\n" + "=" * 60)
    output = layout.display(
        df=df,
        symbol=symbol,
        period=period,
        indicators=indicators
    )
    print(output)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Quant Assistant - 量化交易助手',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 初始化数据库
  python main.py init
  
  # 更新股票列表
  python main.py update-stocks
  
  # 更新日线数据
  python main.py update-daily
  
  # 查询数据
  python main.py query --symbol 000001 --days 30
  
  # 显示K线图
  python main.py chart --symbol 000001
  
  # 显示周线
  python main.py chart --symbol 000001 --period W
  
  # 显示带MACD
  python main.py chart --symbol 000001 --macd
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # init 命令
    subparsers.add_parser('init', help='初始化数据库')
    
    # update-stocks 命令
    subparsers.add_parser('update-stocks', help='更新股票列表')
    
    # update-daily 命令
    update_parser = subparsers.add_parser('update-daily', help='更新日线数据')
    update_parser.add_argument('--symbol', '-s', help='股票代码')
    update_parser.add_argument('--start-date', help='开始日期 (YYYY-MM-DD)')
    update_parser.add_argument('--end-date', help='结束日期 (YYYY-MM-DD)')
    
    # query 命令
    query_parser = subparsers.add_parser('query', help='查询数据')
    query_parser.add_argument('--symbol', '-s', required=True, help='股票代码')
    query_parser.add_argument('--days', '-d', type=int, default=30, help='查询天数')
    
    # chart 命令 (新增)
    chart_parser = subparsers.add_parser('chart', help='显示K线图')
    chart_parser.add_argument('--symbol', '-s', required=True, help='股票代码')
    chart_parser.add_argument('--period', '-p', choices=['D', 'W'], default='D', help='周期')
    chart_parser.add_argument('--days', '-d', type=int, default=30, help='显示天数')
    chart_parser.add_argument('--ma', type=int, nargs='+', help='MA周期，例如: --ma 5 10 20')
    chart_parser.add_argument('--macd', action='store_true', help='显示MACD指标')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 设置日志
    setup_logging()
    
    if args.command == 'init':
        init_database()
    
    elif args.command == 'update-stocks':
        update_stock_list()
    
    elif args.command == 'update-daily':
        update_daily_data(args.symbol, args.start_date, args.end_date)
    
    elif args.command == 'query':
        query_data(args.symbol, args.days)
    
    elif args.command == 'chart':
        show_chart(
            symbol=args.symbol,
            period=args.period,
            days=args.days,
            ma_periods=args.ma,
            show_macd=args.macd
        )


if __name__ == '__main__':
    main()
