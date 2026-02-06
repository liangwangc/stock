#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证登录历史表是否已创建
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection

db = DatabaseConnection()

# 检查表是否存在
sql = """
SELECT TABLE_NAME, TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'user_login_history'
"""

results = db.execute_query(sql)

print("=" * 60)
print("登录历史表验证结果")
print("=" * 60)

if results:
    print(f"\n✓ 表已创建：{results[0]['TABLE_NAME']}")
    print(f"  注释：{results[0]['TABLE_COMMENT']}")
    
    # 检查字段
    fields_sql = """
    SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, COLUMN_COMMENT
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_login_history'
    ORDER BY ORDINAL_POSITION
    """
    
    fields = db.execute_query(fields_sql)
    if fields:
        print(f"\n字段列表（共 {len(fields)} 个字段）：\n")
        for field in fields:
            print(f"  {field['COLUMN_NAME']:30s} {field['COLUMN_TYPE']:20s} {field['COLUMN_COMMENT']}")
    
    # 检查索引
    indexes_sql = """
    SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_login_history'
    ORDER BY INDEX_NAME, SEQ_IN_INDEX
    """
    
    indexes = db.execute_query(indexes_sql)
    if indexes:
        print(f"\n索引列表（共 {len(indexes)} 个索引）：\n")
        current_index = None
        for idx in indexes:
            if current_index != idx['INDEX_NAME']:
                if current_index:
                    print()
                current_index = idx['INDEX_NAME']
                unique = "UNIQUE" if idx['NON_UNIQUE'] == 0 else "INDEX"
                print(f"  {idx['INDEX_NAME']} ({unique})")
            print(f"    - {idx['COLUMN_NAME']}")
    
    # 检查记录数
    count_sql = "SELECT COUNT(*) as cnt FROM user_login_history"
    count_result = db.execute_query(count_sql)
    if count_result:
        print(f"\n当前记录数：{count_result[0]['cnt']} 条")
else:
    print("\n✗ 表不存在！请先执行 database/user_login_history.sql")

print("\n" + "=" * 60)
