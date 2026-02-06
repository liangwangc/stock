"""
检查价格单位一致性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_connection import DatabaseConnection
import pandas as pd

def check_price_units():
    """检查价格单位一致性"""
    db = DatabaseConnection()
    
    # 查询不同时间段的价格范围
    sql = """
    SELECT 
        CASE 
            WHEN trade_date < '2026-01-16' THEN 'before_16'
            WHEN trade_date >= '2026-01-16' THEN 'after_16'
        END AS period,
        data_source,
        MIN(close_price) AS min_price,
        MAX(close_price) AS max_price,
        AVG(close_price) AS avg_price,
        COUNT(*) AS count
    FROM stock_history_data
    WHERE trade_date >= '2026-01-01' AND trade_date <= '2026-01-20'
    AND close_price IS NOT NULL
    GROUP BY period, data_source
    ORDER BY period, data_source
    """
    
    results = db.execute_query(sql)
    
    if not results:
        print("未找到数据")
        return
    
    df = pd.DataFrame(results)
    
    print("=" * 100)
    print("价格单位检查")
    print("=" * 100)
    print(f"\n{df.to_string()}\n")
    
    # 检查同一只股票在不同时间段的价格
    sql2 = """
    SELECT symbol, trade_date, close_price, data_source
    FROM stock_history_data
    WHERE symbol IN ('000001', '000026', '000031', '000034')
    AND trade_date >= '2026-01-10' AND trade_date <= '2026-01-17'
    AND close_price IS NOT NULL
    ORDER BY symbol, trade_date
    """
    
    results2 = db.execute_query(sql2)
    if results2:
        df2 = pd.DataFrame(results2)
        print("-" * 100)
        print("同一股票在不同时间段的价格（检查单位一致性）")
        print("-" * 100)
        print(f"\n{df2.to_string()}\n")
        
        # 检查是否有价格单位问题（如果akshare的价格是tushare的100倍，说明单位不一致）
        for symbol in df2['symbol'].unique():
            symbol_data = df2[df2['symbol'] == symbol].sort_values('trade_date')
            akshare_data = symbol_data[symbol_data['data_source'] == 'akshare']
            tushare_data = symbol_data[symbol_data['data_source'] == 'tushare']
            
            if len(akshare_data) > 0 and len(tushare_data) > 0:
                akshare_price = akshare_data['close_price'].iloc[-1]
                tushare_price = tushare_data['close_price'].iloc[0]
                
                if akshare_price > 0:
                    ratio = tushare_price / akshare_price
                    if 0.9 < ratio < 1.1:
                        print(f"{symbol}: 价格单位一致（akshare={akshare_price:.2f}, tushare={tushare_price:.2f}, 比值={ratio:.4f}）")
                    elif 90 < ratio < 110:
                        print(f"{symbol}: ⚠️ 可能的价格单位问题（akshare={akshare_price:.2f}, tushare={tushare_price:.2f}, 比值={ratio:.4f}，接近100倍）")
                    else:
                        print(f"{symbol}: 价格差异异常（akshare={akshare_price:.2f}, tushare={tushare_price:.2f}, 比值={ratio:.4f}）")

if __name__ == '__main__':
    check_price_units()
