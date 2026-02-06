#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查单只股票的数据情况
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def check_stock(symbol: str, date: str):
    """检查单只股票在指定日期的数据"""
    logger.info("=" * 60)
    logger.info(f"检查股票 {symbol} 在 {date} 的数据")
    logger.info("=" * 60)
    
    # 1. 检查该日期的数据
    sql = """
        SELECT symbol, trade_date, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2,
               close_price, high_price, low_price
        FROM stock_history_data
        WHERE symbol = %s
          AND trade_date = %s
          AND period_type = 'daily'
    """
    result = DatabaseConnection.execute_query(sql, (symbol, date))
    if not result:
        logger.warning(f"股票 {symbol} 在 {date} 没有数据！")
        return
    
    row = result[0]
    logger.info(f"数据情况:")
    logger.info(f"  symbol: {row['symbol']}")
    logger.info(f"  trade_date: {row['trade_date']}")
    logger.info(f"  ma5: {row['ma5']}")
    logger.info(f"  ma10: {row['ma10']}")
    logger.info(f"  ma20: {row['ma20']}")
    logger.info(f"  ma60: {row['ma60']}")
    logger.info(f"  rsi: {row['rsi']}")
    logger.info(f"  macd: {row['macd']}")
    logger.info(f"  macd_signal: {row['macd_signal']}")
    logger.info(f"  macd_hist: {row['macd_hist']}")
    logger.info(f"  x2: {row['x2']}")
    logger.info(f"  close_price: {row['close_price']}")
    
    # 2. 检查该日期之前有多少历史数据
    sql_history = """
        SELECT COUNT(*) as count, MIN(trade_date) as earliest, MAX(trade_date) as latest
        FROM stock_history_data
        WHERE symbol = %s
          AND trade_date <= %s
          AND period_type = 'daily'
    """
    history = DatabaseConnection.execute_query(sql_history, (symbol, date))
    if history:
        h = history[0]
        logger.info(f"\n历史数据情况（截至 {date}）:")
        logger.info(f"  总记录数: {h['count']}")
        logger.info(f"  最早日期: {h['earliest']}")
        logger.info(f"  最晚日期: {h['latest']}")
        
        if h['count'] < 60:
            logger.warning(f"  警告：历史数据不足 60 天，无法计算 MA60 和 MACD 等指标")


if __name__ == "__main__":
    # 检查 000007 在 2026-01-12 的数据
    check_stock('000007', '2026-01-12')
