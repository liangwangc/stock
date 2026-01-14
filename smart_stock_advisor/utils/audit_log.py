"""
操作审计日志模块
记录用户操作、系统事件等重要操作的审计日志
"""
import os
import sys
import threading
from datetime import datetime
from typing import Dict, List, Optional
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)


class AuditLogger:
    """操作审计日志记录器"""
    
    def __init__(self):
        self.logger = logger
        self.db = DBConnection()
        self.use_database = USE_DATABASE
    
    def log_operation(self, user_id: int, operation_type: str, resource_type: str,
                     resource_id: Optional[str] = None, details: Optional[Dict] = None,
                     ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                     success: bool = True, error_message: Optional[str] = None) -> bool:
        """
        记录操作审计日志
        
        Args:
            user_id: 用户ID
            operation_type: 操作类型（create/update/delete/view/login/logout等）
            resource_type: 资源类型（user/stock/prediction/task/config等）
            resource_id: 资源ID（可选）
            details: 操作详情（可选，JSON格式）
            ip_address: IP地址（可选）
            user_agent: 用户代理（可选）
            success: 是否成功
            error_message: 错误信息（可选）
        
        Returns:
            是否记录成功
        """
        if not self.use_database:
            # 如果数据库未启用，只记录到日志文件
            log_message = (
                f"审计日志: user_id={user_id}, operation={operation_type}, "
                f"resource={resource_type}, resource_id={resource_id}, "
                f"success={success}, ip={ip_address}"
            )
            if error_message:
                log_message += f", error={error_message}"
            self.logger.info(log_message)
            return True
        
        try:
            # 检查audit_logs表是否存在，如果不存在则创建
            self._ensure_table_exists()
            
            sql = """
                INSERT INTO audit_logs
                (user_id, operation_type, resource_type, resource_id,
                 details, ip_address, user_agent, success, error_message,
                 created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            details_json = json.dumps(details, ensure_ascii=False) if details else None
            
            params = (
                user_id, operation_type, resource_type, resource_id,
                details_json, ip_address, user_agent, 1 if success else 0,
                error_message, datetime.now()
            )
            
            self.db.execute_update(sql, params)
            return True
            
        except Exception as e:
            # 如果表不存在或插入失败，记录到日志文件
            log_message = (
                f"审计日志（数据库失败）: user_id={user_id}, operation={operation_type}, "
                f"resource={resource_type}, error={str(e)}"
            )
            self.logger.warning(log_message)
            return False
    
    def _ensure_table_exists(self):
        """确保audit_logs表存在"""
        try:
            # 检查表是否存在
            check_sql = """
                SELECT COUNT(*) as cnt 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'audit_logs'
            """
            result = self.db.execute_query(check_sql)
            
            if not result or result[0].get('cnt', 0) == 0:
                # 表不存在，创建表
                create_sql = """
                    CREATE TABLE IF NOT EXISTS `audit_logs` (
                        `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                        `user_id` INT NOT NULL COMMENT '用户ID',
                        `operation_type` VARCHAR(50) NOT NULL COMMENT '操作类型（create/update/delete/view/login/logout等）',
                        `resource_type` VARCHAR(50) NOT NULL COMMENT '资源类型（user/stock/prediction/task/config等）',
                        `resource_id` VARCHAR(100) DEFAULT NULL COMMENT '资源ID',
                        `details` JSON DEFAULT NULL COMMENT '操作详情（JSON格式）',
                        `ip_address` VARCHAR(50) DEFAULT NULL COMMENT 'IP地址',
                        `user_agent` VARCHAR(500) DEFAULT NULL COMMENT '用户代理',
                        `success` TINYINT(1) DEFAULT 1 COMMENT '是否成功（1=成功，0=失败）',
                        `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
                        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        
                        INDEX `idx_user_id` (`user_id`),
                        INDEX `idx_operation_type` (`operation_type`),
                        INDEX `idx_resource_type` (`resource_type`),
                        INDEX `idx_resource_id` (`resource_id`),
                        INDEX `idx_created_at` (`created_at`),
                        INDEX `idx_success` (`success`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作审计日志表';
                """
                
                try:
                    self.db.execute_update(create_sql)
                    self.logger.info("audit_logs表已创建")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        self.logger.warning(f"创建audit_logs表失败（可能已存在）: {str(e)}")
        except Exception as e:
            self.logger.debug(f"检查audit_logs表失败: {str(e)}")
    
    def get_audit_logs(self, user_id: Optional[int] = None, operation_type: Optional[str] = None,
                      resource_type: Optional[str] = None, start_date: Optional[str] = None,
                      end_date: Optional[str] = None, page: int = 1, page_size: int = 50) -> Dict:
        """
        获取审计日志
        
        Args:
            user_id: 用户ID（可选）
            operation_type: 操作类型（可选）
            resource_type: 资源类型（可选）
            start_date: 开始日期（可选，YYYY-MM-DD）
            end_date: 结束日期（可选，YYYY-MM-DD）
            page: 页码（默认1）
            page_size: 每页数量（默认50）
        
        Returns:
            审计日志列表和分页信息
        """
        if not self.use_database:
            return {'data': [], 'total': 0, 'page': page, 'page_size': page_size, 'total_pages': 0}
        
        try:
            # 构建WHERE条件
            where_conditions = []
            params = []
            
            if user_id:
                where_conditions.append("user_id = %s")
                params.append(user_id)
            
            if operation_type:
                where_conditions.append("operation_type = %s")
                params.append(operation_type)
            
            if resource_type:
                where_conditions.append("resource_type = %s")
                params.append(resource_type)
            
            if start_date:
                where_conditions.append("created_at >= %s")
                params.append(f"{start_date} 00:00:00")
            
            if end_date:
                where_conditions.append("created_at <= %s")
                params.append(f"{end_date} 23:59:59")
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) as cnt FROM audit_logs WHERE {where_clause}"
            count_result = self.db.execute_query(count_sql, tuple(params))
            total = count_result[0]['cnt'] if count_result else 0
            
            # 分页查询
            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT * FROM audit_logs
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])
            
            results = self.db.execute_query(query_sql, tuple(params))
            
            # 解析JSON字段
            for record in results:
                if record.get('details'):
                    try:
                        record['details'] = json.loads(record['details'])
                    except:
                        pass
            
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            return {
                'data': results or [],
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            self.logger.error(f"获取审计日志失败: {str(e)}")
            return {'data': [], 'total': 0, 'page': page, 'page_size': page_size, 'total_pages': 0}


# 全局审计日志记录器实例
_audit_logger = None
_audit_logger_lock = threading.Lock()


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志记录器实例（单例模式）"""
    global _audit_logger
    
    if _audit_logger is None:
        with _audit_logger_lock:
            if _audit_logger is None:
                _audit_logger = AuditLogger()
    
    return _audit_logger
