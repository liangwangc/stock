"""
新闻抓取任务管理模块
提供任务的创建、启动、停止、查询等功能
已统一使用 ScheduledTaskManager 进行任务调度
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.news_crawler import NewsCrawler
from utils.logger import get_logger
from config_db import USE_DATABASE, DB_CONFIG

logger = get_logger(__name__)

# 尝试导入统一调度器（如果可用）
try:
    from utils.scheduled_task_manager import ScheduledTaskManager
    UNIFIED_SCHEDULER_AVAILABLE = True
except ImportError:
    UNIFIED_SCHEDULER_AVAILABLE = False


class NewsTaskManager:
    """新闻抓取任务管理器（统一使用 ScheduledTaskManager 调度）"""
    
    def __init__(self):
        """
        初始化新闻任务管理器
        
        注意：初始化时不会自动启动任何任务。
        任务必须通过 start_task() 方法手动启动，或通过Web界面启动。
        """
        self.logger = logger
        self.use_database = USE_DATABASE
        self.crawler = NewsCrawler()
        self.active_tasks = {}  # 存储正在运行的任务 {task_id: crawler_instance}
        
        # 使用统一调度器（如果可用）
        self.unified_scheduler = None
        if UNIFIED_SCHEDULER_AVAILABLE:
            try:
                # 获取全局的 ScheduledTaskManager 实例
                # 如果不存在，创建一个新实例（但通常应该使用全局实例）
                self.unified_scheduler = ScheduledTaskManager()
                self.logger.info("已启用统一任务调度器")
            except Exception as e:
                self.logger.warning(f"初始化统一调度器失败，使用独立调度: {str(e)}")
                self.unified_scheduler = None
    
    def create_task(self, task_name: str, task_type: str, 
                   interval_minutes: float = 10.0, symbol: Optional[str] = None,
                   sources: Optional[List[str]] = None, 
                   schedule_type: str = 'interval',
                   schedule_time: Optional[str] = None) -> Optional[int]:
        """
        创建新闻抓取任务（统一使用 ScheduledTaskManager）
        
        Args:
            task_name: 任务名称
            task_type: 任务类型（market/stock/all）
            interval_minutes: 抓取间隔（分钟，可以是小数）
            symbol: 股票代码（如果是股票任务）
            sources: 新闻源列表
            schedule_type: 调度类型（daily/hourly/interval）
            schedule_time: 每日执行时间（HH:MM格式，仅daily类型需要）
            
        Returns:
            任务ID，如果创建失败返回None
        """
        if not self.use_database:
            self.logger.warning("数据库未启用，无法创建任务")
            return None
        
        try:
            # 构建任务配置
            task_config = {
                'task_type': task_type,
                'symbol': symbol,
                'sources': sources or [],
                'interval_minutes': interval_minutes
            }
            
            # 如果统一调度器可用，使用统一调度器创建任务
            if self.unified_scheduler:
                try:
                    # 根据schedule_type确定调度类型
                    if schedule_type == 'daily':
                        # 每日执行
                        actual_schedule_type = 'daily'
                        actual_schedule_time = schedule_time or '09:00'
                    elif schedule_type == 'hourly':
                        # 每小时执行（根据interval_minutes计算）
                        actual_schedule_type = 'hourly'
                        actual_schedule_time = None  # hourly类型不需要具体时间
                    else:
                        # 间隔执行（默认）
                        actual_schedule_type = 'interval'
                        actual_schedule_time = None
                    
                    # 使用统一调度器创建任务
                    task_id = self.unified_scheduler.create_task(
                        task_name=task_name,
                        task_type='news_crawl',
                        schedule_type=actual_schedule_type,
                        schedule_time=actual_schedule_time,
                        task_config=task_config,
                        is_active=False  # 默认不激活，需要手动启动
                    )
                    
                    if task_id:
                        self.logger.info(f"使用统一调度器创建新闻抓取任务成功: {task_name} (ID: {task_id}), 调度类型: {actual_schedule_type}")
                        
                        # 同时保存到 news_crawl_tasks 表（保持兼容性）
                        self._save_to_legacy_table(task_id, task_name, task_type, symbol, sources, interval_minutes)
                        
                        return task_id
                except Exception as e:
                    self.logger.warning(f"使用统一调度器创建任务失败，回退到独立创建: {str(e)}")
                    # 继续执行，使用独立创建方式
            
            # 回退到独立创建（保持向后兼容）
            # 即使统一调度器不可用，也可以使用独立方式创建任务
            try:
                return self._create_task_legacy(task_name, task_type, interval_minutes, symbol, sources)
            except Exception as e:
                self.logger.error(f"独立创建任务也失败: {str(e)}")
                raise
            
        except Exception as e:
            self.logger.error(f"创建任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def _create_task_legacy(self, task_name: str, task_type: str,
                           interval_minutes: float, symbol: Optional[str] = None,
                           sources: Optional[List[str]] = None) -> Optional[int]:
        """独立创建任务（向后兼容）"""
        try:
            # 处理小数分钟数
            minutes = int(interval_minutes)
            seconds = int((interval_minutes - minutes) * 60)
            next_run = datetime.now() + timedelta(minutes=minutes, seconds=seconds)
            sources_json = json.dumps(sources or [])
            
            sql = """
                INSERT INTO news_crawl_tasks 
                (task_name, task_type, symbol, sources, interval_minutes, 
                 is_active, next_run_time, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            now = datetime.now()
            params = (
                task_name, task_type, symbol, sources_json, interval_minutes,
                0, next_run, now, now  # 默认不激活，需要手动启动
            )
            
            conn = DBConnection.get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(sql, params)
                    if not DB_CONFIG.get('autocommit', True):
                        conn.commit()
                    task_id = cursor.lastrowid
                    cursor.close()
                except Exception as e:
                    if not DB_CONFIG.get('autocommit', True):
                        conn.rollback()
                    raise
            else:
                task_id = None
            
            self.logger.info(f"创建新闻抓取任务成功（独立模式）: {task_name} (ID: {task_id})")
            return task_id
            
        except Exception as e:
            self.logger.error(f"独立创建任务失败: {str(e)}")
            return None
    
    def _save_to_legacy_table(self, task_id: int, task_name: str, task_type: str,
                              symbol: Optional[str], sources: Optional[List[str]], 
                              interval_minutes: float):
        """保存到旧表（保持兼容性）"""
        try:
            # 处理小数分钟数
            minutes = int(interval_minutes)
            seconds = int((interval_minutes - minutes) * 60)
            next_run = datetime.now() + timedelta(minutes=minutes, seconds=seconds)
            sources_json = json.dumps(sources or [])
            
            sql = """
                INSERT INTO news_crawl_tasks 
                (id, task_name, task_type, symbol, sources, interval_minutes, 
                 is_active, next_run_time, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    task_name = VALUES(task_name),
                    task_type = VALUES(task_type),
                    symbol = VALUES(symbol),
                    sources = VALUES(sources),
                    interval_minutes = VALUES(interval_minutes),
                    updated_at = VALUES(updated_at)
            """
            
            now = datetime.now()
            params = (
                task_id, task_name, task_type, symbol, sources_json, interval_minutes,
                0, next_run, now, now
            )
            
            DBConnection.execute_update(sql, params)
        except Exception as e:
            # 如果旧表不存在或出错，不影响主流程
            self.logger.debug(f"保存到旧表失败（不影响主流程）: {str(e)}")
    
    def start_task(self, task_id: int) -> bool:
        """启动任务（优先使用统一调度器）"""
        if not self.use_database:
            return False
        
        try:
            # 如果统一调度器可用，使用统一调度器启动任务
            if self.unified_scheduler:
                # 先检查scheduled_tasks表是否存在
                try:
                    check_sql = """
                        SELECT COUNT(*) as count 
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE() AND table_name = 'scheduled_tasks'
                    """
                    table_check = DBConnection.execute_query(check_sql)
                    table_exists = table_check and len(table_check) > 0 and table_check[0].get('count', 0) > 0
                except:
                    table_exists = False
                
                if table_exists:
                    try:
                        # 检查任务是否在 scheduled_tasks 表中
                        sql = "SELECT * FROM scheduled_tasks WHERE id = %s AND task_type = 'news_crawl'"
                        result = DBConnection.execute_query(sql, (task_id,))
                        
                        if result:
                            # 使用统一调度器启动
                            success = self.unified_scheduler.start_task(task_id)
                            if success:
                                # 同步更新旧表状态
                                sql_update = "UPDATE news_crawl_tasks SET is_active = 1 WHERE id = %s"
                                DBConnection.execute_update(sql_update, (task_id,))
                                self.logger.info(f"使用统一调度器启动任务 {task_id} 成功")
                                return True
                    except Exception as e:
                        self.logger.warning(f"使用统一调度器启动任务失败，回退到独立启动: {str(e)}")
                else:
                    self.logger.debug("scheduled_tasks表不存在，使用独立启动")
            
            # 回退到独立启动（保持向后兼容）
            return self._start_task_legacy(task_id)
            
        except Exception as e:
            self.logger.error(f"启动任务失败: {str(e)}")
            return False
    
    def _start_task_legacy(self, task_id: int) -> bool:
        """独立启动任务（向后兼容）"""
        try:
            # 获取任务信息
            task = self.get_task(task_id)
            if not task:
                self.logger.error(f"任务 {task_id} 不存在")
                return False
            
            # 检查任务是否已在运行（检查爬虫线程）
            if task_id in self.crawler.crawl_threads:
                self.logger.warning(f"任务 {task_id} 已在运行（线程已存在）")
                # 如果数据库状态不一致，更新数据库状态
                if not task['is_active']:
                    sql = "UPDATE news_crawl_tasks SET is_active = 1 WHERE id = %s"
                    DBConnection.execute_update(sql, (task_id,))
                return True
            
            if task['is_active']:
                self.logger.warning(f"任务 {task_id} 标记为运行中，但线程不存在，重新启动")
                # 如果数据库标记为运行中但线程不存在，先更新数据库状态
                sql = "UPDATE news_crawl_tasks SET is_active = 0 WHERE id = %s"
                DBConnection.execute_update(sql, (task_id,))
            
            # 更新任务状态
            sql = "UPDATE news_crawl_tasks SET is_active = 1 WHERE id = %s"
            DBConnection.execute_update(sql, (task_id,))
            
            # 启动抓取任务
            self.crawler.start_crawl_task(
                task_id=task_id,
                interval_minutes=task['interval_minutes'],
                task_type=task['task_type'],
                symbol=task.get('symbol')
            )
            
            self.active_tasks[task_id] = self.crawler
            self.logger.info(f"任务 {task_id} 已启动（独立模式）")
            return True
            
        except Exception as e:
            self.logger.error(f"独立启动任务失败: {str(e)}")
            return False
    
    def stop_task(self, task_id: int) -> bool:
        """停止任务（优先使用统一调度器）"""
        if not self.use_database:
            return False
        
        try:
            # 如果统一调度器可用，使用统一调度器停止任务
            if self.unified_scheduler:
                # 先检查scheduled_tasks表是否存在
                try:
                    check_sql = """
                        SELECT COUNT(*) as count 
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE() AND table_name = 'scheduled_tasks'
                    """
                    table_check = DBConnection.execute_query(check_sql)
                    table_exists = table_check and len(table_check) > 0 and table_check[0].get('count', 0) > 0
                except:
                    table_exists = False
                
                if table_exists:
                    try:
                        # 检查任务是否在 scheduled_tasks 表中
                        sql = "SELECT * FROM scheduled_tasks WHERE id = %s AND task_type = 'news_crawl'"
                        result = DBConnection.execute_query(sql, (task_id,))
                        
                        if result:
                            # 使用统一调度器停止
                            success = self.unified_scheduler.stop_task(task_id)
                            if success:
                                # 同步更新旧表状态
                                sql_update = "UPDATE news_crawl_tasks SET is_active = 0 WHERE id = %s"
                                DBConnection.execute_update(sql_update, (task_id,))
                                self.logger.info(f"使用统一调度器停止任务 {task_id} 成功")
                                return True
                    except Exception as e:
                        self.logger.warning(f"使用统一调度器停止任务失败，回退到独立停止: {str(e)}")
                else:
                    self.logger.debug("scheduled_tasks表不存在，使用独立停止")
            
            # 回退到独立停止（保持向后兼容）
            return self._stop_task_legacy(task_id)
            
        except Exception as e:
            self.logger.error(f"停止任务失败: {str(e)}")
            return False
    
    def _stop_task_legacy(self, task_id: int) -> bool:
        """独立停止任务（向后兼容）"""
        try:
            # 先更新数据库状态
            sql = "UPDATE news_crawl_tasks SET is_active = 0 WHERE id = %s"
            DBConnection.execute_update(sql, (task_id,))
            
            # 停止抓取任务（发送停止信号）
            self.crawler.stop_crawl_task(task_id)
            
            # 等待线程结束（最多等待5秒）
            if task_id in self.crawler.crawl_threads:
                thread = self.crawler.crawl_threads[task_id]
                thread.join(timeout=5)
                if thread.is_alive():
                    self.logger.warning(f"任务 {task_id} 线程未在5秒内结束")
            
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            self.logger.info(f"任务 {task_id} 已停止（独立模式）")
            return True
            
        except Exception as e:
            self.logger.error(f"独立停止任务失败: {str(e)}")
            return False
    
    def get_task(self, task_id: int) -> Optional[Dict]:
        """获取任务信息（优先从统一调度表查询）"""
        if not self.use_database:
            return None
        
        try:
            # 先尝试从统一调度表查询
            if self.unified_scheduler:
                # 先检查scheduled_tasks表是否存在
                try:
                    check_sql = """
                        SELECT COUNT(*) as count 
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE() AND table_name = 'scheduled_tasks'
                    """
                    table_check = DBConnection.execute_query(check_sql)
                    table_exists = table_check and len(table_check) > 0 and table_check[0].get('count', 0) > 0
                except:
                    table_exists = False
                
                if table_exists:
                    try:
                        sql = "SELECT * FROM scheduled_tasks WHERE id = %s AND task_type = 'news_crawl'"
                        result = DBConnection.execute_query(sql, (task_id,))
                        if result:
                            task = result[0]
                            # 解析task_config
                            if task.get('task_config'):
                                try:
                                    config = json.loads(task['task_config'])
                                    task['task_type'] = config.get('task_type', 'market')
                                    task['symbol'] = config.get('symbol')
                                    task['sources'] = config.get('sources', [])
                                    task['interval_minutes'] = config.get('interval_minutes', 60)
                                except:
                                    pass
                            return task
                    except Exception as e:
                        self.logger.debug(f"从统一调度表查询失败，尝试旧表: {str(e)}")
            
            # 回退到旧表查询
            sql = "SELECT * FROM news_crawl_tasks WHERE id = %s"
            result = DBConnection.execute_query(sql, (task_id,))
            if result:
                task = result[0]
                # 解析JSON字段
                if task.get('sources'):
                    try:
                        task['sources'] = json.loads(task['sources'])
                    except:
                        task['sources'] = []
                return task
            return None
        except Exception as e:
            self.logger.error(f"获取任务失败: {str(e)}")
            return None
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务（合并统一调度表和旧表）"""
        if not self.use_database:
            return []
        
        try:
            all_tasks = []
            
            # 从统一调度表查询
            if self.unified_scheduler:
                # 先检查表是否存在
                try:
                    check_sql = """
                        SELECT COUNT(*) as count 
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE() AND table_name = 'scheduled_tasks'
                    """
                    table_check = DBConnection.execute_query(check_sql)
                    table_exists = table_check and len(table_check) > 0 and table_check[0].get('count', 0) > 0
                except:
                    table_exists = False
                
                if table_exists:
                    try:
                        sql = "SELECT * FROM scheduled_tasks WHERE task_type = 'news_crawl' ORDER BY created_at DESC"
                        tasks = DBConnection.execute_query(sql)
                        for task in tasks:
                            # 解析task_config
                            if task.get('task_config'):
                                try:
                                    config = json.loads(task['task_config'])
                                    task['task_type'] = config.get('task_type', 'market')
                                    task['symbol'] = config.get('symbol')
                                    task['sources'] = config.get('sources', [])
                                    task['interval_minutes'] = config.get('interval_minutes', 60)
                                except:
                                    pass
                            all_tasks.append(task)
                    except Exception as e:
                        self.logger.debug(f"从统一调度表查询失败: {str(e)}")
                else:
                    self.logger.debug("scheduled_tasks表不存在，跳过统一调度表查询")
            
            # 从旧表查询（补充）
            try:
                sql = "SELECT * FROM news_crawl_tasks ORDER BY created_at DESC"
                legacy_tasks = DBConnection.execute_query(sql)
                for task in legacy_tasks:
                    # 检查是否已在all_tasks中（避免重复）
                    if not any(t.get('id') == task.get('id') for t in all_tasks):
                        # 解析JSON字段
                        if task.get('sources'):
                            try:
                                task['sources'] = json.loads(task['sources'])
                            except:
                                task['sources'] = []
                        all_tasks.append(task)
            except Exception as e:
                self.logger.debug(f"从旧表查询失败: {str(e)}")
            
            return all_tasks
        except Exception as e:
            self.logger.error(f"获取任务列表失败: {str(e)}")
            return []
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        """更新任务"""
        if not self.use_database:
            return False
        
        try:
            # 检查任务是否存在
            task = self.get_task(task_id)
            if not task:
                self.logger.error(f"任务 {task_id} 不存在")
                return False
            
            # 如果任务正在运行，不允许更新某些字段
            is_running = task.get('is_active') == 1
            if is_running:
                # 允许更新任务名称，但不允许更新任务类型、间隔等运行中的配置
                allowed_fields_when_active = ['task_name']
                for key in kwargs.keys():
                    if key not in allowed_fields_when_active:
                        self.logger.warning(f"任务 {task_id} 正在运行，不允许更新 {key}，请先停止任务")
                        # 不返回False，允许更新任务名称
            
            # 构建更新SQL
            updates = []
            params = []
            
            allowed_fields = ['task_name', 'task_type', 'symbol', 'sources', 
                             'interval_minutes', 'is_active']
            
            for key, value in kwargs.items():
                if key in allowed_fields:
                    # 如果任务正在运行，只允许更新任务名称
                    if is_running and key not in ['task_name']:
                        continue
                    
                    if key == 'sources' and isinstance(value, list):
                        value = json.dumps(value)
                    elif key == 'symbol' and value is None:
                        value = None
                    updates.append(f"{key} = %s")
                    params.append(value)
            
            if not updates:
                self.logger.warning(f"没有可更新的字段")
                return False
            
            updates.append("updated_at = %s")
            params.append(datetime.now())
            params.append(task_id)
            
            sql = f"UPDATE news_crawl_tasks SET {', '.join(updates)} WHERE id = %s"
            DBConnection.execute_update(sql, tuple(params))
            
            self.logger.info(f"更新任务 {task_id} 成功")
            return True
            
        except Exception as e:
            self.logger.error(f"更新任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        if not self.use_database:
            return False
        
        try:
            # 先停止任务
            if task_id in self.active_tasks:
                self.stop_task(task_id)
            
            # 删除任务
            sql = "DELETE FROM news_crawl_tasks WHERE id = %s"
            DBConnection.execute_update(sql, (task_id,))
            
            self.logger.info(f"删除任务 {task_id} 成功")
            return True
            
        except Exception as e:
            self.logger.error(f"删除任务失败: {str(e)}")
            return False
    
    def get_task_statistics(self, task_id: int) -> Dict:
        """获取任务统计信息"""
        task = self.get_task(task_id)
        if not task:
            return {}
        
        return {
            'task_id': task_id,
            'task_name': task.get('task_name'),
            'run_count': task.get('run_count', 0),
            'success_count': task.get('success_count', 0),
            'fail_count': task.get('fail_count', 0),
            'last_run_time': task.get('last_run_time'),
            'next_run_time': task.get('next_run_time'),
            'is_active': task.get('is_active', 0),
            'last_error': task.get('last_error')
        }
