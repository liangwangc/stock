#!/usr/bin/env python3
"""
修复密码字段脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'audit_system'))

from audit_system.database import DatabaseManager

def fix_password_field():
    """修复密码字段"""
    print("🔧 正在修复密码字段...")
    
    try:
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✅ 数据库连接成功")
        
        # 添加 password_hash 字段
        print("添加 password_hash 字段...")
        try:
            add_password_hash_sql = """
            ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希'
            """
            db_manager.execute_query(add_password_hash_sql)
            print("✅ 添加 password_hash 字段成功")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("ℹ️  password_hash 字段已存在")
            else:
                print(f"❌ 添加 password_hash 字段失败: {e}")
                return None
        
        # 重新创建管理员用户
        print("\n👤 重新创建管理员用户...")
        try:
            # 先删除旧的admin用户
            delete_admin_sql = "DELETE FROM users WHERE username = 'admin'"
            db_manager.execute_query(delete_admin_sql)
            print("✅ 删除旧的管理员用户")
            
            from audit_system.auth import AuthManager
            auth_manager = AuthManager(db_manager)
            
            # 创建新的管理员用户
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
                return None
                
        except Exception as e:
            print(f"❌ 创建管理员用户失败: {e}")
            return None
        
        # 验证用户创建
        print("\n🔍 验证用户创建...")
        try:
            users_sql = "SELECT id, username, real_name, email, role, department, status FROM users"
            users = db_manager.execute_query(users_sql)
            if users:
                print("✅ 用户列表:")
                for user in users:
                    print(f"  ID: {user['id']}, 用户名: {user['username']}, 姓名: {user['real_name']}, 角色: {user['role']}")
            else:
                print("❌ 没有找到任何用户")
                return None
        except Exception as e:
            print(f"❌ 验证用户失败: {e}")
            return None
        
        print("\n🎉 密码字段修复完成！")
        return db_manager
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 稽核档案管理系统 - 密码字段修复")
    print("=" * 60)
    
    # 修复密码字段
    db_manager = fix_password_field()
    if not db_manager:
        print("❌ 密码字段修复失败，系统无法继续")
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