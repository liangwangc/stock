#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查索引使用情况
分析代码中的查询模式，验证索引是否被使用
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

def check_index_usage():
    """检查索引使用情况"""
    print("=" * 80)
    print("索引使用情况检查")
    print("=" * 80)
    
    db = DatabaseConnection()
    
    # 检查 stock_history_data 表的索引
    print("\n1. stock_history_data 表索引:")
    indexes = db.execute_query("SHOW INDEX FROM stock_history_data")
    
    index_info = {}
    for idx in indexes:
        index_name = idx.get('Key_name', '')
        if index_name not in index_info:
            index_info[index_name] = {
                'type': 'UNIQUE' if idx.get('Non_unique', 1) == 0 else 'INDEX',
                'columns': []
            }
        index_info[index_name]['columns'].append(idx.get('Column_name', ''))
    
    for index_name, info in sorted(index_info.items()):
        columns_str = ', '.join(sorted(set(info['columns'])))
        print(f"  {info['type']:8} {index_name:30} ({columns_str})")
    
    # 分析重复索引
    print("\n2. 重复索引分析:")
    
    # 检查 idx_symbol 是否被复合索引覆盖
    has_idx_symbol = 'idx_symbol' in index_info
    has_composite_with_symbol = any(
        info['columns'][0] == 'symbol' if info['columns'] else False
        for info in index_info.values()
        if len(info['columns']) > 1
    )
    
    if has_idx_symbol and has_composite_with_symbol:
        print("  ⚠️ idx_symbol 可能冗余（被复合索引前缀覆盖）")
    
    # 检查 idx_symbol_date 和 idx_date_range
    has_idx_symbol_date = 'idx_symbol_date' in index_info
    has_idx_date_range = 'idx_date_range' in index_info
    
    if has_idx_symbol_date and has_idx_date_range:
        print("  ⚠️ idx_symbol_date 和 idx_date_range 字段相同但顺序不同")
        print("     建议：保留 idx_symbol_date，删除 idx_date_range")
    
    # 检查代码中的查询模式
    print("\n3. 代码中的查询模式分析:")
    
    query_patterns = {
        'WHERE symbol = ?': 0,
        'WHERE symbol = ? AND trade_date = ?': 0,
        'WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?': 0,
        'WHERE symbol IN (...) AND trade_date IN (...)': 0,
        'WHERE trade_date BETWEEN ? AND ?': 0,
        'WHERE trade_date = ?': 0,
    }
    
    # 搜索代码文件
    import glob
    code_files = []
    for root, dirs, files in os.walk(os.path.join(project_root, 'utils')):
        for file in files:
            if file.endswith('.py'):
                code_files.append(os.path.join(root, file))
    
    for file_path in code_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查查询模式
                if re.search(r'WHERE\s+symbol\s*=\s*%s', content, re.IGNORECASE):
                    query_patterns['WHERE symbol = ?'] += 1
                
                if re.search(r'WHERE\s+symbol\s*=\s*%s.*AND.*trade_date\s*=\s*%s', content, re.IGNORECASE):
                    query_patterns['WHERE symbol = ? AND trade_date = ?'] += 1
                
                if re.search(r'WHERE\s+symbol\s*=\s*%s.*AND.*trade_date\s*>=\s*%s.*AND.*trade_date\s*<=\s*%s', content, re.IGNORECASE):
                    query_patterns['WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?'] += 1
                
                if re.search(r'WHERE\s+symbol\s+IN\s*\(.*\).*AND.*trade_date\s+IN\s*\(', content, re.IGNORECASE):
                    query_patterns['WHERE symbol IN (...) AND trade_date IN (...)'] += 1
                
                if re.search(r'WHERE\s+trade_date\s+BETWEEN', content, re.IGNORECASE):
                    query_patterns['WHERE trade_date BETWEEN ? AND ?'] += 1
                
                if re.search(r'WHERE\s+trade_date\s*=\s*%s', content, re.IGNORECASE):
                    query_patterns['WHERE trade_date = ?'] += 1
        except:
            pass
    
    print("\n  查询模式统计:")
    for pattern, count in query_patterns.items():
        if count > 0:
            print(f"    {pattern}: {count} 处")
    
    print("\n4. 索引使用建议:")
    print("  ✅ WHERE symbol = ? 查询:")
    print("     - 可以使用 uk_symbol_date_period 或 idx_symbol_date 的前缀")
    print("     - idx_symbol 可以删除")
    
    print("\n  ✅ WHERE symbol = ? AND trade_date = ? 查询:")
    print("     - 可以使用 uk_symbol_date_period 或 idx_symbol_date")
    print("     - 这是最常见的查询模式")
    
    print("\n  ⚠️ WHERE trade_date BETWEEN ? AND ? 查询:")
    print("     - 可以使用 idx_trade_date（单列索引）")
    print("     - idx_date_range 可以删除（使用场景少）")

if __name__ == '__main__':
    check_index_usage()
