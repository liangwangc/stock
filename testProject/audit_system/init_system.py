#!/usr/bin/env python3
"""
系统初始化脚本

用于初始化稽核档案管理系统的数据库和基础数据
"""

import sys
import os
import getpass

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audit_system.database import DatabaseManager
from audit_system.auth import AuthManager


def init_database():
    """初始化数据库"""
    print("🔧 正在初始化数据库...")
    
    try:
        db_manager = DatabaseManager()
        
        # 读取SQL文件
        sql_file_path = os.path.join(os.path.dirname(__file__), 'database_schema.sql')
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        # 执行SQL语句
        for i, statement in enumerate(sql_statements, 1):
            if statement.startswith('--') or not statement:
                continue
            
            try:
                db_manager.execute_query(statement)
                print(f"✅ 执行SQL语句 {i}/{len(sql_statements)}")
            except Exception as e:
                print(f"⚠️  SQL语句 {i} 执行失败: {e}")
                # 继续执行其他语句
        
        print("✅ 数据库初始化完成")
        return db_manager
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return None


def create_admin_user(db_manager):
    """创建管理员用户"""
    print("\n👤 创建管理员用户...")
    
    try:
        auth_manager = AuthManager(db_manager)
        
        print("请输入管理员账户信息:")
        username = input("用户名 (默认: admin): ").strip() or "admin"
        real_name = input("真实姓名: ").strip()
        email = input("邮箱: ").strip()
        department = input("部门: ").strip() or "稽核部"
        
        while True:
            password = getpass.getpass("密码: ").strip()
            confirm_password = getpass.getpass("确认密码: ").strip()
            
            if password != confirm_password:
                print("❌ 两次输入的密码不匹配，请重新输入")
                continue
            
            if len(password) < 6:
                print("❌ 密码长度不能少于6位，请重新输入")
                continue
            
            break
        
        # 创建管理员用户
        result = auth_manager.create_user(
            username=username,
            password=password,
            real_name=real_name,
            email=email,
            role="admin",
            department=department
        )
        
        if result["success"]:
            print(f"✅ 管理员用户创建成功！")
            print(f"   用户名: {username}")
            print(f"   真实姓名: {real_name}")
            print(f"   角色: admin")
        else:
            print(f"❌ 管理员用户创建失败: {result['message']}")
            
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")


def create_sample_data(db_manager):
    """创建示例数据"""
    print("\n📊 创建示例数据...")
    
    try:
        # 创建示例稽核档案
        print("正在创建示例稽核档案...")
        
        # 获取第一个分类和部门
        categories = db_manager.execute_query("SELECT id FROM file_categories LIMIT 1")
        departments = db_manager.execute_query("SELECT id FROM departments LIMIT 1")
        users = db_manager.execute_query("SELECT id FROM users LIMIT 1")
        
        if categories and departments and users:
            category_id = categories[0]['id']
            department_id = departments[0]['id']
            user_id = users[0]['id']
            
            # 插入示例档案
            sample_files = [
                ("AUDIT-2024-001", "财务流程稽核", "对财务部门的日常流程进行稽核检查", "medium"),
                ("AUDIT-2024-002", "IT系统安全稽核", "检查IT系统的安全配置和访问控制", "high"),
                ("AUDIT-2024-003", "人事制度稽核", "稽核人事管理制度的执行情况", "medium"),
                ("AUDIT-2024-004", "运营效率稽核", "评估运营部门的效率指标", "low"),
                ("AUDIT-2024-005", "合规性稽核", "检查业务操作的合规性", "urgent")
            ]
            
            for file_number, title, description, priority in sample_files:
                query = """
                INSERT INTO audit_files (file_number, title, category_id, department_id, 
                                       auditor_id, description, priority, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                db_manager.execute_insert(query, (file_number, title, category_id, department_id,
                                                 user_id, description, priority, user_id))
            
            print(f"✅ 创建了 {len(sample_files)} 个示例稽核档案")
        else:
            print("⚠️  无法创建示例档案，缺少必要的分类、部门或用户数据")
        
        # 创建示例通知
        print("正在创建示例通知...")
        sample_notifications = [
            ("系统初始化完成", "稽核档案管理系统已成功初始化，欢迎使用！", "success"),
            ("新档案创建提醒", "有新的稽核档案需要处理，请及时查看。", "info"),
            ("系统维护通知", "系统将于今晚进行维护，请提前保存工作。", "warning")
        ]
        
        for title, content, type_ in sample_notifications:
            query = """
            INSERT INTO notifications (user_id, title, content, type)
            VALUES (%s, %s, %s, %s)
            """
            db_manager.execute_insert(query, (user_id, title, content, type_))
        
        print(f"✅ 创建了 {len(sample_notifications)} 个示例通知")
        
    except Exception as e:
        print(f"❌ 创建示例数据失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("🏛️  稽核档案管理系统初始化")
    print("=" * 60)
    
    # 检查是否已安装必要的依赖
    try:
        import bcrypt
        import jwt
        import pymysql
    except ImportError as e:
        print(f"❌ 缺少必要的依赖包: {e}")
        print("请先运行: pip install bcrypt PyJWT pymysql")
        return
    
    # 初始化数据库
    db_manager = init_database()
    if not db_manager:
        print("❌ 数据库初始化失败，系统无法继续")
        return
    
    # 创建管理员用户
    create_admin_user(db_manager)
    
    # 创建示例数据
    create_sample_data(db_manager)
    
    print("\n" + "=" * 60)
    print("🎉 系统初始化完成！")
    print("=" * 60)
    print("现在你可以运行以下命令启动系统:")
    print("  py audit_system/main.py")
    print("\n默认管理员账户:")
    print("  用户名: admin")
    print("  密码: admin123")
    print("\n注意: 请及时修改默认密码！")
    print("=" * 60)
    
    # 关闭数据库连接
    db_manager.close()


if __name__ == "__main__":
    main() 