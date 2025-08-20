#!/usr/bin/env python3
"""
检查用户表数据脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'audit_system'))

from audit_system.database import DatabaseManager

def check_users():
    """检查用户表数据"""
    print("🔍 检查用户表数据...")
    
    try:
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✅ 数据库连接成功")
        
        # 查看用户表结构
        print("\n📋 用户表结构:")
        try:
            desc_sql = "DESCRIBE users"
            result = db_manager.execute_query(desc_sql)
            for row in result:
                print(f"  {row['Field']} - {row['Type']} - {row['Null']} - {row['Default']} - {row['Comment']}")
        except Exception as e:
            print(f"❌ 查看表结构失败: {e}")
        
        # 查看所有用户
        print("\n👥 用户列表:")
        try:
            users_sql = "SELECT id, username, real_name, email, role, department, status FROM users"
            users = db_manager.execute_query(users_sql)
            if users:
                for user in users:
                    print(f"  ID: {user['id']}, 用户名: {user['username']}, 姓名: {user['real_name']}, 角色: {user['role']}, 部门: {user['department']}, 状态: {user['status']}")
            else:
                print("  ❌ 没有找到任何用户")
        except Exception as e:
            print(f"❌ 查询用户失败: {e}")
        
        # 测试登录验证
        print("\n🔐 测试登录验证:")
        try:
            from audit_system.auth import AuthManager
            auth_manager = AuthManager(db_manager)
            
            # 测试admin用户登录
            result = auth_manager.login("admin", "admin123")
            print(f"  登录结果: {result}")
            
            if result['success']:
                print("  ✅ 登录验证成功")
                user_data = result['user']
                print(f"  用户信息: {user_data}")
            else:
                print(f"  ❌ 登录验证失败: {result['message']}")
                
        except Exception as e:
            print(f"❌ 测试登录失败: {e}")
        
        return db_manager
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 稽核档案管理系统 - 用户数据检查")
    print("=" * 60)
    
    # 检查用户数据
    db_manager = check_users()
    if not db_manager:
        print("❌ 检查失败")
        return
    
    print("\n" + "=" * 60)
    print("🔍 检查完成！")
    print("=" * 60)
    
    # 关闭数据库连接
    db_manager.close()

if __name__ == "__main__":
    main() 