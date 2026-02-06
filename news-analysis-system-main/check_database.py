"""
检查数据库连接和表结构
"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

import pymysql
from src.config.config import DB_CONFIG, MAIN_DB_CONFIG

def check_database():
    """检查数据库连接"""
    print("=" * 80)
    print("检查数据库连接")
    print("=" * 80)
    
    # 检查财联社数据库
    print("\n1. 检查财联社数据库连接...")
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port'],
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # 检查数据库是否存在
        cursor.execute("SHOW DATABASES LIKE 'cls_news_db'")
        result = cursor.fetchone()
        if result:
            print(f"   [成功] 数据库 cls_news_db 存在")
            
            # 连接到数据库
            cursor.execute("USE cls_news_db")
            
            # 检查表
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"   [成功] 找到 {len(tables)} 个表: {[t[0] for t in tables]}")
            
            # 检查news表结构
            cursor.execute("DESCRIBE news")
            columns = cursor.fetchall()
            column_names = [col[0] for col in columns]
            print(f"   [成功] news表字段: {', '.join(column_names)}")
            
            # 检查是否有股票关联字段
            stock_fields = ['symbol', 'sector', 'industry', 'concept', 'source']
            missing_fields = [f for f in stock_fields if f not in column_names]
            if missing_fields:
                print(f"   [警告] 缺少字段: {', '.join(missing_fields)}")
            else:
                print(f"   [成功] 所有股票关联字段已存在")
            
        else:
            print(f"   [失败] 数据库 cls_news_db 不存在")
            print(f"   配置信息: host={DB_CONFIG['host']}, port={DB_CONFIG['port']}, user={DB_CONFIG['user']}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"   [失败] 连接失败: {str(e)}")
        print(f"   配置信息: host={DB_CONFIG['host']}, port={DB_CONFIG['port']}, user={DB_CONFIG['user']}")
    
    # 检查主数据库
    print("\n2. 检查主数据库连接...")
    try:
        conn = pymysql.connect(
            host=MAIN_DB_CONFIG['host'],
            user=MAIN_DB_CONFIG['user'],
            password=MAIN_DB_CONFIG['password'],
            port=MAIN_DB_CONFIG['port'],
            database=MAIN_DB_CONFIG['database'],
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # 检查stock_predictions表
        cursor.execute("SELECT COUNT(*) FROM stock_predictions")
        count = cursor.fetchone()[0]
        print(f"   [成功] 主数据库连接成功，stock_predictions表有 {count} 条记录")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"   [失败] 主数据库连接失败: {str(e)}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_database()
