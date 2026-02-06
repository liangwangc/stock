#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
执行SQL脚本工具
用于执行SQL脚本文件
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def execute_sql_file(sql_file_path: str):
    """
    执行SQL脚本文件
    
    Args:
        sql_file_path: SQL文件路径
    """
    try:
        # 读取SQL文件
        if not os.path.exists(sql_file_path):
            logger.error(f"SQL文件不存在: {sql_file_path}")
            return False
        
        logger.info(f"读取SQL文件: {sql_file_path}")
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 连接数据库
        db = DatabaseConnection()
        if db is None:
            logger.error("数据库连接失败")
            return False
        
        logger.info("数据库连接成功")
        
        # 分割SQL语句（按分号分割，但要注意注释中的分号）
        # 先移除注释
        lines = sql_content.split('\n')
        sql_lines = []
        for line in lines:
            # 移除单行注释
            if '--' in line:
                line = line[:line.index('--')]
            line = line.strip()
            if line and not line.startswith('--'):
                sql_lines.append(line)
        
        # 合并SQL语句
        sql_text = ' '.join(sql_lines)
        
        # 按分号分割SQL语句
        sql_statements = []
        current_statement = []
        in_string = False
        string_char = None
        
        for char in sql_text:
            if char in ("'", '"', '`') and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            
            current_statement.append(char)
            
            if char == ';' and not in_string:
                statement = ''.join(current_statement).strip()
                if statement:
                    sql_statements.append(statement)
                current_statement = []
        
        # 执行每个SQL语句
        logger.info(f"准备执行 {len(sql_statements)} 条SQL语句")
        
        success_count = 0
        error_count = 0
        
        for i, sql in enumerate(sql_statements, 1):
            sql = sql.strip()
            if not sql or sql == ';':
                continue
            
            try:
                logger.info(f"执行SQL语句 {i}/{len(sql_statements)}: {sql[:100]}...")
                
                # 检查是否是ALTER TABLE语句
                if sql.upper().startswith('ALTER TABLE'):
                    # MySQL不支持IF NOT EXISTS和IF EXISTS，需要先检查
                    sql_clean = sql
                    import re
                    
                    # 处理 DROP INDEX IF EXISTS
                    if 'DROP INDEX IF EXISTS' in sql.upper():
                        # 提取表名和索引名
                        index_match = re.search(r'DROP INDEX IF EXISTS\s+`?(\w+)`?', sql, re.IGNORECASE)
                        table_match = re.search(r'ALTER TABLE\s+`?(\w+)`?', sql, re.IGNORECASE)
                        if index_match and table_match:
                            index_name = index_match.group(1)
                            table_name = table_match.group(1)
                            # 检查索引是否存在
                            check_sql = f"SELECT COUNT(*) as cnt FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}' AND INDEX_NAME = '{index_name}'"
                            result = db.execute_query(check_sql)
                            if result and result[0].get('cnt', 0) == 0:
                                logger.warning(f"SQL语句 {i} 跳过（索引 {index_name} 不存在）")
                                success_count += 1
                                continue
                            # MySQL语法：ALTER TABLE table_name DROP INDEX index_name
                            # 移除IF EXISTS，直接使用DROP INDEX
                            sql_clean = re.sub(r'DROP INDEX IF EXISTS\s+`?(\w+)`?', r'DROP INDEX `\1`', sql, flags=re.IGNORECASE)
                    
                    # 处理 ADD COLUMN IF NOT EXISTS
                    elif 'IF NOT EXISTS' in sql.upper():
                        # 提取表名和字段名
                        # 匹配 ADD COLUMN IF NOT EXISTS `字段名`
                        match = re.search(r'ADD COLUMN IF NOT EXISTS\s+`?(\w+)`?', sql, re.IGNORECASE)
                        if match:
                            column_name = match.group(1)
                            table_match = re.search(r'ALTER TABLE\s+`?(\w+)`?', sql, re.IGNORECASE)
                            if table_match:
                                table_name = table_match.group(1)
                                # 检查字段是否存在
                                check_sql = f"SELECT COUNT(*) as cnt FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}' AND COLUMN_NAME = '{column_name}'"
                                result = db.execute_query(check_sql)
                                if result and result[0].get('cnt', 0) > 0:
                                    logger.warning(f"SQL语句 {i} 跳过（字段 {column_name} 已存在）")
                                    success_count += 1
                                    continue
                        
                        # 移除IF NOT EXISTS
                        sql_clean = re.sub(r'\s+IF NOT EXISTS\s+', ' ', sql, flags=re.IGNORECASE)
                    
                    try:
                        db.execute_update(sql_clean)
                        logger.info(f"✓ SQL语句 {i} 执行成功")
                        success_count += 1
                    except Exception as e:
                        error_msg = str(e)
                        # 如果错误是字段已存在，则忽略
                        if 'Duplicate column name' in error_msg or 'already exists' in error_msg.lower() or 'Duplicate key name' in error_msg:
                            logger.warning(f"⚠ SQL语句 {i} 跳过（字段/索引已存在）: {error_msg}")
                            success_count += 1
                        else:
                            logger.error(f"✗ SQL语句 {i} 执行失败: {error_msg}")
                            logger.error(f"SQL: {sql_clean[:200]}")
                            error_count += 1
                elif 'ADD INDEX' in sql.upper() and 'IF NOT EXISTS' in sql.upper():
                    # 索引创建，移除IF NOT EXISTS并检查
                    import re
                    sql_clean = sql
                    match = re.search(r'ADD INDEX IF NOT EXISTS\s+`?(\w+)`?', sql, re.IGNORECASE)
                    if match:
                        index_name = match.group(1)
                        table_match = re.search(r'ALTER TABLE\s+`?(\w+)`?', sql, re.IGNORECASE)
                        if table_match:
                            table_name = table_match.group(1)
                            # 检查索引是否存在
                            check_sql = f"SELECT COUNT(*) as cnt FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}' AND INDEX_NAME = '{index_name}'"
                            result = db.execute_query(check_sql)
                            if result and result[0].get('cnt', 0) > 0:
                                logger.warning(f"⚠ SQL语句 {i} 跳过（索引 {index_name} 已存在）")
                                success_count += 1
                                continue
                    
                    # 移除IF NOT EXISTS
                    sql_clean = re.sub(r'\s+IF NOT EXISTS\s+', ' ', sql, flags=re.IGNORECASE)
                    
                    try:
                        db.execute_update(sql_clean)
                        logger.info(f"✓ SQL语句 {i} 执行成功")
                        success_count += 1
                    except Exception as e:
                        error_msg = str(e)
                        if 'Duplicate key name' in error_msg or 'already exists' in error_msg.lower():
                            logger.warning(f"⚠ SQL语句 {i} 跳过（索引已存在）: {error_msg}")
                            success_count += 1
                        else:
                            logger.error(f"✗ SQL语句 {i} 执行失败: {error_msg}")
                            error_count += 1
                else:
                    # 其他SQL语句（如UPDATE）
                    db.execute_update(sql)
                    logger.info(f"✓ SQL语句 {i} 执行成功")
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"✗ SQL语句 {i} 执行失败: {str(e)}")
                logger.error(f"SQL: {sql[:200]}")
                error_count += 1
        
        logger.info("\n" + "=" * 60)
        logger.info("SQL脚本执行完成")
        logger.info("=" * 60)
        logger.info(f"成功: {success_count} 条")
        logger.info(f"失败: {error_count} 条")
        
        return error_count == 0
        
    except Exception as e:
        logger.error(f"执行SQL脚本失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='执行SQL脚本文件')
    parser.add_argument('sql_file', type=str, help='SQL文件路径')
    
    args = parser.parse_args()
    
    # 如果是相对路径，转换为绝对路径
    sql_file_path = args.sql_file
    if not os.path.isabs(sql_file_path):
        sql_file_path = os.path.join(project_root, sql_file_path)
    
    success = execute_sql_file(sql_file_path)
    sys.exit(0 if success else 1)
