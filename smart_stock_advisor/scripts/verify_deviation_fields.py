#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证偏差值字段是否已添加
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection

db = DatabaseConnection()

# 检查字段是否存在
sql = """
SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'stock_predictions'
  AND COLUMN_NAME IN ('deviation_pct', 'absolute_deviation_pct', 'deviation_price')
ORDER BY ORDINAL_POSITION
"""

results = db.execute_query(sql)

print("=" * 60)
print("偏差值字段验证结果")
print("=" * 60)

if results:
    print(f"\n找到 {len(results)} 个偏差值字段：\n")
    for row in results:
        print(f"字段名: {row['COLUMN_NAME']}")
        print(f"数据类型: {row['DATA_TYPE']}")
        print(f"完整类型: {row['COLUMN_TYPE']}")
        print(f"注释: {row['COLUMN_COMMENT']}")
        print("-" * 60)
else:
    print("\n未找到偏差值字段！")

# 检查索引
index_sql = """
SELECT INDEX_NAME, COLUMN_NAME
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'stock_predictions'
  AND INDEX_NAME IN ('idx_deviation_pct', 'idx_absolute_deviation_pct')
ORDER BY INDEX_NAME, SEQ_IN_INDEX
"""

index_results = db.execute_query(index_sql)

print("\n索引验证结果：")
if index_results:
    print(f"\n找到 {len(index_results)} 个索引：\n")
    current_index = None
    for row in index_results:
        if current_index != row['INDEX_NAME']:
            if current_index:
                print()
            current_index = row['INDEX_NAME']
            print(f"索引名: {row['INDEX_NAME']}")
        print(f"  字段: {row['COLUMN_NAME']}")
else:
    print("\n未找到相关索引！")

# 检查数据填充情况
data_sql = """
SELECT 
    COUNT(*) as total_count,
    COUNT(deviation_pct) as deviation_pct_count,
    COUNT(absolute_deviation_pct) as absolute_deviation_pct_count,
    COUNT(deviation_price) as deviation_price_count
FROM stock_predictions
WHERE actual_change_pct IS NOT NULL 
  AND predicted_change_pct IS NOT NULL
"""

data_results = db.execute_query(data_sql)

print("\n" + "=" * 60)
print("数据填充情况")
print("=" * 60)

if data_results:
    row = data_results[0]
    print(f"\n总记录数: {row['total_count']}")
    print(f"deviation_pct 已填充: {row['deviation_pct_count']} ({row['deviation_pct_count']/row['total_count']*100:.1f}%)")
    print(f"absolute_deviation_pct 已填充: {row['absolute_deviation_pct_count']} ({row['absolute_deviation_pct_count']/row['total_count']*100:.1f}%)")
    print(f"deviation_price 已填充: {row['deviation_price_count']} ({row['deviation_price_count']/row['total_count']*100:.1f}%)")

print("\n" + "=" * 60)
