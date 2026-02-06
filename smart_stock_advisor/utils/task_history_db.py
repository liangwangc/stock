"""
任务历史数据库访问模块
"""
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from utils.db_connection import DatabaseConnection
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)


def save_task_history(task_id: str, user_id: Optional[int] = None, username: Optional[str] = None,
                      analysis_type: Optional[str] = 'by_count', limit_count: Optional[int] = None, 
                      sort_type: Optional[str] = None, symbols: Optional[str] = None,
                      status: str = 'completed', total_stocks: int = 0, success_count: int = 0,
                      fail_count: int = 0, progress: int = 0, start_time: Optional[str] = None,
                      end_time: Optional[str] = None, duration_seconds: Optional[int] = None,
                      error_message: Optional[str] = None) -> bool:
    """
    保存任务历史记录到数据库
    
    Args:
        task_id: 任务ID
        user_id: 用户ID
        username: 用户名
        limit_count: 分析数量
        sort_type: 排序方式
        status: 任务状态
        total_stocks: 总股票数
        success_count: 成功数量
        fail_count: 失败数量
        progress: 当前进度
        start_time: 开始时间（ISO格式字符串）
        end_time: 结束时间（ISO格式字符串）
        duration_seconds: 耗时（秒）
        error_message: 错误信息
    
    Returns:
        bool: 是否保存成功
    """
    if not USE_DATABASE:
        logger.warning("数据库未启用，跳过任务历史保存")
        return False
    
    try:
        # 检查并更新表结构（如果缺少新字段）
        try:
            from config_db import DB_CONFIG
            conn = DatabaseConnection.get_connection()
            if conn:
                with conn.cursor() as cursor:
                    try:
                        # 检查现有列
                        cursor.execute("SHOW COLUMNS FROM analysis_tasks")
                        columns_result = cursor.fetchall()
                        
                        # 处理返回结果（PyMySQL返回元组列表，第一个元素是列名）
                        if columns_result:
                            existing_columns = [row[0] if isinstance(row, (tuple, list)) else str(row) for row in columns_result]
                        else:
                            existing_columns = []
                        
                        # 需要添加的字段列表
                        columns_to_add = []
                        
                        if 'analysis_type' not in existing_columns:
                            columns_to_add.append("""
                                ALTER TABLE `analysis_tasks` 
                                ADD COLUMN `analysis_type` VARCHAR(20) DEFAULT 'by_count' 
                                COMMENT '分析类型（by_count=按数量, by_symbols=按股票）' 
                                AFTER `username`
                            """)
                        
                        if 'symbols' not in existing_columns:
                            columns_to_add.append("""
                                ALTER TABLE `analysis_tasks` 
                                ADD COLUMN `symbols` TEXT DEFAULT NULL 
                                COMMENT '股票代码列表（JSON格式，仅在按股票模式时使用）' 
                                AFTER `sort_type`
                            """)
                        
                        # 执行添加字段的SQL
                        for alter_sql in columns_to_add:
                            try:
                                cursor.execute(alter_sql)
                                conn.commit()
                                logger.info(f"成功添加字段到 analysis_tasks 表")
                            except Exception as alter_error:
                                error_msg = str(alter_error)
                                # 如果字段已存在，忽略错误
                                if 'Duplicate column' in error_msg or 'already exists' in error_msg.lower():
                                    logger.debug(f"字段可能已存在，跳过: {error_msg}")
                                else:
                                    logger.warning(f"添加字段时出错（可能已存在）: {error_msg}")
                    except Exception as show_columns_error:
                        # 如果SHOW COLUMNS失败，记录错误但继续执行
                        error_msg = str(show_columns_error)
                        logger.warning(f"检查 analysis_tasks 表列结构时出错: {error_msg}")
        except Exception as alter_error:
            error_msg = str(alter_error) if alter_error else "未知错误"
            logger.warning(f"检查或更新 analysis_tasks 表结构时出错: {error_msg}")
            # 继续执行，不影响主流程
        
        # 转换时间格式
        start_dt = None
        if start_time:
            try:
                # 尝试ISO格式
                if 'T' in start_time or '+' in start_time or 'Z' in start_time:
                    # 处理ISO格式：2024-01-08T10:00:00 或 2024-01-08T10:00:00.123456
                    clean_time = start_time.replace('Z', '').replace('+00:00', '')
                    if '.' in clean_time:
                        start_dt = datetime.strptime(clean_time.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    else:
                        start_dt = datetime.strptime(clean_time, '%Y-%m-%dT%H:%M:%S')
                else:
                    # 尝试常见格式
                    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logger.warning(f"解析开始时间失败: {start_time}, 错误: {str(e)}")
                try:
                    # 尝试只取前19个字符（去掉微秒）
                    if len(start_time) > 19:
                        start_dt = datetime.strptime(start_time[:19], '%Y-%m-%dT%H:%M:%S')
                    else:
                        start_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
                except:
                    pass
        
        end_dt = None
        if end_time:
            try:
                # 尝试ISO格式
                if 'T' in end_time or '+' in end_time or 'Z' in end_time:
                    # 处理ISO格式
                    clean_time = end_time.replace('Z', '').replace('+00:00', '')
                    if '.' in clean_time:
                        end_dt = datetime.strptime(clean_time.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    else:
                        end_dt = datetime.strptime(clean_time, '%Y-%m-%dT%H:%M:%S')
                else:
                    # 尝试常见格式
                    end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logger.warning(f"解析结束时间失败: {end_time}, 错误: {str(e)}")
                try:
                    # 尝试只取前19个字符（去掉微秒）
                    if len(end_time) > 19:
                        end_dt = datetime.strptime(end_time[:19], '%Y-%m-%dT%H:%M:%S')
                    else:
                        end_dt = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')
                except:
                    pass
        
        # 插入或更新任务历史
        sql = """
            INSERT INTO analysis_tasks 
            (task_id, user_id, username, analysis_type, limit_count, sort_type, symbols, status, total_stocks,
             success_count, fail_count, progress, start_time, end_time, duration_seconds, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                user_id = VALUES(user_id),
                username = VALUES(username),
                analysis_type = VALUES(analysis_type),
                limit_count = VALUES(limit_count),
                sort_type = VALUES(sort_type),
                symbols = VALUES(symbols),
                status = VALUES(status),
                total_stocks = VALUES(total_stocks),
                success_count = VALUES(success_count),
                fail_count = VALUES(fail_count),
                progress = VALUES(progress),
                start_time = VALUES(start_time),
                end_time = VALUES(end_time),
                duration_seconds = VALUES(duration_seconds),
                error_message = VALUES(error_message),
                updated_at = CURRENT_TIMESTAMP
        """
        
        params = (
            task_id, user_id, username, analysis_type, limit_count, sort_type, symbols, status, total_stocks,
            success_count, fail_count, progress, start_dt, end_dt, duration_seconds, error_message
        )
        
        # 使用execute_update方法
        affected_rows = DatabaseConnection.execute_update(sql, params)
        logger.info(f"任务历史已保存: {task_id} (影响行数: {affected_rows}, 状态: {status}, 成功: {success_count}, 失败: {fail_count})")
        return True
        
    except Exception as e:
        logger.error(f"保存任务历史失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False
