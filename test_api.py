#!/usr/bin/env python3
"""
测试 QuantAPI 是否能正常工作
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from quant_assistant import QuantAPI
    
    print("正在初始化 QuantAPI...")
    api = QuantAPI()
    
    print("\n测试获取股票列表...")
    try:
        stocks = api.data.get_stock_list()
        print(f"✓ 获取到 {len(stocks)} 只股票")
        print(f"  前5只: {stocks.head()}")
    except Exception as e:
        print(f"✗ 获取股票列表失败: {e}")
    
    print("\n测试获取股票数据...")
    try:
        data = api.data.get_stock_data(
            symbol='300751',
            start='2024-01-01',
            end='2024-01-31'
        )
        print(f"✓ 获取到 {len(data)} 条数据")
        print(f"  数据预览:\n{data.head()}")
    except Exception as e:
        print(f"✗ 获取股票数据失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n测试完成!")
    
except ImportError as e:
    print(f"导入失败: {e}")
    import traceback
    traceback.print_exc()
