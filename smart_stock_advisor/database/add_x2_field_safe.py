"""
安全添加X2字段到数据库表
检查字段是否存在，如果不存在则添加
使用方法：python database/add_x2_field_safe.py
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def column_exists(db, table_name, column_name):
    """检查字段是否存在"""
    try:
        sql = f"SHOW COLUMNS FROM `{table_name}` LIKE %s"
        result = db.execute_query(sql, (column_name,))
        return len(result) > 0
    except Exception as e:
        logger.warning(f"检查字段失败: {table_name}.{column_name}, 错误: {str(e)}")
        return False


def add_x2_field():
    """添加x2字段到数据库表"""
    db = DatabaseConnection()
    
    try:
        column_name = 'x2'
        
        # 检查A股表
        table_name = 'stock_history_data'
        
        if column_exists(db, table_name, column_name):
            logger.info(f"表 {table_name} 中字段 {column_name} 已存在，跳过")
        else:
            logger.info(f"为表 {table_name} 添加字段 {column_name}...")
            sql = f"""
                ALTER TABLE `{table_name}` 
                ADD COLUMN `{column_name}` DECIMAL(8, 4) DEFAULT NULL 
                COMMENT 'X2指标（收盘价在20日区间中的相对位置，0-100）' 
                AFTER `rsi`
            """
            db.execute_update(sql)
            logger.info(f"✅ 表 {table_name} 添加字段 {column_name} 成功")
        
        # 检查美股表
        table_name = 'us_stock_history_data'
        
        if column_exists(db, table_name, column_name):
            logger.info(f"表 {table_name} 中字段 {column_name} 已存在，跳过")
        else:
            logger.info(f"为表 {table_name} 添加字段 {column_name}...")
            sql = f"""
                ALTER TABLE `{table_name}` 
                ADD COLUMN `{column_name}` DECIMAL(8, 4) DEFAULT NULL 
                COMMENT 'X2指标（收盘价在20日区间中的相对位置，0-100）' 
                AFTER `rsi`
            """
            db.execute_update(sql)
            logger.info(f"✅ 表 {table_name} 添加字段 {column_name} 成功")
        
        logger.info("✅ X2字段添加完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 添加X2字段失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        db.close_connection()


if __name__ == '__main__':
    print("=" * 60)
    print("开始添加X2字段到数据库表...")
    print("=" * 60)
    success = add_x2_field()
    if success:
        print("=" * 60)
        print("✅ X2字段添加成功！现在可以正常使用X2指标功能。")
        print("=" * 60)
    else:
        print("=" * 60)
        print("❌ X2字段添加失败，请检查错误信息。")
        print("=" * 60)
        sys.exit(1)
