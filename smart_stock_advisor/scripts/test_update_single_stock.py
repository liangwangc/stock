#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试更新单只股票的技术指标
"""

import sys
import os
import pandas as pd
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def test_update_stock(symbol: str, date: str):
    """测试更新单只股票在指定日期的技术指标"""
    logger.info("=" * 60)
    logger.info(f"测试更新股票 {symbol} 在 {date} 的技术指标")
    logger.info("=" * 60)
    
    # 1. 加载历史数据（从目标日期往前取最后 500 条记录）
    sql = """
        SELECT trade_date, close_price, high_price, low_price
        FROM (
            SELECT trade_date, close_price, high_price, low_price
            FROM stock_history_data
            WHERE symbol = %s
              AND period_type = 'daily'
              AND trade_date <= %s
            ORDER BY trade_date DESC
            LIMIT 500
        ) AS sub
        ORDER BY trade_date ASC
    """
    rows = DatabaseConnection.execute_query(sql, (symbol, date))
    if not rows:
        logger.warning(f"没有找到历史数据")
        return
    
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df.set_index("trade_date", inplace=True)
    df.sort_index(inplace=True)
    
    logger.info(f"加载了 {len(df)} 条历史数据")
    logger.info(f"日期范围: {df.index.min()} 至 {df.index.max()}")
    
    # 2. 计算技术指标
    date_idx = pd.to_datetime(date)
    if date_idx not in df.index:
        logger.warning(f"日期 {date} 不在历史数据中")
        return
    
    df_hist = df.loc[:date_idx].copy()
    closes = df_hist["close_price"]
    highs = df_hist["high_price"]
    lows = df_hist["low_price"]
    
    indicators = {}
    
    # 计算均线
    if len(closes) >= 5:
        indicators["ma5"] = float(closes.tail(5).mean())
    if len(closes) >= 10:
        indicators["ma10"] = float(closes.tail(10).mean())
    if len(closes) >= 20:
        indicators["ma20"] = float(closes.tail(20).mean())
    if len(closes) >= 60:
        indicators["ma60"] = float(closes.tail(60).mean())
    
    # 计算RSI
    if len(closes) >= 14:
        delta = closes.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        indicators["rsi"] = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None
    
    # 计算MACD
    if len(closes) >= 26:
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        indicators["macd"] = float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None
        indicators["macd_signal"] = float(signal.iloc[-1]) if pd.notna(signal.iloc[-1]) else None
        indicators["macd_hist"] = float(hist.iloc[-1]) if pd.notna(hist.iloc[-1]) else None
    
    # 计算X2
    if len(df_hist) >= 20:
        window_highs = highs.tail(20)
        window_lows = lows.tail(20)
        llv_low = window_lows.min()
        hhv_high = window_highs.max()
        current_close = closes.iloc[-1]
        if pd.notna(current_close) and pd.notna(llv_low) and pd.notna(hhv_high):
            range_width = hhv_high - llv_low
            if range_width > 0:
                indicators["x2"] = float(round((current_close - llv_low) / range_width * 100, 4))
            else:
                indicators["x2"] = 50.0
    
    logger.info(f"\n计算出的技术指标:")
    for key, value in indicators.items():
        logger.info(f"  {key}: {value}")
    
    # 3. 更新数据库
    sql_update = """
        UPDATE stock_history_data
        SET ma5 = %s,
            ma10 = %s,
            ma20 = %s,
            ma60 = %s,
            rsi = %s,
            macd = %s,
            macd_signal = %s,
            macd_hist = %s,
            x2 = %s
        WHERE symbol = %s
          AND trade_date = %s
          AND period_type = 'daily'
    """
    params = (
        indicators.get("ma5"),
        indicators.get("ma10"),
        indicators.get("ma20"),
        indicators.get("ma60"),
        indicators.get("rsi"),
        indicators.get("macd"),
        indicators.get("macd_signal"),
        indicators.get("macd_hist"),
        indicators.get("x2"),
        symbol,
        date,
    )
    
    affected = DatabaseConnection.execute_update(sql_update, params)
    logger.info(f"\n更新结果: 影响 {affected} 行")
    
    if affected > 0:
        logger.info("更新成功！")
    else:
        logger.warning("更新失败或无匹配行")


if __name__ == "__main__":
    test_update_stock('000007', '2026-01-12')
