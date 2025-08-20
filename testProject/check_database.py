#!/usr/bin/env python3
"""
数据库状态检查脚本
"""

import pymysql
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'audit_system'))

from config import config

def check_database():
    """检查数据库状态"""
    try:
        db_config = config.DATABASE_CONFIG.MYSQL_CONFIG
        connection = pymysql.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            charset=db_config["charset"],
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print(f"✅ 成功连接到数据库: {db_config['database']}")
        
        with connection.cursor() as cursor:
            # 检查表是否存在
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            print(f"\n📊 数据库中的表:")
            print("-" * 50)
            for table in tables:
                table_name = list(table.values())[0]
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count = cursor.fetchone()['count']
                print(f"{table_name:<20} - {count} 行")
            
            # 检查file_attachments表
            print(f"\n🔍 检查file_attachments表:")
            try:
                cursor.execute("DESCRIBE file_attachments")
                columns = cursor.fetchall()
                print("✅ file_attachments表存在")
                print("字段结构:")
                for col in columns:
                    print(f"  {col['Field']:<15} {col['Type']:<20} {col['Null']:<5} {col['Key']:<5} {col['Default']:<10}")
            except Exception as e:
                print(f"❌ file_attachments表不存在: {e}")
            
            # 检查audit_files表的notes字段
            print(f"\n🔍 检查audit_files表的notes字段:")
            try:
                cursor.execute("DESCRIBE audit_files")
                columns = cursor.fetchall()
                has_notes = any(col['Field'] == 'notes' for col in columns)
                if has_notes:
                    print("✅ notes字段已存在")
                else:
                    print("❌ notes字段不存在")
            except Exception as e:
                print(f"❌ 检查audit_files表失败: {e}")
        
        connection.close()
        print("\n🔌 数据库连接已关闭")
        
    except Exception as e:
        print(f"❌ 检查数据库失败: {e}")

if __name__ == "__main__":
    check_database() 