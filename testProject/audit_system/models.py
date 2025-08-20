#!/usr/bin/env python3
"""
数据模型定义

定义系统中的所有数据结构和关系
"""

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class User:
    """用户模型"""
    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    real_name: str = ""
    email: str = ""
    phone: str = ""
    department: str = ""
    role: str = "user"  # admin, user, auditor
    status: str = "active"  # active, inactive, locked
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    login_attempts: int = 0


@dataclass
class AuditFile:
    """稽核档案模型"""
    id: Optional[int] = None
    file_number: str = ""  # 档案编号
    title: str = ""  # 档案标题
    category: str = ""  # 档案分类
    department: str = ""  # 所属部门
    auditor: str = ""  # 稽核人员
    audit_date: Optional[datetime] = None  # 稽核日期
    status: str = "pending"  # pending, in_progress, completed, archived
    priority: str = "medium"  # low, medium, high, urgent
    description: str = ""  # 档案描述
    findings: str = ""  # 稽核发现
    recommendations: str = ""  # 建议措施
    attachments: str = ""  # 附件路径（JSON格式存储多个文件）
    created_by: int = 0  # 创建人ID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class FileCategory:
    """档案分类模型"""
    id: Optional[int] = None
    name: str = ""  # 分类名称
    code: str = ""  # 分类代码
    parent_id: Optional[int] = None  # 父分类ID
    description: str = ""  # 分类描述
    sort_order: int = 0  # 排序
    status: str = "active"  # active, inactive
    created_at: Optional[datetime] = None


@dataclass
class Department:
    """部门模型"""
    id: Optional[int] = None
    name: str = ""  # 部门名称
    code: str = ""  # 部门代码
    parent_id: Optional[int] = None  # 父部门ID
    manager: str = ""  # 部门负责人
    description: str = ""  # 部门描述
    status: str = "active"  # active, inactive
    created_at: Optional[datetime] = None


@dataclass
class AuditLog:
    """稽核日志模型"""
    id: Optional[int] = None
    user_id: int = 0  # 操作用户ID
    action: str = ""  # 操作类型
    target_type: str = ""  # 操作对象类型
    target_id: int = 0  # 操作对象ID
    details: str = ""  # 操作详情
    ip_address: str = ""  # IP地址
    user_agent: str = ""  # 用户代理
    created_at: Optional[datetime] = None


@dataclass
class FileAttachment:
    """档案附件模型"""
    id: Optional[int] = None
    file_id: int = 0  # 档案ID
    filename: str = ""  # 文件名
    original_name: str = ""  # 原始文件名
    file_path: str = ""  # 文件路径
    file_size: int = 0  # 文件大小（字节）
    file_type: str = ""  # 文件类型
    uploaded_by: int = 0  # 上传人ID
    uploaded_at: Optional[datetime] = None
    description: str = ""  # 文件描述


@dataclass
class Notification:
    """通知模型"""
    id: Optional[int] = None
    user_id: int = 0  # 接收用户ID
    title: str = ""  # 通知标题
    content: str = ""  # 通知内容
    type: str = "info"  # info, warning, error, success
    is_read: bool = False  # 是否已读
    related_type: str = ""  # 相关对象类型
    related_id: int = 0  # 相关对象ID
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


@dataclass
class SystemSetting:
    """系统设置模型"""
    id: Optional[int] = None
    key: str = ""  # 设置键
    value: str = ""  # 设置值
    description: str = ""  # 设置描述
    category: str = ""  # 设置分类
    is_public: bool = False  # 是否公开
    updated_by: int = 0  # 更新人ID
    updated_at: Optional[datetime] = None 