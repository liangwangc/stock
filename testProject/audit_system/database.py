#!/usr/bin/env python3
"""
数据库连接和操作类

提供数据库连接、查询、插入、更新、删除等基本操作
"""

import pymysql
import pymysql.cursors
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.database.config import config


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.config = config.DATABASE_CONFIG
        self.connection = None
    
    def connect(self) -> pymysql.Connection:
        """连接到MySQL数据库"""
        try:
            self.connection = pymysql.connect(
                host=self.config.MYSQL_CONFIG["host"],
                port=self.config.MYSQL_CONFIG["port"],
                user=self.config.MYSQL_CONFIG["user"],
                password=self.config.MYSQL_CONFIG["password"],
                database=self.config.MYSQL_CONFIG["database"],
                charset=self.config.MYSQL_CONFIG["charset"],
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor
            )
            return self.connection
        except Exception as e:
            print(f"❌ 连接MySQL数据库失败: {e}")
            raise
    
    def get_connection(self) -> pymysql.Connection:
        """获取数据库连接"""
        if not self.connection or not self.connection.open:
            self.connect()
        return self.connection
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询语句"""
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except Exception as e:
            print(f"❌ 执行查询失败: {e}")
            print(f"SQL: {query}")
            print(f"参数: {params}")
            raise
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新语句，返回影响的行数"""
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                rows = cursor.execute(query, params or ())
                return rows
        except Exception as e:
            print(f"❌ 执行更新失败: {e}")
            print(f"SQL: {query}")
            print(f"参数: {params}")
            raise
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """执行插入语句，返回插入的ID"""
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.lastrowid
        except Exception as e:
            print(f"❌ 执行插入失败: {e}")
            print(f"SQL: {query}")
            print(f"参数: {params}")
            raise
    
    def execute_delete(self, query: str, params: tuple = None) -> int:
        """执行删除语句，返回影响的行数"""
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                rows = cursor.execute(query, params or ())
                return rows
        except Exception as e:
            print(f"❌ 执行删除失败: {e}")
            print(f"SQL: {query}")
            print(f"参数: {params}")
            raise
    
    def execute_transaction(self, queries: List[Tuple[str, tuple]]) -> bool:
        """执行事务"""
        try:
            connection = self.get_connection()
            connection.begin()
            
            for query, params in queries:
                with connection.cursor() as cursor:
                    cursor.execute(query, params or ())
            
            connection.commit()
            return True
        except Exception as e:
            connection.rollback()
            print(f"❌ 事务执行失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.connection and self.connection.open:
            self.connection.close()


class UserDAO:
    """用户数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_user(self, username: str, password_hash: str, real_name: str, 
                    email: str, phone: str = "", department: str = "", 
                    role: str = "user") -> int:
        """创建用户"""
        query = """
        INSERT INTO users (username, password_hash, real_name, email, phone, department, role)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return self.db.execute_insert(query, (username, password_hash, real_name, email, phone, department, role))
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        query = "SELECT * FROM users WHERE username = %s AND status = 'active'"
        results = self.db.execute_query(query, (username,))
        return results[0] if results else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取用户"""
        query = "SELECT * FROM users WHERE id = %s AND status = 'active'"
        results = self.db.execute_query(query, (user_id,))
        return results[0] if results else None
    
    def update_user_login(self, user_id: int, login_attempts: int = 0):
        """更新用户登录信息"""
        if login_attempts == 0:
            query = """
            UPDATE users SET last_login = NOW(), login_attempts = 0 
            WHERE id = %s
            """
            self.db.execute_update(query, (user_id,))
        else:
            query = """
            UPDATE users SET login_attempts = %s 
            WHERE id = %s
            """
            self.db.execute_update(query, (login_attempts, user_id))
    
    def lock_user(self, user_id: int):
        """锁定用户"""
        query = "UPDATE users SET status = 'locked' WHERE id = %s"
        self.db.execute_update(query, (user_id,))
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """获取所有用户"""
        query = "SELECT * FROM users ORDER BY created_at DESC"
        return self.db.execute_query(query)
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """更新用户信息"""
        if not kwargs:
            return False
        
        set_clauses = []
        params = []
        
        for key, value in kwargs.items():
            if key in ['real_name', 'email', 'phone', 'department', 'role', 'status']:
                set_clauses.append(f"{key} = %s")
                params.append(value)
            elif key == 'password':
                # 密码需要加密
                import bcrypt
                password_hash = bcrypt.hashpw(value.encode('utf-8'), bcrypt.gensalt())
                set_clauses.append("password_hash = %s")
                params.append(password_hash.decode('utf-8'))
        
        if not set_clauses:
            return False
        
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = %s"
        
        return self.db.execute_update(query, tuple(params)) > 0
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户（软删除）"""
        query = "UPDATE users SET status = 'deleted' WHERE id = %s"
        return self.db.execute_update(query, (user_id,)) > 0


class AuditFileDAO:
    """稽核档案数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_audit_file(self, file_number: str, title: str, category_id: int,
                          department_id: int, auditor_id: int, description: str = "",
                          priority: str = "medium", audit_date: str = None) -> int:
        """创建稽核档案"""
        query = """
        INSERT INTO audit_files (file_number, title, category_id, department_id, 
                                auditor_id, description, priority, audit_date, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.db.execute_insert(query, (file_number, title, category_id, department_id,
                                             auditor_id, description, priority, audit_date, auditor_id))
    
    def get_audit_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取稽核档案"""
        query = """
        SELECT af.*, u1.real_name as auditor_name, u2.real_name as creator_name,
               fc.name as category_name, d.name as department_name
        FROM audit_files af
        LEFT JOIN users u1 ON af.auditor_id = u1.id
        LEFT JOIN users u2 ON af.created_by = u2.id
        LEFT JOIN file_categories fc ON af.category_id = fc.id
        LEFT JOIN departments d ON af.department_id = d.id
        WHERE af.id = %s
        """
        results = self.db.execute_query(query, (file_id,))
        return results[0] if results else None
    
    def get_audit_files(self, status: str = None, category_id: int = None, 
                        department_id: int = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取稽核档案列表"""
        query = """
        SELECT af.*, u1.real_name as auditor_name, u2.real_name as creator_name,
               fc.name as category_name, d.name as department_name
        FROM audit_files af
        LEFT JOIN users u1 ON af.auditor_id = u1.id
        LEFT JOIN users u2 ON af.created_by = u2.id
        LEFT JOIN file_categories fc ON af.category_id = fc.id
        LEFT JOIN departments d ON af.department_id = d.id
        WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND af.status = %s"
            params.append(status)
        
        if category_id:
            query += " AND af.category_id = %s"
            params.append(category_id)
        
        if department_id:
            query += " AND af.department_id = %s"
            params.append(department_id)
        
        query += " ORDER BY af.created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.db.execute_query(query, tuple(params))
    
    def update_audit_file(self, file_id: int, **kwargs) -> bool:
        """更新稽核档案"""
        if not kwargs:
            return False
        
        set_clauses = []
        params = []
        
        for key, value in kwargs.items():
            if key in ['file_number', 'title', 'category_id', 'department_id', 'description', 'findings', 'recommendations', 'status', 'priority', 'audit_date', 'notes']:
                set_clauses.append(f"{key} = %s")
                params.append(value)
        
        if not set_clauses:
            return False
        
        params.append(file_id)
        query = f"UPDATE audit_files SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = %s"
        
        return self.db.execute_update(query, tuple(params)) > 0
    
    def delete_audit_file(self, file_id: int) -> bool:
        """删除稽核档案"""
        query = "DELETE FROM audit_files WHERE id = %s"
        return self.db.execute_delete(query, (file_id,)) > 0


class DepartmentDAO:
    """部门数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_all_departments(self) -> List[Dict[str, Any]]:
        """获取所有部门"""
        query = "SELECT * FROM departments WHERE status = 'active' ORDER BY sort_order, name"
        return self.db.execute_query(query)
    
    def get_department_by_id(self, dept_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取部门"""
        query = "SELECT * FROM departments WHERE id = %s AND status = 'active'"
        results = self.db.execute_query(query, (dept_id,))
        return results[0] if results else None


class FileCategoryDAO:
    """档案分类数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """获取所有档案分类"""
        query = "SELECT * FROM file_categories WHERE status = 'active' ORDER BY sort_order, name"
        return self.db.execute_query(query)
    
    def get_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取档案分类"""
        query = "SELECT * FROM file_categories WHERE id = %s AND status = 'active'"
        results = self.db.execute_query(query, (category_id,))
        return results[0] if results else None


class FileAttachmentDAO:
    """档案附件数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_attachment(self, file_id: int, filename: str, original_name: str, 
                         file_path: str, file_size: int, file_type: str, 
                         uploaded_by: int, description: str = "") -> int:
        """创建附件记录"""
        query = """
        INSERT INTO file_attachments (file_id, filename, original_name, file_path, 
                                    file_size, file_type, uploaded_by, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.db.execute_insert(query, (file_id, filename, original_name, file_path, 
                                            file_size, file_type, uploaded_by, description))
    
    def get_attachments_by_file_id(self, file_id: int) -> List[Dict[str, Any]]:
        """根据档案ID获取附件列表"""
        query = """
        SELECT fa.*, u.username as uploaded_by_name 
        FROM file_attachments fa
        LEFT JOIN users u ON fa.uploaded_by = u.id
        WHERE fa.file_id = %s AND fa.status = 'active'
        ORDER BY fa.created_at DESC
        """
        return self.db.execute_query(query, (file_id,))
    
    def get_attachment_by_id(self, attachment_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取附件"""
        query = "SELECT * FROM file_attachments WHERE id = %s AND status = 'active'"
        results = self.db.execute_query(query, (attachment_id,))
        return results[0] if results else None
    
    def delete_attachment(self, attachment_id: int) -> bool:
        """删除附件（软删除）"""
        query = "UPDATE file_attachments SET status = 'deleted', updated_at = NOW() WHERE id = %s"
        return self.db.execute_update(query, (attachment_id,)) > 0
    
    def update_attachment(self, attachment_id: int, **kwargs) -> bool:
        """更新附件信息"""
        if not kwargs:
            return False
        
        set_clauses = []
        params = []
        
        for key, value in kwargs.items():
            if key in ['description', 'status']:
                set_clauses.append(f"{key} = %s")
                params.append(value)
        
        if not set_clauses:
            return False
        
        params.append(attachment_id)
        query = f"UPDATE file_attachments SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = %s"
        
        return self.db.execute_update(query, tuple(params)) > 0


class AuditLogDAO:
    """稽核日志数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def log_action(self, user_id: int, action: str, target_type: str, 
                   target_id: int, details: str = "", ip_address: str = "",
                   user_agent: str = ""):
        """记录操作日志"""
        query = """
        INSERT INTO audit_logs (user_id, action, target_type, target_id, details, ip_address, user_agent)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return self.db.execute_insert(query, (user_id, action, target_type, target_id, details, ip_address, user_agent))
    
    def get_user_logs(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户操作日志"""
        query = """
        SELECT * FROM audit_logs WHERE user_id = %s ORDER BY created_at DESC LIMIT %s
        """
        return self.db.execute_query(query, (user_id, limit))
    
    def get_system_logs(self, action: str = None, user_id: int = None, 
                        date_from: str = None, date_to: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取系统操作日志"""
        query = """
        SELECT al.*, u.username, u.real_name as user_name FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.id
        WHERE 1=1
        """
        params = []
        
        if action:
            query += " AND al.action = %s"
            params.append(action)
        
        if user_id:
            query += " AND al.user_id = %s"
            params.append(user_id)
        
        if date_from:
            query += " AND DATE(al.created_at) >= %s"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(al.created_at) <= %s"
            params.append(date_to)
        
        query += " ORDER BY al.created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.db.execute_query(query, tuple(params))
    
    def get_log_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取单个日志详情"""
        query = """
        SELECT al.*, u.username, u.real_name as user_name, u.department as user_department
        FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.id
        WHERE al.id = %s
        """
        results = self.db.execute_query(query, (log_id,))
        return results[0] if results else None 