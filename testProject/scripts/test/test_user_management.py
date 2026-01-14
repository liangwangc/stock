#!/usr/bin/env python3
"""
测试用户管理和操作日志功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'audit_system'))

from audit_system.database import DatabaseManager, UserDAO, AuditLogDAO
from audit_system.auth import AuthManager

def test_user_management():
    """测试用户管理功能"""
    print("🔧 测试用户管理功能...")
    
    try:
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✅ 数据库连接成功")
        
        # 测试用户DAO
        user_dao = UserDAO(db_manager)
        
        # 获取所有用户
        print("\n📋 获取所有用户...")
        users = user_dao.get_all_users()
        print(f"✅ 找到 {len(users)} 个用户:")
        for user in users:
            print(f"  - ID: {user['id']}, 用户名: {user['username']}, 角色: {user['role']}, 状态: {user.get('status', 'N/A')}")
        
        # 测试获取特定用户
        if users:
            first_user = users[0]
            print(f"\n🔍 测试获取用户 {first_user['username']}...")
            user_by_id = user_dao.get_user_by_id(first_user['id'])
            if user_by_id:
                print(f"✅ 用户信息: {user_by_id['real_name']} ({user_by_id['email']})")
            else:
                print("❌ 获取用户失败")
        
        # 测试AuthManager
        print("\n🔐 测试AuthManager...")
        auth_manager = AuthManager(db_manager)
        
        # 测试创建用户（模拟）
        print("📝 测试用户创建逻辑...")
        test_username = "test_user_123"
        test_email = "test123@example.com"
        
        # 检查用户是否已存在
        existing_user = user_dao.get_user_by_username(test_username)
        if existing_user:
            print(f"⚠️  测试用户 {test_username} 已存在")
        else:
            print(f"✅ 测试用户名 {test_username} 可用")
        
        existing_email = user_dao.get_user_by_email(test_email)
        if existing_email:
            print(f"⚠️  测试邮箱 {test_email} 已存在")
        else:
            print(f"✅ 测试邮箱 {test_email} 可用")
        
        print("\n✅ 用户管理功能测试完成")
        return db_manager
        
    except Exception as e:
        print(f"❌ 用户管理功能测试失败: {e}")
        return None

def test_audit_logs():
    """测试操作日志功能"""
    print("\n🔧 测试操作日志功能...")
    
    try:
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✅ 数据库连接成功")
        
        # 测试日志DAO
        log_dao = AuditLogDAO(db_manager)
        
        # 获取系统日志
        print("\n📋 获取系统操作日志...")
        logs = log_dao.get_system_logs(limit=20)
        print(f"✅ 找到 {len(logs)} 条日志记录:")
        
        for i, log in enumerate(logs[:5]):  # 只显示前5条
            print(f"  {i+1}. [{log.get('created_at', 'N/A')}] {log.get('user_name', '未知用户')} - {log.get('action', 'N/A')}")
        
        if len(logs) > 5:
            print(f"  ... 还有 {len(logs) - 5} 条记录")
        
        # 测试日志筛选
        print("\n🔍 测试日志筛选功能...")
        
        # 按操作类型筛选
        login_logs = log_dao.get_system_logs(action='web_login', limit=10)
        print(f"✅ 登录日志: {len(login_logs)} 条")
        
        # 按日期筛选（最近7天）
        from datetime import datetime, timedelta
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        recent_logs = log_dao.get_system_logs(
            date_from=week_ago.strftime('%Y-%m-%d'),
            date_to=today.strftime('%Y-%m-%d'),
            limit=10
        )
        print(f"✅ 最近7天日志: {len(recent_logs)} 条")
        
        print("\n✅ 操作日志功能测试完成")
        return db_manager
        
    except Exception as e:
        print(f"❌ 操作日志功能测试失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 稽核档案管理系统 - 用户管理和操作日志功能测试")
    print("=" * 60)
    
    # 测试用户管理
    db_manager1 = test_user_management()
    
    # 测试操作日志
    db_manager2 = test_audit_logs()
    
    print("\n" + "=" * 60)
    print("🎉 测试完成！")
    print("=" * 60)
    
    if db_manager1:
        db_manager1.close()
    if db_manager2 and db_manager2 != db_manager1:
        db_manager2.close()

if __name__ == "__main__":
    main() 