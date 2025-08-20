#!/usr/bin/env python3
"""
文件附件数据访问对象
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

class FileAttachmentDAO:
    """文件附件数据访问对象"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def create_attachment(self, file_id: int, filename: str, original_name: str, 
                         file_path: str, file_size: int, file_type: str, 
                         uploaded_by: int, description: str = "") -> int:
        """创建文件附件记录"""
        sql = """
        INSERT INTO file_attachments (
            file_id, filename, original_name, file_path, file_size, 
            file_type, uploaded_by, description, uploaded_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            file_id, filename, original_name, file_path, file_size,
            file_type, uploaded_by, description, datetime.now()
        )
        
        return self.db_manager.execute_insert(sql, params)
    
    def get_attachment_by_id(self, attachment_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取附件信息"""
        sql = """
        SELECT fa.*, u.real_name as uploader_name
        FROM file_attachments fa
        LEFT JOIN users u ON fa.uploaded_by = u.id
        WHERE fa.id = %s
        """
        result = self.db_manager.execute_query(sql, (attachment_id,))
        return result[0] if result else None
    
    def get_attachments_by_file_id(self, file_id: int) -> List[Dict[str, Any]]:
        """根据档案ID获取所有附件"""
        sql = """
        SELECT fa.*, u.real_name as uploader_name
        FROM file_attachments fa
        LEFT JOIN users u ON fa.uploaded_by = u.id
        WHERE fa.file_id = %s
        ORDER BY fa.uploaded_at DESC
        """
        return self.db_manager.execute_query(sql, (file_id,))
    
    def get_all_attachments(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有附件"""
        sql = """
        SELECT fa.*, u.real_name as uploader_name, af.title as file_title
        FROM file_attachments fa
        LEFT JOIN users u ON fa.uploaded_by = u.id
        LEFT JOIN audit_files af ON fa.file_id = af.id
        ORDER BY fa.uploaded_at DESC
        LIMIT %s
        """
        return self.db_manager.execute_query(sql, (limit,))
    
    def update_attachment(self, attachment_id: int, description: str) -> bool:
        """更新附件描述"""
        sql = """
        UPDATE file_attachments 
        SET description = %s
        WHERE id = %s
        """
        return self.db_manager.execute_query(sql, (description, attachment_id))
    
    def delete_attachment(self, attachment_id: int) -> bool:
        """删除附件记录"""
        sql = "DELETE FROM file_attachments WHERE id = %s"
        return self.db_manager.execute_query(sql, (attachment_id,))
    
    def get_attachments_by_user(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户上传的所有附件"""
        sql = """
        SELECT fa.*, af.title as file_title
        FROM file_attachments fa
        LEFT JOIN audit_files af ON fa.file_id = af.id
        WHERE fa.uploaded_by = %s
        ORDER BY fa.uploaded_at DESC
        LIMIT %s
        """
        return self.db_manager.execute_query(sql, (user_id, limit))
    
    def get_attachment_stats(self) -> Dict[str, Any]:
        """获取附件统计信息"""
        # 总附件数
        total_sql = "SELECT COUNT(*) as total FROM file_attachments"
        total_result = self.db_manager.execute_query(total_sql)
        total = total_result[0]['total'] if total_result else 0
        
        # 按类型统计
        type_sql = """
        SELECT file_type, COUNT(*) as count
        FROM file_attachments
        GROUP BY file_type
        ORDER BY count DESC
        """
        type_stats = self.db_manager.execute_query(type_sql)
        
        # 按大小统计
        size_sql = """
        SELECT 
            SUM(file_size) as total_size,
            AVG(file_size) as avg_size,
            MAX(file_size) as max_size
        FROM file_attachments
        """
        size_result = self.db_manager.execute_query(size_sql)
        size_stats = size_result[0] if size_result else {}
        
        return {
            'total': total,
            'type_stats': type_stats,
            'size_stats': size_stats
        } 