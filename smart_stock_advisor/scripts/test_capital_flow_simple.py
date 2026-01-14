"""
简单测试资金流向API解析
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import akshare as ak
import pandas as pd

# 测试股票
symbol = "600519"

print("测试资金流向API解析...")
print("="*60)

# 获取数据
try:
    df = ak.stock_individual_fund_flow(stock=symbol, market="sh")
    if df.empty:
        print("API返回空数据")
    else:
        print(f"成功获取数据，共 {len(df)} 行")
        latest = df.iloc[-1]
        
        # 打印所有列名和数据
        print("\n列名和对应数据：")
        for col in df.columns:
            col_str = str(col)
            value = latest[col]
            print(f"  {col_str}: {value}")
            
            # 尝试匹配
            if '主力' in col_str and ('净流入' in col_str or '净额' in col_str):
                print(f"    -> 匹配主力净流入: {value}")
            elif '超大单' in col_str and ('净流入' in col_str or '净额' in col_str):
                print(f"    -> 匹配超大单净流入: {value}")
            elif '大单' in col_str and '超大' not in col_str and ('净流入' in col_str or '净额' in col_str):
                print(f"    -> 匹配大单净流入: {value}")
            elif '中单' in col_str and ('净流入' in col_str or '净额' in col_str):
                print(f"    -> 匹配中单净流入: {value}")
            elif '小单' in col_str and ('净流入' in col_str or '净额' in col_str):
                print(f"    -> 匹配小单净流入: {value}")
        
        print("\n测试代码逻辑...")
        result = {}
        for col in df.columns:
            try:
                value = latest[col]
                if pd.notna(value):
                    col_str = str(col).strip()
                    try:
                        val = float(value)
                    except:
                        continue
                    
                    if ('主力' in col_str or 'main' in col_str.lower()) and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                        if 'main_net_inflow' not in result:
                            result['main_net_inflow'] = val
                            print(f"  提取主力净流入: {val}")
                    elif ('超大单' in col_str or 'super' in col_str.lower()) and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                        if 'super_large_net_inflow' not in result:
                            result['super_large_net_inflow'] = val
                            print(f"  提取超大单净流入: {val}")
                    elif ('大单' in col_str and '超大' not in col_str) and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                        if 'large_net_inflow' not in result:
                            result['large_net_inflow'] = val
                            print(f"  提取大单净流入: {val}")
                    elif '中单' in col_str and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                        if 'medium_net_inflow' not in result:
                            result['medium_net_inflow'] = val
                            print(f"  提取中单净流入: {val}")
                    elif '小单' in col_str and ('净流入' in col_str or '净额' in col_str or 'net' in col_str.lower()):
                        if 'small_net_inflow' not in result:
                            result['small_net_inflow'] = val
                            print(f"  提取小单净流入: {val}")
            except Exception as e:
                print(f"  处理列 {col} 时出错: {str(e)}")
        
        print(f"\n最终结果: {result}")
        
except Exception as e:
    import traceback
    print(f"错误: {str(e)}")
    traceback.print_exc()
