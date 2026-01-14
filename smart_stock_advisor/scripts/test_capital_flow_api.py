"""
测试资金流向API
检查akshare中可用的资金流向API
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import akshare as ak
import pandas as pd

def test_apis():
    """测试各种资金流向API"""
    symbol = "600519"
    
    print("="*80)
    print("测试资金流向API")
    print("="*80)
    
    # 测试1: stock_zh_a_spot_em
    print("\n1. 测试 stock_zh_a_spot_em (实时行情)")
    try:
        df = ak.stock_zh_a_spot_em()
        if not df.empty:
            print(f"   成功获取数据，共 {len(df)} 行")
            print(f"   列名: {list(df.columns)[:10]}")
            # 查找资金流向相关列
            flow_cols = [c for c in df.columns if any(kw in str(c) for kw in ['资金', '流入', '流出', '主力'])]
            print(f"   资金流向相关列: {flow_cols[:5]}")
            # 查找600519
            code_col = None
            for col in df.columns:
                if '代码' in str(col) or str(col).lower() in ['code', 'symbol']:
                    code_col = col
                    break
            if code_col:
                row = df[df[code_col] == symbol]
                if not row.empty:
                    print(f"   找到 {symbol} 的数据")
                    # 尝试提取资金流向数据
                    for col in flow_cols:
                        try:
                            val = row.iloc[0][col]
                            print(f"   {col}: {val}")
                        except:
                            pass
                else:
                    print(f"   未找到 {symbol} 的数据")
        else:
            print("   返回空数据")
    except Exception as e:
        print(f"   错误: {str(e)}")
    
    # 测试2: stock_individual_fund_flow
    print("\n2. 测试 stock_individual_fund_flow (个股资金流向)")
    try:
        df = ak.stock_individual_fund_flow(stock=symbol, market="sh")
        if not df.empty:
            print(f"   成功获取数据，共 {len(df)} 行")
            print(f"   列名: {list(df.columns)}")
            print(f"   最新数据: {df.iloc[-1].to_dict()}")
        else:
            print("   返回空数据")
    except Exception as e:
        print(f"   错误: {str(e)}")
    
    # 测试3: stock_individual_fund_flow_rank
    print("\n3. 测试 stock_individual_fund_flow_rank (资金流向排名)")
    try:
        df = ak.stock_individual_fund_flow_rank(indicator="今日")
        if not df.empty:
            print(f"   成功获取数据，共 {len(df)} 行")
            print(f"   列名: {list(df.columns)[:10]}")
            # 查找600519
            code_col = None
            for col in df.columns:
                if '代码' in str(col) or 'code' in str(col).lower():
                    code_col = col
                    break
            if code_col:
                row = df[df[code_col].astype(str).str.contains(symbol)]
                if not row.empty:
                    print(f"   找到 {symbol} 的数据")
                    print(f"   数据: {row.iloc[0].to_dict()}")
                else:
                    print(f"   未找到 {symbol} 的数据（显示前5条）")
                    print(df.head(5))
        else:
            print("   返回空数据")
    except Exception as e:
        print(f"   错误: {str(e)}")
    
    # 测试4: 尝试其他可能的API
    print("\n4. 尝试其他可能的API")
    apis_to_try = [
        'stock_fund_flow_individual',
        'stock_fund_flow_detail',
        'stock_individual_fund_flow_rank_hist',
    ]
    
    for api_name in apis_to_try:
        try:
            api_func = getattr(ak, api_name, None)
            if api_func:
                print(f"   找到 {api_name}，尝试调用...")
                # 尝试调用（可能需要不同的参数）
                try:
                    if 'individual' in api_name:
                        result = api_func(stock=symbol)
                    elif 'rank' in api_name:
                        result = api_func(indicator="今日")
                    else:
                        result = api_func(symbol=symbol)
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        print(f"   {api_name}: 成功，共 {len(result)} 行")
                    else:
                        print(f"   {api_name}: 返回空数据或非DataFrame")
                except Exception as e:
                    print(f"   {api_name}: 调用失败 - {str(e)[:100]}")
        except Exception as e:
            pass

if __name__ == '__main__':
    test_apis()
