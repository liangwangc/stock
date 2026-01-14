"""快速测试SQL修复是否成功"""
import os
import sys
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage

collector = StockHistoryCollector()
storage = StockHistoryStorage()

test_symbol = '000001'
test_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

print(f"测试股票: {test_symbol}, 日期: {test_date}")
print("获取数据...")
data = collector.collect_stock_daily_data(test_symbol, test_date)

if data:
    print("数据获取成功")
    print(f"包含字段: {len(data)} 个")
    print(f"trade_date: {data.get('trade_date')}")
    print(f"period_type: {data.get('period_type')}")
    print("保存到数据库...")
    try:
        success = storage.save_stock_daily_data(test_symbol, test_date, data)
        if success:
            print("保存成功!")
        else:
            print("保存失败")
    except Exception as e:
        print(f"保存错误: {e}")
        import traceback
        traceback.print_exc()
else:
    print("数据获取失败")
