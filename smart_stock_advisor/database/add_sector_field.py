#!/usr/bin/env python3
"""
执行 add_sector_field.sql 脚本
为 stock_predictions 表添加 sector 字段
"""
import os
import sys
import pymysql

# 设置输出编码为UTF-8（Windows控制台）
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config_db import DB_CONFIG

def execute_sql_script():
    """执行SQL脚本"""
    sql_file = os.path.join(os.path.dirname(__file__), 'add_sector_field.sql')
    
    if not os.path.exists(sql_file):
        print(f"SQL文件不存在: {sql_file}")
        return False
    
    print(f"读取SQL文件: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 分割SQL语句（按分号）
    sql_statements = []
    current_stmt = []
    for line in sql_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('--'):
            continue
        current_stmt.append(line)
        if line.endswith(';'):
            sql_statements.append(' '.join(current_stmt))
            current_stmt = []
    
    if not sql_statements:
        print("未找到有效的SQL语句")
        return False
    
    try:
        # 连接数据库
        print(f"正在连接到数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        connection = pymysql.connect(**DB_CONFIG)
        
        success_count = 0
        error_count = 0
        
        with connection.cursor() as cursor:
            for i, sql in enumerate(sql_statements, 1):
                try:
                    print(f"\n[{i}/{len(sql_statements)}] 执行SQL:")
                    print(f"   {sql[:100]}...")
                    cursor.execute(sql)
                    success_count += 1
                    print(f"   执行成功")
                except Exception as e:
                    error_count += 1
                    error_msg = str(e)
                    print(f"   执行失败: {error_msg}")
                    
                    # 如果字段或索引已存在，不算错误
                    if 'Duplicate column name' in error_msg or 'Duplicate key name' in error_msg:
                        print(f"   字段或索引已存在，跳过")
                        success_count += 1
                        error_count -= 1
        
        if not DB_CONFIG.get('autocommit', True):
            connection.commit()
        connection.close()
        
        print("\n" + "=" * 60)
        print(f"SQL脚本执行完成！")
        print(f"   成功: {success_count} 个SQL语句")
        if error_count > 0:
            print(f"   失败: {error_count} 个SQL语句")
        print("=" * 60)
        
        return error_count == 0
        
    except Exception as e:
        print(f"\n执行SQL脚本失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("执行 add_sector_field.sql 脚本")
    print("=" * 60)
    
    success = execute_sql_script()
    
    if success:
        print("\nsector字段添加成功！")
        print("现在可以正常使用板块匹配功能了。")
        sys.exit(0)
    else:
        print("\n执行过程中遇到一些问题，请检查上面的错误信息。")
        sys.exit(1)
