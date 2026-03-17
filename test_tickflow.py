#!/usr/bin/env python3
"""
TickFlow 数据获取器测试脚本

测试免费版 API 功能:
- 交易所列表
- 股票列表
- 日线数据
- 财务数据

使用方法:
    python test_tickflow.py
"""
import sys
import pandas as pd
from datetime import datetime, timedelta

# 直接导入 tickflow_fetcher 模块，不依赖其他模块
import importlib.util
spec = importlib.util.spec_from_file_location(
    'tickflow_fetcher', 
    '/home/admin/.openclaw/workspace/quant-assistant-github/quant_assistant/data/fetcher/tickflow_fetcher.py'
)
tickflow_module = importlib.util.module_from_spec(spec)
sys.modules['tickflow_fetcher'] = tickflow_module

# 需要模拟 base_fetcher
base_spec = importlib.util.spec_from_file_location(
    'base_fetcher',
    '/home/admin/.openclaw/workspace/quant-assistant-github/quant_assistant/data/fetcher/base_fetcher.py'
)
base_module = importlib.util.module_from_spec(base_spec)
sys.modules['base_fetcher'] = base_module
base_spec.loader.exec_module(base_module)

# 现在执行 tickflow_fetcher
spec.loader.exec_module(tickflow_module)
TickFlowFetcher = tickflow_module.TickFlowFetcher


def test_free_version():
    """测试免费版功能"""
    print("=" * 60)
    print("测试 TickFlow 免费版数据获取器")
    print("=" * 60)
    
    # 创建免费版获取器
    fetcher = TickFlowFetcher()
    print(f"\n✓ 创建获取器: {fetcher}")
    
    # 测试服务可用性
    print("\n[1/5] 测试服务可用性...")
    try:
        if fetcher.is_available():
            print("  ✓ TickFlow 服务可用")
        else:
            print("  ✗ TickFlow 服务不可用")
            return
    except Exception as e:
        print(f"  ✗ 检查服务可用性失败: {e}")
        return
    
    # 测试获取交易所列表
    print("\n[2/5] 获取交易所列表...")
    try:
        exchanges = fetcher.get_exchanges()
        print(f"  ✓ 获取到 {len(exchanges)} 个交易所")
        if not exchanges.empty:
            print(f"  交易所: {', '.join(exchanges['code'].tolist()[:5])}...")
    except Exception as e:
        print(f"  ✗ 获取失败: {e}")
    
    # 测试获取股票列表
    print("\n[3/5] 获取股票列表...")
    try:
        # 只获取上交所前10只股票作为测试
        stocks = fetcher.get_stock_list('SH')
        print(f"  ✓ 获取到 {len(stocks)} 只股票")
        if not stocks.empty:
            print(f"  示例股票:")
            for _, row in stocks.head(3).iterrows():
                print(f"    - {row['symbol']}: {row['name']}")
    except Exception as e:
        print(f"  ✗ 获取失败: {e}")
    
    # 测试获取日线数据
    print("\n[4/5] 获取日线数据...")
    try:
        # 获取浦发银行近30天数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        df = fetcher.get_daily_quotes(
            '600000',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
        
        if not df.empty:
            print(f"  ✓ 获取到 {len(df)} 条日线数据")
            print(f"  数据列: {', '.join(df.columns.tolist())}")
            print(f"  最新数据:")
            print(f"    日期: {df.iloc[-1]['trade_date']}")
            print(f"    开盘: {df.iloc[-1]['open']}")
            print(f"    收盘: {df.iloc[-1]['close']}")
            print(f"    最高: {df.iloc[-1]['high']}")
            print(f"    最低: {df.iloc[-1]['low']}")
            print(f"    成交量: {df.iloc[-1]['volume']}")
        else:
            print("  ! 返回空数据（可能日期范围内无交易）")
    except Exception as e:
        print(f"  ✗ 获取失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试获取财务数据
    print("\n[5/5] 获取财务数据...")
    try:
        df = fetcher.get_financial_indicators('600000.SH')
        if not df.empty:
            print(f"  ✓ 获取到 {len(df)} 条财务指标")
            print(f"  数据列: {', '.join(df.columns.tolist()[:5])}...")
        else:
            print("  ! 无财务数据")
    except Exception as e:
        print(f"  ✗ 获取失败: {e}")
    
    print("\n" + "=" * 60)
    print("免费版测试完成")
    print("=" * 60)


def test_paid_version_placeholder():
    """测试付费版接口（仅验证会抛出正确错误）"""
    print("\n" + "=" * 60)
    print("测试 TickFlow 付费版接口（预期会提示需要付费版）")
    print("=" * 60)
    
    fetcher = TickFlowFetcher()  # 免费版
    
    # 测试分钟数据（应该报错）
    print("\n[1/2] 测试分钟数据接口...")
    try:
        df = fetcher.get_minute_quotes('600000.SH', period='5m')
        print("  ! 意外获取到数据")
    except Exception as e:
        if "付费版" in str(e):
            print(f"  ✓ 正确提示需要付费版")
        else:
            print(f"  ✗ 其他错误: {e}")
    
    # 测试实时行情（应该报错）
    print("\n[2/2] 测试实时行情接口...")
    try:
        df = fetcher.get_realtime_quotes(['600000.SH'])
        print("  ! 意外获取到数据")
    except Exception as e:
        if "付费版" in str(e):
            print(f"  ✓ 正确提示需要付费版")
        else:
            print(f"  ✗ 其他错误: {e}")
    
    print("\n" + "=" * 60)
    print("付费版接口测试完成")
    print("=" * 60)


def test_paid_version_with_key():
    """测试付费版初始化（使用模拟 API Key）"""
    print("\n" + "=" * 60)
    print("测试付费版初始化")
    print("=" * 60)
    
    # 创建付费版获取器（使用模拟 key）
    fetcher = TickFlowFetcher(api_key='demo-key', use_paid=True)
    print(f"\n✓ 创建付费版获取器: {fetcher}")
    print("  注意: 使用模拟 API Key，实际请求会失败")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    try:
        test_free_version()
        test_paid_version_placeholder()
        test_paid_version_with_key()
        
        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
