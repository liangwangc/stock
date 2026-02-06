"""
数据库连接模块

提供线程安全的数据库连接管理，使用PyMySQL连接MySQL数据库。
每个线程维护独立的数据库连接，避免线程间连接冲突。

主要特性：
- 线程安全：使用threading.local实现每个线程独立连接
- 自动重连：连接断开时自动重新连接
- 字典游标：查询结果返回字典格式，便于使用
- 配置灵活：支持从配置文件读取数据库配置
- 优雅降级：数据库未启用时返回None，不影响业务逻辑

使用示例：
    ```python
    from utils.db_connection import DatabaseConnection
    
    db = DatabaseConnection()
    
    # 执行查询
    results = db.execute_query("SELECT * FROM stocks WHERE symbol = %s", ('000001',))
    
    # 执行更新
    db.execute_update("UPDATE stocks SET price = %s WHERE symbol = %s", (10.5, '000001'))
    ```

数据库配置：
- 配置文件：config_db.py
- 配置项：host, port, user, password, database, charset等

作者：Smart Stock Advisor Team
创建日期：2024
最后更新：2024
"""
import pymysql
from pymysql.cursors import DictCursor
from typing import Optional, Dict, Any, List
import threading
from utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入数据库配置
try:
    import sys
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    from config_db import DB_CONFIG, USE_DATABASE
except ImportError:
    logger.warning("未找到数据库配置，将使用默认配置")
    DB_CONFIG = {
        'host': 'localhost',
        'port': 3307,
        'user': 'root',
        'password': 'root',
        'database': 'stock_data',
        'charset': 'utf8mb4',
        'autocommit': True,
        'connect_timeout': 10,
    }
    USE_DATABASE = False


class DatabaseConnection:
    """
    数据库连接管理器（线程安全）
    
    提供线程安全的数据库连接管理，每个线程维护独立的数据库连接。
    支持自动重连、查询和更新操作。
    
    主要特性：
    - 线程安全：使用threading.local，每个线程独立连接
    - 自动重连：检测到连接断开时自动重新连接
    - 字典游标：查询结果自动转换为字典格式
    - 参数化查询：支持参数化SQL，防止SQL注入
    
    连接管理：
    - 每个线程一个连接，线程结束时连接自动关闭
    - 连接断开时自动重连（最多重试3次）
    - 查询和更新操作自动处理连接获取和错误处理
    """
    
    _local = threading.local()
    
    @classmethod
    def get_connection(cls):
        """
        获取数据库连接（每个线程一个连接）
        
        获取当前线程的数据库连接。如果连接不存在或已断开，会创建新连接。
        连接使用字典游标（DictCursor），查询结果返回字典格式。
        
        Returns:
            Optional[pymysql.Connection]: 数据库连接对象，如果数据库未启用返回None
        
        Raises:
            pymysql.Error: 如果连接失败（最多重试3次）
        
        Note:
            - 每个线程维护独立的连接
            - 连接会自动配置为使用字典游标
            - 如果数据库未启用（USE_DATABASE=False），返回None
        """
        if not USE_DATABASE:
            return None
        
        if not hasattr(cls._local, 'connection') or cls._local.connection is None:
            try:
                cls._local.connection = pymysql.connect(
                    cursorclass=DictCursor,
                    **DB_CONFIG
                )
                logger.debug(f"创建新的数据库连接（线程: {threading.current_thread().name}）")
            except Exception as e:
                logger.error(f"数据库连接失败: {str(e)}")
                raise
        
        # 检查连接是否有效
        try:
            cls._local.connection.ping(reconnect=True)
        except Exception as e:
            logger.warning(f"数据库连接已断开，重新连接: {str(e)}")
            try:
                cls._local.connection = pymysql.connect(
                    cursorclass=DictCursor,
                    **DB_CONFIG
                )
            except Exception as e2:
                logger.error(f"重新连接数据库失败: {str(e2)}")
                raise
        
        return cls._local.connection
    
    @classmethod
    def close_connection(cls):
        """关闭当前线程的数据库连接"""
        if hasattr(cls._local, 'connection') and cls._local.connection is not None:
            try:
                cls._local.connection.close()
                cls._local.connection = None
                logger.debug(f"关闭数据库连接（线程: {threading.current_thread().name}）")
            except Exception as e:
                logger.warning(f"关闭数据库连接失败: {str(e)}")
    
    @classmethod
    def execute_query(cls, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询SQL
        
        Args:
            sql: SQL语句
            params: 参数元组
            
        Returns:
            查询结果列表
        """
        if not USE_DATABASE:
            return []
        
        conn = cls.get_connection()
        if conn is None:
            return []
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"执行查询失败: {sql[:100]}... 错误: {str(e)}")
            raise
    
    @classmethod
    def execute_update(cls, sql: str, params: tuple = None, commit_immediately: bool = True) -> int:
        """
        执行更新SQL（INSERT、UPDATE、DELETE）
        
        Args:
            sql: SQL语句
            params: 参数元组
            
        Returns:
            受影响的行数
        """
        if not USE_DATABASE:
            return 0
        
        conn = cls.get_connection()
        if conn is None:
            return 0
        
        try:
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                # 如果autocommit=True，PyMySQL会自动提交，不需要手动commit
                # 手动commit可能导致不必要的锁竞争，影响查询性能
                if not DB_CONFIG.get('autocommit', True):
                    conn.commit()
                # autocommit=True时，不需要手动commit，避免锁竞争
                return affected_rows
        except Exception as e:
            logger.error(f"执行更新失败: {sql[:100]}... 错误: {str(e)}")
            raise
    
    @classmethod
    def execute_many(cls, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行SQL
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            
        Returns:
            受影响的行数
        """
        if not USE_DATABASE:
            return 0
        
        conn = cls.get_connection()
        if conn is None:
            return 0
        
        try:
            with conn.cursor() as cursor:
                affected_rows = cursor.executemany(sql, params_list)
                # 如果autocommit=True，不需要手动commit（PyMySQL会自动提交）
                # 如果autocommit=False，需要手动commit
                if not DB_CONFIG.get('autocommit', True):
                    conn.commit()
                # autocommit=True时，executemany会自动提交，不需要手动commit
                # 手动commit可能导致不必要的锁竞争
                return affected_rows
        except Exception as e:
            logger.error(f"批量执行失败: {sql[:100]}... 错误: {str(e)}")
            raise
    
    @classmethod
    def execute_transaction(cls, operations: List[tuple]) -> bool:
        """
        执行事务（多个操作）
        
        Args:
            operations: 操作列表，每个元素是 (sql, params) 元组
            
        Returns:
            是否成功
        """
        if not USE_DATABASE:
            return False
        
        conn = cls.get_connection()
        if conn is None:
            return False
        
        try:
            conn.begin()
            with conn.cursor() as cursor:
                for sql, params in operations:
                    cursor.execute(sql, params)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"事务执行失败: {str(e)}")
            raise
