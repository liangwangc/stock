"""
定时任务管理器

本模块提供统一的定时任务管理功能，支持多种任务类型的调度和执行：
- 股票历史数据更新（增量/全量）
- 股票分析任务
- 新闻抓取任务
- 模型评估和优化任务
- 数据备份任务
- 其他自定义任务

主要特性：
- 统一任务调度：使用schedule库进行任务调度
- 多种调度方式：支持每日、每周、间隔等多种调度类型
- 任务状态管理：支持启动、停止、删除任务
- 执行历史记录：记录每次任务的执行结果
- 自动加载：系统启动时自动加载并启动启用的任务

使用示例：
    ```python
    from utils.scheduled_task_manager import ScheduledTaskManager
    
    # 创建任务管理器实例（单例模式）
    manager = ScheduledTaskManager()
    
    # 创建定时任务
    task_id = manager.create_task(
        task_name='每日数据更新',
        task_type='stock_history_update',
        schedule_type='daily',
        schedule_time='15:00'
    )
    
    # 启动任务
    manager.start_task(task_id)
    
    # 获取所有任务
    tasks = manager.get_all_tasks()
    ```

作者：Smart Stock Advisor Team
创建日期：2024
最后更新：2024
"""
import threading
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os
import json
import time
import threading

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


def get_next_trading_day(start_date: str = None) -> str:
    """
    计算下一个交易日（排除周末）
    
    Args:
        start_date: 起始日期（格式：YYYY-MM-DD），如果为None则使用今天
    
    Returns:
        下一个交易日的日期字符串（格式：YYYY-MM-DD）
    """
    if start_date is None:
        start_date = datetime.now().strftime('%Y-%m-%d')
    
    current = datetime.strptime(start_date, '%Y-%m-%d')
    # 从下一天开始查找
    current += timedelta(days=1)
    
    # 最多查找7天（避免无限循环）
    for _ in range(7):
        # 排除周末（0=Monday, 6=Sunday）
        if current.weekday() < 5:  # 0-4 表示周一到周五
            return current.strftime('%Y-%m-%d')
        current += timedelta(days=1)
    
    # 如果7天内没找到（理论上不会发生），返回下周一
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current.strftime('%Y-%m-%d')


class ScheduledTaskManager:
    """定时任务管理器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
        self.tasks = {}  # {task_id: {'job': job, 'thread': thread, 'stop_flag': threading.Event}}
        self.scheduler_thread = None
        self.stop_scheduler = threading.Event()
        self.running_tasks = {}  # {task_id: {'start_time': datetime, 'thread': thread}}
        
        # 确保表存在
        self._ensure_tables_exist()
        
        # 启动调度器线程
        self.start_scheduler()
    
    def _ensure_tables_exist(self):
        """确保数据表存在"""
        try:
            sql_file = os.path.join(project_root, "database", "scheduled_tasks_table.sql")
            if os.path.exists(sql_file):
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                    
                    # 将SQL内容按分号分割成多个语句
                    # 移除注释行和空行，然后按分号分割
                    lines = []
                    for line in sql_content.split('\n'):
                        stripped = line.strip()
                        # 保留非注释行
                        if stripped and not stripped.startswith('--'):
                            lines.append(line)
                    
                    # 重新组合并按分号分割
                    full_sql = '\n'.join(lines)
                    statements = [stmt.strip() for stmt in full_sql.split(';') if stmt.strip()]
                    
                    # 逐个执行每个CREATE TABLE语句
                    for statement in statements:
                        if statement.strip():
                            try:
                                self.db.execute_update(statement + ';')
                            except Exception as e:
                                # 如果表已存在，忽略错误
                                error_msg = str(e).lower()
                                if "already exists" not in error_msg and "duplicate" not in error_msg:
                                    self.logger.warning(f"创建表时出错: {str(e)}")
                    
                    self.logger.info("定时任务管理表已创建或已存在")
        except Exception as e:
            self.logger.warning(f"检查数据表时出错: {str(e)}")
    
    def _parse_task_config(self, task: Dict) -> Dict:
        """
        安全地解析任务配置，兼容字符串和字典两种格式
        
        Args:
            task: 任务字典，包含 task_config 字段
            
        Returns:
            解析后的任务配置字典
        """
        raw_task_config = task.get('task_config')
        if isinstance(raw_task_config, str):
            try:
                return json.loads(raw_task_config) if raw_task_config else {}
            except Exception as e:
                self.logger.warning(f"解析任务配置JSON失败，将使用空配置: {e}")
                return {}
        elif isinstance(raw_task_config, dict):
            return raw_task_config
        else:
            return {}
    
    def start_scheduler(self):
        """启动调度器线程"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.logger.warning("调度器线程已在运行，跳过重复启动")
            return
        
        self.stop_scheduler.clear()
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="ScheduledTaskScheduler")
        self.scheduler_thread.start()
        self.logger.info("✅ 定时任务调度器线程已启动")
        
        # 加载并启动所有启用的任务
        self.load_and_start_tasks()
        
        # 输出调度器状态
        self.logger.info(f"📊 调度器状态: 已加载 {len(self.tasks)} 个任务到调度器")
        
        # 验证调度器线程是否真的在运行
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.logger.info(f"✅ 调度器线程运行正常 (线程ID: {self.scheduler_thread.ident})")
        else:
            self.logger.error("❌ 调度器线程未正常运行！")
        
        # 验证schedule库中的任务数量
        schedule_jobs_count = len(schedule.jobs)
        self.logger.info(f"📋 schedule库中注册的任务数量: {schedule_jobs_count}")
        if schedule_jobs_count == 0 and len(self.tasks) > 0:
            self.logger.warning("⚠️  警告: 有任务已加载但未注册到schedule库！")
    
    def stop_scheduler_thread(self):
        """停止调度器线程"""
        if self.scheduler_thread:
            self.stop_scheduler.set()
            schedule.clear()
            self.logger.info("定时任务调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        self.logger.info("🔄 调度器主循环已开始运行")
        loop_count = 0
        last_status_log = 0
        
        while not self.stop_scheduler.is_set():
            try:
                # 检查是否有待执行的任务
                pending_jobs = schedule.jobs
                jobs_to_run = [job for job in pending_jobs if job.should_run]
                
                # 如果有任务应该执行，记录详细信息
                if jobs_to_run:
                    self.logger.info(f"⏰ 检测到 {len(jobs_to_run)} 个任务应该执行")
                    for job in jobs_to_run:
                        # 尝试获取任务信息
                        job_info = f"任务: {getattr(job.job_func, '__name__', 'unknown')}"
                        if hasattr(job, 'next_run'):
                            job_info += f", 下次执行: {job.next_run}"
                        self.logger.info(f"  - {job_info}")
                
                # 执行待执行的任务
                schedule.run_pending()
                
                loop_count += 1
                
                # 每60秒输出一次状态（默认改为debug级别，避免控制台日志过多）
                current_time = time.time()
                if current_time - last_status_log >= 60:
                    self.logger.debug(f"📊 调度器运行中... 当前有 {len(pending_jobs)} 个已注册任务")
                    # 显示每个任务的详细信息（仅在debug级别打印）
                    for idx, job in enumerate(pending_jobs, 1):
                        job_name = getattr(job.job_func, '__name__', 'unknown')
                        next_run = getattr(job, 'next_run', 'unknown')
                        should_run = getattr(job, 'should_run', False)
                        self.logger.debug(f"  任务 {idx}: {job_name}, 下次执行: {next_run}, 应该执行: {should_run}")
                    last_status_log = current_time
                    
            except Exception as e:
                self.logger.error(f"调度器循环执行异常: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
            time.sleep(1)
        self.logger.info("⏹️  调度器主循环已停止")
    
    def load_and_start_tasks(self):
        """加载并启动所有启用的任务"""
        try:
            sql = "SELECT * FROM scheduled_tasks WHERE is_active = 1"
            tasks = self.db.execute_query(sql)
            
            if not tasks:
                self.logger.info("未找到启用的定时任务")
                return
            
            self.logger.info(f"开始加载定时任务，找到 {len(tasks)} 个启用的任务")
            
            loaded_count = 0
            failed_count = 0
            
            for task in tasks:
                try:
                    self._schedule_task(task)
                    loaded_count += 1
                    task_name = task.get('task_name', '未知')
                    task_id = task.get('id', '未知')
                    schedule_type = task.get('schedule_type', '未知')
                    schedule_time = task.get('schedule_time', '未知')
                    self.logger.info(f"  ✓ 已加载: {task_name} (ID: {task_id}, 类型: {schedule_type}, 时间: {schedule_time})")
                except Exception as e:
                    failed_count += 1
                    task_id = task.get('id', '未知')
                    self.logger.error(f"  ✗ 加载失败 (ID: {task_id}): {str(e)}")
                    import traceback
                    self.logger.debug(traceback.format_exc())
            
            self.logger.info(f"定时任务加载完成: 成功 {loaded_count} 个, 失败 {failed_count} 个, 总计 {len(tasks)} 个")
            
        except Exception as e:
            self.logger.error(f"加载定时任务列表失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _normalize_schedule_time(self, schedule_time) -> Optional[str]:
        """规范化schedule_time为字符串格式（HH:MM:SS）
        
        Args:
            schedule_time: 可能是字符串、datetime.time、timedelta或None
            
        Returns:
            时间字符串（HH:MM:SS）或None
        """
        if schedule_time is None:
            return None
        
        if isinstance(schedule_time, str):
            # 已经是字符串，直接返回
            return schedule_time
        elif isinstance(schedule_time, timedelta):
            # timedelta对象：转换为HH:MM:SS格式
            total_seconds = int(schedule_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        elif hasattr(schedule_time, 'strftime'):
            # datetime.time或datetime对象：使用strftime
            try:
                return schedule_time.strftime('%H:%M:%S')
            except:
                return str(schedule_time)
        else:
            # 其他类型：转换为字符串
            return str(schedule_time)
    
    def _schedule_task(self, task: Dict):
        """调度任务"""
        task_id = task['id']
        task_type = task['task_type']
        schedule_type = task.get('schedule_type', 'daily')
        schedule_time = task.get('schedule_time')
        schedule_weekdays = task.get('schedule_weekdays')
        cron_expression = task.get('cron_expression')
        
        # 取消已存在的任务
        if task_id in self.tasks:
            old_task_info = self.tasks[task_id]
            # 取消所有相关的jobs
            if 'jobs' in old_task_info:
                for old_job in old_task_info['jobs']:
                    try:
                        schedule.cancel_job(old_job)
                    except:
                        pass
            elif 'job' in old_task_info:
                try:
                    schedule.cancel_job(old_task_info['job'])
                except:
                    pass
        
        # 创建任务执行函数
        def task_wrapper():
            try:
                self.logger.info(f"🔔 定时任务触发: {task.get('task_name', '未知')} (ID: {task_id})")
                self._execute_task(task_id)
            except Exception as e:
                self.logger.error(f"定时任务包装函数执行异常 (ID: {task_id}): {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
        
        # 根据调度类型设置任务
        jobs = []  # 存储所有创建的job（可能有多个，如工作日）
        if schedule_type == 'daily':
            if schedule_time:
                time_str = self._normalize_schedule_time(schedule_time)
                if time_str:  # 确保time_str不为None
                    if schedule_weekdays:
                        weekdays = [int(d) for d in str(schedule_weekdays).split(',') if d.strip()]
                        # schedule库的weekday: 0=Monday, 6=Sunday
                        for day in weekdays:
                            # Python weekday: 0=Monday, 6=Sunday
                            # schedule库: schedule.every().monday.at(time_str)
                            day_map = {1: schedule.every().monday, 2: schedule.every().tuesday,
                                      3: schedule.every().wednesday, 4: schedule.every().thursday,
                                      5: schedule.every().friday, 6: schedule.every().saturday,
                                      7: schedule.every().sunday}
                            if day in day_map:
                                job = day_map[day].at(time_str).do(task_wrapper)
                                jobs.append(job)
                                self.logger.debug(f"任务 {task_id} 已调度到工作日 {day} 的 {time_str}")
                    else:
                        job = schedule.every().day.at(time_str).do(task_wrapper)
                        jobs.append(job)
                        self.logger.debug(f"任务 {task_id} 已调度到每天 {time_str}")
                else:
                    # 如果时间规范化失败，使用默认时间
                    self.logger.warning(f"任务 {task_id} 的时间格式无法解析，使用默认时间 15:05")
                    job = schedule.every().day.at("15:05").do(task_wrapper)
                    jobs.append(job)
            else:
                job = schedule.every().day.at("15:05").do(task_wrapper)  # 默认15:05（收盘后5分钟）
                jobs.append(job)
                self.logger.debug(f"任务 {task_id} 已调度到每天 15:05（默认时间）")
        elif schedule_type == 'hourly':
            if schedule_time:
                time_str = self._normalize_schedule_time(schedule_time)
                if time_str and ':' in time_str:
                    minute = int(time_str.split(':')[1]) if len(time_str.split(':')) > 1 else 0
                else:
                    minute = 0
                job = schedule.every().hour.at(f":{minute:02d}").do(task_wrapper)
                jobs.append(job)
                self.logger.debug(f"任务 {task_id} 已调度到每小时第 {minute} 分钟")
            else:
                job = schedule.every().hour.do(task_wrapper)
                jobs.append(job)
                self.logger.debug(f"任务 {task_id} 已调度到每小时")
        elif schedule_type == 'interval':
            # 间隔执行（用于新闻抓取等任务）
            task_config = self._parse_task_config(task)
            interval_minutes = task_config.get('interval_minutes', 60)
            
            # schedule库支持按分钟执行
            if interval_minutes >= 60:
                # 按小时执行（如果间隔>=60分钟）
                hours = interval_minutes // 60
                job = schedule.every(hours).hours.do(task_wrapper)
                jobs.append(job)
                self.logger.debug(f"任务 {task_id} 已调度到每 {hours} 小时执行一次")
            else:
                # 按分钟执行（间隔<60分钟）
                job = schedule.every(interval_minutes).minutes.do(task_wrapper)
                jobs.append(job)
                self.logger.debug(f"任务 {task_id} 已调度到每 {interval_minutes} 分钟执行一次")
        elif schedule_type == 'monthly':
            # 每月执行：在每天检查是否是当月的指定日期
            task_config = self._parse_task_config(task)
            month_day = task_config.get('schedule_month_day', 1)
            if schedule_time:
                time_str = self._normalize_schedule_time(schedule_time)
            else:
                time_str = "15:05"
            
            # 创建一个包装函数，检查日期
            def monthly_task_wrapper():
                today = datetime.now()
                if today.day == month_day:
                    task_wrapper()
            
            job = schedule.every().day.at(time_str).do(monthly_task_wrapper)
            jobs.append(job)
            self.logger.debug(f"任务 {task_id} 已调度到每月第 {month_day} 天的 {time_str}")
        elif schedule_type == 'custom':
            # 如果是cron表达式，需要转换为schedule格式（这里简化处理）
            # 实际使用时可以使用APScheduler库来支持完整的cron表达式
            if cron_expression:
                self.logger.warning(f"任务 {task_id} 使用cron表达式，需要APScheduler支持")
                # 暂时按每天执行
                job = schedule.every().day.at("15:05").do(task_wrapper)
            else:
                job = schedule.every().day.at("15:05").do(task_wrapper)
            jobs.append(job)
            self.logger.debug(f"任务 {task_id} 已调度到每天 15:05（自定义类型）")
        else:
            job = schedule.every().day.at("15:05").do(task_wrapper)
            jobs.append(job)
            self.logger.warning(f"任务 {task_id} 使用未知的调度类型 {schedule_type}，使用默认调度（每天 15:05）")
        
        if jobs:
            # 保存第一个job作为主要job（用于取消等操作）
            self.tasks[task_id] = {
                'job': jobs[0],  # 保存第一个job
                'jobs': jobs,    # 保存所有jobs（如果有多个）
                'task': task,
                'stop_flag': threading.Event()
            }
            
            # 更新下次执行时间
            self._update_next_run_time(task_id)
            
            # 输出调度成功日志
            task_name = task.get('task_name', '未知')
            self.logger.info(f"✅ 任务调度成功: {task_name} (ID: {task_id}, 类型: {schedule_type}, 时间: {schedule_time or '默认'}, 共 {len(jobs)} 个调度)")
        else:
            self.logger.error(f"❌ 任务调度失败: {task.get('task_name', '未知')} (ID: {task_id})，未创建任何job")
    
    def _execute_task(self, task_id: int):
        """执行任务"""
        try:
            # 检查任务是否还在运行
            if task_id in self.running_tasks:
                self.logger.warning(f"任务 {task_id} 上次执行尚未完成，跳过本次执行")
                return
            
            # 获取任务信息
            sql = "SELECT * FROM scheduled_tasks WHERE id = %s"
            tasks = self.db.execute_query(sql, (task_id,))
            if not tasks:
                self.logger.error(f"任务 {task_id} 不存在")
                return
            
            task = tasks[0]
            task_type = task['task_type']
            
            # 确保 task_config 存在且是字典类型（处理数据库中 task_config 为 NULL 的情况）
            if 'task_config' not in task or task.get('task_config') is None:
                task['task_config'] = {}
            elif isinstance(task.get('task_config'), str):
                # 如果是字符串，尝试解析JSON
                try:
                    task['task_config'] = json.loads(task['task_config']) if task['task_config'] else {}
                except:
                    task['task_config'] = {}
            elif not isinstance(task.get('task_config'), dict):
                task['task_config'] = {}
            
            # 记录开始执行
            start_time = datetime.now()
            history_id = self._create_task_history(task_id, task.get('task_name'), task_type, start_time)
            self.running_tasks[task_id] = {
                'start_time': start_time,
                'history_id': history_id
            }
            
            # 更新任务状态
            self._update_task_status(task_id, last_run_time=start_time, last_run_status='running')
            
            self.logger.info(f"开始执行定时任务: {task['task_name']} (ID: {task_id})")
            
            # 执行任务
            result = None
            status = 'failed'
            message = ''
            error_info = None
            
            try:
                if task_type == 'stock_history_update':
                    result = self._execute_stock_history_update(task)
                elif task_type == 'stock_analysis':
                    result = self._execute_stock_analysis(task)
                elif task_type == 'stock_data_collection_cn':
                    result = self._execute_cn_stock_data_collection(task)
                elif task_type == 'stock_data_collection_us':
                    result = self._execute_us_stock_data_collection(task)
                elif task_type == 'news_crawl':
                    result = self._execute_news_crawl(task)
                elif task_type == 'llm_analysis':
                    result = self._execute_llm_analysis(task)
                elif task_type == 'model_evaluation':
                    result = self._execute_model_evaluation(task)
                elif task_type == 'model_optimization':
                    result = self._execute_model_optimization(task)
                elif task_type == 'adaptive_optimization':
                    result = self._execute_adaptive_optimization(task)
                elif task_type == 'comprehensive_evaluation':
                    result = self._execute_comprehensive_evaluation(task)
                elif task_type == 'online_learning':
                    result = self._execute_online_learning(task)
                elif task_type == 'model_backtest':
                    result = self._execute_model_backtest(task)
                elif task_type == 'automated_backtest':
                    result = self._execute_automated_backtest(task)
                elif task_type == 'backup':
                    result = self._execute_backup(task)
                elif task_type.startswith('other_data_'):
                    # 其他数据获取任务（北向资金、市场指数、融资融券、主力资金、行业信息、板块轮动）
                    result = self._execute_other_data_collection(task)
                elif task_type == 'main_force_capital_collection':
                    # 兼容旧格式：main_force_capital_collection -> other_data_main_force_capital
                    # 将旧格式任务转换为新格式并执行
                    task['task_type'] = 'other_data_main_force_capital'
                    # 检查并设置 data_type（task_config 已经在前面统一处理过了）
                    if 'data_type' not in task.get('task_config', {}):
                        task['task_config']['data_type'] = 'main_force_capital'
                    result = self._execute_other_data_collection(task)
                else:
                    message = f"未知的任务类型: {task_type}"
                    self.logger.warning(message)
                    result = None
                
                # 对于股票数据收集任务，需要根据实际收集结果判断状态
                if task_type in ['stock_data_collection_cn', 'stock_data_collection_us']:
                    if result and result.get('success', False):
                        # 检查实际收集结果
                        data = result.get('data', {})
                        success_count = data.get('success_count', 0)
                        fail_count = data.get('fail_count', 0)
                        total_count = success_count + fail_count
                        
                        # 如果全部失败，标记为失败
                        if total_count > 0 and success_count == 0:
                            status = 'failed'
                            message = f"所有股票收集失败: {fail_count} 只股票失败"
                            error_info = result.get('message', '所有股票收集失败')
                        # 如果有部分成功，保持成功状态但更新消息
                        elif success_count > 0:
                            status = 'success'
                            message = result.get('message', '执行成功')
                            error_info = ''
                        else:
                            # 没有数据，可能是配置问题
                            status = 'failed'
                            message = result.get('message', '没有需要处理的股票')
                            error_info = result.get('message', '没有需要处理的股票')
                    else:
                        status = 'failed'
                        message = result.get('message', '执行失败') if result else '执行失败'
                        error_info = result.get('error', '') if result else ''
                elif result and result.get('success', False):
                    status = 'success'
                    message = result.get('message', '执行成功')
                    error_info = ''
                else:
                    status = 'failed'
                    message = result.get('message', '执行失败') if result else '执行失败'
                    error_info = result.get('error', '') if result else ''
                    
            except Exception as e:
                status = 'failed'
                message = f"执行异常: {str(e)}"
                error_info = str(e)
                self.logger.error(f"定时任务执行异常 {task_id}: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
            
            # 记录执行结果
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            self._update_task_history(history_id, end_time, duration, status, message, result, error_info)
            
            # 更新任务状态（只更新允许的字段）
            update_kwargs = {
                'last_run_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'run_count': task.get('run_count', 0) + 1
            }
            
            # 如果数据库表有这些字段，尝试更新（通过检查表结构）
            try:
                # 检查字段是否存在
                sql_check = "SHOW COLUMNS FROM scheduled_tasks LIKE %s"
                if self.db.execute_query(sql_check, ('last_run_status',)):
                    update_kwargs['last_run_status'] = status
                if self.db.execute_query(sql_check, ('last_run_message',)):
                    update_kwargs['last_run_message'] = message[:500] if message else None  # 限制长度
                if self.db.execute_query(sql_check, ('success_count',)):
                    update_kwargs['success_count'] = task.get('success_count', 0) + (1 if status == 'success' else 0)
                if self.db.execute_query(sql_check, ('fail_count',)):
                    update_kwargs['fail_count'] = task.get('fail_count', 0) + (1 if status == 'failed' else 0)
            except Exception as e:
                self.logger.debug(f"检查字段存在性失败: {str(e)}")
            
            self._update_task_status(task_id, **update_kwargs)
            
            # 计算下次执行时间
            self._update_next_run_time(task_id)
            
            # 清除运行中标记
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            self.logger.info(f"定时任务执行完成: {task['task_name']} (ID: {task_id}), 状态: {status}, 耗时: {duration}秒")
            
        except Exception as e:
            self.logger.error(f"执行定时任务异常 {task_id}: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def _execute_stock_history_update(self, task: Dict) -> Dict:
        """执行股票历史数据增量更新任务（使用TushareDataFetcher方式）"""
        try:
            # 导入TushareDataFetcher（从scripts目录导入）
            import sys
            import os
            scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
            if scripts_path not in sys.path:
                sys.path.insert(0, scripts_path)
            
            from fetch_tushare_data_16_23 import TushareDataFetcher
            
            fetcher = TushareDataFetcher()
            task_config = self._parse_task_config(task)
            symbols = task_config.get('symbols', None)  # 如果指定了股票列表
            
            # 多线程参数（从任务配置读取，默认值：delay=1.2, threads=30）
            # 注意：delay会根据线程数动态调整，RateLimiter已控制总体速率（每分钟50次）
            base_delay = task_config.get('delay', 1.2)  # 基础延迟1.2秒（对应RateLimiter的最小延迟60/50=1.2秒）
            max_workers = task_config.get('max_workers', 30)  # 默认30个线程（与stock_data_collection_cn保持一致）
            
            # 动态调整延迟：线程数越多，延迟可以适当减少（RateLimiter会控制总体速率）
            if max_workers >= 30:
                delay = base_delay  # 1.2秒
            elif max_workers >= 20:
                delay = base_delay * 1.2  # 1.44秒
            elif max_workers >= 10:
                delay = base_delay * 1.5  # 1.8秒
            else:
                delay = base_delay * 2.0  # 2.4秒
            
            # 确定日期范围（增量更新：定时任务应该总是获取当天数据）
            # 原因：如果用户在1月26日创建定时任务并选择1月26日，那么1月27日执行时应该获取1月27日的数据，而不是1月26日
            # target_date 参数只在手动执行时使用，定时任务执行时应该忽略它
            today = datetime.now().strftime('%Y-%m-%d')
            start_date = today
            end_date = today
            self.logger.info(f"增量更新模式（定时任务）：获取当天 {today} 的数据")
            
            # 使用TushareDataFetcher获取数据
            self.logger.info(f"开始增量更新（线程数: {max_workers}, 延迟: {delay}秒）")
            
            # 调用fetch_and_save_missing_data方法
            result = fetcher.fetch_and_save_missing_data(
                start_date=start_date,
                end_date=end_date,
                delay=delay,
                max_workers=max_workers,
                max_stocks=None if symbols is None else len(symbols) if isinstance(symbols, list) else None
            )
            
            # 数据收集完成后，更新预测表的真实价格字段
            try:
                self.logger.info("开始更新预测表的真实价格字段...")
                from visualizer.prediction_visualizer import PredictionVisualizer
                visualizer = PredictionVisualizer()
                visualizer._update_historical_actual_data()
                self.logger.info("预测表真实价格字段更新完成")
            except Exception as e:
                self.logger.warning(f"更新预测表真实价格字段失败: {str(e)}")
            
            # 转换结果格式以匹配原有接口
            return {
                'success': True,
                'message': f"更新完成: 成功 {result.get('success_count', 0)}, 失败 {result.get('fail_count', 0)}, 跳过 {result.get('skip_count', 0)}, 重试成功 {result.get('retry_success_count', 0)}",
                'data': {
                    'success_count': result.get('success_count', 0),
                    'fail_count': result.get('fail_count', 0),
                    'skip_count': result.get('skip_count', 0),
                    'retry_success_count': result.get('retry_success_count', 0),
                    'retry_fail_count': result.get('retry_fail_count', 0),
                    'rate_limit_count': result.get('rate_limit_count', 0),
                    'total_duration_seconds': result.get('total_duration_seconds', 0) if 'total_duration_seconds' in result else 0
                }
            }
        except Exception as e:
            self.logger.error(f"执行股票历史数据增量更新任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f"执行失败: {str(e)}",
                'error': str(e)
            }
    
    def _execute_stock_analysis(self, task: Dict) -> Dict:
        """执行股票分析任务"""
        try:
            # 导入必要的模块
            import sys
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, project_root)
            
            # 这里需要调用web_app中的run_stock_analysis_task函数
            # 但由于循环依赖问题，我们通过任务配置来执行
            task_config = self._parse_task_config(task)
            limit = task_config.get('limit', None)
            sort_type = task_config.get('sort_type', 'turnover')
            symbols = task_config.get('symbols', None)  # 个股分析：股票代码列表
            
            # 获取预测时间和数据获取时间
            target_date = task_config.get('target_date', None)  # 预测时间（目标日期）
            data_date = task_config.get('data_date', None)  # 数据获取时间
            
            # 如果没有指定，使用默认值
            if not target_date:
                target_date = get_next_trading_day()  # 默认下一个交易日
            if not data_date:
                data_date = datetime.now().strftime('%Y-%m-%d')  # 默认今天
            
            self.logger.info(f"任务配置: 预测时间={target_date}, 数据获取时间={data_date}")
            
            # 通过模块导入的方式调用
            try:
                from predictor.stock_predictor import StockPredictor
                from visualizer.prediction_visualizer import PredictionVisualizer
                
                if StockPredictor is None:
                    return {
                        'success': False,
                        'message': '股票分析模块未导入',
                        'error': '模块未导入'
                    }
                
                # StockPredictor内部会自动创建StockDataSource实例，不需要传入
                predictor = StockPredictor()
                success_count = 0
                fail_count = 0
                
                # 如果指定了股票代码列表（个股分析）
                if symbols and isinstance(symbols, list) and len(symbols) > 0:
                    self.logger.info(f"开始个股分析，共 {len(symbols)} 只股票: {', '.join(symbols)}")
                    for symbol in symbols:
                        symbol = str(symbol).strip()
                        if not symbol:
                            continue
                        try:
                            self.logger.info(f"正在分析股票: {symbol}")
                            # 传递日期参数，设置页面预测：不使用API，只使用数据库数据
                            predictor.predict(symbol, target_date=target_date, data_date=data_date, use_api=False)
                            success_count += 1
                        except Exception as e:
                            self.logger.error(f"分析股票 {symbol} 失败: {str(e)}")
                            fail_count += 1
                else:
                    # 全量分析：直接从数据库获取股票列表（避免API调用）
                    self.logger.info("从数据库获取股票列表（避免API调用）...")
                    try:
                        from utils.db_connection import DatabaseConnection
                        db = DatabaseConnection()
                        
                        # 根据data_date获取有数据的股票列表（优先使用data_date，如果没有则使用target_date）
                        filter_date = data_date if data_date else target_date
                        if filter_date:
                            # 获取指定日期有数据的股票列表
                            sql = """
                                SELECT DISTINCT symbol, name
                                FROM stock_history_data
                                WHERE trade_date = %s AND period_type = 'daily'
                                ORDER BY symbol
                            """
                            results = db.execute_query(sql, (filter_date,))
                            stock_list = [{'symbol': str(row['symbol']).zfill(6), 'name': row.get('name', '')} for row in results]
                            self.logger.info(f"从数据库获取到 {len(stock_list)} 只股票（日期: {filter_date}）")
                        else:
                            # 如果没有指定日期，获取所有有数据的股票
                            sql = """
                                SELECT DISTINCT symbol, name
                                FROM stock_history_data
                                WHERE period_type = 'daily'
                                ORDER BY symbol
                            """
                            results = db.execute_query(sql)
                            stock_list = [{'symbol': str(row['symbol']).zfill(6), 'name': row.get('name', '')} for row in results]
                            self.logger.info(f"从数据库获取到 {len(stock_list)} 只股票（所有日期）")
                        
                        if not stock_list:
                            return {
                                'success': False,
                                'message': '数据库中暂无股票数据',
                                'error': '数据库中没有股票数据'
                            }
                        
                        # 如果指定了limit，限制数量
                        if limit and limit > 0:
                            stock_list = stock_list[:limit]
                        
                        # 如果指定了按成交额排序，需要从数据库获取成交额数据
                        if sort_type == 'turnover':
                            self.logger.info("按成交额排序（从数据库获取成交额数据）...")
                            # 获取成交额数据并排序
                            if filter_date:
                                sql = """
                                    SELECT symbol, amount
                                    FROM stock_history_data
                                    WHERE trade_date = %s AND period_type = 'daily'
                                    ORDER BY amount DESC
                                """
                                turnover_results = db.execute_query(sql, (filter_date,))
                            else:
                                # 获取最新日期的成交额数据
                                sql = """
                                    SELECT symbol, amount
                                    FROM stock_history_data
                                    WHERE period_type = 'daily'
                                    AND trade_date = (SELECT MAX(trade_date) FROM stock_history_data WHERE period_type = 'daily')
                                    ORDER BY amount DESC
                                """
                                turnover_results = db.execute_query(sql)
                            
                            # 构建成交额映射
                            turnover_map = {str(row['symbol']).zfill(6): row.get('amount', 0) or 0 for row in turnover_results}
                            
                            # 按成交额排序
                            stock_list.sort(key=lambda x: turnover_map.get(x['symbol'], 0), reverse=True)
                        
                        self.logger.info(f"开始全量分析，共 {len(stock_list)} 只股票（limit={limit}）")
                        for stock_info in stock_list:
                            symbol = stock_info.get('symbol', '')
                            try:
                                self.logger.info(f"正在分析股票: {symbol}")
                                # 传递日期参数，设置页面预测：不使用API，只使用数据库数据
                                predictor.predict(symbol, target_date=target_date, data_date=data_date, use_api=False)
                                success_count += 1
                            except Exception as e:
                                self.logger.error(f"分析股票 {symbol} 失败: {str(e)}")
                                fail_count += 1
                    except Exception as e:
                        self.logger.error(f"从数据库获取股票列表失败: {str(e)}")
                        import traceback
                        self.logger.error(traceback.format_exc())
                        return {
                            'success': False,
                            'message': f'从数据库获取股票列表失败: {str(e)}',
                            'error': str(e)
                        }
                
                return {
                    'success': True,
                    'message': f"分析完成: 成功 {success_count}, 失败 {fail_count}",
                    'data': {
                        'success_count': success_count,
                        'fail_count': fail_count,
                        'total': success_count + fail_count
                    }
                }
            except ImportError as e:
                return {
                    'success': False,
                    'message': f'模块导入失败: {str(e)}',
                    'error': str(e)
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"执行失败: {str(e)}",
                'error': str(e)
            }
    
    def _execute_backup(self, task: Dict) -> Dict:
        """执行数据备份任务"""
        try:
            from utils.backup_manager import BackupManager
            
            backup_manager = BackupManager()
            task_config = self._parse_task_config(task)
            
            # 获取任务配置
            backup_type = task_config.get('backup_type', 'full')  # full: 全量备份, incremental: 增量备份
            description = task_config.get('description', '定时备份')
            
            # 创建备份
            backup_info = backup_manager.create_backup(backup_type=backup_type, description=description)
            
            if backup_info:
                return {
                    'success': True,
                    'message': f"备份创建成功: {backup_info.get('filename')} (大小: {backup_info.get('size', 0) / 1024 / 1024:.2f} MB)",
                    'data': {
                        'filename': backup_info.get('filename'),
                        'size': backup_info.get('size'),
                        'type': backup_info.get('type'),
                        'created_at': backup_info.get('created_at')
                    }
                }
            else:
                return {
                    'success': False,
                    'message': '备份创建失败',
                    'error': '备份创建返回None'
                }
        except ImportError as e:
            return {
                'success': False,
                'message': f'模块导入失败: {str(e)}',
                'error': str(e)
            }
        except Exception as e:
            self.logger.error(f"执行备份任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f"执行失败: {str(e)}",
                'error': str(e)
            }
    
    def _collect_single_cn_stock_worker(self, symbol: str, collection_type: str, years: int, collector=None, delay: float = 1.0, max_workers: int = 1) -> Dict:
        """单线程工作函数（用于多线程环境）- 中国股票
        
        Args:
            symbol: 股票代码
            collection_type: 收集类型（incremental/full）
            years: 收集年数（仅用于full类型）
            collector: 收集器实例（如果为None，会创建新实例）
            delay: 延迟时间（秒），用于多线程模式下的延迟控制
            max_workers: 最大线程数，用于调整延迟策略
        
        Returns:
            收集结果字典
        """
        # 每个线程创建自己的收集器实例
        if collector is None:
            from utils.stock_history_collector import StockHistoryCollector
            collector = StockHistoryCollector()
        
        try:
            if collection_type == 'incremental':
                # 增量更新今日数据
                today = datetime.now().strftime('%Y-%m-%d')
                
                # 注意：数据存在性检查已在主函数中批量完成，这里不再重复检查
                # 如果传入的symbol已经在批量检查中被过滤，这里不会执行
                
                # 使用 collect_stock_daily_data 方法采集单日数据（使用快速模式）
                # 多线程模式下减少延迟（参考batch_collect_10years_data.py）
                import random
                if max_workers > 1:
                    # 多线程模式下减少延迟（批量模式已经优化了API调用）
                    time.sleep(delay * random.uniform(0.1, 0.3))
                else:
                    # 单线程模式保持原延迟
                    time.sleep(delay * random.uniform(0.5, 1.0))
                
                # 使用快速模式采集数据（跳过不必要的API调用，但仍获取PE/PB和市值数据）
                data = collector.collect_stock_daily_data(symbol, today, fast_mode=True)
                if data:
                    # 保存数据
                    if collector.storage.save_stock_daily_data(symbol, today, data):
                        return {
                            'symbol': symbol,
                            'success': True,
                            'message': '今日数据更新成功',
                            'records_count': 1,
                            'skipped': False
                        }
                    else:
                        return {
                            'symbol': symbol,
                            'success': False,
                            'message': '今日数据保存失败',
                            'records_count': 0,
                            'skipped': False
                        }
                else:
                    return {
                        'symbol': symbol,
                        'success': False,
                        'message': '今日数据采集失败',
                        'records_count': 0,
                        'skipped': False
                    }
            else:
                # 全量收集
                result = collector.collect_stock_history_data(symbol, years=years)
                return {
                    'symbol': symbol,
                    'success': result.get('success', False),
                    'message': result.get('message', ''),
                    'records_count': result.get('count', 0),
                    'skipped': False
                }
        except Exception as e:
            return {
                'symbol': symbol,
                'success': False,
                'message': str(e),
                'records_count': 0,
                'skipped': False
            }
    
    def _execute_cn_stock_data_collection(self, task: Dict) -> Dict:
        """执行中国股票数据获取任务（使用TushareDataFetcher方式）"""
        try:
            # 导入TushareDataFetcher（从scripts目录导入）
            import sys
            import os
            scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
            if scripts_path not in sys.path:
                sys.path.insert(0, scripts_path)
            
            from fetch_tushare_data_16_23 import TushareDataFetcher
            
            fetcher = TushareDataFetcher()
            task_config = self._parse_task_config(task)
            
            # 获取任务配置
            collection_type = task_config.get('collection_type', 'incremental')  # incremental: 增量更新, full: 全量收集
            symbols = task_config.get('symbols', None)  # 如果指定了股票列表
            years = task_config.get('years', 10)  # 收集年数（仅用于全量收集）
            
            # 多线程参数（从任务配置读取，默认值：delay=1.2, threads=30）
            # 注意：delay会根据线程数动态调整，RateLimiter已控制总体速率（每分钟50次）
            base_delay = task_config.get('delay', 1.2)  # 基础延迟1.2秒（对应RateLimiter的最小延迟60/50=1.2秒）
            max_workers = task_config.get('threads', 30)  # 默认30个线程
            
            # 动态调整延迟：线程数越多，延迟可以适当减少（RateLimiter会控制总体速率）
            # 30线程时，delay=1.2秒；线程数减少时，delay适当增加
            if max_workers >= 30:
                delay = base_delay  # 1.2秒
            elif max_workers >= 20:
                delay = base_delay * 1.2  # 1.44秒
            elif max_workers >= 10:
                delay = base_delay * 1.5  # 1.8秒
            else:
                delay = base_delay * 2.0  # 2.4秒
            
            # 确定日期范围
            if collection_type == 'incremental':
                # 增量更新：定时任务应该总是获取当天数据，而不是使用创建任务时指定的固定日期
                # 原因：如果用户在1月26日创建定时任务并选择1月26日，那么1月27日执行时应该获取1月27日的数据，而不是1月26日
                # target_date 参数只在手动执行时使用，定时任务执行时应该忽略它
                today = datetime.now().strftime('%Y-%m-%d')
                start_date = today
                end_date = today
                self.logger.info(f"增量更新模式（定时任务）：获取当天 {today} 的数据")
            else:
                # 全量收集：获取指定年数的历史数据
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date_obj = datetime.now() - timedelta(days=years * 365)
                start_date = start_date_obj.strftime('%Y-%m-%d')
                self.logger.info(f"全量收集模式：获取 {start_date} 至 {end_date} 的数据（约{years}年）")
            
            # 使用TushareDataFetcher获取数据
            self.logger.info(f"开始{collection_type}收集（线程数: {max_workers}, 延迟: {delay}秒）")
            
            # 调用fetch_and_save_missing_data方法
            # 如果指定了股票列表，直接传入symbols参数（优化：避免处理不必要的股票）
            result = fetcher.fetch_and_save_missing_data(
                start_date=start_date,
                end_date=end_date,
                delay=delay,
                max_workers=max_workers,
                max_stocks=None if symbols is None else len(symbols) if isinstance(symbols, list) else None,
                symbols=symbols  # 新增：指定股票列表，只处理这些股票
            )
            
            # 数据收集完成后，更新预测表的真实价格字段
            try:
                self.logger.info("开始更新预测表的真实价格字段...")
                from visualizer.prediction_visualizer import PredictionVisualizer
                visualizer = PredictionVisualizer()
                visualizer._update_historical_actual_data()
                self.logger.info("预测表真实价格字段更新完成")
            except Exception as e:
                self.logger.warning(f"更新预测表真实价格字段失败: {str(e)}")
            
            # 数据收集完成后，修复MACD值（使用动态日期）
            try:
                self.logger.info(f"开始修复MACD值（日期范围: {start_date} 及之后）...")
                # 导入MACD修复脚本（从scripts目录导入）
                # scripts_path已经在前面添加到sys.path了
                from fix_macd_values_after_16 import MACDFixer
                macd_fixer = MACDFixer()
                
                # 使用start_date作为修复的起始日期（动态日期）
                # 使用max_workers作为线程数（默认10，如果max_workers>=10则使用max_workers，否则使用10）
                fix_threads = max(max_workers, 10) if max_workers > 0 else 10
                fix_result = macd_fixer.fix_all_after_date(start_date=start_date, max_workers=fix_threads)
                
                self.logger.info(f"MACD修复完成: 总计 {fix_result.get('total', 0)}, 成功 {fix_result.get('success', 0)}, 失败 {fix_result.get('failed', 0)}")
            except Exception as e:
                self.logger.warning(f"修复MACD值失败: {str(e)}")
                import traceback
                self.logger.warning(traceback.format_exc())
            
            # 转换结果格式以匹配原有接口
            return {
                'success': True,
                'message': f"{collection_type}收集完成: 成功 {result.get('success_count', 0)}, 失败 {result.get('fail_count', 0)}, 跳过 {result.get('skip_count', 0)}",
                'data': {
                    'success_count': result.get('success_count', 0),
                    'fail_count': result.get('fail_count', 0),
                    'skip_count': result.get('skip_count', 0),
                    'rate_limit_count': result.get('rate_limit_count', 0)
                }
            }
        except Exception as e:
            self.logger.error(f"执行中国股票数据获取任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f"执行失败: {str(e)}",
                'error': str(e)
            }
    
    def _collect_single_us_stock_worker(self, symbol: str, collection_type: str, start_date: str, end_date: str, period: str, collector=None) -> Dict:
        """单线程工作函数（用于多线程环境）- 美国股票
        
        Args:
            symbol: 股票代码
            collection_type: 收集类型（incremental/full）
            start_date: 开始日期（仅用于incremental）
            end_date: 结束日期（仅用于incremental）
            period: 收集周期（仅用于full）
            collector: 收集器实例（如果为None，会创建新实例）
        
        Returns:
            收集结果字典
        """
        # 每个线程创建自己的收集器实例
        if collector is None:
            from utils.us_stock_collector import USStockCollector
            collector = USStockCollector()
        
        try:
            if collection_type == 'incremental':
                # 增量更新
                result = collector.collect_stock_history(symbol, start_date=start_date, end_date=end_date, period=None)
                return {
                    'symbol': symbol,
                    'success': result.get('success', False),
                    'message': result.get('message', ''),
                    'records_count': result.get('count', 0),
                    'skipped': False
                }
            else:
                # 全量收集
                result = collector.collect_stock_history(symbol, start_date=None, end_date=None, period=period)
                return {
                    'symbol': symbol,
                    'success': result.get('success', False),
                    'message': result.get('message', ''),
                    'records_count': result.get('count', 0),
                    'skipped': False
                }
        except Exception as e:
            return {
                'symbol': symbol,
                'success': False,
                'message': str(e),
                'records_count': 0,
                'skipped': False
            }
    
    def _execute_us_stock_data_collection(self, task: Dict) -> Dict:
        """执行美国股票数据获取任务（支持多线程）"""
        try:
            from utils.us_stock_collector import USStockCollector
            
            collector = USStockCollector()
            task_config = self._parse_task_config(task)
            
            # 获取任务配置
            collection_type = task_config.get('collection_type', 'incremental')  # incremental: 增量更新, full: 全量收集
            symbols = task_config.get('symbols', None)  # 如果指定了股票列表
            period = task_config.get('period', '10y')  # 收集周期
            index_type = task_config.get('index_type', None)  # sp500, nasdaq100, 或None（指定股票）
            
            # 多线程参数（从任务配置读取，默认值：batch_size=1000, delay=1.0, threads=10）
            # 注意：美股API速率限制较严格，建议使用较少的线程数
            batch_size = task_config.get('batch_size', 1000)
            delay = task_config.get('delay', 1.0)
            max_workers = task_config.get('threads', 10)
            
            # 美股API速率限制较严格，限制最大线程数为2
            if max_workers > 2:
                self.logger.warning(f"美股API速率限制较严格，将线程数从 {max_workers} 降低到 2")
                max_workers = 2
            
            # 获取股票列表
            if collection_type == 'incremental':
                # 增量更新（获取最近30天的数据）
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                if not symbols:
                    return {
                        'success': False,
                        'message': '增量更新需要指定股票列表',
                        'error': 'symbols required'
                    }
            else:
                # 全量收集
                if index_type == 'sp500':
                    # 收集S&P 500所有股票
                    try:
                        from scripts.get_us_stock_list import get_sp500_stocks
                        symbols = get_sp500_stocks()
                    except:
                        symbols = []
                    if not symbols:
                        return {
                            'success': False,
                            'message': '获取S&P 500股票列表失败',
                            'error': 'failed to get sp500 list'
                        }
                elif index_type == 'nasdaq100':
                    # 收集NASDAQ 100所有股票
                    try:
                        from scripts.get_us_stock_list import get_nasdaq100_stocks
                        symbols = get_nasdaq100_stocks()
                    except:
                        symbols = []
                    if not symbols:
                        return {
                            'success': False,
                            'message': '获取NASDAQ 100股票列表失败',
                            'error': 'failed to get nasdaq100 list'
                        }
                elif symbols:
                    # 使用指定的股票列表
                    pass
                else:
                    return {
                        'success': False,
                        'message': '全量收集需要指定股票列表或指数类型',
                        'error': 'symbols or index_type required'
                    }
                
                start_date = None
                end_date = None
            
            if not symbols:
                return {
                    'success': False,
                    'message': '没有需要处理的股票',
                    'data': {'success_count': 0, 'fail_count': 0, 'skip_count': 0}
                }
            
            self.logger.info(f"开始{collection_type}收集，共 {len(symbols)} 只股票（批次大小: {batch_size}, 延迟: {delay}秒, 线程数: {max_workers}）")
            
            # 如果线程数为1，使用单线程模式（兼容旧代码）
            if max_workers <= 1:
                if collection_type == 'incremental':
                    result_list = []
                    success_count = 0
                    fail_count = 0
                    
                    for symbol in symbols:
                        try:
                            r = collector.collect_stock_history(symbol, start_date=start_date, end_date=end_date, period=None)
                            if r.get('success'):
                                success_count += r.get('count', 0)
                            else:
                                fail_count += 1
                            result_list.append(r)
                        except Exception as e:
                            self.logger.error(f"收集 {symbol} 失败: {str(e)}")
                            fail_count += 1
                    
                    # 数据收集完成后，更新预测表的真实价格字段
                    try:
                        self.logger.info("开始更新预测表的真实价格字段...")
                        from visualizer.prediction_visualizer import PredictionVisualizer
                        visualizer = PredictionVisualizer()
                        visualizer._update_historical_actual_data()
                        self.logger.info("预测表真实价格字段更新完成")
                    except Exception as e:
                        self.logger.warning(f"更新预测表真实价格字段失败: {str(e)}")
                    
                    return {
                        'success': True,
                        'message': f"增量更新完成: 成功 {success_count} 条, 失败 {fail_count} 只股票",
                        'data': {
                            'success_count': success_count,
                            'fail_count': fail_count,
                            'results': result_list
                        }
                    }
                else:
                    # 全量收集
                    result = collector.collect_batch_stocks(symbols, start_date=None, end_date=None, period=period)
                    # 数据收集完成后，更新预测表的真实价格字段
                    try:
                        self.logger.info("开始更新预测表的真实价格字段...")
                        from visualizer.prediction_visualizer import PredictionVisualizer
                        visualizer = PredictionVisualizer()
                        visualizer._update_historical_actual_data()
                        self.logger.info("预测表真实价格字段更新完成")
                    except Exception as e:
                        self.logger.warning(f"更新预测表真实价格字段失败: {str(e)}")
                    
                    return {
                        'success': True,
                        'message': f"全量收集完成: 成功 {result.get('success_count', 0)}, 失败 {result.get('fail_count', 0)}",
                        'data': result
                    }
            
            # 多线程模式
            start_time = datetime.now()
            total_success = 0
            total_failed = 0
            total_skipped = 0
            
            # 分批处理（每批内部使用多线程）
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            
            try:
                for batch_num in range(total_batches):
                    batch_start = batch_num * batch_size
                    batch_end = min(batch_start + batch_size, len(symbols))
                    batch = symbols[batch_start:batch_end]
                    
                    self.logger.info(f"\n批次 {batch_num + 1}/{total_batches}: 处理 {len(batch)} 只股票（使用{max_workers}个线程）")
                    
                    batch_start_time = datetime.now()
                    batch_success = 0
                    batch_failed = 0
                    batch_skipped = 0
                    
                    # 使用线程池并行处理
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # 提交所有任务
                        future_to_symbol = {
                            executor.submit(self._collect_single_us_stock_worker, symbol, collection_type, start_date, end_date, period): symbol
                            for symbol in batch
                        }
                        
                        # 处理完成的任务
                        for future in as_completed(future_to_symbol):
                            symbol = future_to_symbol[future]
                            try:
                                result = future.result()
                                if result.get('skipped', False):
                                    batch_skipped += 1
                                    total_skipped += 1
                                elif result.get('success', False):
                                    batch_success += 1
                                    total_success += 1
                                    records_count = result.get('records_count', 0)
                                    self.logger.debug(f"  ✓ {symbol} 收集成功: {records_count} 条记录")
                                else:
                                    batch_failed += 1
                                    total_failed += 1
                                    self.logger.warning(f"  ✗ {symbol} 收集失败: {result.get('message', '未知错误')}")
                            except Exception as e:
                                batch_failed += 1
                                total_failed += 1
                                self.logger.error(f"  ✗ {symbol} 处理异常: {str(e)}")
                    
                    batch_end_time = datetime.now()
                    batch_duration = (batch_end_time - batch_start_time).total_seconds()
                    self.logger.info(f"批次 {batch_num + 1} 完成: 成功 {batch_success}, 失败 {batch_failed}, 跳过 {batch_skipped}, 耗时 {batch_duration:.1f}秒")
                    
                    # 批次之间的延迟
                    if batch_num + 1 < total_batches:
                        time.sleep(delay)
                
                total_duration = (datetime.now() - start_time).total_seconds()
                self.logger.info(f"\n收集完成: 成功 {total_success}, 失败 {total_failed}, 跳过 {total_skipped}, 总耗时 {total_duration:.1f}秒")
                
                # 数据收集完成后，更新预测表的真实价格字段
                try:
                    self.logger.info("开始更新预测表的真实价格字段...")
                    from visualizer.prediction_visualizer import PredictionVisualizer
                    visualizer = PredictionVisualizer()
                    visualizer._update_historical_actual_data()
                    self.logger.info("预测表真实价格字段更新完成")
                except Exception as e:
                    self.logger.warning(f"更新预测表真实价格字段失败: {str(e)}")
                    # 不影响主流程，继续返回成功
                
                return {
                    'success': True,
                    'message': f"{collection_type}收集完成: 成功 {total_success}, 失败 {total_failed}, 跳过 {total_skipped}",
                    'data': {
                        'success_count': total_success,
                        'fail_count': total_failed,
                        'skip_count': total_skipped,
                        'total_duration_seconds': total_duration
                    }
                }
            except Exception as e:
                self.logger.error(f"多线程收集过程出错: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                return {
                    'success': False,
                    'message': f"收集过程出错: {str(e)}",
                    'data': {
                        'success_count': total_success,
                        'fail_count': total_failed,
                        'skip_count': total_skipped
                    }
                }
        except Exception as e:
            self.logger.error(f"执行美国股票数据获取任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f"执行失败: {str(e)}",
                'error': str(e)
            }
    
    def _execute_model_evaluation(self, task: Dict) -> Dict:
        """执行模型性能评估任务"""
        try:
            from utils.model_performance_evaluator import ModelPerformanceEvaluator
            
            evaluator = ModelPerformanceEvaluator()
            task_config = self._parse_task_config(task)
            days = task_config.get('days', 30)
            evaluation_types = task_config.get('evaluation_types', ['prediction', 'trading'])
            
            results = {}
            
            if 'prediction' in evaluation_types:
                prediction_result = evaluator.evaluate_prediction_performance(days=days)
                results['prediction'] = prediction_result
            
            if 'trading' in evaluation_types:
                trading_result = evaluator.evaluate_trading_performance(days=days)
                results['trading'] = trading_result
            
            return {
                'success': True,
                'message': '模型性能评估完成',
                'data': results
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"评估失败: {str(e)}",
                'error': str(e)
            }
    
    def _execute_model_optimization(self, task: Dict) -> Dict:
        """执行模型参数优化任务"""
        try:
            from utils.model_optimizer import ModelOptimizer
            
            optimizer = ModelOptimizer()
            task_config = self._parse_task_config(task)
            
            # 计算日期范围
            days = task_config.get('days', 30)
            end_date_obj = datetime.now().date()
            start_date_obj = end_date_obj - timedelta(days=days)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
            
            # 使用任务配置中的搜索空间，如果没有则使用默认
            optimization_config = task_config.get('optimization_config', {})
            
            # 设置自动应用阈值（默认5%，如果改进超过此值则自动应用）
            if 'auto_apply_threshold' not in optimization_config:
                optimization_config['auto_apply_threshold'] = task_config.get('auto_apply_threshold', 5.0)
            
            # 设置优化方法（默认网格搜索，如果scikit-optimize可用则优先使用贝叶斯优化）
            optimization_method = task_config.get('optimization_method', 'auto')  # auto/grid_search/bayesian
            use_cross_validation = task_config.get('use_cross_validation', True)  # 默认使用交叉验证
            optimization_config['use_cross_validation'] = use_cross_validation
            
            # 根据方法选择优化算法
            if optimization_method == 'bayesian' or (optimization_method == 'auto' and self._check_bayesian_available()):
                # 使用贝叶斯优化
                result = optimizer.optimize_weights_bayesian(
                    start_date=start_date,
                    end_date=end_date,
                    optimization_config=optimization_config
                )
            else:
                # 使用网格搜索
                result = optimizer.optimize_weights_grid_search(
                    start_date=start_date,
                    end_date=end_date,
                    optimization_config=optimization_config
                )
            
            if result.get('success'):
                improvement_pct = result.get('improvement_pct', 0)
                is_auto_applied = result.get('is_auto_applied', False)
                
                message = f"参数优化完成，改进: {improvement_pct:.2f}%"
                if is_auto_applied:
                    message += "（已自动应用）"
                
                return {
                    'success': True,
                    'message': message,
                    'data': result
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', '优化失败'),
                    'error': result.get('message')
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"优化失败: {str(e)}",
                'error': str(e)
            }
    
    def _check_bayesian_available(self) -> bool:
        """检查贝叶斯优化是否可用"""
        try:
            from skopt import gp_minimize
            return True
        except ImportError:
            return False
    
    def _execute_model_backtest(self, task: Dict) -> Dict:
        """执行模型回测任务"""
        try:
            from utils.backtest_engine import BacktestEngine
            
            engine = BacktestEngine()
            task_config = self._parse_task_config(task)
            
            # 计算日期范围
            days = task_config.get('days', 30)
            end_date_obj = datetime.now().date()
            start_date_obj = end_date_obj - timedelta(days=days)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
            
            initial_capital = task_config.get('initial_capital', 100000.0)
            
            result = engine.backtest_predictions(
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital
            )
            
            if result.get('success'):
                return {
                    'success': True,
                    'message': f"回测完成，总收益率: {result.get('total_return', 0):.2f}%",
                    'data': result
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', '回测失败'),
                    'error': result.get('message')
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"回测失败: {str(e)}",
                'error': str(e)
            }
    
    def _execute_automated_backtest(self, task: Dict) -> Dict:
        """执行自动化定期回测任务"""
        try:
            from utils.automated_backtest import get_automated_backtest
            
            automated_backtest = get_automated_backtest()
            task_config = self._parse_task_config(task)
            
            # 获取任务配置
            backtest_days = task_config.get('backtest_days', 30)  # 回测天数
            
            # 执行定期回测
            result = automated_backtest.run_periodic_backtest(days=backtest_days, save_to_db=True)
            
            return result
            
        except Exception as e:
            self.logger.error(f"执行自动化回测任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f"执行失败: {str(e)}",
                'error': str(e)
            }
    
    def _execute_news_crawl(self, task: Dict) -> Dict:
        """执行新闻抓取任务 - 直接调用 news-analysis-system-main 的方法"""
        try:
            task_config = self._parse_task_config(task)
            task_type = task_config.get('task_type', 'market')
            symbol = task_config.get('symbol', None)
            interval_minutes = task_config.get('interval_minutes', 60)
            
            self.logger.info(f"开始执行新闻抓取任务（使用news-analysis-system-main），类型: {task_type}, 股票: {symbol}")
            
            # 尝试导入并调用 news-analysis-system-main 的方法
            try:
                import sys
                import os
                
                # 获取 news-analysis-system-main 项目路径
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                news_system_path = os.path.join(os.path.dirname(current_dir), 'news-analysis-system-main')
                
                if not os.path.exists(news_system_path):
                    raise FileNotFoundError(f"news-analysis-system-main 项目路径不存在: {news_system_path}")
                
                # 添加到 Python 路径
                if news_system_path not in sys.path:
                    sys.path.insert(0, news_system_path)
                
                # 导入 news-analysis-system-main 的新闻获取函数（财联社 + 东方财富个股新闻）
                from src.data_processing.get_cls_news import fetch_and_store_news
                from src.data_processing.get_em_stock_news import fetch_and_store_em_stock_news
                
                self.logger.info("成功导入 news-analysis-system-main 的 fetch_and_store_news 和 fetch_and_store_em_stock_news 函数")
                
                # 调用 news-analysis-system-main 的新闻获取方法
                # 注意：内部已经处理了新闻获取、股票匹配、情感分析和数据库存储
                # 重定向 print() 输出到 logger，以便统一管理日志
                import io
                from contextlib import redirect_stdout, redirect_stderr
                import sys
                
                # 使用不可关闭的缓冲区，避免 akshare 等库内部 close(sys.stdout) 导致 "I/O operation on closed file"
                class _UnclosableStringIO(io.StringIO):
                    def close(self):
                        pass  # 忽略 close，防止第三方库关闭 stdout 后 print 报错
                
                # 保存原始的 stdout 和 stderr
                original_stdout = sys.stdout
                original_stderr = sys.stderr
                
                stdout_buffer = _UnclosableStringIO()
                stderr_buffer = _UnclosableStringIO()
                
                try:
                    # 抑制 pandas SettingWithCopyWarning 警告（来自 akshare 库内部）
                    import warnings
                    # 抑制所有 SettingWithCopyWarning 警告（包括来自 akshare 的）
                    with warnings.catch_warnings():
                        warnings.filterwarnings('ignore', message='.*SettingWithCopyWarning.*')
                        warnings.filterwarnings('ignore', message='.*A value is trying to be set on a copy.*')
                        warnings.filterwarnings('ignore', category=FutureWarning)  # 同时抑制 FutureWarning
                        # 重定向 print() 输出到缓冲区
                        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                            # 先抓取财联社新闻
                            fetch_and_store_news()
                            # 再抓取东方财富个股新闻
                            fetch_and_store_em_stock_news()
                    
                    # 将捕获的输出写入日志（在重定向恢复之前）
                    stdout_output = stdout_buffer.getvalue()
                    stderr_output = stderr_buffer.getvalue()
                    
                    if stdout_output:
                        for line in stdout_output.strip().split('\n'):
                            if line.strip():
                                self.logger.info(f"[news-analysis-system-main] {line.strip()}")
                    
                    if stderr_output:
                        for line in stderr_output.strip().split('\n'):
                            if line.strip():
                                self.logger.error(f"[news-analysis-system-main] {line.strip()}")
                finally:
                    # 确保 stdout 和 stderr 已恢复（redirect_stdout 会自动恢复，但为了安全起见显式检查）
                    if sys.stdout is not original_stdout:
                        sys.stdout = original_stdout
                    if sys.stderr is not original_stderr:
                        sys.stderr = original_stderr
                    
                    # 关闭缓冲区（在恢复 stdout/stderr 之后；_UnclosableStringIO.close 为 no-op）
                    try:
                        stdout_buffer.close()
                    except Exception:
                        pass
                    try:
                        stderr_buffer.close()
                    except Exception:
                        pass
                
                self.logger.info("news-analysis-system-main 新闻获取任务执行完成（财联社 + 东方财富个股新闻）")
                
                # 由于新闻抓取函数没有返回值，我们需要查询数据库获取统计信息
                try:
                    from utils.db_connection import DatabaseConnection as DBConnection
                    from config_db import USE_DATABASE
                    
                    if USE_DATABASE:
                        # 查询最近5分钟内新增的新闻数量（作为本次抓取的统计）
                        sql = """
                            SELECT 
                                COUNT(*) as total_count,
                                COUNT(CASE WHEN source = '财联社' THEN 1 END) as cls_count,
                                COUNT(CASE WHEN source = '东方财富个股新闻' THEN 1 END) as em_count
                            FROM news_articles 
                            WHERE fetch_time >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                        """
                        result = DBConnection.execute_query(sql)
                        
                        if result and len(result) > 0:
                            total_count = result[0].get('total_count', 0)
                            cls_count = result[0].get('cls_count', 0)
                            em_count = result[0].get('em_count', 0)
                            
                            return {
                                'success': True,
                                'message': f"新闻获取完成（通过news-analysis-system-main），最近5分钟新增 {total_count} 条新闻（财联社 {cls_count} 条，东方财富个股新闻 {em_count} 条）",
                                'data': {
                                    'success_count': total_count,
                                    'fail_count': 0,
                                    'duplicate_count': 0,
                                    'total': total_count,
                                    'source': 'news-analysis-system-main'
                                }
                            }
                except Exception as e:
                    self.logger.warning(f"查询统计信息失败: {str(e)}")
                
                # 如果无法查询统计信息，返回成功但无详细数据
                return {
                    'success': True,
                    'message': "新闻获取完成（通过news-analysis-system-main）",
                    'data': {
                        'success_count': 0,
                        'fail_count': 0,
                        'duplicate_count': 0,
                        'total': 0,
                        'source': 'news-analysis-system-main',
                        'note': '统计信息查询失败，但任务已执行'
                    }
                }
                
            except ImportError as e:
                self.logger.error(f"导入 news-analysis-system-main 模块失败: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                return {
                    'success': False,
                    'message': f'导入 news-analysis-system-main 模块失败: {str(e)}',
                    'error': str(e),
                    'hint': '请确保 news-analysis-system-main 项目存在且路径正确'
                }
            except FileNotFoundError as e:
                self.logger.error(f"news-analysis-system-main 项目路径不存在: {str(e)}")
                return {
                    'success': False,
                    'message': f'news-analysis-system-main 项目路径不存在: {str(e)}',
                    'error': str(e),
                    'hint': '请确保 news-analysis-system-main 项目与 smart_stock_advisor 在同一父目录下'
                }
            except Exception as e:
                self.logger.error(f"调用 news-analysis-system-main 方法失败: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                return {
                    'success': False,
                    'message': f'调用 news-analysis-system-main 方法失败: {str(e)}',
                    'error': str(e)
                }
        except Exception as e:
            self.logger.error(f"执行新闻抓取任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f"执行失败: {str(e)}",
                'error': str(e)
            }
            try:
                if 'news_content_analyzer' in locals() and news_content_analyzer:
                    del news_content_analyzer
            except:
                pass
            import gc
            gc.collect()  # 强制垃圾回收
    
    def _execute_llm_analysis(self, task: Dict) -> Dict:
        """执行LLM深度分析任务"""
        try:
            self.logger.info("开始执行LLM深度分析任务（定时任务）")
            
            # 导入web_app中的run_llm_analysis函数
            import sys
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 尝试直接调用run_llm_analysis函数
            try:
                # 动态导入web_app模块
                sys.path.insert(0, project_root)
                from web_app import run_llm_analysis
                
                # 在后台线程中执行LLM分析（避免阻塞）
                import threading
                analysis_thread = threading.Thread(target=run_llm_analysis, daemon=True)
                analysis_thread.start()
                
                self.logger.info("LLM分析任务已在后台线程启动（定时任务）")
                
                return {
                    'success': True,
                    'message': 'LLM分析任务已启动，正在后台处理...',
                    'data': {
                        'task_name': task.get('task_name', 'LLM深度分析'),
                        'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
            except ImportError as e:
                self.logger.error(f"无法导入run_llm_analysis函数: {str(e)}")
                return {
                    'success': False,
                    'message': f'无法导入LLM分析函数: {str(e)}',
                    'error': str(e)
                }
            except Exception as e:
                self.logger.error(f"启动LLM分析任务失败: {str(e)}", exc_info=True)
                return {
                    'success': False,
                    'message': f'启动LLM分析任务失败: {str(e)}',
                    'error': str(e)
                }
                
        except Exception as e:
            self.logger.error(f"执行LLM分析任务异常: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'执行LLM分析任务异常: {str(e)}',
                'error': str(e)
            }
    
    def _create_task_history(self, task_id: int, task_name: str, task_type: str, start_time: datetime) -> Optional[int]:
        """创建任务执行历史记录"""
        try:
            sql = """
                INSERT INTO scheduled_task_history 
                (task_id, task_name, task_type, start_time, status)
                VALUES (%s, %s, %s, %s, 'running')
            """
            self.db.execute_update(sql, (task_id, task_name, task_type, start_time))
            
            # 获取刚插入的记录ID
            sql2 = "SELECT LAST_INSERT_ID() as id"
            results = self.db.execute_query(sql2)
            if results:
                return results[0].get('id')
            return None
        except Exception as e:
            self.logger.error(f"创建任务历史记录失败: {str(e)}")
            return None
    
    def _update_task_history(self, history_id: Optional[int], end_time: datetime, duration: int,
                            status: str, message: str, result_data: Optional[Dict], error_info: Optional[str]):
        """更新任务执行历史"""
        if not history_id:
            return
        
        try:
            result_json = json.dumps(result_data, ensure_ascii=False) if result_data else None
            sql = """
                UPDATE scheduled_task_history 
                SET end_time = %s, duration_seconds = %s, status = %s, 
                    message = %s, result_data = %s, error_info = %s
                WHERE id = %s
            """
            self.db.execute_update(sql, (end_time, duration, status, message, result_json, error_info, history_id))
        except Exception as e:
            self.logger.error(f"更新任务历史记录失败: {str(e)}")
    
    def _update_task_status(self, task_id: int, **kwargs):
        """更新任务状态"""
        try:
            # 定义允许更新的字段（防止SQL注入）
            # 注意：这个列表应该与数据库表结构保持一致
            allowed_fields = {
                'status', 'next_run_time', 'last_run_time', 
                'run_count', 'error_count', 'last_error', 
                'is_enabled', 'last_result',
                'last_run_status', 'last_run_message',  # 如果表中有这些字段
                'success_count', 'fail_count'  # 如果表中有这些字段
            }
            
            updates = []
            params = []
            for key, value in kwargs.items():
                # 验证字段名（防止SQL注入）
                if key in allowed_fields:
                    if value is not None:
                        updates.append(f"{key} = %s")
                        params.append(value)
                    # 如果值为None，不记录警告（可能是可选字段）
                else:
                    # 只对不在允许列表中的字段记录警告
                    self.logger.debug(f"字段 {key} 不在允许更新列表中，跳过")
            
            if updates:
                params.append(task_id)
                sql = f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE id = %s"
                self.db.execute_update(sql, tuple(params))
        except Exception as e:
            self.logger.error(f"更新任务状态失败: {str(e)}")
    
    def _update_next_run_time(self, task_id: int):
        """计算并更新下次执行时间"""
        try:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]['task']
            schedule_type = task.get('schedule_type', 'daily')
            schedule_time = task.get('schedule_time')
            
            now = datetime.now()
            next_run = None
            
            if schedule_type == 'daily':
                if schedule_time:
                    time_str = self._normalize_schedule_time(schedule_time)
                    if time_str:
                        # 解析时间字符串（HH:MM:SS或HH:MM）
                        time_parts = time_str.split(':')
                        hour = int(time_parts[0]) if len(time_parts) > 0 else 15
                        minute = int(time_parts[1]) if len(time_parts) > 1 else 5
                        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if next_run <= now:
                            next_run += timedelta(days=1)
                else:
                    next_run = now.replace(hour=15, minute=5, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)
            elif schedule_type == 'hourly':
                if schedule_time:
                    time_str = self._normalize_schedule_time(schedule_time)
                    if time_str and ':' in time_str:
                        minute = int(time_str.split(':')[1]) if len(time_str.split(':')) > 1 else 0
                    else:
                        minute = 0
                    next_run = now.replace(minute=minute, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(hours=1)
                else:
                    next_run = now + timedelta(hours=1)
            elif schedule_type == 'interval':
                # 间隔执行：根据task_config中的interval_minutes计算
                task_config = self._parse_task_config(task)
                interval_minutes = task_config.get('interval_minutes', 60)
                next_run = now + timedelta(minutes=interval_minutes)
            
            if next_run:
                sql = "UPDATE scheduled_tasks SET next_run_time = %s WHERE id = %s"
                self.db.execute_update(sql, (next_run, task_id))
        except Exception as e:
            self.logger.error(f"更新下次执行时间失败: {str(e)}")
    
    def create_task(self, task_name: str, task_type: str, schedule_type: str = 'daily',
                   schedule_time: str = None, schedule_weekdays: str = None,
                   schedule_month_day: int = None, task_config: Dict = None, created_by: int = None) -> Optional[int]:
        """创建定时任务"""
        try:
            task_config_json = json.dumps(task_config, ensure_ascii=False) if task_config else None
            
            # 如果schedule_month_day不为None，将其添加到task_config中
            if schedule_month_day is not None:
                if task_config is None:
                    task_config = {}
                task_config['schedule_month_day'] = schedule_month_day
            
            task_config_json = json.dumps(task_config, ensure_ascii=False) if task_config else None
            
            sql = """
                INSERT INTO scheduled_tasks 
                (task_name, task_type, schedule_type, schedule_time, schedule_weekdays, 
                 task_config, created_by, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
            """
            self.db.execute_update(sql, (task_name, task_type, schedule_type, schedule_time,
                                       schedule_weekdays, task_config_json, created_by))
            
            # 获取刚插入的记录ID
            sql2 = "SELECT LAST_INSERT_ID() as id"
            results = self.db.execute_query(sql2)
            if results:
                task_id = results[0].get('id')
                self.logger.info(f"创建定时任务成功: {task_name} (ID: {task_id})")
                return task_id
            return None
        except Exception as e:
            self.logger.error(f"创建定时任务失败: {str(e)}")
            return None
    
    def update_task(self, task_id: int, task_name: str = None, schedule_type: str = None,
                    schedule_time: str = None, schedule_weekdays: str = None,
                    schedule_month_day: int = None, task_config: Dict = None) -> bool:
        """更新定时任务（仅当任务已停止时可修改）"""
        try:
            task = self.get_task(task_id)
            if not task:
                self.logger.error(f"任务 {task_id} 不存在")
                return False
            
            if task.get('is_active') == 1:
                self.logger.warning(f"任务 {task_id} 正在运行中，需先停止才能修改")
                return False
            
            # 构建更新字段
            updates = []
            params = []
            
            if task_name is not None:
                updates.append("task_name = %s")
                params.append(task_name)
            if schedule_type is not None:
                updates.append("schedule_type = %s")
                params.append(schedule_type)
            if schedule_time is not None:
                updates.append("schedule_time = %s")
                params.append(schedule_time)
            if schedule_weekdays is not None:
                updates.append("schedule_weekdays = %s")
                params.append(schedule_weekdays)
            if task_config is not None:
                task_config_json = json.dumps(task_config, ensure_ascii=False)
                updates.append("task_config = %s")
                params.append(task_config_json)
            
            if schedule_month_day is not None:
                merged_config = task.get('task_config') or {}
                if not isinstance(merged_config, dict):
                    merged_config = {}
                merged_config['schedule_month_day'] = schedule_month_day
                task_config_json = json.dumps(merged_config, ensure_ascii=False)
                updates.append("task_config = %s")
                params.append(task_config_json)
            
            if not updates:
                self.logger.warning("无有效更新字段")
                return True
            
            params.append(task_id)
            sql = f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE id = %s"
            self.db.execute_update(sql, tuple(params))
            self.logger.info(f"定时任务已更新: ID {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"更新定时任务失败: {str(e)}")
            return False
    
    def start_task(self, task_id: int, task_source: str = None) -> bool:
        """启动任务（支持多种任务类型）"""
        try:
            # 如果指定了来源，根据来源处理
            if task_source == 'news_crawl_tasks':
                # 启动新闻抓取任务
                try:
                    from utils.news_task_manager import NewsTaskManager
                    manager = NewsTaskManager()
                    return manager.start_task(task_id)
                except Exception as e:
                    self.logger.error(f"启动新闻抓取任务失败: {str(e)}")
                    return False
            
            # 处理scheduled_tasks中的任务
            sql = "SELECT * FROM scheduled_tasks WHERE id = %s"
            tasks = self.db.execute_query(sql, (task_id,))
            if not tasks:
                self.logger.error(f"任务 {task_id} 不存在")
                return False
            
            task = tasks[0]
            task_type = task.get('task_type')
            
            # 根据任务类型执行不同的启动逻辑
            if task_type == 'stock_analysis':
                # 股票分析任务：立即执行一次，并更新状态为激活（加入调度器）
                # 更新任务状态为激活
                sql = "UPDATE scheduled_tasks SET is_active = 1 WHERE id = %s"
                self.db.execute_update(sql, (task_id,))
                task['is_active'] = 1
                
                # 将任务加入调度器（如果配置了定时执行）
                self._schedule_task(task)
                
                # 立即执行一次（在后台线程中执行，避免阻塞）
                import threading
                threading.Thread(target=self._execute_task, args=(task_id,), daemon=True).start()
                
                self.logger.info(f"股票分析任务已启动: ID {task_id}，已加入调度器并立即执行一次")
                return True
            elif task_type == 'news_crawl':
                # 新闻抓取任务：加入调度器，支持定时和间隔两种方式
                # 更新任务状态为激活
                sql = "UPDATE scheduled_tasks SET is_active = 1 WHERE id = %s"
                self.db.execute_update(sql, (task_id,))
                task['is_active'] = 1
                
                # 将任务加入调度器（schedule库会自动处理interval类型）
                self._schedule_task(task)
                
                # 如果配置了interval类型，立即执行一次（后续会按照调度器的时间执行）
                if task.get('schedule_type') == 'interval':
                    # 间隔执行任务，立即执行一次，然后由调度器定期执行
                    task_config = self._parse_task_config(task)
                    interval_minutes = task_config.get('interval_minutes', 60)
                    self.logger.info(f"新闻抓取任务已加入调度器，间隔: {interval_minutes}分钟，立即执行一次")
                    # 在后台线程中立即执行一次（避免阻塞）
                    import threading
                    threading.Thread(target=self._execute_task, args=(task_id,), daemon=True).start()
                
                return True
            else:
                # 其他类型：加入调度器
                sql = "UPDATE scheduled_tasks SET is_active = 1 WHERE id = %s"
                self.db.execute_update(sql, (task_id,))
                task['is_active'] = 1
                self._schedule_task(task)
                return True
            
        except Exception as e:
            self.logger.error(f"启动任务失败: {str(e)}")
            return False
    
    def stop_task(self, task_id: int, task_source: str = None) -> bool:
        """停止任务（支持多种任务类型）"""
        try:
            # 如果指定了来源，根据来源处理
            if task_source == 'news_crawl_tasks':
                # 停止新闻抓取任务
                try:
                    from utils.news_task_manager import NewsTaskManager
                    manager = NewsTaskManager()
                    return manager.stop_task(task_id)
                except Exception as e:
                    self.logger.error(f"停止新闻抓取任务失败: {str(e)}")
                    return False
            elif task_source == 'analysis_tasks':
                # 停止股票分析任务（需要通过web_app的API）
                # 这里只更新状态，实际停止需要调用web_app的停止接口
                self.logger.warning(f"股票分析任务需要通过API停止: {task_id}")
                return False
            
            # 处理scheduled_tasks中的任务
            if task_id not in self.tasks:
                self.logger.warning(f"任务 {task_id} 未在运行")
            
            # 取消调度
            if task_id in self.tasks:
                schedule.cancel_job(self.tasks[task_id]['job'])
                del self.tasks[task_id]
            
            # 更新任务状态
            sql = "UPDATE scheduled_tasks SET is_active = 0 WHERE id = %s"
            self.db.execute_update(sql, (task_id,))
            
            self.logger.info(f"定时任务已停止: ID {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"停止任务失败: {str(e)}")
            return False
    
    def get_task(self, task_id: int) -> Optional[Dict]:
        """获取任务信息"""
        try:
            sql = "SELECT * FROM scheduled_tasks WHERE id = %s"
            tasks = self.db.execute_query(sql, (task_id,))
            if tasks:
                task = tasks[0]
                # 解析JSON字段
                if task.get('task_config'):
                    try:
                        task['task_config'] = json.loads(task['task_config']) if isinstance(task['task_config'], str) else task['task_config']
                    except:
                        task['task_config'] = {}
                return task
            return None
        except Exception as e:
            self.logger.error(f"获取任务信息失败: {str(e)}")
            return None
    
    def get_all_tasks(self, task_type_filter: str = None) -> List[Dict]:
        """获取所有任务（包括scheduled_tasks和news_crawl_tasks）
        
        Args:
            task_type_filter: 任务类型过滤，支持逗号分隔的多个类型，如 'model_evaluation,model_optimization'
        """
        try:
            all_tasks = []
            
            # 解析task_type过滤条件
            task_types = None
            if task_type_filter:
                task_types = [t.strip() for t in task_type_filter.split(',') if t.strip()]
            
            # 1. 获取scheduled_tasks表中的任务
            if task_types:
                # 使用IN子句过滤
                placeholders = ','.join(['%s'] * len(task_types))
                sql = f"SELECT * FROM scheduled_tasks WHERE task_type IN ({placeholders}) ORDER BY id DESC"
                tasks = self.db.execute_query(sql, tuple(task_types))
            else:
                sql = "SELECT * FROM scheduled_tasks ORDER BY id DESC"
                tasks = self.db.execute_query(sql)
            
            # 解析JSON字段并标记来源
            for task in tasks:
                if task.get('task_config'):
                    try:
                        task['task_config'] = json.loads(task['task_config']) if isinstance(task['task_config'], str) else task['task_config']
                    except:
                        task['task_config'] = {}
                task['_source'] = 'scheduled_tasks'
                all_tasks.append(task)
            
            # 2. 获取news_crawl_tasks表中的任务（迁移到统一管理）
            # 只有在没有task_type过滤或过滤条件包含'news_crawl'时才获取
            if not task_types or 'news_crawl' in task_types:
                try:
                    sql2 = "SELECT * FROM news_crawl_tasks ORDER BY id DESC"
                    news_tasks = self.db.execute_query(sql2)
                    
                    for news_task in news_tasks:
                        # 转换为统一格式
                        unified_task = {
                            '_source': 'news_crawl_tasks',
                            '_original_id': news_task.get('id'),
                            'id': news_task.get('id'),  # 临时使用原ID，后续可以迁移
                            'task_name': news_task.get('task_name', ''),
                            'task_type': 'news_crawl',
                            'is_active': news_task.get('is_active', 0),
                            'schedule_type': 'interval',  # 新闻抓取是间隔执行
                            'schedule_time': None,
                            'schedule_weekdays': None,
                            'last_run_time': news_task.get('last_run_time'),
                            'next_run_time': None,
                            'last_run_status': None,
                            'last_run_message': None,
                            'run_count': 0,
                            'success_count': 0,
                            'fail_count': 0,
                            'task_config': {
                                'task_type': news_task.get('task_type', 'market'),
                                'symbol': news_task.get('symbol'),
                                'interval_minutes': news_task.get('interval_minutes', 60),
                                'sources': json.loads(news_task.get('sources', '[]')) if isinstance(news_task.get('sources'), str) else news_task.get('sources', [])
                            },
                            'created_at': news_task.get('created_at'),
                            'updated_at': news_task.get('updated_at')
                        }
                        all_tasks.append(unified_task)
                except Exception as e:
                    self.logger.debug(f"获取新闻抓取任务失败（可能表不存在）: {str(e)}")
            
            # 3. 获取analysis_tasks表中的任务（股票分析任务，一次性任务）
            # 只有在没有task_type过滤或过滤条件包含'stock_analysis'时才获取
            if not task_types or 'stock_analysis' in task_types:
                try:
                    sql3 = """
                        SELECT * FROM analysis_tasks 
                        WHERE status IN ('running', 'completed', 'cancelled')
                        ORDER BY id DESC 
                        LIMIT 50
                    """
                    analysis_tasks = self.db.execute_query(sql3)
                    
                    for analysis_task in analysis_tasks:
                        # 转换为统一格式
                        unified_task = {
                            '_source': 'analysis_tasks',
                            '_original_id': analysis_task.get('id'),
                            'id': analysis_task.get('id'),
                            'task_name': f"股票分析任务 #{analysis_task.get('id', '')}",
                            'task_type': 'stock_analysis',
                            'is_active': 1 if analysis_task.get('status') == 'running' else 0,
                            'schedule_type': 'once',  # 一次性任务
                            'schedule_time': None,
                            'schedule_weekdays': None,
                            'last_run_time': analysis_task.get('start_time'),
                            'next_run_time': None,
                            'last_run_status': analysis_task.get('status'),  # running/completed/cancelled
                            'last_run_message': None,
                            'run_count': 1,
                            'success_count': analysis_task.get('success_count', 0),
                            'fail_count': analysis_task.get('fail_count', 0),
                            'task_config': {
                                'limit': analysis_task.get('limit'),
                                'sort_type': analysis_task.get('sort_type', 'turnover')
                            },
                            'created_at': analysis_task.get('start_time'),
                            'updated_at': analysis_task.get('end_time') or analysis_task.get('start_time')
                        }
                        all_tasks.append(unified_task)
                except Exception as e:
                    self.logger.debug(f"获取股票分析任务失败（可能表不存在）: {str(e)}")
            
            return all_tasks
        except Exception as e:
            self.logger.error(f"获取任务列表失败: {str(e)}")
            return []
    
    def get_task_history(self, task_id: int = None, limit: int = 50) -> List[Dict]:
        """获取任务执行历史"""
        try:
            if task_id:
                sql = """
                    SELECT * FROM scheduled_task_history 
                    WHERE task_id = %s 
                    ORDER BY start_time DESC 
                    LIMIT %s
                """
                results = self.db.execute_query(sql, (task_id, limit))
            else:
                sql = """
                    SELECT * FROM scheduled_task_history 
                    ORDER BY start_time DESC 
                    LIMIT %s
                """
                results = self.db.execute_query(sql, (limit,))
            
            # 解析JSON字段
            for result in results:
                if result.get('result_data'):
                    try:
                        result['result_data'] = json.loads(result['result_data']) if isinstance(result['result_data'], str) else result['result_data']
                    except:
                        result['result_data'] = {}
            
            return results
        except Exception as e:
            self.logger.error(f"获取任务历史失败: {str(e)}")
            return []
    
    def _execute_other_data_collection(self, task: Dict) -> Dict:
        """执行其他数据获取任务（北向资金、市场指数、融资融券、主力资金、行业信息、板块轮动）
        
        根据测试脚本的逻辑：
        1. 先尝试AkShare（多个方法，如果第一个失败尝试第二个）
        2. 如果AkShare失败，再尝试Tushare
        3. 失败后最多重试3次
        """
        try:
            from data_source.stock_data_source import StockDataSource
            from utils.db_storage import DatabaseStorage
            from utils.data_storage import DataStorage
            import akshare as ak
            import tushare as ts
            from config import TUSHARE_TOKEN
            from datetime import timedelta
            import time
            
            data_source = StockDataSource()
            task_config = self._parse_task_config(task)
            data_type = task_config.get('data_type')
            symbols = task_config.get('symbols', None)
            
            if not data_type:
                return {
                    'success': False,
                    'message': '任务配置中缺少data_type',
                    'data': {}
                }
            
            self.logger.info(f"开始执行其他数据获取任务: {data_type}")
            start_time = datetime.now()
            success_count = 0
            fail_count = 0
            
            # 初始化Tushare
            pro = None
            if TUSHARE_TOKEN:
                try:
                    ts.set_token(TUSHARE_TOKEN)
                    pro = ts.pro_api()
                except:
                    pass
            
            def _retry_with_limit(func, max_retries=3, *args, **kwargs):
                """重试函数，最多重试max_retries次"""
                last_error = None
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            wait_time = 2 * (attempt + 1)  # 2秒、4秒、6秒
                            self.logger.debug(f"第 {attempt + 1}/{max_retries} 次尝试失败，等待 {wait_time} 秒后重试: {str(e)}")
                            time.sleep(wait_time)
                        else:
                            self.logger.debug(f"重试 {max_retries} 次后仍然失败: {str(e)}")
                if last_error:
                    raise last_error
                return None
            
            try:
                # 初始化数据存储
                db_storage = DatabaseStorage()
                # DataStorage会自动检测USE_DATABASE配置并初始化数据库存储（不需要传入参数）
                data_storage = DataStorage()
                
                if data_type == 'north_bound_capital':
                    # 获取北向资金数据（按照测试脚本的逻辑：先AkShare，失败后Tushare）
                    north_data = None
                    try:
                        # 方法1: 尝试AkShare（多个方法）
                        try:
                            from data_source.stock_data_source import _call_akshare_without_proxy
                            
                            # 尝试方法1: stock_connect_north_flow_em
                            if hasattr(ak, 'stock_connect_north_flow_em'):
                                try:
                                    north_data_df = _retry_with_limit(
                                        lambda: _call_akshare_without_proxy(
                                            ak.stock_connect_north_flow_em,
                                            indicator="北向资金"
                                        ),
                                        max_retries=3
                                    )
                                    if north_data_df is not None and not north_data_df.empty:
                                        # 解析数据
                                        latest = north_data_df.iloc[-1]
                                        today_net = 0.0
                                        for col in north_data_df.columns:
                                            col_str = str(col)
                                            if '净流入' in col_str or '净买入' in col_str:
                                                try:
                                                    val_str = str(latest[col]).replace('亿', '').replace('万', '').replace(',', '').strip()
                                                    val = float(val_str)
                                                    if '万' in str(latest[col]) or val < 100:
                                                        val = val / 10000
                                                    today_net = val
                                                    break
                                                except:
                                                    pass
                                        
                                        if today_net != 0:
                                            # 计算平均值
                                            avg_5d = today_net
                                            avg_10d = today_net
                                            if len(north_data_df) >= 5:
                                                for col in north_data_df.columns:
                                                    if '净流入' in str(col) or '净买入' in str(col):
                                                        try:
                                                            recent_5 = north_data_df[col].tail(5)
                                                            avg_5d = recent_5.mean()
                                                            if '万' in str(col) or avg_5d < 100:
                                                                avg_5d = avg_5d / 10000
                                                            if len(north_data_df) >= 10:
                                                                recent_10 = north_data_df[col].tail(10)
                                                                avg_10d = recent_10.mean()
                                                                if '万' in str(col) or avg_10d < 100:
                                                                    avg_10d = avg_10d / 10000
                                                            break
                                                        except:
                                                            pass
                                            
                                            north_data = {
                                                'today_net_inflow': today_net,
                                                'avg_net_inflow_5d': avg_5d if avg_5d != 0 else today_net,
                                                'avg_net_inflow_10d': avg_10d if avg_10d != 0 else today_net,
                                                'trend': 'inflow' if today_net > 0 else 'outflow'
                                            }
                                            self.logger.info("使用AkShare成功获取北向资金数据")
                                except Exception as e:
                                    self.logger.debug(f"AkShare方法1失败: {str(e)}")
                            
                            # 如果方法1失败，尝试方法2: stock_connect_north_sina
                            if north_data is None and hasattr(ak, 'stock_connect_north_sina'):
                                try:
                                    north_data_df = _retry_with_limit(
                                        lambda: _call_akshare_without_proxy(ak.stock_connect_north_sina),
                                        max_retries=3
                                    )
                                    if north_data_df is not None and not north_data_df.empty:
                                        latest = north_data_df.iloc[-1]
                                        today_net = 0.0
                                        for col in north_data_df.columns:
                                            col_str = str(col)
                                            if '净流入' in col_str or '净买入' in col_str:
                                                try:
                                                    val_str = str(latest[col]).replace('亿', '').replace('万', '').replace(',', '').strip()
                                                    val = float(val_str)
                                                    if '万' in str(latest[col]) or val < 100:
                                                        val = val / 10000
                                                    today_net = val
                                                    break
                                                except:
                                                    pass
                                        
                                        if today_net != 0:
                                            north_data = {
                                                'today_net_inflow': today_net,
                                                'avg_net_inflow_5d': today_net,
                                                'avg_net_inflow_10d': today_net,
                                                'trend': 'inflow' if today_net > 0 else 'outflow'
                                            }
                                            self.logger.info("使用AkShare方法2成功获取北向资金数据")
                                except Exception as e:
                                    self.logger.debug(f"AkShare方法2失败: {str(e)}")
                        except Exception as e:
                            self.logger.debug(f"AkShare获取北向资金失败: {str(e)}")
                        
                        # 方法2: 如果AkShare失败，尝试Tushare
                        if north_data is None and pro:
                            try:
                                today = datetime.now().strftime('%Y%m%d')
                                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
                                north_data_df = _retry_with_limit(
                                    pro.moneyflow_hsgt,
                                    max_retries=3,
                                    start_date=start_date,
                                    end_date=today
                                )
                                
                                if north_data_df is not None and not north_data_df.empty:
                                    latest = north_data_df.iloc[-1]
                                    today_net = 0.0
                                    for col in ['ggt_ss', 'ggt_s2h', 'hgt', 'sgt']:
                                        if col in north_data_df.columns:
                                            try:
                                                val = float(latest[col])
                                                if abs(val) > 10000:
                                                    val = val / 10000
                                                today_net += val
                                            except:
                                                pass
                                    
                                    if today_net != 0:
                                        avg_5d = today_net
                                        avg_10d = today_net
                                        if len(north_data_df) >= 5:
                                            for col in ['ggt_ss', 'ggt_s2h', 'hgt', 'sgt']:
                                                if col in north_data_df.columns:
                                                    try:
                                                        recent_5 = north_data_df[col].tail(5)
                                                        avg_val = recent_5.mean()
                                                        if abs(avg_val) > 10000:
                                                            avg_val = avg_val / 10000
                                                        avg_5d += avg_val
                                                        if len(north_data_df) >= 10:
                                                            recent_10 = north_data_df[col].tail(10)
                                                            avg_val_10 = recent_10.mean()
                                                            if abs(avg_val_10) > 10000:
                                                                avg_val_10 = avg_val_10 / 10000
                                                            avg_10d += avg_val_10
                                                    except:
                                                        pass
                                        
                                        north_data = {
                                            'today_net_inflow': today_net,
                                            'avg_net_inflow_5d': avg_5d if avg_5d != 0 else today_net,
                                            'avg_net_inflow_10d': avg_10d if avg_10d != 0 else today_net,
                                            'trend': 'inflow' if today_net > 0 else 'outflow'
                                        }
                                        self.logger.info("使用Tushare成功获取北向资金数据")
                            except Exception as e:
                                self.logger.debug(f"Tushare获取北向资金失败: {str(e)}")
                        
                        # 保存数据
                        if north_data and north_data.get('today_net_inflow') is not None:
                            timestamp = datetime.now()
                            date_str = timestamp.strftime('%Y-%m-%d')
                            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                            
                            sql = """
                                INSERT INTO north_bound_capital 
                                (timestamp, date, today_net_inflow, avg_net_inflow_5d, avg_net_inflow_10d, trend)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    timestamp = VALUES(timestamp),
                                    today_net_inflow = VALUES(today_net_inflow),
                                    avg_net_inflow_5d = VALUES(avg_net_inflow_5d),
                                    avg_net_inflow_10d = VALUES(avg_net_inflow_10d),
                                    trend = VALUES(trend)
                            """
                            db_storage.db.execute_update(sql, (
                                timestamp_str, date_str,
                                north_data.get('today_net_inflow', 0.0),
                                north_data.get('avg_net_inflow_5d', 0.0),
                                north_data.get('avg_net_inflow_10d', 0.0),
                                north_data.get('trend', 'neutral')
                            ))
                            success_count = 1
                        else:
                            fail_count = 1
                    except Exception as e:
                        self.logger.error(f"获取北向资金数据失败: {str(e)}")
                        fail_count = 1
                
                elif data_type == 'market_index':
                    # 获取市场指数数据（按照测试脚本的逻辑：先AkShare，失败后Tushare）
                    index_codes = {
                        'sh000001': '上证指数',
                        'sz399001': '深证成指',
                        'sz399006': '创业板指',
                        'sh000016': '上证50',
                        'sz399005': '中小板指'
                    }
                    
                    from data_source.stock_data_source import _call_akshare_without_proxy
                    
                    for index_code, index_name in index_codes.items():
                        index_data = None
                        index_symbol = index_code.replace('sh', '').replace('sz', '')
                        
                        try:
                            # 方法1: 尝试AkShare（多个方法）
                            # 方法1.1: index_zh_a_hist
                            try:
                                end_date = datetime.now().strftime('%Y%m%d')
                                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
                                index_data = _retry_with_limit(
                                    lambda: _call_akshare_without_proxy(
                                        ak.index_zh_a_hist,
                                        symbol=index_symbol,
                                        period="日k",
                                        start_date=start_date,
                                        end_date=end_date
                                    ),
                                    max_retries=3
                                )
                                if index_data is not None and not index_data.empty:
                                    self.logger.info(f"使用AkShare方法1成功获取指数 {index_name} 数据")
                            except Exception as e:
                                self.logger.debug(f"AkShare方法1获取指数 {index_name} 失败: {str(e)}")
                            
                            # 方法1.2: stock_zh_index_daily
                            if index_data is None or (hasattr(index_data, 'empty') and index_data.empty):
                                try:
                                    index_data = _retry_with_limit(
                                        lambda: _call_akshare_without_proxy(
                                            ak.stock_zh_index_daily,
                                            symbol=index_code
                                        ),
                                        max_retries=3
                                    )
                                    if index_data is not None and not index_data.empty:
                                        self.logger.info(f"使用AkShare方法2成功获取指数 {index_name} 数据")
                                except Exception as e:
                                    self.logger.debug(f"AkShare方法2获取指数 {index_name} 失败: {str(e)}")
                            
                            # 方法2: 如果AkShare失败，尝试Tushare
                            if (index_data is None or (hasattr(index_data, 'empty') and index_data.empty)) and pro:
                                try:
                                    tushare_code = f"{index_symbol}.SH" if index_code.startswith('sh') else f"{index_symbol}.SZ"
                                    today = datetime.now().strftime('%Y%m%d')
                                    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
                                    index_data = _retry_with_limit(
                                        pro.index_daily,
                                        max_retries=3,
                                        ts_code=tushare_code,
                                        start_date=start_date,
                                        end_date=today
                                    )
                                    if index_data is not None and not index_data.empty:
                                        self.logger.info(f"使用Tushare成功获取指数 {index_name} 数据")
                                except Exception as e:
                                    self.logger.debug(f"Tushare获取指数 {index_name} 失败: {str(e)}")
                            
                            # 记录结果
                            if index_data is not None and not index_data.empty:
                                success_count += 1
                            else:
                                fail_count += 1
                        except Exception as e:
                            self.logger.debug(f"获取指数 {index_name} 数据失败: {str(e)}")
                            fail_count += 1
                
                elif data_type == 'margin_trading':
                    # 获取融资融券数据（按照测试脚本的逻辑：先AkShare，失败后Tushare）
                    if not symbols:
                        sql = "SELECT DISTINCT symbol FROM stock_history_data LIMIT 5000"
                        results = db_storage.db.execute_query(sql)
                        symbols = [r['symbol'] for r in results]
                    
                    if not symbols:
                        return {
                            'success': False,
                            'message': '没有需要处理的股票',
                            'data': {'success_count': 0, 'fail_count': 0}
                        }
                    
                    timestamp = datetime.now()
                    date_str = timestamp.strftime('%Y-%m-%d')
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    
                    from data_source.stock_data_source import _call_akshare_without_proxy
                    
                    for symbol in symbols[:1000]:  # 限制每次最多处理1000只股票
                        margin_data = None
                        try:
                            # 方法1: 尝试AkShare（多个方法）
                            if symbol.startswith('6'):
                                # 上交所股票
                                try:
                                    if hasattr(ak, 'stock_margin_underlying_info_sse'):
                                        margin_data_df = _retry_with_limit(
                                            lambda: _call_akshare_without_proxy(
                                                ak.stock_margin_underlying_info_sse,
                                                symbol=symbol
                                            ),
                                            max_retries=3
                                        )
                                        if margin_data_df is not None and not margin_data_df.empty:
                                            # 解析数据
                                            latest = margin_data_df.iloc[-1]
                                            margin_balance = 0.0
                                            short_balance = 0.0
                                            for col in margin_data_df.columns:
                                                col_str = str(col)
                                                if '融资余额' in col_str:
                                                    try:
                                                        val_str = str(latest[col]).replace(',', '').replace('万', '').replace('亿', '').strip()
                                                        margin_balance = float(val_str)
                                                        if '亿' in str(latest[col]):
                                                            margin_balance = margin_balance * 10000
                                                    except:
                                                        pass
                                                elif '融券余额' in col_str:
                                                    try:
                                                        val_str = str(latest[col]).replace(',', '').replace('万', '').replace('亿', '').strip()
                                                        short_balance = float(val_str)
                                                        if '亿' in str(latest[col]):
                                                            short_balance = short_balance * 10000
                                                    except:
                                                        pass
                                            
                                            # 计算变化
                                            margin_change = 0.0
                                            margin_change_pct = 0.0
                                            if len(margin_data_df) > 1:
                                                for col in margin_data_df.columns:
                                                    if '融资余额' in str(col):
                                                        try:
                                                            prev_val_str = str(margin_data_df.iloc[-2][col]).replace(',', '').replace('万', '').replace('亿', '').strip()
                                                            prev_margin = float(prev_val_str)
                                                            if '亿' in str(margin_data_df.iloc[-2][col]):
                                                                prev_margin = prev_margin * 10000
                                                            margin_change = margin_balance - prev_margin
                                                            if prev_margin > 0:
                                                                margin_change_pct = (margin_change / prev_margin) * 100
                                                            break
                                                        except:
                                                            pass
                                            
                                            trend = 'increasing' if margin_change_pct > 2 else 'decreasing' if margin_change_pct < -2 else 'stable'
                                            margin_data = {
                                                'margin_balance': margin_balance,
                                                'margin_change': margin_change,
                                                'margin_change_pct': margin_change_pct,
                                                'short_balance': short_balance,
                                                'trend': trend
                                            }
                                            self.logger.debug(f"使用AkShare成功获取股票 {symbol} 融资融券数据")
                                except Exception as e:
                                    self.logger.debug(f"AkShare获取上交所股票 {symbol} 融资融券失败: {str(e)}")
                            else:
                                # 深交所股票
                                try:
                                    if hasattr(ak, 'stock_margin_underlying_info_szse'):
                                        # 注意：stock_margin_underlying_info_szse可能不接受symbol参数
                                        # 尝试不同的调用方式
                                        def get_szse_margin_data():
                                            try:
                                                # 方法1：尝试不带参数（返回所有股票数据，然后筛选）
                                                margin_data_all = _call_akshare_without_proxy(ak.stock_margin_underlying_info_szse)
                                                if margin_data_all is not None and not margin_data_all.empty:
                                                    # 查找代码列并筛选
                                                    code_col = None
                                                    for col in margin_data_all.columns:
                                                        if '代码' in str(col) or 'code' in str(col).lower() or 'symbol' in str(col).lower():
                                                            code_col = col
                                                            break
                                                    if code_col:
                                                        return margin_data_all[margin_data_all[code_col].astype(str).str.contains(symbol)]
                                                    else:
                                                        return margin_data_all
                                            except TypeError:
                                                # 方法2：如果必须带参数，尝试使用date参数
                                                try:
                                                    from datetime import datetime
                                                    today = datetime.now().strftime('%Y%m%d')
                                                    margin_data_all = _call_akshare_without_proxy(ak.stock_margin_underlying_info_szse, date=today)
                                                    if margin_data_all is not None and not margin_data_all.empty:
                                                        # 查找代码列并筛选
                                                        code_col = None
                                                        for col in margin_data_all.columns:
                                                            if '代码' in str(col) or 'code' in str(col).lower() or 'symbol' in str(col).lower():
                                                                code_col = col
                                                                break
                                                        if code_col:
                                                            return margin_data_all[margin_data_all[code_col].astype(str).str.contains(symbol)]
                                                        else:
                                                            return margin_data_all
                                                except Exception:
                                                    return None
                                        
                                        margin_data_df = _retry_with_limit(
                                            get_szse_margin_data,
                                            max_retries=3
                                        )
                                        if margin_data_df is not None and not margin_data_df.empty:
                                            # 解析数据（类似上交所逻辑）
                                            latest = margin_data_df.iloc[-1]
                                            margin_balance = 0.0
                                            short_balance = 0.0
                                            for col in margin_data_df.columns:
                                                col_str = str(col)
                                                if '融资余额' in col_str or '融资' in col_str:
                                                    try:
                                                        val = str(latest[col]).replace(',', '').replace('万', '').strip()
                                                        margin_balance = float(val)
                                                    except:
                                                        pass
                                                elif '融券余额' in col_str or '融券' in col_str:
                                                    try:
                                                        val = str(latest[col]).replace(',', '').replace('万', '').strip()
                                                        short_balance = float(val)
                                                    except:
                                                        pass
                                            
                                            # 计算变化
                                            margin_change = 0.0
                                            margin_change_pct = 0.0
                                            if len(margin_data_df) > 1:
                                                prev_margin = 0.0
                                                for col in margin_data_df.columns:
                                                    if '融资余额' in str(col):
                                                        try:
                                                            val = str(margin_data_df.iloc[-2][col]).replace(',', '').replace('万', '').strip()
                                                            prev_margin = float(val)
                                                            break
                                                        except:
                                                            pass
                                                margin_change = margin_balance - prev_margin
                                                margin_change_pct = (margin_change / prev_margin * 100) if prev_margin > 0 else 0.0
                                            
                                            trend = 'increasing' if margin_change_pct > 2 else 'decreasing' if margin_change_pct < -2 else 'stable'
                                            margin_data = {
                                                'margin_balance': margin_balance,
                                                'margin_change': margin_change,
                                                'margin_change_pct': margin_change_pct,
                                                'short_balance': short_balance,
                                                'trend': trend
                                            }
                                            self.logger.debug(f"使用AkShare成功获取股票 {symbol} 融资融券数据")
                                except Exception as e:
                                    self.logger.debug(f"AkShare获取深交所股票 {symbol} 融资融券失败: {str(e)}")
                            
                            # 方法2: 如果AkShare失败，尝试Tushare
                            if (margin_data is None or margin_data.get('margin_balance') is None) and pro:
                                try:
                                    tushare_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                                    today = datetime.now().strftime('%Y%m%d')
                                    start_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                                    margin_data_df = _retry_with_limit(
                                        pro.margin,
                                        max_retries=3,
                                        ts_code=tushare_code,
                                        start_date=start_date,
                                        end_date=today
                                    )
                                    
                                    if margin_data_df is not None and not margin_data_df.empty:
                                        latest = margin_data_df.iloc[-1]
                                        margin_balance = float(latest.get('rzye', 0)) / 10000 if latest.get('rzye') else 0.0
                                        short_balance = float(latest.get('rqye', 0)) / 10000 if latest.get('rqye') else 0.0
                                        
                                        # 计算变化
                                        margin_change = 0.0
                                        margin_change_pct = 0.0
                                        if len(margin_data_df) > 1:
                                            prev = margin_data_df.iloc[-2]
                                            prev_margin = float(prev.get('rzye', 0)) / 10000 if prev.get('rzye') else 0.0
                                            margin_change = margin_balance - prev_margin
                                            if prev_margin > 0:
                                                margin_change_pct = (margin_change / prev_margin) * 100
                                        
                                        trend = 'increasing' if margin_change_pct > 2 else 'decreasing' if margin_change_pct < -2 else 'stable'
                                        margin_data = {
                                            'margin_balance': margin_balance,
                                            'margin_change': margin_change,
                                            'margin_change_pct': margin_change_pct,
                                            'short_balance': short_balance,
                                            'trend': trend
                                        }
                                        self.logger.debug(f"使用Tushare成功获取股票 {symbol} 融资融券数据")
                                except Exception as e:
                                    self.logger.debug(f"Tushare获取股票 {symbol} 融资融券失败: {str(e)}")
                            
                            # 保存数据
                            if margin_data and margin_data.get('margin_balance') is not None:
                                sql = """
                                    INSERT INTO margin_trading 
                                    (timestamp, date, symbol, margin_balance, margin_change, margin_change_pct, short_balance, trend)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE
                                        timestamp = VALUES(timestamp),
                                        margin_balance = VALUES(margin_balance),
                                        margin_change = VALUES(margin_change),
                                        margin_change_pct = VALUES(margin_change_pct),
                                        short_balance = VALUES(short_balance),
                                        trend = VALUES(trend)
                                """
                                db_storage.db.execute_update(sql, (
                                    timestamp_str, date_str, symbol,
                                    margin_data.get('margin_balance', 0.0),
                                    margin_data.get('margin_change', 0.0),
                                    margin_data.get('margin_change_pct', 0.0),
                                    margin_data.get('short_balance', 0.0),
                                    margin_data.get('trend', 'stable')
                                ))
                                success_count += 1
                            else:
                                fail_count += 1
                        except Exception as e:
                            self.logger.debug(f"获取股票 {symbol} 融资融券数据失败: {str(e)}")
                            fail_count += 1
                
                elif data_type == 'main_force_capital':
                    # 获取主力资金数据（按照测试脚本的逻辑：先AkShare，失败后Tushare）
                    if not symbols:
                        sql = "SELECT DISTINCT symbol FROM stock_history_data LIMIT 5000"
                        results = db_storage.db.execute_query(sql)
                        symbols = [r['symbol'] for r in results]
                    
                    if not symbols:
                        return {
                            'success': False,
                            'message': '没有需要处理的股票',
                            'data': {'success_count': 0, 'fail_count': 0}
                        }
                    
                    timestamp = datetime.now()
                    date_str = timestamp.strftime('%Y-%m-%d')
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    
                    from data_source.stock_data_source import _call_akshare_without_proxy
                    
                    for symbol in symbols[:1000]:  # 限制每次最多处理1000只股票
                        capital_data = None
                        try:
                            # 方法1: 尝试AkShare（多个方法）
                            # 方法1.1: stock_individual_fund_flow
                            try:
                                market = "sh" if symbol.startswith('6') else "sz"
                                capital_flow = _retry_with_limit(
                                    lambda: _call_akshare_without_proxy(
                                        ak.stock_individual_fund_flow,
                                        stock=symbol,
                                        market=market
                                    ),
                                    max_retries=3
                                )
                                if capital_flow is not None and not capital_flow.empty:
                                    # 解析数据
                                    latest = capital_flow.iloc[-1]
                                    main_net = 0.0
                                    main_net_pct = 0.0
                                    for col in capital_flow.columns:
                                        col_str = str(col)
                                        if '主力净流入' in col_str or '主力资金' in col_str:
                                            try:
                                                val = float(latest[col])
                                                if abs(val) > 10000:
                                                    val = val / 10000
                                                main_net = val
                                            except:
                                                pass
                                        elif '主力' in col_str and ('占比' in col_str or '净流入占比' in col_str):
                                            try:
                                                val = float(latest[col])
                                                main_net_pct = val
                                            except:
                                                pass
                                    
                                    if main_net != 0 or main_net_pct != 0:
                                        capital_data = {
                                            'main_net_inflow': main_net,
                                            'main_net_inflow_pct': main_net_pct,
                                            'trend': 'inflow' if main_net > 0 else ('outflow' if main_net < 0 else 'neutral')
                                        }
                                        self.logger.debug(f"使用AkShare方法1成功获取股票 {symbol} 主力资金数据")
                            except Exception as e:
                                self.logger.debug(f"AkShare方法1获取股票 {symbol} 主力资金失败: {str(e)}")
                            
                            # 方法1.2: stock_individual_fund_flow_rank
                            if capital_data is None:
                                try:
                                    capital_flow = _retry_with_limit(
                                        lambda: _call_akshare_without_proxy(
                                            ak.stock_individual_fund_flow_rank,
                                            indicator="今日"
                                        ),
                                        max_retries=3
                                    )
                                    if capital_flow is not None and not capital_flow.empty:
                                        # 查找该股票的数据
                                        code_col = None
                                        for col in capital_flow.columns:
                                            if '代码' in str(col) or 'code' in str(col).lower():
                                                code_col = col
                                                break
                                        if code_col:
                                            row = capital_flow[capital_flow[code_col].astype(str).str.contains(symbol)]
                                            if not row.empty:
                                                # 解析数据
                                                main_net = 0.0
                                                main_net_pct = 0.0
                                                for col in capital_flow.columns:
                                                    col_str = str(col)
                                                    if '主力净流入' in col_str or '主力资金' in col_str:
                                                        try:
                                                            val = float(row.iloc[0][col])
                                                            if abs(val) > 10000:
                                                                val = val / 10000
                                                            main_net = val
                                                        except:
                                                            pass
                                                    elif '主力' in col_str and ('占比' in col_str or '净流入占比' in col_str):
                                                        try:
                                                            val = float(row.iloc[0][col])
                                                            main_net_pct = val
                                                        except:
                                                            pass
                                                
                                                if main_net != 0 or main_net_pct != 0:
                                                    capital_data = {
                                                        'main_net_inflow': main_net,
                                                        'main_net_inflow_pct': main_net_pct,
                                                        'trend': 'inflow' if main_net > 0 else ('outflow' if main_net < 0 else 'neutral')
                                                    }
                                                    self.logger.debug(f"使用AkShare方法2成功获取股票 {symbol} 主力资金数据")
                                except Exception as e:
                                    self.logger.debug(f"AkShare方法2获取股票 {symbol} 主力资金失败: {str(e)}")
                            
                            # 方法2: 如果AkShare失败，尝试Tushare（但Tushare需要付费权限，通常不会成功）
                            if capital_data is None and pro:
                                try:
                                    tushare_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                                    today = datetime.now().strftime('%Y%m%d')
                                    start_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                                    moneyflow_data = _retry_with_limit(
                                        pro.moneyflow,
                                        max_retries=3,
                                        ts_code=tushare_code,
                                        start_date=start_date,
                                        end_date=today
                                    )
                                    if moneyflow_data is not None and not moneyflow_data.empty:
                                        # 解析数据（Tushare的moneyflow接口字段）
                                        latest = moneyflow_data.iloc[-1]
                                        main_net = float(latest.get('buy_sm_amount', 0)) - float(latest.get('sell_sm_amount', 0)) if latest.get('buy_sm_amount') else 0.0
                                        main_net = main_net / 10000 if abs(main_net) > 10000 else main_net
                                        capital_data = {
                                            'main_net_inflow': main_net,
                                            'main_net_inflow_pct': 0.0,
                                            'trend': 'inflow' if main_net > 0 else ('outflow' if main_net < 0 else 'neutral')
                                        }
                                        self.logger.debug(f"使用Tushare成功获取股票 {symbol} 主力资金数据")
                                except Exception as e:
                                    self.logger.debug(f"Tushare获取股票 {symbol} 主力资金失败: {str(e)}")
                            
                            # 保存数据
                            if capital_data and capital_data.get('main_net_inflow') is not None:
                                sql = """
                                    INSERT INTO main_force_capital 
                                    (timestamp, date, symbol, main_net_inflow, main_net_inflow_pct, trend)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE
                                        timestamp = VALUES(timestamp),
                                        main_net_inflow = VALUES(main_net_inflow),
                                        main_net_inflow_pct = VALUES(main_net_inflow_pct),
                                        trend = VALUES(trend)
                                """
                                db_storage.db.execute_update(sql, (
                                    timestamp_str, date_str, symbol,
                                    capital_data.get('main_net_inflow', 0.0),
                                    capital_data.get('main_net_inflow_pct', 0.0),
                                    capital_data.get('trend', 'neutral')
                                ))
                                success_count += 1
                            else:
                                fail_count += 1
                        except Exception as e:
                            self.logger.debug(f"获取股票 {symbol} 主力资金数据失败: {str(e)}")
                            fail_count += 1
                
                elif data_type == 'stock_industry_info':
                    # 获取股票行业信息（按照测试脚本的逻辑：先AkShare，失败后Tushare）
                    if not symbols:
                        sql = "SELECT DISTINCT symbol FROM stock_history_data"
                        results = db_storage.db.execute_query(sql)
                        symbols = [r['symbol'] for r in results]
                    
                    if not symbols:
                        return {
                            'success': False,
                            'message': '没有需要处理的股票',
                            'data': {'success_count': 0, 'fail_count': 0}
                        }
                    
                    timestamp = datetime.now()
                    from data_source.stock_data_source import _call_akshare_without_proxy
                    import json as json_lib
                    
                    for symbol in symbols[:5000]:  # 每月全量更新，可以处理更多股票
                        industry_info = None
                        try:
                            # 方法1: 尝试AkShare
                            try:
                                if hasattr(ak, 'stock_individual_info_em'):
                                    stock_info = _retry_with_limit(
                                        lambda: _call_akshare_without_proxy(
                                            ak.stock_individual_info_em,
                                            symbol=symbol
                                        ),
                                        max_retries=3
                                    )
                                elif hasattr(ak, 'stock_individual_info'):
                                    stock_info = _retry_with_limit(
                                        lambda: _call_akshare_without_proxy(
                                            ak.stock_individual_info,
                                            symbol=symbol
                                        ),
                                        max_retries=3
                                    )
                                else:
                                    stock_info = None
                                
                                if stock_info is not None and not stock_info.empty:
                                    industry_info = {
                                        'industry': '',
                                        'concepts': [],
                                        'industry_keywords': []
                                    }
                                    for _, row in stock_info.iterrows():
                                        key = str(row.iloc[0]).strip()
                                        value = str(row.iloc[1]).strip()
                                        if '行业' in key or 'industry' in key.lower():
                                            industry_info['industry'] = value
                                            industry_info['industry_keywords'].append(value)
                                        if '概念' in key or 'concept' in key.lower():
                                            if value and value != 'nan':
                                                concepts = [c.strip() for c in value.split(',') if c.strip()]
                                                industry_info['concepts'].extend(concepts)
                                                industry_info['industry_keywords'].extend(concepts)
                                    
                                    # 尝试获取概念板块
                                    try:
                                        concept_data = _retry_with_limit(
                                            lambda: _call_akshare_without_proxy(ak.stock_board_concept_name_em),
                                            max_retries=3
                                        )
                                        if concept_data is not None and not concept_data.empty:
                                            for _, row in concept_data.iterrows():
                                                concept_name = str(row.iloc[0]) if len(row) > 0 else ''
                                                if concept_name and concept_name not in industry_info['concepts']:
                                                    industry_info['industry_keywords'].append(concept_name)
                                    except:
                                        pass
                                    
                                    # 去重
                                    industry_info['concepts'] = list(set(industry_info['concepts']))
                                    industry_info['industry_keywords'] = list(set(industry_info['industry_keywords']))
                                    self.logger.debug(f"使用AkShare成功获取股票 {symbol} 行业信息")
                            except Exception as e:
                                self.logger.debug(f"AkShare获取股票 {symbol} 行业信息失败: {str(e)}")
                            
                            # 方法2: 如果AkShare失败，尝试Tushare
                            if (industry_info is None or not industry_info.get('industry')) and pro:
                                try:
                                    tushare_code = f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ"
                                    stock_basic = _retry_with_limit(
                                        pro.stock_basic,
                                        max_retries=3,
                                        ts_code=tushare_code,
                                        fields='ts_code,symbol,name,area,industry,list_date'
                                    )
                                    if stock_basic is not None and not stock_basic.empty:
                                        industry_info = {
                                            'industry': stock_basic.iloc[0].get('industry', ''),
                                            'concepts': [],
                                            'industry_keywords': [stock_basic.iloc[0].get('industry', '')]
                                        }
                                        self.logger.debug(f"使用Tushare成功获取股票 {symbol} 行业信息")
                                except Exception as e:
                                    self.logger.debug(f"Tushare获取股票 {symbol} 行业信息失败: {str(e)}")
                            
                            # 保存数据
                            if industry_info and industry_info.get('industry'):
                                extra_data = {
                                    'industry': industry_info.get('industry', ''),
                                    'concepts': industry_info.get('concepts', []),
                                    'industry_keywords': industry_info.get('industry_keywords', []),
                                    'updated_at': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                                }
                                
                                sql = """
                                    UPDATE stock_history_data 
                                    SET extra_data = JSON_SET(COALESCE(extra_data, '{}'), 
                                        '$.industry', %s,
                                        '$.concepts', %s,
                                        '$.industry_keywords', %s,
                                        '$.updated_at', %s)
                                    WHERE symbol = %s
                                    LIMIT 1
                                """
                                db_storage.db.execute_update(sql, (
                                    extra_data['industry'],
                                    json_lib.dumps(extra_data['concepts'], ensure_ascii=False),
                                    json_lib.dumps(extra_data['industry_keywords'], ensure_ascii=False),
                                    extra_data['updated_at'],
                                    symbol
                                ))
                                success_count += 1
                            else:
                                fail_count += 1
                        except Exception as e:
                            self.logger.debug(f"获取股票 {symbol} 行业信息失败: {str(e)}")
                            fail_count += 1
                
                elif data_type == 'sector_rotation':
                    # 获取板块轮动数据（按照测试脚本的逻辑：先AkShare，失败后Tushare）
                    sector_data = None
                    try:
                        # 抑制 pandas SettingWithCopyWarning 警告（来自 akshare 库内部）
                        import warnings
                        with warnings.catch_warnings():
                            warnings.filterwarnings('ignore', message='.*SettingWithCopyWarning.*')
                            warnings.filterwarnings('ignore', message='.*A value is trying to be set on a copy.*')
                            warnings.filterwarnings('ignore', category=FutureWarning)
                            
                            # 方法1: 尝试AkShare
                            from data_source.stock_data_source import _call_akshare_without_proxy
                            
                            try:
                                # 获取行业板块
                                if hasattr(ak, 'stock_board_industry_name_em'):
                                    industry_board = _retry_with_limit(
                                        lambda: _call_akshare_without_proxy(ak.stock_board_industry_name_em),
                                        max_retries=3
                                    )
                                elif hasattr(ak, 'stock_board_industry_name'):
                                    industry_board = _retry_with_limit(
                                        lambda: _call_akshare_without_proxy(ak.stock_board_industry_name),
                                        max_retries=3
                                    )
                                else:
                                    industry_board = None
                                
                                # 获取概念板块
                                if hasattr(ak, 'stock_board_concept_name_em'):
                                    concept_board = _retry_with_limit(
                                        lambda: _call_akshare_without_proxy(ak.stock_board_concept_name_em),
                                        max_retries=3
                                    )
                                else:
                                    concept_board = None
                                
                                if industry_board is not None and not industry_board.empty:
                                    industry_dict = {}
                                    concept_dict = {}
                                    
                                    # 处理行业板块
                                    sector_list = []
                                    for _, row in industry_board.head(50).iterrows():
                                        sector_name = str(row.get('板块名称', row.get('name', ''))).strip()
                                        if sector_name:
                                            sector_list.append(sector_name)
                                    
                                    # 获取板块实时行情数据
                                    for sector_name in sector_list[:30]:  # 只处理前30个
                                        try:
                                            if hasattr(ak, 'stock_board_industry_info_em'):
                                                board_info = _retry_with_limit(
                                                    lambda: _call_akshare_without_proxy(
                                                        ak.stock_board_industry_info_em,
                                                        symbol=sector_name
                                                    ),
                                                    max_retries=3
                                                )
                                                if board_info is not None and not board_info.empty:
                                                    change_pct = 0.0
                                                    for col in board_info.columns:
                                                        if '涨跌幅' in str(col) or '涨跌' in str(col):
                                                            try:
                                                                change_pct = float(board_info[col].iloc[-1])
                                                                break
                                                            except:
                                                                pass
                                                    industry_dict[sector_name] = {
                                                        'change_pct': change_pct,
                                                        'capital_flow': 0.0,
                                                        'heat': 0.5 + abs(change_pct) / 10.0
                                                    }
                                        except:
                                            industry_dict[sector_name] = {
                                                'change_pct': 0.0,
                                                'capital_flow': 0.0,
                                                'heat': 0.5
                                            }
                                    
                                    # 处理概念板块
                                    if concept_board is not None and not concept_board.empty:
                                        for _, row in concept_board.head(30).iterrows():
                                            sector_name = str(row.get('板块名称', row.get('name', ''))).strip()
                                            if sector_name:
                                                concept_dict[sector_name] = {
                                                    'change_pct': 0.0,
                                                    'capital_flow': 0.0,
                                                    'heat': 0.5
                                                }
                                    
                                    # 计算热门板块
                                    hot_sectors = []
                                    all_sectors = []
                                    for sector_name, sector_info in industry_dict.items():
                                        all_sectors.append((sector_name, sector_info.get('change_pct', 0.0)))
                                    for sector_name, sector_info in concept_dict.items():
                                        all_sectors.append((sector_name, sector_info.get('change_pct', 0.0)))
                                    
                                    if all_sectors:
                                        all_sectors.sort(key=lambda x: abs(x[1]), reverse=True)
                                        hot_sectors = [name for name, pct in all_sectors[:10] if abs(pct) > 1.0]
                                    
                                    sector_data = {
                                        'industry_sectors': industry_dict,
                                        'concept_sectors': concept_dict,
                                        'hot_sectors': hot_sectors
                                    }
                                    self.logger.info("使用AkShare成功获取板块轮动数据")
                            except Exception as e:
                                self.logger.debug(f"AkShare获取板块轮动数据失败: {str(e)}")
                        
                        # 方法2: 如果AkShare失败，尝试Tushare（但Tushare通常需要付费权限）
                        if sector_data is None and pro:
                            try:
                                industry_classify = _retry_with_limit(
                                    pro.index_classify,
                                    max_retries=3,
                                    level='L1',
                                    src='SW2021'
                                )
                                if industry_classify is not None and not industry_classify.empty:
                                    # 构建简单的板块数据
                                    industry_dict = {}
                                    for _, row in industry_classify.iterrows():
                                        sector_name = str(row.get('industry_name', ''))
                                        if sector_name:
                                            industry_dict[sector_name] = {
                                                'change_pct': 0.0,
                                                'capital_flow': 0.0,
                                                'heat': 0.5
                                            }
                                    sector_data = {
                                        'industry_sectors': industry_dict,
                                        'concept_sectors': {},
                                        'hot_sectors': []
                                    }
                                    self.logger.info("使用Tushare成功获取板块轮动数据")
                            except Exception as e:
                                self.logger.debug(f"Tushare获取板块轮动数据失败: {str(e)}")
                        
                        # 保存数据
                        if sector_data:
                            db_storage.save_sector_rotation_data(sector_data)
                            success_count = 1
                        else:
                            fail_count = 1
                    except Exception as e:
                        self.logger.error(f"获取板块轮动数据失败: {str(e)}")
                        fail_count = 1
                
                else:
                    return {
                        'success': False,
                        'message': f'未知的数据类型: {data_type}',
                        'data': {'success_count': 0, 'fail_count': 0}
                    }
                
                end_time = datetime.now()
                duration = int((end_time - start_time).total_seconds())
                
                return {
                    'success': True,
                    'message': f'数据获取完成: 成功 {success_count}, 失败 {fail_count}',
                    'data': {
                        'success_count': success_count,
                        'fail_count': fail_count,
                        'duration': duration
                    }
                }
                
            except Exception as e:
                self.logger.error(f"执行其他数据获取任务异常: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                return {
                    'success': False,
                    'message': f'执行异常: {str(e)}',
                    'error': str(e),
                    'data': {'success_count': success_count, 'fail_count': fail_count}
                }
                
        except Exception as e:
            self.logger.error(f"执行其他数据获取任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'执行失败: {str(e)}',
                'error': str(e),
                'data': {}
            }
    
    def delete_task(self, task_id: int, task_source: str = None) -> bool:
        """删除定时任务
        
        Args:
            task_id: 任务ID
            task_source: 任务来源（scheduled_tasks/news_crawl_tasks/analysis_tasks），如果为None则自动检测
        """
        try:
            # 如果未指定来源，先尝试从scheduled_tasks查找
            if task_source is None:
                task = self.get_task(task_id)
                if task:
                    task_source = task.get('_source', 'scheduled_tasks')
                else:
                    # 如果找不到任务，尝试从scheduled_tasks删除
                    task_source = 'scheduled_tasks'
            
            # 根据来源处理删除
            if task_source == 'news_crawl_tasks':
                # 删除新闻抓取任务
                try:
                    from utils.news_task_manager import NewsTaskManager
                    manager = NewsTaskManager()
                    return manager.delete_task(task_id)
                except Exception as e:
                    self.logger.error(f"删除新闻抓取任务失败: {str(e)}")
                    return False
            elif task_source == 'analysis_tasks':
                # 股票分析任务通常不删除，只更新状态
                self.logger.warning(f"股票分析任务不支持删除: {task_id}")
                return False
            
            # 处理scheduled_tasks中的任务
            # 先停止任务（如果正在运行）
            try:
                self.stop_task(task_id)
            except Exception as e:
                self.logger.debug(f"停止任务失败（可能未运行）: {str(e)}")
            
            # 删除任务
            sql = "DELETE FROM scheduled_tasks WHERE id = %s"
            rows_affected = self.db.execute_update(sql, (task_id,))
            
            if rows_affected > 0:
                self.logger.info(f"定时任务已删除: ID {task_id}")
                return True
            else:
                self.logger.warning(f"未找到要删除的任务: ID {task_id}")
                return False
        except Exception as e:
            self.logger.error(f"删除定时任务失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
