"""
测试资金流向数据存储（简化版）
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage
from datetime import date

print("测试资金流向数据收集和存储...")
print("="*60)

symbol = "600519"
test_date = date.today().strftime("%Y-%m-%d")

print(f"\n1. 收集数据")
collector = StockHistoryCollector()
data = collector.collect_stock_daily_data(symbol, test_date)

if data:
    print(f"收集成功")
    print(f"  main_net_inflow: {data.get('main_net_inflow')}")
    print(f"  super_large_inflow: {data.get('super_large_inflow')}")
    print(f"  large_inflow: {data.get('large_inflow')}")
    print(f"  medium_inflow: {data.get('medium_inflow')}")
    print(f"  small_inflow: {data.get('small_inflow')}")
    
    print(f"\n2. 保存数据到数据库")
    storage = StockHistoryStorage()
    result = storage.save_stock_daily_data(symbol, test_date, data)
    print(f"保存结果: {result}")
    
    if result:
        print(f"\n3. 从数据库读取数据验证")
        stored_data = storage.get_stock_history_data(symbol, test_date, test_date)
        if stored_data and len(stored_data) > 0:
            record = stored_data[0]
            print(f"读取成功")
            print(f"  main_net_inflow: {record.get('main_net_inflow')}")
            print(f"  super_large_inflow: {record.get('super_large_inflow')}")
            print(f"  large_inflow: {record.get('large_inflow')}")
            print(f"  medium_inflow: {record.get('medium_inflow')}")
            print(f"  small_inflow: {record.get('small_inflow')}")
            
            # 验证数据一致性
            print(f"\n4. 数据一致性验证")
            fields = ['main_net_inflow', 'super_large_inflow', 'large_inflow', 'medium_inflow', 'small_inflow']
            all_match = True
            for field in fields:
                original = data.get(field)
                stored = record.get(field)
                match = (original == stored) or (original is None and stored is None)
                status = "OK" if match else "MISMATCH"
                print(f"  {field}: {status} (原始: {original}, 存储: {stored})")
                if not match:
                    all_match = False
            
            if all_match:
                print(f"\n结论: 所有资金流向字段都正确获取和存储")
            else:
                print(f"\n结论: 部分字段不匹配，需要检查")
        else:
            print("从数据库读取失败或数据为空")
    else:
        print("保存失败")
else:
    print("数据收集失败")
