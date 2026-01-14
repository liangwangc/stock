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
import sys
import os
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


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
    
    def start_scheduler(self):
        """启动调度器线程"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            return
        
        self.stop_scheduler.clear()
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="ScheduledTaskScheduler")
        self.scheduler_thread.start()
        self.logger.info("定时任务调度器已启动")
        
        # 加载并启动所有启用的任务
        self.load_and_start_tasks()
    
    def stop_scheduler_thread(self):
        """停止调度器线程"""
        if self.scheduler_thread:
            self.stop_scheduler.set()
            schedule.clear()
            self.logger.info("定时任务调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while not self.stop_scheduler.is_set():
            schedule.run_pending()
            time.sleep(1)
    
    def load_and_start_tasks(self):
        """加载并启动所有启用的任务"""
        try:
            sql = "SELECT * FROM scheduled_tasks WHERE is_active = 1"
            tasks = self.db.execute_query(sql)
            
            for task in tasks:
                try:
                    self._schedule_task(task)
                    self.logger.info(f"已加载定时任务: {task['task_name']} (ID: {task['id']})")
                except Exception as e:
                    self.logger.error(f"加载定时任务失败 {task['id']}: {str(e)}")
        except Exception as e:
            self.logger.error(f"加载定时任务列表失败: {str(e)}")
    
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
            schedule.cancel_job(self.tasks[task_id]['job'])
        
        # 创建任务执行函数
        def task_wrapper():
            self._execute_task(task_id)
        
        # 根据调度类型设置任务
        job = None
        if schedule_type == 'daily':
            if schedule_time:
                time_str = str(schedule_time) if isinstance(schedule_time, str) else schedule_time.strftime('%H:%M:%S')
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
                            day_map[day].at(time_str).do(task_wrapper)
                else:
                    job = schedule.every().day.at(time_str).do(task_wrapper)
            else:
                job = schedule.every().day.at("15:05").do(task_wrapper)  # 默认15:05（收盘后5分钟）
        elif schedule_type == 'hourly':
            if schedule_time:
                minute = int(str(schedule_time).split(':')[1]) if ':' in str(schedule_time) else 0
                job = schedule.every().hour.at(f":{minute:02d}").do(task_wrapper)
            else:
                job = schedule.every().hour.do(task_wrapper)
        elif schedule_type == 'interval':
            # 间隔执行（用于新闻抓取等任务）
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            interval_minutes = task_config.get('interval_minutes', 60)
            
            # schedule库支持按分钟执行
            if interval_minutes >= 60:
                # 按小时执行（如果间隔>=60分钟）
                hours = interval_minutes // 60
                job = schedule.every(hours).hours.do(task_wrapper)
            else:
                # 按分钟执行（间隔<60分钟）
                job = schedule.every(interval_minutes).minutes.do(task_wrapper)
        elif schedule_type == 'custom':
            # 如果是cron表达式，需要转换为schedule格式（这里简化处理）
            # 实际使用时可以使用APScheduler库来支持完整的cron表达式
            if cron_expression:
                self.logger.warning(f"任务 {task_id} 使用cron表达式，需要APScheduler支持")
                # 暂时按每天执行
                job = schedule.every().day.at("15:05").do(task_wrapper)
            else:
                job = schedule.every().day.at("15:05").do(task_wrapper)
        else:
            job = schedule.every().day.at("15:05").do(task_wrapper)
        
        if job:
            self.tasks[task_id] = {
                'job': job,
                'task': task,
                'stop_flag': threading.Event()
            }
            
            # 更新下次执行时间
            self._update_next_run_time(task_id)
    
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
                elif task_type == 'model_evaluation':
                    result = self._execute_model_evaluation(task)
                elif task_type == 'model_optimization':
                    result = self._execute_model_optimization(task)
                elif task_type == 'model_backtest':
                    result = self._execute_model_backtest(task)
                elif task_type == 'automated_backtest':
                    result = self._execute_automated_backtest(task)
                elif task_type == 'backup':
                    result = self._execute_backup(task)
                else:
                    message = f"未知的任务类型: {task_type}"
                    self.logger.warning(message)
                    result = None
                
                if result and result.get('success', False):
                    status = 'success'
                    message = result.get('message', '执行成功')
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
            self._update_task_status(task_id, last_run_time=start_time, last_run_status=status,
                                   last_run_message=message, run_count=task.get('run_count', 0) + 1,
                                   success_count=task.get('success_count', 0) + (1 if status == 'success' else 0),
                                   fail_count=task.get('fail_count', 0) + (1 if status == 'failed' else 0))
            
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
        """执行股票历史数据增量更新任务"""
        try:
            from utils.stock_history_collector import StockHistoryCollector
            
            collector = StockHistoryCollector()
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            symbols = task_config.get('symbols', None)  # 如果指定了股票列表
            
            result = collector.incremental_update_today(symbols)
            
            return {
                'success': True,
                'message': f"更新完成: 成功 {result.get('success_count', 0)}, 失败 {result.get('fail_count', 0)}",
                'data': result
            }
        except Exception as e:
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
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            limit = task_config.get('limit', None)
            sort_type = task_config.get('sort_type', 'turnover')
            symbols = task_config.get('symbols', None)  # 个股分析：股票代码列表
            
            # 通过模块导入的方式调用
            try:
                from data_source.stock_data_source import StockDataSource
                from predictor.stock_predictor import StockPredictor
                from visualizer.prediction_visualizer import PredictionVisualizer
                
                if StockDataSource is None or StockPredictor is None:
                    return {
                        'success': False,
                        'message': '股票分析模块未导入',
                        'error': '模块未导入'
                    }
                
                data_source = StockDataSource()
                predictor = StockPredictor(data_source=data_source)
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
                            predictor.predict(symbol)
                            success_count += 1
                        except Exception as e:
                            self.logger.error(f"分析股票 {symbol} 失败: {str(e)}")
                            fail_count += 1
                else:
                    # 全量分析
                    stock_list = data_source.get_all_stock_list(limit=limit, sort_by_turnover=(sort_type == 'turnover'))
                    
                    self.logger.info(f"开始全量分析，共 {len(stock_list)} 只股票（limit={limit}）")
                    for stock_info in stock_list[:limit if limit else len(stock_list)]:
                        symbol = stock_info.get('symbol', '')
                        try:
                            self.logger.info(f"正在分析股票: {symbol}")
                            predictor.predict(symbol)
                            success_count += 1
                        except Exception as e:
                            self.logger.error(f"分析股票 {symbol} 失败: {str(e)}")
                            fail_count += 1
                
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
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            
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
    
    def _execute_cn_stock_data_collection(self, task: Dict) -> Dict:
        """执行中国股票数据获取任务"""
        try:
            from utils.stock_history_collector import StockHistoryCollector
            
            collector = StockHistoryCollector()
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            
            # 获取任务配置
            collection_type = task_config.get('collection_type', 'incremental')  # incremental: 增量更新, full: 全量收集
            symbols = task_config.get('symbols', None)  # 如果指定了股票列表
            years = task_config.get('years', 10)  # 收集年数
            
            if collection_type == 'incremental':
                # 增量更新今日数据
                result = collector.incremental_update_today(symbols)
                return {
                    'success': True,
                    'message': f"增量更新完成: 成功 {result.get('success_count', 0)}, 失败 {result.get('fail_count', 0)}, 跳过 {result.get('skip_count', 0)}",
                    'data': result
                }
            else:
                # 全量收集
                if symbols:
                    result = collector.batch_collect_stocks_history(symbols, years=years)
                else:
                    # 如果没有指定股票列表，获取所有股票
                    from data_source.stock_data_source import StockDataSource
                    data_source = StockDataSource()
                    all_stocks = data_source.get_all_stock_list()
                    symbols = [s.get('symbol') for s in all_stocks if s.get('symbol')]
                    result = collector.batch_collect_stocks_history(symbols, years=years)
                
                return {
                    'success': True,
                    'message': f"全量收集完成: 成功 {result.get('success_count', 0)}, 失败 {result.get('fail_count', 0)}",
                    'data': result
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
    
    def _execute_us_stock_data_collection(self, task: Dict) -> Dict:
        """执行美国股票数据获取任务"""
        try:
            from utils.us_stock_collector import USStockCollector
            
            collector = USStockCollector()
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            
            # 获取任务配置
            collection_type = task_config.get('collection_type', 'incremental')  # incremental: 增量更新, full: 全量收集
            symbols = task_config.get('symbols', None)  # 如果指定了股票列表
            period = task_config.get('period', '10y')  # 收集周期
            index_type = task_config.get('index_type', None)  # sp500, nasdaq100, 或None（指定股票）
            
            if collection_type == 'incremental':
                # 增量更新（获取最近30天的数据）
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                if symbols:
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
                
                # 批量收集
                result = collector.collect_batch_stocks(symbols, start_date=None, end_date=None, period=period)
                
                return {
                    'success': True,
                    'message': f"全量收集完成: 成功 {result.get('success_count', 0)}, 失败 {result.get('fail_count', 0)}",
                    'data': result
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
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
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
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            
            # 计算日期范围
            days = task_config.get('days', 30)
            end_date_obj = datetime.now().date()
            start_date_obj = end_date_obj - timedelta(days=days)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
            
            # 使用任务配置中的搜索空间，如果没有则使用默认
            optimization_config = task_config.get('optimization_config', None)
            
            # 设置自动应用阈值（默认5%，如果改进超过此值则自动应用）
            if optimization_config is None:
                optimization_config = {}
            if 'auto_apply_threshold' not in optimization_config:
                optimization_config['auto_apply_threshold'] = task_config.get('auto_apply_threshold', 5.0)
            
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
    
    def _execute_model_backtest(self, task: Dict) -> Dict:
        """执行模型回测任务"""
        try:
            from utils.backtest_engine import BacktestEngine
            
            engine = BacktestEngine()
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            
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
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            
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
        """执行新闻抓取任务"""
        try:
            task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
            task_type = task_config.get('task_type', 'market')
            symbol = task_config.get('symbol', None)
            
            try:
                from news.unified_news_source import UnifiedNewsSource
                from utils.news_storage import NewsStorage
                
                news_source = UnifiedNewsSource()
                news_storage = NewsStorage()
                
                success_count = 0
                fail_count = 0
                news_list = []
                
                if task_type == 'market':
                    # 抓取市场新闻
                    news_list = news_source.fetch_market_news(limit=50)
                elif task_type == 'stock' and symbol:
                    # 抓取股票新闻
                    news_list = news_source.fetch_stock_news(symbol, limit=50)
                elif task_type == 'all':
                    # 抓取全部新闻
                    news_list = news_source.fetch_all_news(limit=100)
                else:
                    news_list = news_source.fetch_market_news(limit=50)
                
                for news_item in news_list:
                    try:
                        news_storage.save_news(news_item)
                        success_count += 1
                    except Exception as e:
                        self.logger.error(f"保存新闻失败: {str(e)}")
                        fail_count += 1
                
                return {
                    'success': True,
                    'message': f"抓取完成: 成功 {success_count}, 失败 {fail_count}",
                    'data': {
                        'success_count': success_count,
                        'fail_count': fail_count,
                        'total': len(news_list)
                    }
                }
            except ImportError as e:
                return {
                    'success': False,
                    'message': f'新闻模块导入失败: {str(e)}',
                    'error': str(e)
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"执行失败: {str(e)}",
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
            allowed_fields = {
                'status', 'next_run_time', 'last_run_time', 
                'run_count', 'error_count', 'last_error', 
                'is_enabled', 'last_result'
            }
            
            updates = []
            params = []
            for key, value in kwargs.items():
                # 验证字段名（防止SQL注入）
                if key in allowed_fields and value is not None:
                    updates.append(f"{key} = %s")
                    params.append(value)
                else:
                    self.logger.warning(f"不允许更新字段或值为None: {key}")
            
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
                    time_str = str(schedule_time) if isinstance(schedule_time, str) else schedule_time.strftime('%H:%M:%S')
                    hour, minute = map(int, time_str.split(':'))
                    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)
                else:
                    next_run = now.replace(hour=15, minute=5, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)
            
            if next_run:
                sql = "UPDATE scheduled_tasks SET next_run_time = %s WHERE id = %s"
                self.db.execute_update(sql, (next_run, task_id))
        except Exception as e:
            self.logger.error(f"更新下次执行时间失败: {str(e)}")
    
    def create_task(self, task_name: str, task_type: str, schedule_type: str = 'daily',
                   schedule_time: str = None, schedule_weekdays: str = None,
                   task_config: Dict = None, created_by: int = None) -> Optional[int]:
        """创建定时任务"""
        try:
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
                # 股票分析任务：立即执行一次
                self._execute_task(task_id)
                return True
            elif task_type == 'news_crawl':
                # 新闻抓取任务：如果配置了定时，加入调度器；否则立即执行
                if task.get('schedule_type') == 'interval':
                    # 间隔执行，需要特殊处理
                    task_config = json.loads(task.get('task_config', '{}')) if task.get('task_config') else {}
                    interval_minutes = task_config.get('interval_minutes', 60)
                    # 这里可以启动一个后台线程定期执行
                    self._execute_task(task_id)  # 先执行一次
                    # 更新任务状态
                    sql = "UPDATE scheduled_tasks SET is_active = 1 WHERE id = %s"
                    self.db.execute_update(sql, (task_id,))
                    return True
                else:
                    # 定时执行，加入调度器
                    sql = "UPDATE scheduled_tasks SET is_active = 1 WHERE id = %s"
                    self.db.execute_update(sql, (task_id,))
                    task['is_active'] = 1
                    self._schedule_task(task)
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
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务（包括scheduled_tasks和news_crawl_tasks）"""
        try:
            all_tasks = []
            
            # 1. 获取scheduled_tasks表中的任务
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
    
    def delete_task(self, task_id: int) -> bool:
        """删除定时任务"""
        try:
            # 先停止任务
            self.stop_task(task_id)
            
            # 删除任务
            sql = "DELETE FROM scheduled_tasks WHERE id = %s"
            self.db.execute_update(sql, (task_id,))
            
            self.logger.info(f"定时任务已删除: ID {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"删除定时任务失败: {str(e)}")
            return False
