#!/usr/bin/env python3
"""
完全清理数据库脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'audit_system'))

from audit_system.database import DatabaseManager

def clean_database():
    """完全清理数据库"""
    print("🧹 正在完全清理数据库...")
    
    try:
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✅ 数据库连接成功")
        
        # 禁用外键检查
        print("禁用外键检查...")
        db_manager.execute_query("SET FOREIGN_KEY_CHECKS = 0")
        
        # 获取所有表名
        print("获取所有表名...")
        show_tables_sql = "SHOW TABLES"
        tables_result = db_manager.execute_query(show_tables_sql)
        
        if tables_result:
            table_names = []
            for row in tables_result:
                # 获取表名（可能是第一个字段）
                table_name = list(row.values())[0]
                table_names.append(table_name)
            
            print(f"找到以下表: {table_names}")
            
            # 删除所有表
            print("删除所有表...")
            for table_name in table_names:
                try:
                    drop_sql = f"DROP TABLE IF EXISTS `{table_name}`"
                    db_manager.execute_query(drop_sql)
                    print(f"✅ 删除表 {table_name} 成功")
                except Exception as e:
                    print(f"⚠️  删除表 {table_name} 时出现问题: {e}")
        else:
            print("ℹ️  数据库中没有表")
        
        # 重新启用外键检查
        print("重新启用外键检查...")
        db_manager.execute_query("SET FOREIGN_KEY_CHECKS = 1")
        
        print("\n🎉 数据库清理完成！")
        return db_manager
        
    except Exception as e:
        print(f"❌ 清理数据库失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🧹 稽核档案管理系统 - 数据库清理")
    print("=" * 60)
    
    # 清理数据库
    db_manager = clean_database()
    if not db_manager:
        print("❌ 数据库清理失败")
        return
    
    print("\n" + "=" * 60)
    print("🎉 清理完成！")
    print("=" * 60)
    print("现在你可以运行以下命令重新创建表:")
    print("  py recreate_tables.py")
    print("=" * 60)
    
    # 关闭数据库连接
    db_manager.close()

if __name__ == "__main__":
    main() 