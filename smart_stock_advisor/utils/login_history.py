"""
用户登录历史记录模块
用于记录和管理用户登录历史
"""
import re
from typing import Dict, Optional
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


class LoginHistoryManager:
    """登录历史管理器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
    
    def parse_user_agent(self, user_agent: str) -> Dict[str, Optional[str]]:
        """
        解析User-Agent字符串，提取设备类型、浏览器、操作系统等信息
        
        Args:
            user_agent: User-Agent字符串
            
        Returns:
            包含device_type、browser、os的字典
        """
        if not user_agent:
            return {
                'device_type': None,
                'browser': None,
                'os': None
            }
        
        result = {
            'device_type': None,
            'browser': None,
            'os': None
        }
        
        user_agent_lower = user_agent.lower()
        
        # 检测设备类型
        if any(x in user_agent_lower for x in ['mobile', 'android', 'iphone', 'ipod', 'ipad']):
            if 'ipad' in user_agent_lower:
                result['device_type'] = 'Tablet'
            elif any(x in user_agent_lower for x in ['iphone', 'ipod', 'android']):
                result['device_type'] = 'Mobile'
            else:
                result['device_type'] = 'Mobile'
        elif 'tablet' in user_agent_lower:
            result['device_type'] = 'Tablet'
        else:
            result['device_type'] = 'PC'
        
        # 检测浏览器
        if 'chrome' in user_agent_lower and 'edg' not in user_agent_lower:
            result['browser'] = 'Chrome'
        elif 'edg' in user_agent_lower:
            result['browser'] = 'Edge'
        elif 'firefox' in user_agent_lower:
            result['browser'] = 'Firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            result['browser'] = 'Safari'
        elif 'opera' in user_agent_lower or 'opr' in user_agent_lower:
            result['browser'] = 'Opera'
        elif 'msie' in user_agent_lower or 'trident' in user_agent_lower:
            result['browser'] = 'IE'
        elif 'micromessenger' in user_agent_lower:
            result['browser'] = 'WeChat'
        elif 'qqbrowser' in user_agent_lower:
            result['browser'] = 'QQ Browser'
        else:
            result['browser'] = 'Unknown'
        
        # 检测操作系统
        if 'windows' in user_agent_lower:
            if 'windows nt 10' in user_agent_lower or 'windows nt 11' in user_agent_lower:
                result['os'] = 'Windows 10/11'
            elif 'windows nt 6.3' in user_agent_lower:
                result['os'] = 'Windows 8.1'
            elif 'windows nt 6.2' in user_agent_lower:
                result['os'] = 'Windows 8'
            elif 'windows nt 6.1' in user_agent_lower:
                result['os'] = 'Windows 7'
            else:
                result['os'] = 'Windows'
        elif 'mac os x' in user_agent_lower or 'macintosh' in user_agent_lower:
            result['os'] = 'macOS'
        elif 'linux' in user_agent_lower:
            result['os'] = 'Linux'
        elif 'android' in user_agent_lower:
            result['os'] = 'Android'
        elif 'iphone' in user_agent_lower or 'ipad' in user_agent_lower or 'ipod' in user_agent_lower:
            result['os'] = 'iOS'
        else:
            result['os'] = 'Unknown'
        
        return result
    
    def record_login(self, username: str, login_status: str, user_id: Optional[int] = None,
                    failure_reason: Optional[str] = None, ip_address: Optional[str] = None,
                    user_agent: Optional[str] = None, session_id: Optional[str] = None) -> bool:
        """
        记录登录历史
        
        Args:
            username: 用户名
            login_status: 登录状态（'success' 或 'failed'）
            user_id: 用户ID（登录成功时提供）
            failure_reason: 失败原因（登录失败时提供）
            ip_address: IP地址
            user_agent: User-Agent字符串
            session_id: 会话ID（登录成功时提供）
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 解析User-Agent
            ua_info = self.parse_user_agent(user_agent or '')
            
            # 检查表是否存在
            try:
                check_sql = """
                    SELECT COUNT(*) as cnt 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                      AND table_name = 'user_login_history'
                """
                result = self.db.execute_query(check_sql)
                table_exists = result and len(result) > 0 and result[0].get('cnt', 0) > 0
                
                if not table_exists:
                    self.logger.warning("user_login_history 表不存在，请先执行 database/user_login_history.sql")
                    return False
            except Exception as e:
                self.logger.error(f"检查表是否存在失败: {str(e)}")
                return False
            
            # 插入登录历史记录
            sql = """
                INSERT INTO user_login_history 
                (user_id, username, login_status, failure_reason, ip_address, user_agent, 
                 session_id, device_type, browser, os, login_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            params = (
                user_id,
                username,
                login_status,
                failure_reason,
                ip_address,
                user_agent,
                session_id,
                ua_info['device_type'],
                ua_info['browser'],
                ua_info['os']
            )
            
            self.db.execute_update(sql, params)
            
            self.logger.debug(f"记录登录历史成功: username={username}, status={login_status}")
            return True
            
        except Exception as e:
            self.logger.error(f"记录登录历史失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def get_login_history(self, user_id: Optional[int] = None, username: Optional[str] = None,
                         start_date: Optional[str] = None, end_date: Optional[str] = None,
                         login_status: Optional[str] = None, limit: int = 100) -> list:
        """
        获取登录历史记录
        
        Args:
            user_id: 用户ID（可选）
            username: 用户名（可选）
            start_date: 开始日期（可选，格式：YYYY-MM-DD）
            end_date: 结束日期（可选，格式：YYYY-MM-DD）
            login_status: 登录状态（可选，'success' 或 'failed'）
            limit: 返回记录数限制
            
        Returns:
            登录历史记录列表
        """
        try:
            sql = """
                SELECT id, user_id, username, login_status, failure_reason,
                       ip_address, user_agent, login_time, session_id,
                       device_type, browser, os
                FROM user_login_history
                WHERE 1=1
            """
            params = []
            
            if user_id:
                sql += " AND user_id = %s"
                params.append(user_id)
            
            if username:
                sql += " AND username = %s"
                params.append(username)
            
            if start_date:
                sql += " AND login_time >= %s"
                params.append(start_date)
            
            if end_date:
                sql += " AND login_time <= %s"
                params.append(end_date)
            
            if login_status:
                sql += " AND login_status = %s"
                params.append(login_status)
            
            sql += " ORDER BY login_time DESC LIMIT %s"
            params.append(limit)
            
            results = self.db.execute_query(sql, tuple(params))
            return results if results else []
            
        except Exception as e:
            self.logger.error(f"获取登录历史失败: {str(e)}")
            return []
