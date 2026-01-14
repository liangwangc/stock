"""
操作审计日志测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from utils.audit_log import AuditLogger, get_audit_logger


class TestAuditLogger:
    """AuditLogger测试类"""
    
    @patch('utils.audit_log.USE_DATABASE', False)
    def test_log_operation_no_database(self):
        """测试记录操作（数据库未启用）"""
        logger = AuditLogger()
        result = logger.log_operation(
            user_id=1,
            operation_type='test',
            resource_type='test_resource',
            success=True
        )
        assert result is True
    
    @patch('utils.audit_log.USE_DATABASE', True)
    @patch('utils.audit_log.DatabaseConnection')
    def test_log_operation_with_database(self, mock_db):
        """测试记录操作（数据库启用）"""
        # 模拟数据库连接
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.execute_update = Mock(return_value=1)
        
        logger = AuditLogger()
        logger.db = mock_db_instance
        
        # 模拟表已存在
        mock_db_instance.execute_query = Mock(return_value=[{'cnt': 1}])
        
        result = logger.log_operation(
            user_id=1,
            operation_type='create',
            resource_type='user',
            resource_id='123',
            details={'key': 'value'},
            ip_address='127.0.0.1',
            user_agent='test-agent',
            success=True
        )
        
        assert result is True
        # 验证execute_update被调用
        assert mock_db_instance.execute_update.called
    
    @patch('utils.audit_log.USE_DATABASE', False)
    def test_get_audit_logs_no_database(self):
        """测试获取审计日志（数据库未启用）"""
        logger = AuditLogger()
        result = logger.get_audit_logs()
        assert result['success'] is False or 'total' in result
        assert result['total'] == 0
    
    def test_singleton(self):
        """测试单例模式"""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is logger2
