#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
删除重复索引脚本
执行 database/remove_duplicate_indexes.sql 中的SQL语句
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.execute_sql_script import execute_sql_file
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """执行删除重复索引脚本"""
    sql_file = os.path.join(project_root, 'database', 'remove_duplicate_indexes.sql')
    
    logger.info("=" * 60)
    logger.info("开始执行数据库索引优化脚本")
    logger.info("=" * 60)
    logger.info(f"SQL文件: {sql_file}")
    
    success = execute_sql_file(sql_file)
    
    if success:
        logger.info("\n✅ 数据库索引优化完成！")
        logger.info("建议：")
        logger.info("1. 监控查询性能（特别是 WHERE symbol = ? 和 WHERE trade_date BETWEEN ? AND ? 查询）")
        logger.info("2. 监控写入性能（应该有所提升）")
        logger.info("3. 监控数据库锁竞争（应该有所减少）")
    else:
        logger.error("\n❌ 数据库索引优化失败，请检查错误信息")
        sys.exit(1)


if __name__ == '__main__':
    main()
