"""
测试获取前一天美股板块走势
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from data_source.us_stock_data_source import USStockDataSource

print("=" * 60)
print("测试获取前一天美股板块走势")
print("=" * 60)

try:
    ds = USStockDataSource()
    
    print("\n正在获取所有板块前一天的走势数据...")
    result = ds.get_all_sectors_yesterday_performance()
    
    print("\n" + "=" * 60)
    print("结果汇总")
    print("=" * 60)
    
    success_count = 0
    for sector_name, data in result.items():
        if data.get('success', False):
            success_count += 1
            change_pct = data.get('change_pct')
            change_str = f"{change_pct:+.2f}%" if change_pct is not None else "N/A"
            print(f"{sector_name:25s} ({data['symbol']:5s}): 收盘 {data['close']:8.2f}, 涨跌 {change_str:>8s}")
        else:
            print(f"{sector_name:25s} ({data.get('symbol', 'N/A'):5s}): 失败 - {data.get('message', '未知错误')}")
    
    print("\n" + "=" * 60)
    print(f"成功: {success_count}/{len(result)} 个板块")
    print("=" * 60)
    
except Exception as e:
    print(f"错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
