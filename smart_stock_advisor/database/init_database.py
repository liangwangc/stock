"""
数据库初始化脚本
创建所有需要的数据库表
"""
import pymysql
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config_db import DB_CONFIG
except ImportError:
    print("错误：未找到 config_db.py 文件")
    sys.exit(1)

def init_database():
    """初始化数据库"""
    print("=" * 60)
    print("开始初始化数据库...")
    print("=" * 60)
    
    # 读取SQL文件
    sql_file = os.path.join(os.path.dirname(__file__), 'init_database.sql')
    if not os.path.exists(sql_file):
        print(f"错误：SQL文件不存在: {sql_file}")
        return False
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 读取新闻表SQL脚本
    news_table_path = os.path.join(os.path.dirname(__file__), 'news_table.sql')
    if os.path.exists(news_table_path):
        print("发现新闻表SQL脚本，正在合并...")
        with open(news_table_path, 'r', encoding='utf-8') as f:
            news_script = f.read()
        sql_content += "\n\n" + news_script
    
    # 读取用户表SQL脚本
    user_tables_path = os.path.join(os.path.dirname(__file__), 'user_tables.sql')
    if os.path.exists(user_tables_path):
        print("发现用户表SQL脚本，正在合并...")
        with open(user_tables_path, 'r', encoding='utf-8') as f:
            user_tables_script = f.read()
        sql_content += "\n\n" + user_tables_script
    
    # 读取任务历史表SQL脚本
    analysis_tasks_path = os.path.join(os.path.dirname(__file__), 'analysis_tasks_table.sql')
    if os.path.exists(analysis_tasks_path):
        print("发现任务历史表SQL脚本，正在合并...")
        with open(analysis_tasks_path, 'r', encoding='utf-8') as f:
            analysis_tasks_script = f.read()
        sql_content += "\n\n" + analysis_tasks_script
    
    # 分割SQL语句（按分号和换行）
    sql_statements = []
    current_stmt = []
    for line in sql_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('--'):
            continue
        current_stmt.append(line)
        if line.endswith(';'):
            sql_statements.append(' '.join(current_stmt))
            current_stmt = []
    
    try:
        # 连接数据库
        print(f"正在连接到数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        connection = pymysql.connect(**DB_CONFIG)
        
        success_count = 0
        error_count = 0
        
        with connection.cursor() as cursor:
            for i, sql in enumerate(sql_statements, 1):
                try:
                    print(f"[{i}/{len(sql_statements)}] 执行: {sql[:80]}...")
                    cursor.execute(sql)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ 失败: {str(e)}")
                    # 如果表已存在，不算错误
                    if 'already exists' in str(e).lower() or 'Duplicate table' in str(e):
                        print(f"  ⚠️  表已存在，跳过")
                        success_count += 1
                        error_count -= 1
        
        connection.commit()
        connection.close()
        
        print("=" * 60)
        print(f"数据库初始化完成！")
        print(f"  成功: {success_count} 个SQL语句")
        if error_count > 0:
            print(f"  失败: {error_count} 个SQL语句")
        print("=" * 60)
        
        return error_count == 0
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
