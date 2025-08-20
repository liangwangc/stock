#!/usr/bin/env python3
"""
修复档案分类表结构脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'audit_system'))

from audit_system.database import DatabaseManager

def fix_categories_table():
    """修复档案分类表结构"""
    print("🔧 正在修复档案分类表结构...")
    
    try:
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✅ 数据库连接成功")
        
        # 检查档案分类表结构
        print("检查档案分类表结构...")
        try:
            desc_sql = "DESCRIBE file_categories"
            result = db_manager.execute_query(desc_sql)
            print("当前表结构:")
            for row in result:
                field_name = list(row.values())[0] if row else "unknown"
                print(f"  {field_name}")
        except Exception as e:
            print(f"❌ 查看表结构失败: {e}")
        
        # 添加缺失的字段
        print("\n添加缺失的字段...")
        
        # 添加 sort_order 字段
        try:
            add_sort_order_sql = """
            ALTER TABLE file_categories ADD COLUMN sort_order INT DEFAULT 0 COMMENT '排序'
            """
            db_manager.execute_query(add_sort_order_sql)
            print("✅ 添加 sort_order 字段成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  sort_order 字段已存在")
            else:
                print(f"❌ 添加 sort_order 字段失败: {e}")
        
        # 添加 parent_id 字段
        try:
            add_parent_id_sql = """
            ALTER TABLE file_categories ADD COLUMN parent_id INT NULL COMMENT '父分类ID'
            """
            db_manager.execute_query(add_parent_id_sql)
            print("✅ 添加 parent_id 字段成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  parent_id 字段已存在")
            else:
                print(f"❌ 添加 parent_id 字段失败: {e}")
        
        # 添加 status 字段
        try:
            add_status_sql = """
            ALTER TABLE file_categories ADD COLUMN status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态'
            """
            db_manager.execute_query(add_status_sql)
            print("✅ 添加 status 字段成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  status 字段已存在")
            else:
                print(f"❌ 添加 status 字段失败: {e}")
        
        # 添加 created_at 字段
        try:
            add_created_at_sql = """
            ALTER TABLE file_categories ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
            """
            db_manager.execute_query(add_created_at_sql)
            print("✅ 添加 created_at 字段成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  created_at 字段已存在")
            else:
                print(f"❌ 添加 created_at 字段失败: {e}")
        
        # 更新现有数据的 sort_order
        print("\n更新现有数据的 sort_order...")
        try:
            update_sort_order_sql = """
            UPDATE file_categories SET sort_order = id WHERE sort_order IS NULL OR sort_order = 0
            """
            db_manager.execute_query(update_sort_order_sql)
            print("✅ 更新 sort_order 成功")
        except Exception as e:
            print(f"⚠️  更新 sort_order 时出现问题: {e}")
        
        # 验证修复结果
        print("\n🔍 验证修复结果...")
        try:
            categories_sql = "SELECT id, name, code, sort_order, status FROM file_categories ORDER BY sort_order"
            categories = db_manager.execute_query(categories_sql)
            if categories:
                print("✅ 档案分类列表:")
                for cat in categories:
                    print(f"  ID: {cat['id']}, 名称: {cat['name']}, 代码: {cat['code']}, 排序: {cat['sort_order']}, 状态: {cat['status']}")
            else:
                print("❌ 没有找到档案分类")
        except Exception as e:
            print(f"❌ 验证失败: {e}")
        
        print("\n🎉 档案分类表结构修复完成！")
        return db_manager
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 稽核档案管理系统 - 档案分类表修复")
    print("=" * 60)
    
    # 修复表结构
    db_manager = fix_categories_table()
    if not db_manager:
        print("❌ 表结构修复失败")
        return
    
    print("\n" + "=" * 60)
    print("🎉 修复完成！")
    print("=" * 60)
    print("现在档案分类功能应该可以正常工作了！")
    print("=" * 60)
    
    # 关闭数据库连接
    db_manager.close()

if __name__ == "__main__":
    main() 