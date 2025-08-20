#!/usr/bin/env python3
"""
手动创建数据库表脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'audit_system'))

from audit_system.database import DatabaseManager

def create_tables():
    """创建数据库表"""
    print("🔧 正在创建数据库表...")
    
    try:
        db_manager = DatabaseManager()
        db_manager.connect()
        print("✅ 数据库连接成功")
        
        # 创建用户表
        print("创建用户表...")
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
            password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
            real_name VARCHAR(100) NOT NULL COMMENT '真实姓名',
            email VARCHAR(100) UNIQUE NOT NULL COMMENT '邮箱',
            phone VARCHAR(20) COMMENT '电话',
            department VARCHAR(100) COMMENT '部门',
            role ENUM('admin', 'user', 'auditor') DEFAULT 'user' COMMENT '角色',
            status ENUM('active', 'inactive', 'locked') DEFAULT 'active' COMMENT '状态',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            last_login TIMESTAMP NULL COMMENT '最后登录时间',
            login_attempts INT DEFAULT 0 COMMENT '登录尝试次数',
            INDEX idx_username (username),
            INDEX idx_email (email),
            INDEX idx_role (role),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表'
        """
        db_manager.execute_query(create_users_table)
        print("✅ 用户表创建成功")
        
        # 创建部门表
        print("创建部门表...")
        create_departments_table = """
        CREATE TABLE IF NOT EXISTS departments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL COMMENT '部门名称',
            code VARCHAR(50) UNIQUE NOT NULL COMMENT '部门代码',
            parent_id INT NULL COMMENT '父部门ID',
            manager VARCHAR(100) COMMENT '部门负责人',
            description TEXT COMMENT '部门描述',
            status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            INDEX idx_code (code),
            INDEX idx_parent_id (parent_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部门表'
        """
        db_manager.execute_query(create_departments_table)
        print("✅ 部门表创建成功")
        
        # 创建档案分类表
        print("创建档案分类表...")
        create_categories_table = """
        CREATE TABLE IF NOT EXISTS file_categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL COMMENT '分类名称',
            code VARCHAR(50) UNIQUE NOT NULL COMMENT '分类代码',
            parent_id INT NULL COMMENT '父分类ID',
            description TEXT COMMENT '分类描述',
            sort_order INT DEFAULT 0 COMMENT '排序',
            status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            INDEX idx_code (code),
            INDEX idx_parent_id (parent_id),
            INDEX idx_sort_order (sort_order),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='档案分类表'
        """
        db_manager.execute_query(create_categories_table)
        print("✅ 档案分类表创建成功")
        
        # 创建稽核档案表
        print("创建稽核档案表...")
        create_audit_files_table = """
        CREATE TABLE IF NOT EXISTS audit_files (
            id INT AUTO_INCREMENT PRIMARY KEY,
            file_number VARCHAR(50) UNIQUE NOT NULL COMMENT '档案编号',
            title VARCHAR(200) NOT NULL COMMENT '档案标题',
            category_id INT NOT NULL COMMENT '档案分类ID',
            department_id INT NOT NULL COMMENT '所属部门ID',
            auditor_id INT NOT NULL COMMENT '稽核人员ID',
            audit_date DATE COMMENT '稽核日期',
            status ENUM('pending', 'in_progress', 'completed', 'archived') DEFAULT 'pending' COMMENT '状态',
            priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium' COMMENT '优先级',
            description TEXT COMMENT '档案描述',
            findings TEXT COMMENT '稽核发现',
            recommendations TEXT COMMENT '建议措施',
            created_by INT NOT NULL COMMENT '创建人ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            completed_at TIMESTAMP NULL COMMENT '完成时间',
            INDEX idx_file_number (file_number),
            INDEX idx_category_id (category_id),
            INDEX idx_department_id (department_id),
            INDEX idx_auditor_id (auditor_id),
            INDEX idx_status (status),
            INDEX idx_priority (priority),
            INDEX idx_audit_date (audit_date),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='稽核档案表'
        """
        db_manager.execute_query(create_audit_files_table)
        print("✅ 稽核档案表创建成功")
        
        # 创建稽核日志表
        print("创建稽核日志表...")
        create_logs_table = """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL COMMENT '操作用户ID',
            action VARCHAR(100) NOT NULL COMMENT '操作类型',
            target_type VARCHAR(100) NOT NULL COMMENT '操作对象类型',
            target_id INT NOT NULL COMMENT '操作对象ID',
            details TEXT COMMENT '操作详情',
            ip_address VARCHAR(45) COMMENT 'IP地址',
            user_agent TEXT COMMENT '用户代理',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            INDEX idx_user_id (user_id),
            INDEX idx_action (action),
            INDEX idx_target_type (target_type),
            INDEX idx_target_id (target_id),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='稽核日志表'
        """
        db_manager.execute_query(create_logs_table)
        print("✅ 稽核日志表创建成功")
        
        # 创建通知表
        print("创建通知表...")
        create_notifications_table = """
        CREATE TABLE IF NOT EXISTS notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL COMMENT '接收用户ID',
            title VARCHAR(200) NOT NULL COMMENT '通知标题',
            content TEXT COMMENT '通知内容',
            type ENUM('info', 'warning', 'error', 'success') DEFAULT 'info' COMMENT '通知类型',
            is_read BOOLEAN DEFAULT FALSE COMMENT '是否已读',
            related_type VARCHAR(100) COMMENT '相关对象类型',
            related_id INT COMMENT '相关对象ID',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            read_at TIMESTAMP NULL COMMENT '阅读时间',
            INDEX idx_user_id (user_id),
            INDEX idx_type (type),
            INDEX idx_is_read (is_read),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知表'
        """
        db_manager.execute_query(create_notifications_table)
        print("✅ 通知表创建成功")
        
        # 插入默认数据
        print("插入默认数据...")
        
        # 插入部门
        insert_departments = """
        INSERT IGNORE INTO departments (name, code, description) VALUES 
        ('稽核部', 'AUDIT', '负责内部稽核工作'),
        ('财务部', 'FINANCE', '负责财务管理'),
        ('人事部', 'HR', '负责人力资源管理'),
        ('技术部', 'TECH', '负责技术开发'),
        ('运营部', 'OPERATIONS', '负责日常运营')
        """
        db_manager.execute_query(insert_departments)
        print("✅ 部门数据插入成功")
        
        # 插入档案分类
        insert_categories = """
        INSERT IGNORE INTO file_categories (name, code, description, sort_order) VALUES 
        ('财务稽核', 'FINANCE_AUDIT', '财务相关稽核档案', 1),
        ('运营稽核', 'OPERATIONS_AUDIT', '运营相关稽核档案', 2),
        ('合规稽核', 'COMPLIANCE_AUDIT', '合规相关稽核档案', 3),
        ('IT稽核', 'IT_AUDIT', 'IT系统稽核档案', 4),
        ('人事稽核', 'HR_AUDIT', '人事相关稽核档案', 5)
        """
        db_manager.execute_query(insert_categories)
        print("✅ 档案分类数据插入成功")
        
        print("\n🎉 所有数据库表创建完成！")
        return db_manager
        
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        return None

def create_admin_user(db_manager):
    """创建管理员用户"""
    print("\n👤 创建管理员用户...")
    
    try:
        from audit_system.auth import AuthManager
        auth_manager = AuthManager(db_manager)
        
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
            
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("🏛️  稽核档案管理系统 - 数据库表创建")
    print("=" * 60)
    
    # 创建表
    db_manager = create_tables()
    if not db_manager:
        print("❌ 数据库表创建失败，系统无法继续")
        return
    
    # 创建管理员用户
    create_admin_user(db_manager)
    
    print("\n" + "=" * 60)
    print("🎉 系统初始化完成！")
    print("=" * 60)
    print("现在你可以运行以下命令启动系统:")
    print("  py audit_system/main.py")
    print("\n默认管理员账户:")
    print("  用户名: admin")
    print("  密码: admin123")
    print("=" * 60)
    
    # 关闭数据库连接
    db_manager.close()

if __name__ == "__main__":
    main() 