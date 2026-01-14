"""快速测试美股数据保存功能"""
import os
import sys
import time
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.us_stock_collector import USStockCollector
from utils.us_stock_storage import USStockStorage

collector = USStockCollector()
storage = USStockStorage()

test_symbol = 'AAPL'

print(f"测试股票: {test_symbol}")
print("等待3秒，避免API限流...")
time.sleep(3)

print("获取数据（最近30天）...")
try:
    result = collector.collect_stock_history(test_symbol, period='30d')
    
    if result.get('success', False):
        count = result.get('count', 0)
        print(f"数据获取成功，保存了 {count} 条记录")
        
        # 从数据库读取一条数据验证
        print("\n从数据库读取数据验证...")
        data_list = storage.get_stock_history(test_symbol, limit=1)
        if data_list:
            data = data_list[0]
            print(f"成功读取数据: {data.get('symbol')}, {data.get('trade_date')}")
            print(f"包含字段数: {len(data)}")
            print(f"trade_date: {data.get('trade_date')}")
            print(f"period_type: {data.get('period_type')}")
            print(f"open_price: {data.get('open_price')}")
            print(f"close_price: {data.get('close_price')}")
            print("保存功能正常!")
        else:
            print("未能从数据库读取数据")
    else:
        print(f"数据获取失败: {result.get('message', '未知错误')}")
        print("\n可能原因：")
        print("1. API限流（yfinance有请求频率限制）")
        print("2. 网络问题")
        print("3. 股票代码错误")
        
except Exception as e:
    print(f"测试出错: {e}")
    import traceback
    traceback.print_exc()
