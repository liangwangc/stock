#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查股票历史数据表中的重复数据
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def check_duplicate_data():
    """检查重复数据"""
    logger.info("=" * 80)
    logger.info("检查股票历史数据表中的重复数据")
    logger.info("=" * 80)
    
    # 1. 检查唯一索引
    logger.info("\n1. 检查唯一索引...")
    sql_indexes = """
        SHOW INDEXES FROM stock_history_data 
        WHERE Key_name LIKE 'uk_%' OR Non_unique = 0
    """
    indexes = DatabaseConnection.execute_query(sql_indexes)
    
    logger.info("唯一索引列表:")
    unique_indexes = {}
    for idx in indexes:
        key_name = idx.get('Key_name', '')
        column_name = idx.get('Column_name', '')
        seq = idx.get('Seq_in_index', 0)
        
        if key_name not in unique_indexes:
            unique_indexes[key_name] = []
        unique_indexes[key_name].append((seq, column_name))
    
    for key_name, columns in unique_indexes.items():
        columns_str = ', '.join([col for _, col in sorted(columns)])
        logger.info(f"  {key_name}: ({columns_str})")
    
    # 检查是否有正确的唯一索引
    has_correct_index = False
    for key_name, columns in unique_indexes.items():
        column_names = [col for _, col in sorted(columns)]
        if 'symbol' in column_names and 'trade_date' in column_names and 'period_type' in column_names:
            has_correct_index = True
            logger.info(f"\n✅ 找到正确的唯一索引: {key_name} ({', '.join(column_names)})")
            break
    
    if not has_correct_index:
        logger.warning("\n⚠️ 未找到包含 period_type 的唯一索引！")
        logger.warning("   这可能导致重复数据问题。")
        logger.warning("   请执行: database/add_period_type_field.sql")
    
    # 2. 检查重复数据（基于 symbol, trade_date, period_type）
    logger.info("\n2. 检查重复数据...")
    sql_duplicates = """
        SELECT symbol, trade_date, period_type, COUNT(*) as count
        FROM stock_history_data
        GROUP BY symbol, trade_date, period_type
        HAVING COUNT(*) > 1
        ORDER BY count DESC, symbol, trade_date
        LIMIT 20
    """
    duplicates = DatabaseConnection.execute_query(sql_duplicates)
    
    if duplicates:
        logger.warning(f"\n⚠️ 发现 {len(duplicates)} 组重复数据（显示前20组）:")
        for dup in duplicates:
            logger.warning(f"  {dup['symbol']} | {dup['trade_date']} | {dup['period_type']} | 重复 {dup['count']} 次")
        
        # 统计总重复数
        sql_total = """
            SELECT SUM(count - 1) as total_duplicates
            FROM (
                SELECT symbol, trade_date, period_type, COUNT(*) as count
                FROM stock_history_data
                GROUP BY symbol, trade_date, period_type
                HAVING COUNT(*) > 1
            ) as dup_counts
        """
        result = DatabaseConnection.execute_query(sql_total)
        total_duplicates = result[0]['total_duplicates'] if result else 0
        logger.warning(f"\n总重复记录数: {total_duplicates}")
    else:
        logger.info("\n✅ 未发现重复数据")
    
    # 3. 检查是否有 period_type 为 NULL 的数据
    logger.info("\n3. 检查 period_type 为 NULL 的数据...")
    sql_null_period = """
        SELECT COUNT(*) as count
        FROM stock_history_data
        WHERE period_type IS NULL OR period_type = ''
    """
    result = DatabaseConnection.execute_query(sql_null_period)
    null_count = result[0]['count'] if result else 0
    
    if null_count > 0:
        logger.warning(f"\n⚠️ 发现 {null_count} 条 period_type 为 NULL 的数据")
        logger.warning("   这可能导致唯一索引失效，产生重复数据")
        logger.warning("   建议执行: UPDATE stock_history_data SET period_type = 'daily' WHERE period_type IS NULL")
    else:
        logger.info("\n✅ 未发现 period_type 为 NULL 的数据")
    
    # 4. 检查是否有基于旧唯一索引的重复（symbol, trade_date）
    logger.info("\n4. 检查基于 (symbol, trade_date) 的重复数据...")
    sql_old_duplicates = """
        SELECT symbol, trade_date, COUNT(*) as count, GROUP_CONCAT(DISTINCT period_type) as period_types
        FROM stock_history_data
        GROUP BY symbol, trade_date
        HAVING COUNT(*) > 1
        ORDER BY count DESC, symbol, trade_date
        LIMIT 20
    """
    old_duplicates = DatabaseConnection.execute_query(sql_old_duplicates)
    
    if old_duplicates:
        logger.info(f"\n发现 {len(old_duplicates)} 组基于 (symbol, trade_date) 的重复（显示前20组）:")
        for dup in old_duplicates:
            logger.info(f"  {dup['symbol']} | {dup['trade_date']} | {dup['count']} 条记录 | period_type: {dup['period_types']}")
        
        # 检查这些重复是否是因为 period_type 不同
        valid_period_duplicates = [d for d in old_duplicates if ',' in str(d.get('period_types', ''))]
        if valid_period_duplicates:
            logger.info(f"\n✅ 其中 {len(valid_period_duplicates)} 组是因为 period_type 不同（这是正常的）")
        else:
            logger.warning(f"\n⚠️ 所有重复都是相同 period_type，这表示存在真正的重复数据！")
    else:
        logger.info("\n✅ 未发现基于 (symbol, trade_date) 的重复数据")
    
    logger.info("\n" + "=" * 80)
    logger.info("检查完成")
    logger.info("=" * 80)


if __name__ == '__main__':
    try:
        check_duplicate_data()
    except Exception as e:
        logger.error(f"检查失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
