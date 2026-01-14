#!/usr/bin/env python3
"""
数据库修复脚本
用于创建缺失的表和字段
"""

import pymysql
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'audit_system'))

from config import config

def connect_database():
    """连接数据库"""
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
        return connection
    except Exception as e:
        print(f"❌ 连接数据库失败: {e}")
        return None

def execute_sql_file(connection, sql_file):
    """执行SQL文件"""
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        with connection.cursor() as cursor:
            for i, statement in enumerate(sql_statements, 1):
                if statement and not statement.startswith('--'):
                    try:
                        print(f"执行SQL {i}: {statement[:50]}...")
                        cursor.execute(statement)
                        print(f"✅ SQL {i} 执行成功")
                    except Exception as e:
                        print(f"⚠️ SQL {i} 执行失败: {e}")
                        # 继续执行其他语句
        
        print("✅ SQL文件执行完成")
        return True
    except Exception as e:
        print(f"❌ 执行SQL文件失败: {e}")
        return False

def check_tables(connection):
    """检查表是否创建成功"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    TABLE_NAME,
                    TABLE_ROWS,
                    TABLE_COMMENT
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME IN ('audit_files', 'file_attachments', 'audit_logs', 'notifications', 'system_settings')
                ORDER BY TABLE_NAME
            """, (config.DATABASE_CONFIG.MYSQL_CONFIG["database"],))
            
            tables = cursor.fetchall()
            
            print("\n📊 数据库表状态检查:")
            print("-" * 60)
            print(f"{'表名':<20} {'行数':<10} {'说明'}")
            print("-" * 60)
            
            for table in tables:
                print(f"{table['TABLE_NAME']:<20} {table['TABLE_ROWS']:<10} {table['TABLE_COMMENT']}")
            
            print("-" * 60)
            return len(tables) >= 5  # 应该有5个主要表
            
    except Exception as e:
        print(f"❌ 检查表状态失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始修复稽核档案管理系统数据库...")
    print("=" * 60)
    
    # 连接数据库
    connection = connect_database()
    if not connection:
        return
    
    try:
        # 执行SQL修复脚本
        sql_file = "fix_database_simple.sql"
        if os.path.exists(sql_file):
            print(f"\n📝 执行SQL修复脚本: {sql_file}")
            if execute_sql_file(connection, sql_file):
                print("✅ 数据库修复脚本执行成功")
            else:
                print("❌ 数据库修复脚本执行失败")
        else:
            print(f"❌ SQL修复脚本文件不存在: {sql_file}")
            return
        
        # 检查表状态
        print("\n🔍 检查数据库表状态...")
        if check_tables(connection):
            print("✅ 所有必要的表都已创建成功！")
        else:
            print("⚠️ 部分表可能创建失败，请检查错误信息")
        
        print("\n✨ 数据库修复完成！")
        print("\n📝 下一步操作:")
        print("1. 重启Web应用")
        print("2. 测试编辑功能是否正常")
        print("3. 如果还有问题，请检查错误日志")
        
    except Exception as e:
        print(f"❌ 修复过程中发生错误: {e}")
    finally:
        connection.close()
        print("🔌 数据库连接已关闭")

if __name__ == "__main__":
    main() 