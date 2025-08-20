#!/usr/bin/env python3
"""
用户认证和权限管理模块

提供用户登录、权限验证、密码加密等功能
"""

import hashlib
import bcrypt
import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audit_system.database import DatabaseManager, UserDAO, AuditLogDAO


class AuthManager:
    """认证管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.user_dao = UserDAO(db_manager)
        self.log_dao = AuditLogDAO(db_manager)
        self.secret_key = "your-secret-key-here"  # 在生产环境中应该从配置文件读取
        self.token_expiry = 24 * 60 * 60  # 24小时
    
    def hash_password(self, password: str) -> str:
        """密码加密"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def login(self, username: str, password: str, ip_address: str = "", user_agent: str = "") -> Dict[str, Any]:
        """用户登录"""
        try:
            # 获取用户信息
            user = self.user_dao.get_user_by_username(username)
            if not user:
                return {"success": False, "message": "用户名或密码错误"}
            
            # 检查用户状态
            if user['status'] != 'active':
                if user['status'] == 'locked':
                    return {"success": False, "message": "账户已被锁定，请联系管理员"}
                else:
                    return {"success": False, "message": "账户状态异常，请联系管理员"}
            
            # 验证密码
            if not self.verify_password(password, user['password_hash']):
                # 记录登录失败
                login_attempts = user['login_attempts'] + 1
                self.user_dao.update_user_login(user['id'], login_attempts)
                
                # 如果失败次数过多，锁定账户
                if login_attempts >= 5:
                    self.user_dao.lock_user(user['id'])
                    self.log_dao.log_action(
                        user['id'], "login_failed", "user", user['id'],
                        f"登录失败次数过多，账户被锁定", ip_address, user_agent
                    )
                    return {"success": False, "message": "登录失败次数过多，账户已被锁定"}
                
                return {"success": False, "message": "用户名或密码错误"}
            
            # 登录成功，重置登录失败次数
            self.user_dao.update_user_login(user['id'], 0)
            
            # 生成JWT token
            token = self.generate_token(user['id'], user['username'], user['role'])
            
            # 记录登录日志
            self.log_dao.log_action(
                user['id'], "login", "user", user['id'],
                "用户登录成功", ip_address, user_agent
            )
            
            return {
                "success": True,
                "message": "登录成功",
                "token": token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "real_name": user['real_name'],
                    "email": user['email'],
                    "role": user['role'],
                    "department": user['department']
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"登录失败: {str(e)}"}
    
    def generate_token(self, user_id: int, username: str, role: str) -> str:
        """生成JWT token"""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': time.time() + self.token_expiry
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """获取当前用户信息"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user = self.user_dao.get_user_by_id(payload['user_id'])
        if not user or user['status'] != 'active':
            return None
        
        return user
    
    def require_auth(self, token: str) -> bool:
        """验证用户是否已认证"""
        return self.verify_token(token) is not None
    
    def require_role(self, token: str, required_roles: list) -> bool:
        """验证用户角色权限"""
        payload = self.verify_token(token)
        if not payload:
            return False
        
        return payload['role'] in required_roles
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码"""
        try:
            user = self.user_dao.get_user_by_id(user_id)
            if not user:
                return {"success": False, "message": "用户不存在"}
            
            # 验证旧密码
            if not self.verify_password(old_password, user['password_hash']):
                return {"success": False, "message": "旧密码错误"}
            
            # 加密新密码
            new_password_hash = self.hash_password(new_password)
            
            # 更新密码
            query = "UPDATE users SET password_hash = %s WHERE id = %s"
            self.db.execute_update(query, (new_password_hash, user_id))
            
            # 记录操作日志
            self.log_dao.log_action(
                user_id, "change_password", "user", user_id,
                "用户修改密码"
            )
            
            return {"success": True, "message": "密码修改成功"}
            
        except Exception as e:
            return {"success": False, "message": f"密码修改失败: {str(e)}"}
    
    def create_user(self, username: str, password: str, real_name: str, 
                    email: str, role: str = "user", department: str = "", 
                    phone: str = "", creator_id: int = None) -> Dict[str, Any]:
        """创建新用户"""
        try:
            # 检查用户名是否已存在
            existing_user = self.user_dao.get_user_by_username(username)
            if existing_user:
                return {"success": False, "message": "用户名已存在"}
            
            # 检查邮箱是否已存在
            if email:
                query = "SELECT id FROM users WHERE email = %s"
                existing_email = self.db.execute_query(query, (email,))
                if existing_email:
                    return {"success": False, "message": "邮箱已存在"}
            
            # 加密密码
            password_hash = self.hash_password(password)
            
            # 创建用户
            user_id = self.user_dao.create_user(
                username, password_hash, real_name, email, phone, department, role
            )
            
            # 记录操作日志
            if creator_id:
                self.log_dao.log_action(
                    creator_id, "create_user", "user", user_id,
                    f"创建用户: {username}"
                )
            
            return {"success": True, "message": "用户创建成功", "user_id": user_id}
            
        except Exception as e:
            return {"success": False, "message": f"用户创建失败: {str(e)}"}
    
    def logout(self, token: str, ip_address: str = "", user_agent: str = "") -> Dict[str, Any]:
        """用户登出"""
        try:
            payload = self.verify_token(token)
            if payload:
                # 记录登出日志
                self.log_dao.log_action(
                    payload['user_id'], "logout", "user", payload['user_id'],
                    "用户登出", ip_address, user_agent
                )
            
            return {"success": True, "message": "登出成功"}
            
        except Exception as e:
            return {"success": False, "message": f"登出失败: {str(e)}"}


class PermissionManager:
    """权限管理器"""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth = auth_manager
    
    def can_view_files(self, token: str) -> bool:
        """检查是否可以查看档案"""
        return self.auth.require_auth(token)
    
    def can_create_files(self, token: str) -> bool:
        """检查是否可以创建档案"""
        return self.auth.require_role(token, ['admin', 'auditor'])
    
    def can_edit_files(self, token: str, file_creator_id: int = None) -> bool:
        """检查是否可以编辑档案"""
        payload = self.auth.verify_token(token)
        if not payload:
            return False
        
        # 管理员和稽核员可以编辑所有档案
        if payload['role'] in ['admin', 'auditor']:
            return True
        
        # 普通用户只能编辑自己创建的档案
        if payload['role'] == 'user' and file_creator_id:
            return payload['user_id'] == file_creator_id
        
        return False
    
    def can_delete_files(self, token: str) -> bool:
        """检查是否可以删除档案"""
        return self.auth.require_role(token, ['admin'])
    
    def can_manage_users(self, token: str) -> bool:
        """检查是否可以管理用户"""
        return self.auth.require_role(token, ['admin'])
    
    def can_view_logs(self, token: str) -> bool:
        """检查是否可以查看日志"""
        return self.auth.require_role(token, ['admin', 'auditor'])
    
    def can_manage_system(self, token: str) -> bool:
        """检查是否可以管理系统"""
        return self.auth.require_role(token, ['admin']) 