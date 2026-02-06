#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建trained_models表的脚本
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


def create_trained_models_table():
    """创建trained_models表"""
    try:
        db = DatabaseConnection()
        
        logger.info("开始创建trained_models表...")
        
        # 读取SQL文件
        sql_file = os.path.join(project_root, 'database', 'trained_models_table.sql')
        
        if not os.path.exists(sql_file):
            logger.error(f"SQL文件不存在: {sql_file}")
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # 执行SQL
        db.execute_update(sql)
        
        logger.info("✅ trained_models表创建成功")
        
        # 验证表是否存在
        check_sql = "SHOW TABLES LIKE 'trained_models'"
        results = db.execute_query(check_sql)
        
        if results:
            logger.info("✅ 表验证成功")
            return True
        else:
            logger.warning("⚠️  表验证失败")
            return False
            
    except Exception as e:
        logger.error(f"创建表失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = create_trained_models_table()
    if success:
        print("\n✅ 表创建成功，可以开始训练模型了")
    else:
        print("\n❌ 表创建失败，请检查错误信息")
