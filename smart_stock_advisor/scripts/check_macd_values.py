"""
检查MACD数值差异问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_connection import DatabaseConnection
import pandas as pd

def check_macd_values():
    """检查MACD数值差异"""
    db = DatabaseConnection()
    
    # 查询16号前后的数据
    sql = """
    SELECT symbol, trade_date, close_price, macd, macd_signal, macd_hist, data_source
    FROM stock_history_data 
    WHERE trade_date >= '2026-01-15' AND trade_date <= '2026-01-17'
    AND macd IS NOT NULL 
    ORDER BY symbol, trade_date
    LIMIT 100
    """
    
    results = db.execute_query(sql)
    
    if not results:
        print("未找到数据")
        return
    
    df = pd.DataFrame(results)
    
    print("=" * 100)
    print("MACD数值检查（16号前后对比）")
    print("=" * 100)
    print(f"\n共找到 {len(df)} 条记录\n")
    
    # 按日期分组
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df_15 = df[df['trade_date'] == '2026-01-15']
    df_16 = df[df['trade_date'] == '2026-01-16']
    df_17 = df[df['trade_date'] == '2026-01-17']
    
    print(f"15号数据: {len(df_15)} 条")
    print(f"16号数据: {len(df_16)} 条")
    print(f"17号数据: {len(df_17)} 条")
    
    # 统计MACD数值范围
    print("\n" + "-" * 100)
    print("MACD数值统计（绝对值）")
    print("-" * 100)
    
    if len(df_15) > 0:
        print(f"\n15号 MACD统计:")
        print(f"  最小值: {df_15['macd'].abs().min():.4f}")
        print(f"  最大值: {df_15['macd'].abs().max():.4f}")
        print(f"  平均值: {df_15['macd'].abs().mean():.4f}")
        print(f"  中位数: {df_15['macd'].abs().median():.4f}")
    
    if len(df_16) > 0:
        print(f"\n16号 MACD统计:")
        print(f"  最小值: {df_16['macd'].abs().min():.4f}")
        print(f"  最大值: {df_16['macd'].abs().max():.4f}")
        print(f"  平均值: {df_16['macd'].abs().mean():.4f}")
        print(f"  中位数: {df_16['macd'].abs().median():.4f}")
    
    if len(df_17) > 0:
        print(f"\n17号 MACD统计:")
        print(f"  最小值: {df_17['macd'].abs().min():.4f}")
        print(f"  最大值: {df_17['macd'].abs().max():.4f}")
        print(f"  平均值: {df_17['macd'].abs().mean():.4f}")
        print(f"  中位数: {df_17['macd'].abs().median():.4f}")
    
    # 检查数据源
    print("\n" + "-" * 100)
    print("数据源统计")
    print("-" * 100)
    print(f"\n15号数据源分布:")
    if len(df_15) > 0:
        print(df_15['data_source'].value_counts().to_string())
    
    print(f"\n16号数据源分布:")
    if len(df_16) > 0:
        print(df_16['data_source'].value_counts().to_string())
    
    print(f"\n17号数据源分布:")
    if len(df_17) > 0:
        print(df_17['data_source'].value_counts().to_string())
    
    # 检查同一只股票在不同日期的MACD值
    print("\n" + "-" * 100)
    print("同一股票在不同日期的MACD值对比（前10只）")
    print("-" * 100)
    
    # 找出在15号和16号都有数据的股票
    symbols_15 = set(df_15['symbol'].unique())
    symbols_16 = set(df_16['symbol'].unique())
    common_symbols = list(symbols_15 & symbols_16)[:10]
    
    for symbol in common_symbols:
        row_15 = df_15[df_15['symbol'] == symbol].iloc[0]
        row_16 = df_16[df_16['symbol'] == symbol].iloc[0]
        
        print(f"\n{symbol}:")
        print(f"  15号: close={row_15['close_price']:.2f}, macd={row_15['macd']:.4f}, source={row_15['data_source']}")
        print(f"  16号: close={row_16['close_price']:.2f}, macd={row_16['macd']:.4f}, source={row_16['data_source']}")
        print(f"  MACD比值: {abs(row_16['macd']) / abs(row_15['macd']) if row_15['macd'] != 0 else 'N/A':.2f}x")
        print(f"  收盘价比值: {row_16['close_price'] / row_15['close_price'] if row_15['close_price'] != 0 else 'N/A':.4f}")
    
    # 检查价格单位问题
    print("\n" + "-" * 100)
    print("价格单位检查（如果MACD比值接近100，可能是价格单位问题）")
    print("-" * 100)
    
    for symbol in common_symbols[:5]:
        row_15 = df_15[df_15['symbol'] == symbol].iloc[0]
        row_16 = df_16[df_16['symbol'] == symbol].iloc[0]
        
        if row_15['macd'] != 0:
            ratio = abs(row_16['macd']) / abs(row_15['macd'])
            if 90 < ratio < 110:  # 接近100倍
                print(f"\n{symbol}: MACD比值={ratio:.2f}x (可能的价格单位问题)")
                print(f"  如果16号价格单位是'元'，15号价格单位是'分'，MACD会放大100倍")
                print(f"  15号收盘价: {row_15['close_price']:.2f}")
                print(f"  16号收盘价: {row_16['close_price']:.2f}")

if __name__ == '__main__':
    check_macd_values()
