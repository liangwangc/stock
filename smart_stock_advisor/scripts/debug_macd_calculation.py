"""
调试MACD计算问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_connection import DatabaseConnection
import pandas as pd
import numpy as np

def debug_macd_calculation(symbol='000026', trade_date='2026-01-16'):
    """调试MACD计算"""
    db = DatabaseConnection()
    
    # 获取历史数据（60天）
    sql = """
    SELECT trade_date, close_price
    FROM stock_history_data
    WHERE symbol = %s
    AND trade_date <= %s
    AND close_price IS NOT NULL
    ORDER BY trade_date DESC
    LIMIT 60
    """
    
    results = db.execute_query(sql, (symbol, trade_date))
    
    if not results:
        print(f"未找到 {symbol} 的历史数据")
        return
    
    df = pd.DataFrame(results)
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values('trade_date')
    df = df.set_index('trade_date')
    
    print("=" * 100)
    print(f"调试MACD计算：{symbol} {trade_date}")
    print("=" * 100)
    
    print(f"\n历史数据（前10条）：")
    print(df.head(10).to_string())
    
    print(f"\n历史数据（后10条）：")
    print(df.tail(10).to_string())
    
    # 获取当前收盘价
    current_close_sql = """
    SELECT close_price
    FROM stock_history_data
    WHERE symbol = %s
    AND trade_date = %s
    """
    
    current_result = db.execute_query(current_close_sql, (symbol, trade_date))
    if not current_result:
        print(f"未找到 {symbol} {trade_date} 的收盘价")
        return
    
    current_close = float(current_result[0]['close_price'])
    print(f"\n当前收盘价: {current_close}")
    
    # 计算MACD（按照fetch_tushare_data_16_23.py的逻辑）
    closes = df['close_price'].dropna()
    if len(closes) == 0:
        print("没有有效的收盘价数据")
        return
    
    # 添加当前收盘价
    closes = pd.concat([closes, pd.Series([current_close])])
    
    print(f"\n用于计算MACD的收盘价序列（最后10个值）：")
    print(closes.tail(10).to_string())
    
    # 计算EMA12和EMA26
    if len(closes) >= 26:
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd - macd_signal
        
        print(f"\nEMA12（最后10个值）：")
        print(ema12.tail(10).to_string())
        
        print(f"\nEMA26（最后10个值）：")
        print(ema26.tail(10).to_string())
        
        print(f"\nMACD（最后10个值）：")
        print(macd.tail(10).to_string())
        
        print(f"\nMACD Signal（最后10个值）：")
        print(macd_signal.tail(10).to_string())
        
        print(f"\nMACD Histogram（最后10个值）：")
        print(macd_hist.tail(10).to_string())
        
        print(f"\n最终MACD值: {macd.iloc[-1]:.4f}")
        print(f"最终MACD Signal值: {macd_signal.iloc[-1]:.4f}")
        print(f"最终MACD Histogram值: {macd_hist.iloc[-1]:.4f}")
        
        # 检查数据库中的值
        db_sql = """
        SELECT macd, macd_signal, macd_hist
        FROM stock_history_data
        WHERE symbol = %s
        AND trade_date = %s
        """
        
        db_result = db.execute_query(db_sql, (symbol, trade_date))
        if db_result:
            db_macd = db_result[0]['macd']
            db_signal = db_result[0]['macd_signal']
            db_hist = db_result[0]['macd_hist']
            
            print(f"\n数据库中的值:")
            print(f"  MACD: {db_macd}")
            print(f"  MACD Signal: {db_signal}")
            print(f"  MACD Histogram: {db_hist}")
            
            if db_macd is not None:
                calculated_macd = macd.iloc[-1]
                ratio = abs(db_macd) / abs(calculated_macd) if calculated_macd != 0 else None
                print(f"\n数据库值 / 计算值 = {ratio:.2f}x" if ratio else "无法计算比值")
                
                if ratio and (90 < ratio < 110):
                    print(f"⚠️ 可能的问题：数据库中的MACD值是计算值的约{ratio:.0f}倍，可能是单位问题")
    else:
        print(f"数据不足（需要至少26个数据点，实际只有{len(closes)}个）")

if __name__ == '__main__':
    # 测试几个有问题的股票
    debug_macd_calculation('000026', '2026-01-16')
    print("\n" + "=" * 100 + "\n")
    debug_macd_calculation('000031', '2026-01-16')
