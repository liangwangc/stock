"""
系统监控模块
监控系统性能、业务指标、资源使用情况
"""
import os
import sys
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.logger = logger
        self.db = DBConnection()
        self.use_database = USE_DATABASE
        self._monitoring = False
        self._monitor_thread = None
    
    def get_system_metrics(self) -> Dict:
        """
        获取系统性能指标
        
        Returns:
            系统指标字典
        """
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_total_gb = memory.total / (1024 ** 3)
            memory_used_gb = memory.used / (1024 ** 3)
            memory_percent = memory.percent
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_total_gb = disk.total / (1024 ** 3)
            disk_used_gb = disk.used / (1024 ** 3)
            disk_percent = disk.percent
            
            # 进程信息
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 ** 2)
            process_cpu_percent = process.cpu_percent(interval=0.1)
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count
                },
                'memory': {
                    'total_gb': round(memory_total_gb, 2),
                    'used_gb': round(memory_used_gb, 2),
                    'percent': memory_percent,
                    'available_gb': round((memory_total_gb - memory_used_gb), 2)
                },
                'disk': {
                    'total_gb': round(disk_total_gb, 2),
                    'used_gb': round(disk_used_gb, 2),
                    'percent': disk_percent,
                    'free_gb': round((disk_total_gb - disk_used_gb), 2)
                },
                'process': {
                    'memory_mb': round(process_memory_mb, 2),
                    'cpu_percent': process_cpu_percent
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"获取系统指标失败: {str(e)}")
            return {}
    
    def get_business_metrics(self) -> Dict:
        """
        获取业务指标
        
        Returns:
            业务指标字典
        """
        if not self.use_database:
            return {}
        
        try:
            metrics = {}
            
            # 预测准确率（最近30天）
            accuracy_sql = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN prediction_hit = '命中' THEN 1 ELSE 0 END) as hit_count
                FROM stock_predictions
                WHERE target_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                  AND prediction_hit IS NOT NULL
            """
            accuracy_result = self.db.execute_query(accuracy_sql)
            if accuracy_result and accuracy_result[0]['total'] > 0:
                total = accuracy_result[0]['total']
                hit_count = accuracy_result[0]['hit_count']
                accuracy = (hit_count / total) * 100 if total > 0 else 0
                metrics['prediction_accuracy_30d'] = {
                    'total': total,
                    'hit_count': hit_count,
                    'accuracy_percent': round(accuracy, 2)
                }
            
            # 今日预测数量
            today_predictions_sql = """
                SELECT COUNT(*) as cnt
                FROM stock_predictions
                WHERE prediction_date = CURDATE()
            """
            today_result = self.db.execute_query(today_predictions_sql)
            metrics['predictions_today'] = today_result[0]['cnt'] if today_result else 0
            
            # 活跃任务数量
            active_tasks_sql = """
                SELECT COUNT(*) as cnt
                FROM scheduled_tasks
                WHERE is_active = 1
            """
            active_tasks_result = self.db.execute_query(active_tasks_sql)
            metrics['active_tasks'] = active_tasks_result[0]['cnt'] if active_tasks_result else 0
            
            # 新闻总数（最近7天）
            news_count_sql = """
                SELECT COUNT(*) as cnt
                FROM news_articles
                WHERE fetch_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """
            news_result = self.db.execute_query(news_count_sql)
            metrics['news_count_7d'] = news_result[0]['cnt'] if news_result else 0
            
            # 用户总数
            users_count_sql = "SELECT COUNT(*) as cnt FROM users"
            users_result = self.db.execute_query(users_count_sql)
            metrics['total_users'] = users_result[0]['cnt'] if users_result else 0
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"获取业务指标失败: {str(e)}")
            return {}
    
    def save_monitoring_data(self, system_metrics: Dict, business_metrics: Dict) -> bool:
        """
        保存监控数据到数据库
        
        Args:
            system_metrics: 系统指标
            business_metrics: 业务指标
        
        Returns:
            是否保存成功
        """
        if not self.use_database:
            return False
        
        try:
            # 检查monitoring_data表是否存在
            self._ensure_table_exists()
            
            sql = """
                INSERT INTO monitoring_data
                (cpu_percent, memory_percent, disk_percent, 
                 process_memory_mb, process_cpu_percent,
                 prediction_accuracy, active_tasks, predictions_today,
                 news_count_7d, total_users,
                 created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cpu_percent = system_metrics.get('cpu', {}).get('percent', 0)
            memory_percent = system_metrics.get('memory', {}).get('percent', 0)
            disk_percent = system_metrics.get('disk', {}).get('percent', 0)
            process_memory = system_metrics.get('process', {}).get('memory_mb', 0)
            process_cpu = system_metrics.get('process', {}).get('cpu_percent', 0)
            
            accuracy = business_metrics.get('prediction_accuracy_30d', {}).get('accuracy_percent', 0)
            active_tasks = business_metrics.get('active_tasks', 0)
            predictions_today = business_metrics.get('predictions_today', 0)
            news_count = business_metrics.get('news_count_7d', 0)
            total_users = business_metrics.get('total_users', 0)
            
            params = (
                cpu_percent, memory_percent, disk_percent,
                process_memory, process_cpu,
                accuracy, active_tasks, predictions_today,
                news_count, total_users,
                datetime.now()
            )
            
            self.db.execute_update(sql, params)
            return True
            
        except Exception as e:
            self.logger.debug(f"保存监控数据失败（可能表不存在）: {str(e)}")
            return False
    
    def _ensure_table_exists(self):
        """确保monitoring_data表存在"""
        try:
            check_sql = """
                SELECT COUNT(*) as cnt 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'monitoring_data'
            """
            result = self.db.execute_query(check_sql)
            
            if not result or result[0].get('cnt', 0) == 0:
                create_sql = """
                    CREATE TABLE IF NOT EXISTS `monitoring_data` (
                        `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                        `cpu_percent` DECIMAL(5, 2) DEFAULT NULL COMMENT 'CPU使用率（%）',
                        `memory_percent` DECIMAL(5, 2) DEFAULT NULL COMMENT '内存使用率（%）',
                        `disk_percent` DECIMAL(5, 2) DEFAULT NULL COMMENT '磁盘使用率（%）',
                        `process_memory_mb` DECIMAL(10, 2) DEFAULT NULL COMMENT '进程内存使用（MB）',
                        `process_cpu_percent` DECIMAL(5, 2) DEFAULT NULL COMMENT '进程CPU使用率（%）',
                        `prediction_accuracy` DECIMAL(5, 2) DEFAULT NULL COMMENT '预测准确率（%）',
                        `active_tasks` INT DEFAULT 0 COMMENT '活跃任务数',
                        `predictions_today` INT DEFAULT 0 COMMENT '今日预测数',
                        `news_count_7d` INT DEFAULT 0 COMMENT '7天新闻数',
                        `total_users` INT DEFAULT 0 COMMENT '用户总数',
                        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        
                        INDEX `idx_created_at` (`created_at`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统监控数据表';
                """
                
                try:
                    self.db.execute_update(create_sql)
                    self.logger.info("monitoring_data表已创建")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        self.logger.warning(f"创建monitoring_data表失败（可能已存在）: {str(e)}")
        except Exception as e:
            self.logger.debug(f"检查monitoring_data表失败: {str(e)}")
    
    def check_alerts(self, system_metrics: Dict, business_metrics: Dict) -> List[Dict]:
        """
        检查告警条件
        
        Args:
            system_metrics: 系统指标
            business_metrics: 业务指标
        
        Returns:
            告警列表
        """
        alerts = []
        
        try:
            # CPU使用率告警
            cpu_percent = system_metrics.get('cpu', {}).get('percent', 0)
            if cpu_percent > 90:
                alerts.append({
                    'level': 'critical',
                    'type': 'system',
                    'metric': 'cpu_percent',
                    'value': cpu_percent,
                    'message': f'CPU使用率过高: {cpu_percent:.2f}%',
                    'timestamp': datetime.now().isoformat()
                })
            elif cpu_percent > 80:
                alerts.append({
                    'level': 'warning',
                    'type': 'system',
                    'metric': 'cpu_percent',
                    'value': cpu_percent,
                    'message': f'CPU使用率较高: {cpu_percent:.2f}%',
                    'timestamp': datetime.now().isoformat()
                })
            
            # 内存使用率告警
            memory_percent = system_metrics.get('memory', {}).get('percent', 0)
            if memory_percent > 90:
                alerts.append({
                    'level': 'critical',
                    'type': 'system',
                    'metric': 'memory_percent',
                    'value': memory_percent,
                    'message': f'内存使用率过高: {memory_percent:.2f}%',
                    'timestamp': datetime.now().isoformat()
                })
            elif memory_percent > 80:
                alerts.append({
                    'level': 'warning',
                    'type': 'system',
                    'metric': 'memory_percent',
                    'value': memory_percent,
                    'message': f'内存使用率较高: {memory_percent:.2f}%',
                    'timestamp': datetime.now().isoformat()
                })
            
            # 磁盘使用率告警
            disk_percent = system_metrics.get('disk', {}).get('percent', 0)
            if disk_percent > 90:
                alerts.append({
                    'level': 'critical',
                    'type': 'system',
                    'metric': 'disk_percent',
                    'value': disk_percent,
                    'message': f'磁盘使用率过高: {disk_percent:.2f}%',
                    'timestamp': datetime.now().isoformat()
                })
            elif disk_percent > 80:
                alerts.append({
                    'level': 'warning',
                    'type': 'system',
                    'metric': 'disk_percent',
                    'value': disk_percent,
                    'message': f'磁盘使用率较高: {disk_percent:.2f}%',
                    'timestamp': datetime.now().isoformat()
                })
            
            # 预测准确率告警
            accuracy = business_metrics.get('prediction_accuracy_30d', {}).get('accuracy_percent', 0)
            if accuracy > 0 and accuracy < 50:
                alerts.append({
                    'level': 'warning',
                    'type': 'business',
                    'metric': 'prediction_accuracy',
                    'value': accuracy,
                    'message': f'预测准确率较低: {accuracy:.2f}%',
                    'timestamp': datetime.now().isoformat()
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"检查告警失败: {str(e)}")
            return []
    
    def start_monitoring(self, interval: int = 300):
        """
        启动监控（定期收集监控数据）
        
        Args:
            interval: 监控间隔（秒，默认5分钟）
        """
        if self._monitoring:
            self.logger.warning("监控已在运行")
            return
        
        self._monitoring = True
        
        def monitor_loop():
            self.logger.info(f"系统监控已启动，间隔: {interval}秒")
            
            while self._monitoring:
                try:
                    # 收集系统指标
                    system_metrics = self.get_system_metrics()
                    
                    # 收集业务指标
                    business_metrics = self.get_business_metrics()
                    
                    # 保存监控数据
                    self.save_monitoring_data(system_metrics, business_metrics)
                    
                    # 检查告警
                    alerts = self.check_alerts(system_metrics, business_metrics)
                    for alert in alerts:
                        if alert['level'] == 'critical':
                            self.logger.error(f"【严重告警】{alert['message']}")
                        else:
                            self.logger.warning(f"【告警】{alert['message']}")
                    
                except Exception as e:
                    self.logger.error(f"监控数据收集失败: {str(e)}")
                
                # 等待下次监控
                time.sleep(interval)
            
            self.logger.info("系统监控已停止")
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True, name="SystemMonitor")
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("系统监控已停止")
    
    def get_monitoring_history(self, hours: int = 24, page: int = 1, page_size: int = 100) -> Dict:
        """
        获取监控历史数据
        
        Args:
            hours: 查询小时数（默认24小时）
            page: 页码
            page_size: 每页数量
        
        Returns:
            监控历史数据
        """
        if not self.use_database:
            return {'data': [], 'total': 0}
        
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            # 查询总数
            count_sql = """
                SELECT COUNT(*) as cnt
                FROM monitoring_data
                WHERE created_at >= %s
            """
            count_result = self.db.execute_query(count_sql, (start_time,))
            total = count_result[0]['cnt'] if count_result else 0
            
            # 分页查询
            offset = (page - 1) * page_size
            query_sql = """
                SELECT * FROM monitoring_data
                WHERE created_at >= %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            results = self.db.execute_query(query_sql, (start_time, page_size, offset))
            
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            return {
                'data': results or [],
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            self.logger.error(f"获取监控历史失败: {str(e)}")
            return {'data': [], 'total': 0, 'page': page, 'page_size': page_size, 'total_pages': 0}


# 全局监控器实例
_system_monitor = None
_monitor_lock = threading.Lock()


def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控器实例（单例模式）"""
    global _system_monitor
    
    if _system_monitor is None:
        with _monitor_lock:
            if _system_monitor is None:
                _system_monitor = SystemMonitor()
    
    return _system_monitor
