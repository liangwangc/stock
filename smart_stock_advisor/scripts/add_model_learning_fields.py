#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
添加模型学习优化字段脚本
执行SQL脚本，为stock_predictions、prediction_factors、realtime_trading_decisions表添加学习分析相关字段
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def execute_sql_script():
    """执行SQL脚本添加字段"""
    db = None
    try:
        db = DatabaseConnection()
        
        sql_file = os.path.join(project_root, 'database', 'add_model_learning_fields.sql')
        
        if not os.path.exists(sql_file):
            logger.error(f"SQL文件不存在: {sql_file}")
            return False
        
        logger.info("=" * 60)
        logger.info("开始添加模型学习优化字段")
        logger.info("=" * 60)
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句
        statements = []
        current_statement = []
        for line in sql_content.split('\n'):
            line = line.strip()
            # 跳过注释行和空行
            if not line or line.startswith('--'):
                continue
            current_statement.append(line)
            # 如果行以分号结尾，表示一个完整的语句
            if line.endswith(';'):
                statement = ' '.join(current_statement).rstrip(';').strip()
                if statement:
                    statements.append(statement)
                current_statement = []
        
        # 执行所有SQL语句
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for statement in statements:
            if not statement:
                continue
            
            try:
                # 处理MySQL的IF NOT EXISTS语法（MySQL不支持，需要先检查）
                if 'ADD COLUMN IF NOT EXISTS' in statement:
                    # 提取表名和字段名
                    table_match = None
                    column_match = None
                    
                    # 简单的解析（适用于标准格式）
                    parts = statement.split('ADD COLUMN IF NOT EXISTS')
                    if len(parts) == 2:
                        table_part = parts[0].replace('ALTER TABLE', '').strip().strip('`')
                        column_part = parts[1].split()[0].strip('`')
                        
                        # 检查字段是否存在
                        check_sql = f"SHOW COLUMNS FROM `{table_part}` LIKE '{column_part}'"
                        result = db.execute_query(check_sql)
                        
                        if len(result) > 0:
                            logger.info(f"字段 {table_part}.{column_part} 已存在，跳过")
                            skip_count += 1
                            continue
                        
                        # 字段不存在，执行添加（移除IF NOT EXISTS）
                        statement = statement.replace('IF NOT EXISTS', '')
                
                elif 'ADD INDEX IF NOT EXISTS' in statement:
                    # 提取索引名
                    index_match = None
                    if '`idx_' in statement:
                        idx_start = statement.find('`idx_')
                        idx_end = statement.find('`', idx_start + 1)
                        if idx_end > idx_start:
                            index_name = statement[idx_start+1:idx_end]
                            table_name = statement.split('`')[1] if '`' in statement else None
                            
                            if table_name:
                                # 检查索引是否存在
                                check_sql = f"SHOW INDEXES FROM `{table_name}` WHERE Key_name = '{index_name}'"
                                result = db.execute_query(check_sql)
                                
                                if len(result) > 0:
                                    logger.info(f"索引 {table_name}.{index_name} 已存在，跳过")
                                    skip_count += 1
                                    continue
                                
                                # 索引不存在，执行添加（移除IF NOT EXISTS）
                                statement = statement.replace('IF NOT EXISTS', '')
                
                db.execute_update(statement)
                success_count += 1
                logger.info(f"✅ 成功执行: {statement[:80]}...")
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'duplicate column name' in error_msg or 'already exists' in error_msg or 'duplicate key name' in error_msg:
                    logger.info(f"⚠️  字段/索引已存在，跳过: {statement[:60]}...")
                    skip_count += 1
                else:
                    logger.error(f"❌ 执行失败: {statement[:60]}...")
                    logger.error(f"   错误: {str(e)}")
                    error_count += 1
        
        logger.info("=" * 60)
        logger.info(f"执行完成！成功: {success_count}, 跳过: {skip_count}, 失败: {error_count}")
        logger.info("=" * 60)
        
        return error_count == 0
        
    except Exception as e:
        logger.error(f"❌ 执行SQL脚本失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        if db:
            db.close_connection()


if __name__ == '__main__':
    success = execute_sql_script()
    sys.exit(0 if success else 1)
