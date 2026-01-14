"""
数据库配置
"""
import os

# MySQL数据库配置
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

# 是否启用数据库（如果为False，则回退到CSV存储）
# 注意：启用数据库前，需要先运行 database/init_database.py 初始化数据库表
USE_DATABASE = True


# 数据库连接池配置
DB_POOL_CONFIG = {
    # 最小连接数：连接池初始化时创建的连接数
    # 推荐值：2-5（根据应用启动时的并发需求）
    # 说明：保持一定数量的连接可以避免首次请求时的连接创建延迟
    'min_size': 2,
    
    # 最大连接数：连接池允许的最大连接数
    # 推荐值：10-20（根据并发线程数和数据库服务器配置调整）
    # 说明：
    #   - 如果使用多线程数据收集（--threads 3-5），建议设置为 15-20
    #   - 如果只使用单线程，可以设置为 5-10
    #   - 注意：不要超过 MySQL 的 max_connections 配置
    'max_size': 300,
    
    # 空闲连接超时时间（秒）：超过此时间未使用的连接将被关闭
    # 推荐值：300-600（5-10分钟）
    # 说明：避免长时间占用数据库连接，释放资源
    'idle_timeout': 300,
    
    # 获取连接超时时间（秒）：从连接池获取连接时的最大等待时间
    # 推荐值：5.0-10.0
    # 说明：如果连接池已满，等待此时间后返回 None
    'get_connection_timeout': 5.0,
    
    # 连接健康检查：是否在获取连接时进行 ping 检查
    # 推荐值：True（推荐启用）
    # 说明：确保连接有效，避免使用已断开的连接
    'ping_on_checkout': True,
    
    # 连接回收间隔（秒）：定期清理空闲连接的间隔时间
    # 推荐值：60-120（1-2分钟）
    # 说明：定期检查并关闭超时的空闲连接
    'recycle_interval': 60,
}