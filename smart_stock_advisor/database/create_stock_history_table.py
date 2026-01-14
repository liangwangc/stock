"""
创建股票历史数据表
"""
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def create_stock_history_table():
    """创建股票历史数据表"""
    try:
        db = DatabaseConnection()
        
        # 读取SQL文件
        sql_file = os.path.join(project_root, "database", "stock_history_table.sql")
        if not os.path.exists(sql_file):
            logger.error(f"SQL文件不存在: {sql_file}")
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            create_sql = f.read()
        
        # 执行创建表语句
        try:
            db.execute_update(create_sql)
            logger.info("✅ 股票历史数据表创建成功")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg or "duplicate" in error_msg:
                logger.info("ℹ️ 股票历史数据表已存在")
                return True
            else:
                logger.error(f"创建表失败: {str(e)}")
                return False
                
    except Exception as e:
        logger.error(f"创建股票历史数据表异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("创建股票历史数据表")
    print("=" * 60)
    
    success = create_stock_history_table()
    
    if success:
        print("\n✅ 表创建完成")
    else:
        print("\n❌ 表创建失败")
    
    sys.exit(0 if success else 1)
