"""
Quant Assistant 命令行工具

提供便捷的命令行接口来使用框架功能。

用法:
    quant data get 300751 --start 2024-01-01
    quant factor ma 300751 --window 20
    quant backtest run ma_cross --symbol 300751
"""

import sys
import argparse
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from quant_assistant.api import QuantAPI
from quant_assistant.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        prog='quant',
        description='Quant Assistant - 个人量化交易框架',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  quant data get 300751 --start 2024-01-01      获取迈为股份数据
  quant factor ma 300751 --window 20            计算20日均线
  quant factor all 300751                       计算所有指标
  quant backtest run ma_cross --symbol 300751   运行回测
  quant ml train 300751 --model xgboost         训练预测模型
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 数据命令
    data_parser = subparsers.add_parser('data', help='数据操作')
    data_subparsers = data_parser.add_subparsers(dest='data_cmd')
    
    # 数据获取
    data_get = data_subparsers.add_parser('get', help='获取股票数据')
    data_get.add_argument('symbol', help='股票代码')
    data_get.add_argument('--start', '-s', help='开始日期 (YYYY-MM-DD)')
    data_get.add_argument('--end', '-e', help='结束日期 (YYYY-MM-DD)')
    data_get.add_argument('--period', '-p', default='daily', 
                         choices=['daily', 'weekly', 'monthly'],
                         help='数据周期')
    data_get.add_argument('--save', action='store_true', help='保存到数据库')
    
    # 数据查询
    data_query = data_subparsers.add_parser('query', help='查询数据')
    data_query.add_argument('symbol', help='股票代码')
    data_query.add_argument('--days', '-d', type=int, default=30, help='查询天数')
    
    # 股票列表
    data_list = data_subparsers.add_parser('list', help='获取股票列表')
    data_list.add_argument('--market', '-m', default='all',
                          choices=['all', 'sh', 'sz', 'bj'],
                          help='市场')
    
    # 因子命令
    factor_parser = subparsers.add_parser('factor', help='因子计算')
    factor_subparsers = factor_parser.add_subparsers(dest='factor_cmd')
    
    # MA
    factor_ma = factor_subparsers.add_parser('ma', help='移动平均线')
    factor_ma.add_argument('symbol', help='股票代码')
    factor_ma.add_argument('--window', '-w', type=int, default=20, help='窗口')
    factor_ma.add_argument('--start', '-s', help='开始日期')
    factor_ma.add_argument('--end', '-e', help='结束日期')
    
    # MACD
    factor_macd = factor_subparsers.add_parser('macd', help='MACD指标')
    factor_macd.add_argument('symbol', help='股票代码')
    factor_macd.add_argument('--start', '-s', help='开始日期')
    factor_macd.add_argument('--end', '-e', help='结束日期')
    
    # RSI
    factor_rsi = factor_subparsers.add_parser('rsi', help='RSI指标')
    factor_rsi.add_argument('symbol', help='股票代码')
    factor_rsi.add_argument('--window', '-w', type=int, default=14, help='窗口')
    factor_rsi.add_argument('--start', '-s', help='开始日期')
    factor_rsi.add_argument('--end', '-e', help='结束日期')
    
    # 所有指标
    factor_all = factor_subparsers.add_parser('all', help='所有指标')
    factor_all.add_argument('symbol', help='股票代码')
    factor_all.add_argument('--start', '-s', help='开始日期')
    factor_all.add_argument('--end', '-e', help='结束日期')
    factor_all.add_argument('--output', '-o', help='输出文件')
    
    # 回测命令
    backtest_parser = subparsers.add_parser('backtest', help='回测操作')
    backtest_subparsers = backtest_parser.add_subparsers(dest='backtest_cmd')
    
    # 运行回测
    bt_run = backtest_subparsers.add_parser('run', help='运行回测')
    bt_run.add_argument('strategy', help='策略名称')
    bt_run.add_argument('--symbol', '-s', required=True, help='股票代码')
    bt_run.add_argument('--start', help='开始日期')
    bt_run.add_argument('--end', help='结束日期')
    bt_run.add_argument('--capital', '-c', type=float, default=100000, help='初始资金')
    bt_run.add_argument('--commission', type=float, default=0.0003, help='手续费率')
    
    # ML命令
    ml_parser = subparsers.add_parser('ml', help='机器学习')
    ml_subparsers = ml_parser.add_subparsers(dest='ml_cmd')
    
    # 训练模型
    ml_train = ml_subparsers.add_parser('train', help='训练模型')
    ml_train.add_argument('symbol', help='股票代码')
    ml_train.add_argument('--model', '-m', default='random_forest',
                         choices=['random_forest', 'gradient_boosting', 'linear'],
                         help='模型类型')
    ml_train.add_argument('--start', '-s', help='训练开始日期')
    ml_train.add_argument('--end', '-e', help='训练结束日期')
    ml_train.add_argument('--days', '-d', type=int, default=252, help='训练天数')
    
    # 版本命令
    version_parser = subparsers.add_parser('version', help='显示版本')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    api = QuantAPI()
    
    try:
        if args.command == 'data':
            handle_data_command(api, args)
        elif args.command == 'factor':
            handle_factor_command(api, args)
        elif args.command == 'backtest':
            handle_backtest_command(api, args)
        elif args.command == 'ml':
            handle_ml_command(api, args)
        elif args.command == 'version':
            from quant_assistant import __version__
            print(f"Quant Assistant v{__version__}")
    except Exception as e:
        logger.error(f"命令执行失败: {e}")
        raise


def handle_data_command(api: QuantAPI, args):
    """处理数据命令"""
    if args.data_cmd == 'get':
        # 获取数据
        data = api.data.get_stock_data(
            symbol=args.symbol,
            start=args.start,
            end=args.end,
            period=args.period
        )
        print(f"\n获取到 {len(data)} 条数据:")
        print(data.tail(10))
        
        if args.save:
            api.data.save(data, 'daily_quotes')
            print(f"\n数据已保存到数据库")
    
    elif args.data_cmd == 'query':
        # 查询数据
        end = datetime.now()
        start = end - timedelta(days=args.days)
        data = api.data.query(
            table='daily_quotes',
            symbol=args.symbol,
            start=start.strftime('%Y-%m-%d'),
            end=end.strftime('%Y-%m-%d')
        )
        print(f"\n查询到 {len(data)} 条数据:")
        print(data)
    
    elif args.data_cmd == 'list':
        # 获取股票列表
        stocks = api.data.get_stock_list(market=args.market)
        print(f"\n共 {len(stocks)} 只股票:")
        print(stocks.head(20))


def handle_factor_command(api: QuantAPI, args):
    """处理因子命令"""
    # 获取数据
    data = api.data.get_stock_data(
        symbol=args.symbol,
        start=args.start,
        end=args.end
    )
    
    if args.factor_cmd == 'ma':
        result = api.factors.ma(data, window=args.window)
        print(f"\n{args.window}日移动平均线:")
        print(result.tail(10))
    
    elif args.factor_cmd == 'macd':
        result = api.factors.macd(data)
        print(f"\nMACD指标:")
        df = pd.DataFrame(result)
        print(df.tail(10))
    
    elif args.factor_cmd == 'rsi':
        result = api.factors.rsi(data, window=args.window)
        print(f"\nRSI({args.window}):")
        print(result.tail(10))
    
    elif args.factor_cmd == 'all':
        result = api.factors.compute_all(data)
        print(f"\n所有技术指标:")
        print(result.tail(10))
        
        if args.output:
            result.to_csv(args.output)
            print(f"\n结果已保存到 {args.output}")


def handle_backtest_command(api: QuantAPI, args):
    """处理回测命令"""
    # 获取数据
    data = api.data.get_stock_data(
        symbol=args.symbol,
        start=args.start,
        end=args.end
    )
    
    # 创建策略
    strategy = api.strategy.create(args.strategy)
    
    # 运行回测
    result = api.backtest.run(
        strategy=strategy,
        data=data,
        initial_capital=args.capital,
        commission=args.commission
    )
    
    # 分析结果
    analysis = api.backtest.analyze(result)
    
    print("\n========== 回测结果 ==========")
    print(f"策略: {args.strategy}")
    print(f"标的: {args.symbol}")
    print(f"初始资金: {args.capital:,.2f}")
    print(f"最终资金: {analysis.get('final_value', 0):,.2f}")
    print(f"总收益率: {analysis.get('total_return', 0)*100:.2f}%")
    print(f"年化收益率: {analysis.get('annual_return', 0)*100:.2f}%")
    print(f"最大回撤: {analysis.get('max_drawdown', 0)*100:.2f}%")
    print(f"夏普比率: {analysis.get('sharpe_ratio', 0):.2f}")
    print(f"交易次数: {analysis.get('total_trades', 0)}")
    print("==============================")


def handle_ml_command(api: QuantAPI, args):
    """处理ML命令"""
    if args.ml_cmd == 'train':
        # 获取训练数据
        end = datetime.now()
        start = end - timedelta(days=args.days)
        data = api.data.get_stock_data(
            symbol=args.symbol,
            start=start.strftime('%Y-%m-%d'),
            end=end.strftime('%Y-%m-%d')
        )
        
        # 计算特征
        data = api.factors.compute_all(data)
        
        # 训练模型
        predictor = api.ml.train(
            data,
            model_type=args.model
        )
        
        # 评估
        metrics = api.ml.evaluate(predictor, data)
        
        print(f"\n模型训练完成:")
        print(f"模型类型: {args.model}")
        print(f"训练样本: {len(data)}")
        print(f"MSE: {metrics.get('mse', 0):.4f}")
        print(f"RMSE: {metrics.get('rmse', 0):.4f}")
        print(f"MAE: {metrics.get('mae', 0):.4f}")
        print(f"R²: {metrics.get('r2', 0):.4f}")


if __name__ == '__main__':
    main()
