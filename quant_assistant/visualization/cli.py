"""
WP5: CLI Interface - 命令行交互界面
提供图表展示的命令行接口
"""
import argparse
import sys
from datetime import datetime, date, timedelta
from typing import Optional

from .layouts.chart_layout import ChartLayout
from ..data.query.data_query import DataQueryEngine
from ..utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='quant-chart',
        description='量化交易图表展示工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 显示日线K线
  python -m src.visualization.cli 000001
  
  # 显示周线
  python -m src.visualization.cli 000001 --period W
  
  # 显示带MA指标
  python -m src.visualization.cli 000001 --ma 5 10 20
  
  # 显示MACD指标
  python -m src.visualization.cli 000001 --macd
  
  # 显示最近60天
  python -m src.visualization.cli 000001 --days 60
        """
    )
    
    parser.add_argument(
        'symbol',
        type=str,
        help='股票代码 (例如: 000001)'
    )
    
    parser.add_argument(
        '--period', '-p',
        type=str,
        choices=['D', 'W', 'M'],
        default='D',
        help='周期: D=日线, W=周线, M=月线 (默认: D)'
    )
    
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=30,
        help='显示最近N天的数据 (默认: 30)'
    )
    
    parser.add_argument(
        '--ma',
        type=int,
        nargs='+',
        default=None,
        help='显示移动平均线，例如: --ma 5 10 20'
    )
    
    parser.add_argument(
        '--macd',
        action='store_true',
        help='显示MACD指标'
    )
    
    parser.add_argument(
        '--no-table',
        action='store_true',
        help='不显示数据表格'
    )
    
    parser.add_argument(
        '--no-chart',
        action='store_true',
        help='不显示K线图'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        help='开始日期 (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        help='结束日期 (YYYY-MM-DD)'
    )
    
    return parser


def run_chart_command(args: argparse.Namespace) -> int:
    """
    执行图表命令
    
    Args:
        args: 命令行参数
        
    Returns:
        int: 退出码 0=成功, 1=失败
    """
    symbol = args.symbol
    period = args.period
    days = args.days
    
    # 设置日志
    setup_logging()
    
    logger.info(f"开始绘制图表: {symbol}, 周期={period}, 天数={days}")
    
    # 计算日期范围
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
    else:
        end_date = date.today()
    
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=days)
    
    # 查询数据
    try:
        query = DataQueryEngine()
        df = query.get_price_data(symbol, start_date, end_date)
        
        if df.empty:
            print(f"错误: 未找到 {symbol} 的数据")
            return 1
        
        logger.info(f"获取到 {len(df)} 条数据")
        
    except Exception as e:
        logger.error(f"数据查询失败: {e}")
        print(f"错误: 无法获取数据 - {e}")
        return 1
    
    # 创建布局管理器
    layout = ChartLayout()
    
    # 确定要显示的指标
    indicators = []
    if args.ma:
        # 注册MA指标
        from .indicators.moving_average import MAIndicator
        for p in args.ma:
            layout.indicator_engine.register(MAIndicator(period=p))
            indicators.append(f"MA{p}")
    
    if args.macd:
        indicators.append('MACD')
    
    # 如果没有指定指标，使用默认MA
    if not indicators and not args.no_chart:
        indicators = ['MA5', 'MA10', 'MA20']
    
    # 显示图表
    try:
        output = layout.display(
            df=df,
            symbol=symbol,
            period=period,
            indicators=indicators if indicators else None,
            show_table=not args.no_table,
            show_chart=not args.no_chart
        )
        
        print(output)
        
    except Exception as e:
        logger.error(f"图表渲染失败: {e}")
        print(f"错误: 图表渲染失败 - {e}")
        return 1
    
    logger.info("图表展示完成")
    return 0


def main():
    """主入口"""
    parser = create_parser()
    args = parser.parse_args()
    
    exit_code = run_chart_command(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
