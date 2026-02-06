#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查指定日期范围内的数据情况
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def check_date_range(start_date: str, end_date: str):
    """检查指定日期范围内的数据"""
    logger.info("=" * 60)
    logger.info(f"检查日期范围: {start_date} 至 {end_date}")
    logger.info("=" * 60)
    
    # 1. 检查是否有数据
    sql_count = """
        SELECT COUNT(*) as total_count
        FROM stock_history_data
        WHERE trade_date BETWEEN %s AND %s
          AND period_type = 'daily'
    """
    result = DatabaseConnection.execute_query(sql_count, (start_date, end_date))
    total_count = result[0]['total_count'] if result else 0
    logger.info(f"总记录数: {total_count}")
    
    if total_count == 0:
        logger.warning("该日期范围内没有数据！")
        return
    
    # 2. 检查有哪些股票
    sql_symbols = """
        SELECT DISTINCT symbol, COUNT(*) as count
        FROM stock_history_data
        WHERE trade_date BETWEEN %s AND %s
          AND period_type = 'daily'
        GROUP BY symbol
        ORDER BY symbol
        LIMIT 10
    """
    symbols = DatabaseConnection.execute_query(sql_symbols, (start_date, end_date))
    logger.info(f"\n前10只股票的数据情况:")
    for row in symbols:
        logger.info(f"  {row['symbol']}: {row['count']} 条记录")
    
    # 3. 检查技术指标字段是否为空
    sql_indicators = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN ma5 IS NULL THEN 1 ELSE 0 END) as ma5_null,
            SUM(CASE WHEN ma10 IS NULL THEN 1 ELSE 0 END) as ma10_null,
            SUM(CASE WHEN ma20 IS NULL THEN 1 ELSE 0 END) as ma20_null,
            SUM(CASE WHEN ma60 IS NULL THEN 1 ELSE 0 END) as ma60_null,
            SUM(CASE WHEN rsi IS NULL THEN 1 ELSE 0 END) as rsi_null,
            SUM(CASE WHEN macd IS NULL THEN 1 ELSE 0 END) as macd_null,
            SUM(CASE WHEN x2 IS NULL THEN 1 ELSE 0 END) as x2_null
        FROM stock_history_data
        WHERE trade_date BETWEEN %s AND %s
          AND period_type = 'daily'
    """
    indicators = DatabaseConnection.execute_query(sql_indicators, (start_date, end_date))
    if indicators:
        ind = indicators[0]
        logger.info(f"\n技术指标字段为空的情况:")
        logger.info(f"  总记录数: {ind['total']}")
        logger.info(f"  ma5 为空: {ind['ma5_null']} 条")
        logger.info(f"  ma10 为空: {ind['ma10_null']} 条")
        logger.info(f"  ma20 为空: {ind['ma20_null']} 条")
        logger.info(f"  ma60 为空: {ind['ma60_null']} 条")
        logger.info(f"  rsi 为空: {ind['rsi_null']} 条")
        logger.info(f"  macd 为空: {ind['macd_null']} 条")
        logger.info(f"  x2 为空: {ind['x2_null']} 条")
    
    # 4. 检查具体某只股票的数据（如果有数据）
    if total_count > 0:
        sql_sample = """
            SELECT symbol, trade_date, ma5, ma10, ma20, ma60, rsi, macd, macd_signal, macd_hist, x2
            FROM stock_history_data
            WHERE trade_date BETWEEN %s AND %s
              AND period_type = 'daily'
            ORDER BY symbol, trade_date
            LIMIT 5
        """
        samples = DatabaseConnection.execute_query(sql_sample, (start_date, end_date))
        logger.info(f"\n前5条记录示例:")
        for row in samples:
            logger.info(f"  {row['symbol']} {row['trade_date']}: "
                       f"ma5={row['ma5']}, ma10={row['ma10']}, ma20={row['ma20']}, "
                       f"rsi={row['rsi']}, macd={row['macd']}, x2={row['x2']}")


if __name__ == "__main__":
    # 检查 2016 年的数据
    logger.info("\n" + "=" * 60)
    logger.info("检查 2016-01-12 至 2016-01-14 的数据")
    logger.info("=" * 60)
    check_date_range('2016-01-12', '2016-01-14')
    
    # 检查 2026 年的数据
    logger.info("\n" + "=" * 60)
    logger.info("检查 2026-01-12 至 2026-01-14 的数据")
    logger.info("=" * 60)
    check_date_range('2026-01-12', '2026-01-14')
    
    # 检查数据库中最早和最晚的日期
    logger.info("\n" + "=" * 60)
    logger.info("检查数据库中的日期范围")
    logger.info("=" * 60)
    sql_date_range = """
        SELECT 
            MIN(trade_date) as earliest_date,
            MAX(trade_date) as latest_date,
            COUNT(DISTINCT symbol) as stock_count,
            COUNT(*) as total_records
        FROM stock_history_data
        WHERE period_type = 'daily'
    """
    date_range = DatabaseConnection.execute_query(sql_date_range)
    if date_range:
        dr = date_range[0]
        logger.info(f"最早日期: {dr['earliest_date']}")
        logger.info(f"最晚日期: {dr['latest_date']}")
        logger.info(f"股票数量: {dr['stock_count']}")
        logger.info(f"总记录数: {dr['total_records']}")
