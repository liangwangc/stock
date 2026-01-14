"""
系统监控器测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from utils.system_monitor import SystemMonitor, get_system_monitor


class TestSystemMonitor:
    """SystemMonitor测试类"""
    
    @patch('utils.system_monitor.USE_DATABASE', False)
    def test_get_system_metrics(self):
        """测试获取系统指标"""
        monitor = SystemMonitor()
        metrics = monitor.get_system_metrics()
        
        assert 'cpu' in metrics
        assert 'memory' in metrics
        assert 'disk' in metrics
        assert 'process' in metrics
        assert 'timestamp' in metrics
        
        # 检查CPU指标
        assert 'percent' in metrics['cpu']
        assert 'count' in metrics['cpu']
        
        # 检查内存指标
        assert 'total_gb' in metrics['memory']
        assert 'used_gb' in metrics['memory']
        assert 'percent' in metrics['memory']
    
    @patch('utils.system_monitor.USE_DATABASE', False)
    def test_get_business_metrics_no_database(self):
        """测试获取业务指标（数据库未启用）"""
        monitor = SystemMonitor()
        metrics = monitor.get_business_metrics()
        
        # 数据库未启用时应该返回空字典或默认值
        assert isinstance(metrics, dict)
    
    @patch('utils.system_monitor.USE_DATABASE', True)
    @patch('utils.system_monitor.DatabaseConnection')
    def test_get_business_metrics_with_database(self, mock_db):
        """测试获取业务指标（数据库启用）"""
        # 模拟数据库连接
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        
        # 模拟查询结果
        mock_db_instance.execute_query = Mock(return_value=[
            {'total': 100, 'hit_count': 60},
            {'cnt': 50},
            {'cnt': 5},
            {'cnt': 200},
            {'cnt': 10}
        ])
        
        monitor = SystemMonitor()
        monitor.db = mock_db_instance
        
        metrics = monitor.get_business_metrics()
        
        assert 'prediction_accuracy_30d' in metrics or 'predictions_today' in metrics
    
    def test_check_alerts(self):
        """测试检查告警"""
        monitor = SystemMonitor()
        
        # 正常指标（无告警）
        system_metrics = {
            'cpu': {'percent': 50},
            'memory': {'percent': 60},
            'disk': {'percent': 70},
            'process': {'cpu_percent': 30, 'memory_mb': 500}
        }
        business_metrics = {
            'prediction_accuracy_30d': {'accuracy_percent': 55}
        }
        
        alerts = monitor.check_alerts(system_metrics, business_metrics)
        assert isinstance(alerts, list)
        
        # 高CPU使用率（应该有告警）
        system_metrics['cpu'] = {'percent': 85}
        alerts = monitor.check_alerts(system_metrics, business_metrics)
        assert len(alerts) > 0
        assert any(a['metric'] == 'cpu_percent' for a in alerts)
    
    def test_singleton(self):
        """测试单例模式"""
        monitor1 = get_system_monitor()
        monitor2 = get_system_monitor()
        assert monitor1 is monitor2
