#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试股票数据获取功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_source.stock_data_source import StockDataSource

def test_get_stock_data():
    """测试获取股票数据"""
    ds = StockDataSource()
    
    # 测试002202
    symbol = '002202'
    print(f"\n测试获取 {symbol} 的数据...")
    
    try:
        df = ds.get_stock_data(symbol, days=60)
        if df.empty:
            print(f"❌ 获取 {symbol} 数据失败：返回空DataFrame")
        else:
            print(f"✅ 成功获取 {symbol} 数据，共 {len(df)} 条记录")
            print(f"列名: {list(df.columns)}")
            print(f"前3行:")
            print(df.head(3))
    except Exception as e:
        print(f"❌ 获取 {symbol} 数据异常: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_get_stock_data()
