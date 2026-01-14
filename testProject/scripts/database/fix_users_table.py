#!/usr/bin/env python3
"""
修复用户表结构脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'audit_system'))

from audit_system.database import DatabaseManager

def fix_users_table():
    """修复用户表结构"""
    print("🔧 正在修复用户表结构....")
    
    try:
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✅ 数据库连接成功")
        
        # 检查并添加缺失的字段
        print("检查用户表结构...")
        
        # 添加 status 字段
        try:
            add_status_sql = """
            ALTER TABLE users ADD COLUMN status ENUM('active', 'inactive', 'locked') DEFAULT 'active' COMMENT '状态'
            """
            db_manager.execute_query(add_status_sql)
            print("✅ 添加 status 字段成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  status 字段已存在")
            else:
                print(f"⚠️  添加 status 字段时出现问题: {e}")
        
        # 添加其他可能缺失的字段
        try:
            add_phone_sql = """
            ALTER TABLE users ADD COLUMN phone VARCHAR(20) COMMENT '电话'
            """
            db_manager.execute_query(add_phone_sql)
            print("✅ 添加 phone 字段成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  phone 字段已存在")
            else:
                print(f"⚠️  添加 phone 字段时出现问题: {e}")
        
        try:
            add_last_login_sql = """
            ALTER TABLE users ADD COLUMN last_login TIMESTAMP NULL COMMENT '最后登录时间'
            """
            db_manager.execute_query(add_last_login_sql)
            print("✅ 添加 last_login 字段成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  last_login 字段已存在")
            else:
                print(f"⚠️  添加 last_login 字段时出现问题: {e}")
        
        try:
            add_login_attempts_sql = """
            ALTER TABLE users ADD COLUMN login_attempts INT DEFAULT 0 COMMENT '登录尝试次数'
            """
            db_manager.execute_query(add_login_attempts_sql)
            print("✅ 添加 login_attempts 字段成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  login_attempts 字段已存在")
            else:
                print(f"⚠️  添加 login_attempts 字段时出现问题: {e}")
        
        # 创建管理员用户
        print("\n👤 创建管理员用户...")
        try:
            from audit_system.auth import AuthManager
            auth_manager = AuthManager(db_manager)
            
            # 检查是否已存在管理员用户
            check_admin_sql = "SELECT id FROM users WHERE username = 'admin'"
            result = db_manager.execute_query(check_admin_sql)
            
            if not result:
                # 创建默认管理员用户
                result = auth_manager.create_user(
                    username="admin",
                    password="admin123",
                    real_name="系统管理员",
                    email="admin@example.com",
                    role="admin",
                    department="稽核部"
                )
                
                if result["success"]:
                    print("✅ 管理员用户创建成功！")
                    print("   用户名: admin")
                    print("   密码: admin123")
                    print("   角色: admin")
                else:
                    print(f"❌ 管理员用户创建失败: {result['message']}")
            else:
                print("ℹ️  管理员用户已存在")
                
        except Exception as e:
            print(f"❌ 创建管理员用户失败: {e}")
        
        print("\n🎉 用户表结构修复完成！")
        return db_manager
        
    except Exception as e:
        print(f"❌ 修复表结构失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 稽核档案管理系统 - 用户表结构修复")
    print("=" * 60)
    
    # 修复表结构
    db_manager = fix_users_table()
    if not db_manager:
        print("❌ 表结构修复失败，系统无法继续")
        return
    
    print("\n" + "=" * 60)
    print("🎉 修复完成！")
    print("=" * 60)
    print("现在你可以重新启动Web应用:")
    print("  py web_app.py")
    print("\n然后使用以下账户登录:")
    print("  用户名: admin")
    print("  密码: admin123")
    print("=" * 60)
    
    # 关闭数据库连接
    db_manager.close()

if __name__ == "__main__":
    main() 