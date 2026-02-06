#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查数据库表的重复索引
分析索引使用情况，判断是否可以删除重复索引
"""
import os
import sys
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)

def get_table_indexes(table_name):
    """获取表的所有索引"""
    try:
        db = DatabaseConnection()
        sql = f"""
            SHOW INDEX FROM `{table_name}`
        """
        indexes = db.execute_query(sql)
        return indexes
    except Exception as e:
        logger.error(f"获取表 {table_name} 的索引失败: {str(e)}")
        return []

def analyze_indexes(indexes):
    """分析索引，找出重复索引"""
    # 按索引名分组
    index_groups = {}
    for idx in indexes:
        index_name = idx.get('Key_name', '')
        if index_name not in index_groups:
            index_groups[index_name] = []
        index_groups[index_name].append(idx)
    
    # 分析单列索引和复合索引的关系
    single_column_indexes = {}  # {column: [index_names]}
    composite_indexes = []  # [(index_name, columns_list)]
    
    for index_name, index_list in index_groups.items():
        if index_name == 'PRIMARY':
            continue
        
        columns = [idx.get('Column_name', '') for idx in sorted(index_list, key=lambda x: x.get('Seq_in_index', 0))]
        
        if len(columns) == 1:
            # 单列索引
            col = columns[0]
            if col not in single_column_indexes:
                single_column_indexes[col] = []
            single_column_indexes[col].append(index_name)
        else:
            # 复合索引
            composite_indexes.append((index_name, columns))
    
    # 找出重复索引
    duplicate_indexes = []
    
    # 1. 检查单列索引是否被复合索引覆盖
    for col, index_names in single_column_indexes.items():
        if len(index_names) > 1:
            duplicate_indexes.append({
                'type': 'duplicate_single',
                'column': col,
                'indexes': index_names,
                'reason': f'列 {col} 有多个单列索引'
            })
        
        # 检查是否有复合索引以该列为前缀
        for comp_name, comp_cols in composite_indexes:
            if comp_cols[0] == col:
                duplicate_indexes.append({
                    'type': 'covered_by_composite',
                    'column': col,
                    'single_indexes': index_names,
                    'composite_index': comp_name,
                    'reason': f'单列索引 {index_names} 可以被复合索引 {comp_name} 的前缀覆盖'
                })
    
    # 2. 检查复合索引是否重复（字段相同但顺序不同）
    for i, (name1, cols1) in enumerate(composite_indexes):
        for j, (name2, cols2) in enumerate(composite_indexes[i+1:], i+1):
            if set(cols1) == set(cols2) and cols1 != cols2:
                duplicate_indexes.append({
                    'type': 'duplicate_composite',
                    'index1': name1,
                    'index2': name2,
                    'columns': cols1,
                    'reason': f'复合索引 {name1} 和 {name2} 字段相同但顺序不同'
                })
            elif cols1 == cols2:
                duplicate_indexes.append({
                    'type': 'exact_duplicate',
                    'index1': name1,
                    'index2': name2,
                    'columns': cols1,
                    'reason': f'复合索引 {name1} 和 {name2} 完全相同'
                })
    
    return duplicate_indexes, index_groups

def check_index_usage_in_code(table_name, column_name):
    """检查代码中是否使用了该索引字段"""
    import subprocess
    try:
        # 搜索代码中使用该字段的查询
        pattern = f"WHERE.*{column_name}|ORDER BY.*{column_name}"
        result = subprocess.run(
            ['grep', '-r', '-i', pattern, 'smart_stock_advisor'],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        return len(result.stdout.split('\n')) > 1  # 至少有一个匹配
    except:
        return True  # 如果无法检查，假设在使用

def main():
    """主函数"""
    print("=" * 80)
    print("数据库索引重复检查")
    print("=" * 80)
    
    # 主要表列表
    main_tables = [
        'stock_history_data',
        'stock_predictions',
        'news_articles',
        'realtime_trading_decisions',
        'scheduled_task_history',
        'news_notifications',
        'parameter_optimization_history',
        'trained_models',
        'us_stock_history_data'
    ]
    
    all_duplicates = []
    
    for table_name in main_tables:
        print(f"\n{'='*80}")
        print(f"检查表: {table_name}")
        print(f"{'='*80}")
        
        indexes = get_table_indexes(table_name)
        if not indexes:
            print(f"  [跳过] 表 {table_name} 不存在或无法访问")
            continue
        
        duplicates, index_groups = analyze_indexes(indexes)
        
        if duplicates:
            print(f"\n  [发现] {len(duplicates)} 个可能的重复索引问题:")
            for dup in duplicates:
                print(f"    - {dup['reason']}")
                if dup['type'] == 'covered_by_composite':
                    print(f"      建议: 可以删除单列索引 {dup['single_indexes']}")
            all_duplicates.extend([(table_name, dup) for dup in duplicates])
        else:
            print(f"  [OK] 未发现明显的重复索引")
        
        # 显示所有索引
        print(f"\n  当前索引列表:")
        for index_name, index_list in index_groups.items():
            columns = [idx.get('Column_name', '') for idx in sorted(index_list, key=lambda x: x.get('Seq_in_index', 0))]
            index_type = 'UNIQUE' if index_list[0].get('Non_unique', 1) == 0 else 'INDEX'
            print(f"    {index_type:8} {index_name:30} ({', '.join(columns)})")
    
    # 生成报告
    print(f"\n{'='*80}")
    print("重复索引分析报告")
    print(f"{'='*80}")
    
    if all_duplicates:
        print(f"\n发现 {len(all_duplicates)} 个重复索引问题:\n")
        for table_name, dup in all_duplicates:
            print(f"表: {table_name}")
            print(f"  问题: {dup['reason']}")
            print()
    else:
        print("\n[OK] 未发现重复索引问题")
    
    # 特别分析 stock_history_data 表
    print(f"\n{'='*80}")
    print("stock_history_data 表索引详细分析")
    print(f"{'='*80}")
    
    indexes = get_table_indexes('stock_history_data')
    if indexes:
        duplicates, index_groups = analyze_indexes(indexes)
        
        print("\n当前索引:")
        for index_name, index_list in index_groups.items():
            columns = [idx.get('Column_name', '') for idx in sorted(index_list, key=lambda x: x.get('Seq_in_index', 0))]
            index_type = 'UNIQUE' if index_list[0].get('Non_unique', 1) == 0 else 'INDEX'
            print(f"  {index_type:8} {index_name:30} ({', '.join(columns)})")
        
        print("\n分析:")
        print("  1. idx_symbol (symbol) - 单列索引")
        print("  2. idx_symbol_date (symbol, trade_date) - 复合索引")
        print("  3. idx_date_range (trade_date, symbol) - 复合索引（顺序不同）")
        print("  4. uk_symbol_date_period (symbol, trade_date, period_type) - 唯一索引")
        
        print("\n重复索引分析:")
        print("  ❌ idx_symbol 可能冗余:")
        print("     - idx_symbol_date 的前缀是 symbol，可以用于 WHERE symbol = ? 查询")
        print("     - 建议: 可以删除 idx_symbol")
        
        print("\n  ⚠️ idx_symbol_date 和 idx_date_range:")
        print("     - 字段相同但顺序不同")
        print("     - idx_symbol_date: 适合 WHERE symbol = ? AND trade_date = ?")
        print("     - idx_date_range: 适合 WHERE trade_date BETWEEN ? AND ? ORDER BY symbol")
        print("     - 需要根据实际查询模式决定是否都保留")
        
        print("\n  ✅ uk_symbol_date_period:")
        print("     - 唯一索引，必须保留")
        print("     - 可以用于 WHERE symbol = ? AND trade_date = ? AND period_type = ? 查询")

if __name__ == '__main__':
    main()
