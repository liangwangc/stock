# -*- coding: utf-8 -*-
"""
用户管理模块
提供用户的增删改查、登录验证、会话管理等功能
"""
import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib
import secrets

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.logger import get_logger
from config_db import USE_DATABASE, DB_CONFIG
from werkzeug.security import generate_password_hash, check_password_hash

logger = get_logger(__name__)


class UserManager:
    """用户管理器"""
    
    def __init__(self):
        self.use_database = USE_DATABASE
        self.logger = logger
    
    def create_user(self, username: str, password: str, role: str = 'user', 
                   email: Optional[str] = None) -> Optional[int]:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码（明文）
            role: 角色（admin/user）
            email: 邮箱（可选）
            
        Returns:
            用户ID，失败返回None
        """
        if not self.use_database:
            self.logger.warning("数据库未启用，无法创建用户")
            return None
        
        # 检查用户名是否已存在
        if self.get_user_by_username(username):
            self.logger.error(f"用户名 {username} 已存在")
            return None
        
        try:
            # 生成密码哈希
            password_hash = generate_password_hash(password)
            
            # 插入用户
            sql = """
                INSERT INTO users (username, password_hash, role, email, is_active)
                VALUES (%s, %s, %s, %s, 1)
            """
            params = (username, password_hash, role, email)
            DBConnection.execute_update(sql, params)
            
            # 获取新创建的用户ID
            result = DBConnection.execute_query("SELECT LAST_INSERT_ID() as id")
            if result and len(result) > 0:
                user_id = result[0].get('id') or result[0].get('LAST_INSERT_ID()')
            else:
                # 如果LAST_INSERT_ID()失败，通过用户名查询
                user = self.get_user_by_username(username)
                user_id = user.get('id') if user else None
            
            self.logger.info(f"创建用户成功: {username} (ID: {user_id})")
            return user_id
            
        except Exception as e:
            self.logger.error(f"创建用户失败: {str(e)}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """根据用户名获取用户信息"""
        if not self.use_database:
            return None
        
        try:
            sql = "SELECT * FROM users WHERE username = %s"
            result = DBConnection.execute_query(sql, (username,))
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"获取用户失败: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """根据用户ID获取用户信息"""
        if not self.use_database:
            return None
        
        try:
            sql = "SELECT * FROM users WHERE id = %s"
            result = DBConnection.execute_query(sql, (user_id,))
            return result[0] if result else None
        except Exception as e:
            self.logger.error(f"获取用户失败: {str(e)}")
            return None
    
    def verify_password(self, username: str, password: str) -> bool:
        """
        验证用户密码
        
        Args:
            username: 用户名
            password: 密码（明文）
            
        Returns:
            验证成功返回True，失败返回False
        """
        user = self.get_user_by_username(username)
        if not user:
            return False
        
        if not user.get('is_active', 0):
            self.logger.warning(f"用户 {username} 已被禁用")
            return False
        
        return check_password_hash(user['password_hash'], password)
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            **kwargs: 要更新的字段（password, role, email, is_active等）
            
        Returns:
            成功返回True，失败返回False
        """
        if not self.use_database:
            return False
        
        try:
            updates = []
            params = []
            
            allowed_fields = ['password', 'role', 'email', 'is_active']
            
            for key, value in kwargs.items():
                if key in allowed_fields:
                    if key == 'password':
                        # 密码需要哈希
                        updates.append("password_hash = %s")
                        params.append(generate_password_hash(value))
                    else:
                        updates.append(f"{key} = %s")
                        params.append(value)
            
            if not updates:
                return False
            
            params.append(user_id)
            sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
            DBConnection.execute_update(sql, tuple(params))
            
            self.logger.info(f"更新用户成功: ID={user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"更新用户失败: {str(e)}")
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """
        删除用户（软删除，设置为非激活状态）
        
        Args:
            user_id: 用户ID
            
        Returns:
            成功返回True，失败返回False
        """
        if not self.use_database:
            return False
        
        try:
            sql = "UPDATE users SET is_active = 0 WHERE id = %s"
            DBConnection.execute_update(sql, (user_id,))
            self.logger.info(f"删除用户成功: ID={user_id}")
            return True
        except Exception as e:
            self.logger.error(f"删除用户失败: {str(e)}")
            return False
    
    def get_all_users(self) -> List[Dict]:
        """获取所有用户列表"""
        if not self.use_database:
            return []
        
        try:
            sql = "SELECT id, username, role, email, is_active, last_login, created_at FROM users ORDER BY created_at DESC"
            return DBConnection.execute_query(sql)
        except Exception as e:
            self.logger.error(f"获取用户列表失败: {str(e)}")
            return []
    
    def create_session(self, user_id: int, session_id: str, ip_address: Optional[str] = None,
                     user_agent: Optional[str] = None) -> bool:
        """
        创建用户登录会话（用于单点登录）
        
        Args:
            user_id: 用户ID
            session_id: Flask session ID
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            成功返回True，失败返回False
        """
        if not self.use_database:
            return False
        
        try:
            # 先使该用户的所有其他会话失效（实现单点登录）
            self.invalidate_user_sessions(user_id, exclude_session_id=session_id)
            
            # 创建新会话
            sql = """
                INSERT INTO user_sessions (user_id, session_id, ip_address, user_agent, is_active)
                VALUES (%s, %s, %s, %s, 1)
            """
            params = (user_id, session_id, ip_address, user_agent)
            DBConnection.execute_update(sql, params)
            
            # 更新用户最后登录时间
            self.update_last_login(user_id, ip_address)
            
            self.logger.info(f"创建会话成功: user_id={user_id}, session_id={session_id[:20]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"创建会话失败: {str(e)}")
            return False
    
    def validate_session(self, session_id: str) -> Optional[Dict]:
        """
        验证会话是否有效
        
        Args:
            session_id: Flask session ID
            
        Returns:
            如果会话有效，返回用户信息字典，否则返回None
        """
        if not self.use_database:
            return None
        
        try:
            # 检查表是否存在，如果不存在则创建
            try:
                check_table_sql = """
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = 'user_sessions'
                """
                result = DBConnection.execute_query(check_table_sql, (DB_CONFIG.get('database', 'stock_data'),))
                table_exists = result and len(result) > 0 and result[0].get('count', 0) > 0
                
                if not table_exists:
                    self.logger.warning("user_sessions 表不存在，正在自动创建...")
                    # 读取并执行创建表的SQL
                    table_sql_path = os.path.join(project_root, 'database', 'user_tables.sql')
                    if os.path.exists(table_sql_path):
                        with open(table_sql_path, 'r', encoding='utf-8') as f:
                            sql_content = f.read()
                        # 提取 user_sessions 表的创建语句
                        import re
                        # 找到 CREATE TABLE user_sessions 的语句
                        match = re.search(r'CREATE TABLE IF NOT EXISTS `user_sessions`.*?ENGINE=InnoDB.*?COMMENT=.*?;', 
                                        sql_content, re.DOTALL)
                        if match:
                            create_table_sql = match.group(0)
                            conn = DBConnection.get_connection()
                            if conn:
                                with conn.cursor() as cursor:
                                    cursor.execute(create_table_sql)
                                conn.commit()
                                self.logger.info("user_sessions 表创建成功")
                    else:
                        self.logger.warning(f"找不到 user_tables.sql 文件: {table_sql_path}")
            except Exception as table_check_error:
                self.logger.warning(f"检查或创建 user_sessions 表时出错: {str(table_check_error)}")
                # 继续执行，如果表确实不存在，查询会失败
            
            sql = """
                SELECT s.*, u.username, u.role, u.is_active as user_active
                FROM user_sessions s
                INNER JOIN users u ON s.user_id = u.id
                WHERE s.session_id = %s AND s.is_active = 1 AND u.is_active = 1
            """
            result = DBConnection.execute_query(sql, (session_id,))
            
            if result:
                session = result[0]
                # 更新最后活动时间
                self.update_session_activity(session_id)
                return session
            return None
            
        except Exception as e:
            error_msg = str(e)
            # 如果表不存在，记录警告但不抛出异常
            if 'doesn\'t exist' in error_msg or "Table" in error_msg and "doesn't exist" in error_msg:
                self.logger.warning(f"user_sessions 表不存在，无法验证会话: {error_msg}")
                # 返回None表示会话无效，但不会导致程序崩溃
                return None
            self.logger.error(f"验证会话失败: {error_msg}")
            self.logger.error(traceback.format_exc())
            return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """使会话失效"""
        if not self.use_database:
            return False
        
        try:
            sql = "UPDATE user_sessions SET is_active = 0 WHERE session_id = %s"
            DBConnection.execute_update(sql, (session_id,))
            return True
        except Exception as e:
            self.logger.error(f"使会话失效失败: {str(e)}")
            return False
    
    def invalidate_user_sessions(self, user_id: int, exclude_session_id: Optional[str] = None) -> bool:
        """
        使用户的所有会话失效（除了指定的会话ID，用于单点登录）
        
        Args:
            user_id: 用户ID
            exclude_session_id: 要排除的会话ID（不使其失效）
            
        Returns:
            成功返回True
        """
        if not self.use_database:
            return False
        
        try:
            if exclude_session_id:
                sql = "UPDATE user_sessions SET is_active = 0 WHERE user_id = %s AND session_id != %s"
                params = (user_id, exclude_session_id)
            else:
                sql = "UPDATE user_sessions SET is_active = 0 WHERE user_id = %s"
                params = (user_id,)
            
            DBConnection.execute_update(sql, params)
            return True
        except Exception as e:
            self.logger.error(f"使用户会话失效失败: {str(e)}")
            return False
    
    def update_session_activity(self, session_id: str) -> bool:
        """更新会话最后活动时间"""
        if not self.use_database:
            return False
        
        try:
            sql = "UPDATE user_sessions SET last_activity = NOW() WHERE session_id = %s"
            DBConnection.execute_update(sql, (session_id,))
            return True
        except Exception as e:
            self.logger.error(f"更新会话活动时间失败: {str(e)}")
            return False
    
    def update_last_login(self, user_id: int, ip_address: Optional[str] = None) -> bool:
        """更新用户最后登录时间和IP"""
        if not self.use_database:
            return False
        
        try:
            sql = "UPDATE users SET last_login = NOW(), last_login_ip = %s WHERE id = %s"
            DBConnection.execute_update(sql, (ip_address, user_id))
            return True
        except Exception as e:
            self.logger.error(f"更新最后登录信息失败: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self, hours: int = 24) -> int:
        """
        清理过期的会话（超过指定小时未活动的会话）
        
        Args:
            hours: 过期时间（小时）
            
        Returns:
            清理的会话数量
        """
        if not self.use_database:
            return 0
        
        try:
            sql = """
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE is_active = 1 
                AND last_activity < DATE_SUB(NOW(), INTERVAL %s HOUR)
            """
            DBConnection.execute_update(sql, (hours,))
            
            # 获取清理的数量
            result = DBConnection.execute_query("SELECT ROW_COUNT() as count")
            count = result[0]['count'] if result else 0
            
            self.logger.info(f"清理过期会话: {count} 个")
            return count
        except Exception as e:
            self.logger.error(f"清理过期会话失败: {str(e)}")
            return 0
