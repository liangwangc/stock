"""
数据库连接池模块
提供数据库连接池功能，提高数据库访问性能
"""
import pymysql
from pymysql.cursors import DictCursor
from pymysql.err import Error
from typing import Optional
import threading
import queue
import time
from utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入数据库配置
try:
    import sys
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    from config_db import DB_CONFIG, USE_DATABASE, DB_POOL_CONFIG
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
    DB_POOL_CONFIG = {
        'min_size': 2,
        'max_size': 10,
        'idle_timeout': 300,
        'get_connection_timeout': 5.0,
        'ping_on_checkout': True,
        'recycle_interval': 60,
    }


class DatabaseConnectionPool:
    """数据库连接池"""
    
    def __init__(self, min_size: int = 2, max_size: int = 10, idle_timeout: int = 300):
        """
        初始化连接池
        
        Args:
            min_size: 最小连接数
            max_size: 最大连接数
            idle_timeout: 空闲连接超时时间（秒）
        """
        self.min_size = min_size
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self.use_database = USE_DATABASE
        
        self._pool = queue.Queue(maxsize=max_size)
        self._created_connections = 0
        self._lock = threading.Lock()
        self._connection_times = {}  # {connection: last_used_time}
        
        # 如果数据库启用，初始化连接池
        if self.use_database:
            self._initialize_pool()
    
    def _create_connection(self) -> Optional[pymysql.Connection]:
        """创建新的数据库连接"""
        if not self.use_database:
            return None
        
        try:
            conn = pymysql.connect(
                cursorclass=DictCursor,
                **DB_CONFIG
            )
            logger.debug(f"创建新的数据库连接（连接池大小: {self._created_connections + 1}）")
            return conn
        except Exception as e:
            logger.error(f"创建数据库连接失败: {str(e)}")
            return None
    
    def _initialize_pool(self):
        """初始化连接池（创建最小连接数）"""
        for _ in range(self.min_size):
            conn = self._create_connection()
            if conn:
                self._pool.put(conn)
                self._connection_times[conn] = time.time()
                with self._lock:
                    self._created_connections += 1
    
    def get_connection(self, timeout: float = None) -> Optional[pymysql.Connection]:
        """
        从连接池获取连接
        
        Args:
            timeout: 获取连接的超时时间（秒），如果为None则使用配置中的值
        
        Returns:
            数据库连接，如果获取失败返回None
        """
        if not self.use_database:
            return None
        
        # 使用配置中的超时时间，如果未指定则使用默认值
        if timeout is None:
            timeout = DB_POOL_CONFIG.get('get_connection_timeout', 5.0)
        
        try:
            # 尝试从池中获取连接
            conn = self._pool.get(timeout=timeout)
            
            # 检查连接是否有效（如果配置启用）
            ping_on_checkout = DB_POOL_CONFIG.get('ping_on_checkout', True)
            if ping_on_checkout:
                try:
                    conn.ping(reconnect=True)
                except Exception as e:
                    logger.warning(f"连接已断开，重新创建: {str(e)}")
                    # 连接无效，创建新连接
                    with self._lock:
                        self._created_connections -= 1
                    conn = self._create_connection()
                    if conn:
                        with self._lock:
                            self._created_connections += 1
            
            if conn:
                # 更新连接使用时间
                self._connection_times[conn] = time.time()
            
            return conn
            
        except queue.Empty:
            # 池中没有可用连接，尝试创建新连接
            with self._lock:
                if self._created_connections < self.max_size:
                    conn = self._create_connection()
                    if conn:
                        self._created_connections += 1
                        self._connection_times[conn] = time.time()
                        return conn
            
            logger.warning("连接池已满，等待可用连接...")
            # 等待超时后返回None
            return None
    
    def return_connection(self, conn: Optional[pymysql.Connection]):
        """
        将连接归还到连接池
        
        Args:
            conn: 数据库连接
        """
        if not conn or not self.use_database:
            return
        
        try:
            # 检查连接是否有效
            conn.ping(reconnect=False)
            
            # 归还连接（如果池未满）
            if not self._pool.full():
                self._pool.put_nowait(conn)
                self._connection_times[conn] = time.time()
            else:
                # 池已满，关闭连接
                conn.close()
                with self._lock:
                    self._created_connections -= 1
                if conn in self._connection_times:
                    del self._connection_times[conn]
                    
        except Exception as e:
            logger.warning(f"归还连接失败，关闭连接: {str(e)}")
            try:
                conn.close()
            except:
                pass
            with self._lock:
                if self._created_connections > 0:
                    self._created_connections -= 1
            if conn in self._connection_times:
                del self._connection_times[conn]
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass
        
        with self._lock:
            self._created_connections = 0
        
        self._connection_times.clear()
        logger.info("连接池已关闭")
    
    def get_stats(self) -> dict:
        """获取连接池统计信息"""
        with self._lock:
            return {
                'pool_size': self._pool.qsize(),
                'created_connections': self._created_connections,
                'max_size': self.max_size,
                'min_size': self.min_size
            }


# 全局连接池实例
_connection_pool = None
_pool_lock = threading.Lock()


def get_connection_pool() -> DatabaseConnectionPool:
    """
    获取全局连接池实例（单例模式）
    
    使用 config_db.py 中的 DB_POOL_CONFIG 配置初始化连接池
    """
    global _connection_pool
    
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                # 从配置中获取参数，如果不存在则使用默认值
                min_size = DB_POOL_CONFIG.get('min_size', 2)
                max_size = DB_POOL_CONFIG.get('max_size', 10)
                idle_timeout = DB_POOL_CONFIG.get('idle_timeout', 300)
                
                _connection_pool = DatabaseConnectionPool(
                    min_size=min_size,
                    max_size=max_size,
                    idle_timeout=idle_timeout
                )
                
                logger.info(f"初始化数据库连接池: min_size={min_size}, max_size={max_size}, idle_timeout={idle_timeout}s")
    
    return _connection_pool
