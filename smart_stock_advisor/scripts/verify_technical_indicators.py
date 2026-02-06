#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证技术指标计算是否正确
对比数据库中的值与重新计算的值，以及与证券公司标准值的差异
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)

def calculate_ma(closes: pd.Series, window: int) -> float:
    """计算移动平均线"""
    if len(closes) < window:
        return None
    return float(closes.tail(window).mean())

def calculate_rsi(closes: pd.Series, period: int = 14) -> float:
    """计算RSI指标"""
    if len(closes) < period + 1:
        return None
    
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # 避免除零错误
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None

def calculate_macd(closes: pd.Series) -> dict:
    """计算MACD指标"""
    if len(closes) < 26:
        return {'macd': None, 'macd_signal': None, 'macd_hist': None}
    
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    
    return {
        'macd': float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None,
        'macd_signal': float(signal.iloc[-1]) if pd.notna(signal.iloc[-1]) else None,
        'macd_hist': float(histogram.iloc[-1]) if pd.notna(histogram.iloc[-1]) else None
    }

def calculate_x2(closes: pd.Series, highs: pd.Series, lows: pd.Series, period: int = 20) -> float:
    """计算X2指标（收盘价在N日价格区间中的相对位置）"""
    if len(closes) < period:
        return None
    
    llv_low = lows.tail(period).min()
    hhv_high = highs.tail(period).max()
    current_close = closes.iloc[-1]
    
    range_width = hhv_high - llv_low
    if range_width > 0:
        x2_value = (current_close - llv_low) / range_width * 100
        return float(round(x2_value, 4))
    else:
        return 50.0

def verify_indicators(symbol: str, date: str):
    """验证指定股票和日期的技术指标"""
    db = DatabaseConnection()
    
    print("=" * 80)
    print(f"验证技术指标：{symbol} - {date}")
    print("=" * 80)
    
    # 1. 从数据库获取该日期的数据
    sql = """
        SELECT 
            trade_date, close_price, high_price, low_price,
            ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2
        FROM stock_history_data
        WHERE symbol = %s AND trade_date = %s AND period_type = 'daily'
        LIMIT 1
    """
    result = db.execute_query(sql, (str(symbol).zfill(6), date))
    
    if not result:
        print(f"\n[错误] 数据库中未找到 {symbol} {date} 的数据")
        return
    
    db_record = result[0]
    print(f"\n数据库中的值：")
    print(f"  日期: {db_record.get('trade_date')}")
    print(f"  收盘价: {db_record.get('close_price')}")
    print(f"  最高价: {db_record.get('high_price')}")
    print(f"  最低价: {db_record.get('low_price')}")
    print(f"  MA5: {db_record.get('ma5')}")
    print(f"  MA10: {db_record.get('ma10')}")
    print(f"  MA20: {db_record.get('ma20')}")
    print(f"  MA60: {db_record.get('ma60')}")
    print(f"  RSI: {db_record.get('rsi')}")
    print(f"  MACD: {db_record.get('macd')}")
    print(f"  MACD_Signal: {db_record.get('macd_signal')}")
    print(f"  MACD_Hist: {db_record.get('macd_hist')}")
    print(f"  X2: {db_record.get('x2')}")
    
    # 2. 获取历史数据用于重新计算
    print(f"\n获取历史数据用于重新计算...")
    sql_history = """
        SELECT trade_date, close_price, high_price, low_price
        FROM stock_history_data
        WHERE symbol = %s 
          AND trade_date <= %s 
          AND period_type = 'daily'
        ORDER BY trade_date DESC
        LIMIT 100
    """
    history_results = db.execute_query(sql_history, (str(symbol).zfill(6), date))
    
    if len(history_results) < 5:
        print(f"\n[错误] 历史数据不足（需要至少5天），无法重新计算")
        return
    
    # 转换为DataFrame（按日期倒序，然后正序排列）
    history_list = []
    for r in reversed(history_results):  # 反转，使日期从早到晚
        history_list.append({
            'date': pd.to_datetime(r['trade_date']),
            'close': float(r['close_price']) if r['close_price'] else None,
            'high': float(r['high_price']) if r['high_price'] else None,
            'low': float(r['low_price']) if r['low_price'] else None,
        })
    
    df = pd.DataFrame(history_list)
    df.set_index('date', inplace=True)
    
    # 只使用目标日期及之前的数据
    target_date = pd.to_datetime(date)
    df = df.loc[df.index <= target_date]
    
    if df.empty:
        print(f"\n[错误] 无法构建历史数据DataFrame")
        return
    
    closes = df['close']
    highs = df['high']
    lows = df['low']
    
    print(f"\n历史数据范围: {df.index.min()} 到 {df.index.max()}，共 {len(df)} 天")
    
    # 3. 重新计算技术指标
    print(f"\n重新计算技术指标：")
    
    recalculated = {}
    
    # 辅助函数：将数据库值转换为float
    def to_float(val):
        if val is None:
            return None
        return float(val)
    
    # MA5
    recalculated['ma5'] = calculate_ma(closes, 5)
    print(f"  MA5 (重新计算): {recalculated['ma5']}")
    db_ma5 = to_float(db_record.get('ma5'))
    if db_ma5 is not None:
        diff = abs(recalculated['ma5'] - db_ma5)
        print(f"    差异: {diff:.4f} ({'✓ 一致' if diff < 0.01 else '✗ 不一致'})")
    
    # MA10
    recalculated['ma10'] = calculate_ma(closes, 10)
    print(f"  MA10 (重新计算): {recalculated['ma10']}")
    db_ma10 = to_float(db_record.get('ma10'))
    if db_ma10 is not None:
        diff = abs(recalculated['ma10'] - db_ma10)
        print(f"    差异: {diff:.4f} ({'✓ 一致' if diff < 0.01 else '✗ 不一致'})")
    
    # MA20
    recalculated['ma20'] = calculate_ma(closes, 20)
    print(f"  MA20 (重新计算): {recalculated['ma20']}")
    db_ma20 = to_float(db_record.get('ma20'))
    if db_ma20 is not None:
        diff = abs(recalculated['ma20'] - db_ma20)
        print(f"    差异: {diff:.4f} ({'✓ 一致' if diff < 0.01 else '✗ 不一致'})")
    
    # MA60
    recalculated['ma60'] = calculate_ma(closes, 60)
    print(f"  MA60 (重新计算): {recalculated['ma60']}")
    db_ma60 = to_float(db_record.get('ma60'))
    if db_ma60 is not None:
        diff = abs(recalculated['ma60'] - db_ma60)
        print(f"    差异: {diff:.4f} ({'✓ 一致' if diff < 0.01 else '✗ 不一致'})")
    
    # RSI
    recalculated['rsi'] = calculate_rsi(closes, 14)
    print(f"  RSI (重新计算): {recalculated['rsi']}")
    db_rsi = to_float(db_record.get('rsi'))
    if db_rsi is not None:
        diff = abs(recalculated['rsi'] - db_rsi)
        print(f"    差异: {diff:.4f} ({'✓ 一致' if diff < 0.1 else '✗ 不一致'})")
    
    # MACD
    macd_result = calculate_macd(closes)
    recalculated['macd'] = macd_result['macd']
    recalculated['macd_signal'] = macd_result['macd_signal']
    recalculated['macd_hist'] = macd_result['macd_hist']
    print(f"  MACD (重新计算): {recalculated['macd']}")
    print(f"  MACD_Signal (重新计算): {recalculated['macd_signal']}")
    print(f"  MACD_Hist (重新计算): {recalculated['macd_hist']}")
    db_macd = to_float(db_record.get('macd'))
    if db_macd is not None:
        diff = abs(recalculated['macd'] - db_macd)
        print(f"    MACD差异: {diff:.4f} ({'✓ 一致' if diff < 0.01 else '✗ 不一致'})")
    db_macd_signal = to_float(db_record.get('macd_signal'))
    if db_macd_signal is not None:
        diff = abs(recalculated['macd_signal'] - db_macd_signal)
        print(f"    MACD_Signal差异: {diff:.4f} ({'✓ 一致' if diff < 0.01 else '✗ 不一致'})")
    db_macd_hist = to_float(db_record.get('macd_hist'))
    if db_macd_hist is not None:
        diff = abs(recalculated['macd_hist'] - db_macd_hist)
        print(f"    MACD_Hist差异: {diff:.4f} ({'✓ 一致' if diff < 0.01 else '✗ 不一致'})")
    
    # X2
    recalculated['x2'] = calculate_x2(closes, highs, lows, 20)
    print(f"  X2 (重新计算): {recalculated['x2']}")
    db_x2 = to_float(db_record.get('x2'))
    if db_x2 is not None:
        diff = abs(recalculated['x2'] - db_x2)
        print(f"    差异: {diff:.4f} ({'✓ 一致' if diff < 0.01 else '✗ 不一致'})")
    
    # 4. 分析差异原因
    print(f"\n" + "=" * 80)
    print("差异分析：")
    print("=" * 80)
    
    issues = []
    
    # 检查MA计算方式
    if db_ma5 is not None and recalculated['ma5']:
        if abs(recalculated['ma5'] - db_ma5) > 0.01:
            issues.append("MA5计算不一致 - 可能原因：使用了不同的历史数据范围")
    
    # 检查RSI计算方式
    if db_rsi is not None and recalculated['rsi']:
        if abs(recalculated['rsi'] - db_rsi) > 0.1:
            issues.append("RSI计算不一致 - 可能原因：RSI平滑算法不同（Wilder's smoothing vs SMA）")
    
    # 检查MACD计算方式
    if db_macd is not None and recalculated['macd']:
        if abs(recalculated['macd'] - db_macd) > 0.01:
            issues.append("MACD计算不一致 - 可能原因：EMA计算方式不同（adjust参数）")
    
    if issues:
        print("\n发现的问题：")
        for issue in issues:
            print(f"  ⚠️ {issue}")
    else:
        print("\n✓ 所有指标计算一致")
    
    # 5. 与证券公司标准对比说明
    print(f"\n" + "=" * 80)
    print("与证券公司标准对比说明：")
    print("=" * 80)
    print("""
    技术指标计算可能存在差异的原因：

    1. **MA（移动平均线）**
       - 标准：简单移动平均（SMA）
       - 我们的计算：使用pandas rolling().mean()，应该是标准SMA
       - 可能差异：如果证券公司使用加权移动平均（WMA）或指数移动平均（EMA）

    2. **RSI（相对强弱指标）**
       - 标准：Wilder's smoothing（指数移动平均）
       - 我们的计算：使用简单移动平均（SMA）计算gain/loss
       - 差异：这是最常见的差异原因！
       - 标准公式：RS = EMA(gain, 14) / EMA(loss, 14)
       - 我们的公式：RS = SMA(gain, 14) / SMA(loss, 14)

    3. **MACD**
       - 标准：EMA(12) - EMA(26)，Signal = EMA(MACD, 9)
       - 我们的计算：使用ewm(span=12, adjust=False)
       - 可能差异：adjust参数的影响（adjust=False是标准EMA）

    4. **X2（自定义指标）**
       - 这是自定义指标，证券公司可能没有这个指标
       - 我们的计算：收盘价在20日价格区间中的相对位置（0-100）

    建议：
    1. 检查RSI计算方式（最可能的问题）
    2. 确认证券公司使用的MA类型（SMA/WMA/EMA）
    3. 确认MACD的EMA计算方式
    """)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='验证技术指标计算是否正确')
    parser.add_argument('--symbol', '-s', type=str, default='000019', help='股票代码')
    parser.add_argument('--date', '-d', type=str, default=None, help='日期（YYYY-MM-DD），默认今天')
    
    args = parser.parse_args()
    
    if args.date is None:
        args.date = datetime.now().strftime('%Y-%m-%d')
    
    verify_indicators(args.symbol, args.date)
