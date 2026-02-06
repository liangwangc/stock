# 数据库配置（直接使用 stock_data 数据库）
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',  # 如果密码不同，请修改为实际密码
    'database': 'stock_data',
    'port': 3307,
    'charset': 'utf8mb4'
}

# 构建数据库连接字符串
DATABASE_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset={DB_CONFIG['charset']}"

# 保留 MAIN_DB_CONFIG 用于向后兼容（现在和 DB_CONFIG 相同）
MAIN_DB_CONFIG = DB_CONFIG.copy()
MAIN_DATABASE_URL = DATABASE_URL