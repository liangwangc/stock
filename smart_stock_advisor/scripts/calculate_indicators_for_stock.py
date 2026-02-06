#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
计算指定股票指定日期的技术指标
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from data_source.stock_data_source import StockDataSource
from utils.logger import get_logger

logger = get_logger(__name__)

def calculate_indicators(symbol: str, date: str):
    """计算指定股票指定日期的技术指标"""
    
    print("=" * 80)
    print(f"计算技术指标：{symbol} - {date}")
    print("=" * 80)
    
    # 1. 获取数据源
    data_source = StockDataSource()
    
    # 2. 获取历史数据（至少需要60天数据来计算MA60）
    print(f"\n正在获取历史数据...")
    end_date = datetime.strptime(date, '%Y-%m-%d')
    start_date = end_date - pd.Timedelta(days=90)  # 获取90天数据，确保有足够数据
    
    df = data_source.get_stock_data(
        symbol=symbol,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=date
    )
    
    if df.empty:
        print(f"\n[错误] 无法获取 {symbol} 的数据")
        return
    
    print(f"获取到 {len(df)} 天数据")
    print(f"数据范围: {df.index.min()} 到 {df.index.max()}")
    
    # 3. 检查是否有目标日期的数据
    target_date = pd.to_datetime(date)
    if target_date not in df.index:
        print(f"\n[警告] 目标日期 {date} 不在数据范围内")
        print(f"可用的最近日期: {df.index.max()}")
        # 使用最近的数据
        target_date = df.index.max()
        print(f"将使用最近日期: {target_date.strftime('%Y-%m-%d')}")
    
    # 只使用目标日期及之前的数据
    df_filtered = df.loc[df.index <= target_date].copy()
    
    if len(df_filtered) < 60:
        print(f"\n[警告] 数据不足（只有{len(df_filtered)}天），无法计算所有指标")
        print(f"需要至少60天数据来计算MA60")
    
    # 4. 准备数据
    closes = df_filtered['close'].values
    highs = df_filtered['high'].values
    lows = df_filtered['low'].values
    
    print(f"\n使用 {len(df_filtered)} 天数据计算技术指标")
    
    # 5. 尝试使用talib计算
    try:
        import talib
        TALIB_AVAILABLE = True
        print("\n使用talib库计算技术指标（与证券公司算法一致）")
    except ImportError:
        TALIB_AVAILABLE = False
        print("\n[警告] talib库未安装，使用pandas计算（可能与证券公司值不一致）")
        print("建议安装talib: pip install TA-Lib")
    
    results = {}
    
    if TALIB_AVAILABLE:
        # 使用talib计算
        # MA
        if len(closes) >= 5:
            ma5_values = talib.MA(closes, timeperiod=5)
            results['ma5'] = float(ma5_values[-1]) if pd.notna(ma5_values[-1]) else None
        else:
            results['ma5'] = None
        
        if len(closes) >= 10:
            ma10_values = talib.MA(closes, timeperiod=10)
            results['ma10'] = float(ma10_values[-1]) if pd.notna(ma10_values[-1]) else None
        else:
            results['ma10'] = None
        
        if len(closes) >= 20:
            ma20_values = talib.MA(closes, timeperiod=20)
            results['ma20'] = float(ma20_values[-1]) if pd.notna(ma20_values[-1]) else None
        else:
            results['ma20'] = None
        
        if len(closes) >= 60:
            ma60_values = talib.MA(closes, timeperiod=60)
            results['ma60'] = float(ma60_values[-1]) if pd.notna(ma60_values[-1]) else None
        else:
            results['ma60'] = None
        
        # RSI
        if len(closes) >= 14:
            rsi_values = talib.RSI(closes, timeperiod=14)
            results['rsi'] = float(rsi_values[-1]) if pd.notna(rsi_values[-1]) else None
        else:
            results['rsi'] = None
        
        # MACD
        if len(closes) >= 26:
            macd_values, macd_signal_values, macd_hist_values = talib.MACD(
                closes, 
                fastperiod=12, 
                slowperiod=26, 
                signalperiod=9
            )
            results['macd'] = float(macd_values[-1]) if pd.notna(macd_values[-1]) else None
            results['macd_signal'] = float(macd_signal_values[-1]) if pd.notna(macd_signal_values[-1]) else None
            results['macd_hist'] = float(macd_hist_values[-1]) if pd.notna(macd_hist_values[-1]) else None
        else:
            results['macd'] = None
            results['macd_signal'] = None
            results['macd_hist'] = None
        
        # X2（自定义指标，talib没有，使用pandas计算）
        if len(df_filtered) >= 20:
            current_close = closes[-1]
            llv_low = lows[-20:].min()
            hhv_high = highs[-20:].max()
            range_width = hhv_high - llv_low
            if range_width > 0:
                x2_value = (current_close - llv_low) / range_width * 100
                results['x2'] = float(round(x2_value, 4))
            else:
                results['x2'] = 50.0
        else:
            results['x2'] = None
    else:
        # 使用pandas计算
        closes_series = df_filtered['close']
        
        # MA
        results['ma5'] = float(closes_series.tail(5).mean()) if len(closes_series) >= 5 else None
        results['ma10'] = float(closes_series.tail(10).mean()) if len(closes_series) >= 10 else None
        results['ma20'] = float(closes_series.tail(20).mean()) if len(closes_series) >= 20 else None
        results['ma60'] = float(closes_series.tail(60).mean()) if len(closes_series) >= 60 else None
        
        # RSI
        if len(closes_series) >= 14:
            delta = closes_series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            results['rsi'] = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None
        else:
            results['rsi'] = None
        
        # MACD
        if len(closes_series) >= 26:
            ema12 = closes_series.ewm(span=12, adjust=False).mean()
            ema26 = closes_series.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            results['macd'] = float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None
            results['macd_signal'] = float(signal.iloc[-1]) if pd.notna(signal.iloc[-1]) else None
            results['macd_hist'] = float(histogram.iloc[-1]) if pd.notna(histogram.iloc[-1]) else None
        else:
            results['macd'] = None
            results['macd_signal'] = None
            results['macd_hist'] = None
        
        # X2
        if len(df_filtered) >= 20:
            highs_series = df_filtered['high']
            lows_series = df_filtered['low']
            current_close = closes_series.iloc[-1]
            llv_low = lows_series.tail(20).min()
            hhv_high = highs_series.tail(20).max()
            range_width = hhv_high - llv_low
            if range_width > 0:
                x2_value = (current_close - llv_low) / range_width * 100
                results['x2'] = float(round(x2_value, 4))
            else:
                results['x2'] = 50.0
        else:
            results['x2'] = None
    
    # 6. 显示结果
    print("\n" + "=" * 80)
    print("技术指标计算结果：")
    print("=" * 80)
    print(f"\n日期: {target_date.strftime('%Y-%m-%d')}")
    print(f"收盘价: {df_filtered['close'].iloc[-1]:.2f}")
    print(f"\n移动平均线：")
    print(f"  MA5:  {results['ma5']:.4f}" if results['ma5'] else f"  MA5:  None")
    print(f"  MA10: {results['ma10']:.4f}" if results['ma10'] else f"  MA10: None")
    print(f"  MA20: {results['ma20']:.4f}" if results['ma20'] else f"  MA20: None")
    print(f"  MA60: {results['ma60']:.4f}" if results['ma60'] else f"  MA60: None")
    print(f"\nRSI（相对强弱指标）：")
    print(f"  RSI:  {results['rsi']:.4f}" if results['rsi'] else f"  RSI:  None")
    print(f"\nMACD：")
    print(f"  MACD:        {results['macd']:.4f}" if results['macd'] else f"  MACD:        None")
    print(f"  MACD_Signal: {results['macd_signal']:.4f}" if results['macd_signal'] else f"  MACD_Signal: None")
    print(f"  MACD_Hist:   {results['macd_hist']:.4f}" if results['macd_hist'] else f"  MACD_Hist:   None")
    print(f"\nX2（自定义指标）：")
    print(f"  X2:   {results['x2']:.4f}" if results['x2'] else f"  X2:   None")
    
    print("\n" + "=" * 80)
    if TALIB_AVAILABLE:
        print("[OK] 使用talib库计算（与证券公司算法一致）")
    else:
        print("[WARN] 使用pandas计算（可能与证券公司值不一致，建议安装talib）")
    print("=" * 80)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='计算指定股票指定日期的技术指标')
    parser.add_argument('--symbol', '-s', type=str, default='000019', help='股票代码')
    parser.add_argument('--date', '-d', type=str, default='2026-01-16', help='日期（YYYY-MM-DD）')
    
    args = parser.parse_args()
    
    calculate_indicators(args.symbol, args.date)
