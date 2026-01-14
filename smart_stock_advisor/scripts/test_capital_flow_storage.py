"""
测试资金流向数据存储
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data_source.stock_data_source import StockDataSource
from utils.stock_history_collector import StockHistoryCollector
from datetime import datetime, date

print("测试资金流向数据收集和存储...")
print("="*60)

symbol = "600519"
test_date = date.today().strftime("%Y-%m-%d")

print(f"\n1. 测试 get_realtime_capital_flow API")
ds = StockDataSource()
capital_flow = ds.get_realtime_capital_flow(symbol)
print(f"API返回的字段: {list(capital_flow.keys())}")
print(f"数据: {capital_flow}")

print(f"\n2. 测试 StockHistoryCollector.collect_stock_daily_data")
collector = StockHistoryCollector()
data = collector.collect_stock_daily_data(symbol, test_date)

if data:
    print(f"\n收集到的资金流向字段:")
    print(f"  main_net_inflow: {data.get('main_net_inflow')}")
    print(f"  super_large_inflow: {data.get('super_large_inflow')}")
    print(f"  large_inflow: {data.get('large_inflow')}")
    print(f"  medium_inflow: {data.get('medium_inflow')}")
    print(f"  small_inflow: {data.get('small_inflow')}")
    
    # 检查字段映射
    print(f"\n字段映射检查:")
    print(f"  API返回 'super_large_net_inflow': {capital_flow.get('super_large_net_inflow')}")
    print(f"  存储字段 'super_large_inflow': {data.get('super_large_inflow')}")
    print(f"  映射是否正确: {capital_flow.get('super_large_net_inflow') == data.get('super_large_inflow')}")
    
    print(f"  API返回 'large_net_inflow': {capital_flow.get('large_net_inflow')}")
    print(f"  存储字段 'large_inflow': {data.get('large_inflow')}")
    print(f"  映射是否正确: {capital_flow.get('large_net_inflow') == data.get('large_inflow')}")
    
    print(f"  API返回 'medium_net_inflow': {capital_flow.get('medium_net_inflow')}")
    print(f"  存储字段 'medium_inflow': {data.get('medium_inflow')}")
    print(f"  映射是否正确: {capital_flow.get('medium_net_inflow') == data.get('medium_inflow')}")
    
    print(f"  API返回 'small_net_inflow': {capital_flow.get('small_net_inflow')}")
    print(f"  存储字段 'small_inflow': {data.get('small_inflow')}")
    print(f"  映射是否正确: {capital_flow.get('small_net_inflow') == data.get('small_inflow')}")
else:
    print("数据收集失败")
