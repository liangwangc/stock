"""
测试 get_main_force_capital API调用
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import akshare as ak
import pandas as pd

symbol = "600519"

print("测试 get_main_force_capital 使用的API...")
print("="*60)

# 测试方法1的API调用
print("\n方法1: stock_individual_fund_flow(symbol=..., indicator='今日')")
try:
    df = ak.stock_individual_fund_flow(symbol=symbol, indicator="今日")
    print(f"  成功，shape: {df.shape if not df.empty else 'Empty'}")
    if not df.empty:
        print(f"  列名: {list(df.columns)[:5]}")
except Exception as e:
    print(f"  错误: {str(e)[:200]}")

# 测试方法2的API调用（正确的方式）
print("\n方法2: stock_individual_fund_flow(stock=..., market='sh')")
try:
    df = ak.stock_individual_fund_flow(stock=symbol, market="sh")
    print(f"  成功，shape: {df.shape if not df.empty else 'Empty'}")
    if not df.empty:
        print(f"  列名: {list(df.columns)[:5]}")
        latest = df.iloc[-1]
        print(f"  最新数据: {latest.to_dict()}")
except Exception as e:
    print(f"  错误: {str(e)[:200]}")
