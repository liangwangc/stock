"""
安全地添加period_type字段脚本

检查字段是否存在，避免重复添加导致错误。
使用方法：python database/add_period_type_safe.py
"""
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger
from config_db import USE_DATABASE

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


def index_exists(db, table_name, index_name):
    """检查索引是否存在"""
    try:
        sql = f"SHOW INDEX FROM `{table_name}` WHERE Key_name = %s"
        result = db.execute_query(sql, (index_name,))
        return len(result) > 0
    except Exception as e:
        logger.warning(f"检查索引失败: {table_name}.{index_name}, 错误: {str(e)}")
        return False


def main():
    """主函数：添加period_type字段"""
    if not USE_DATABASE:
        logger.warning("数据库未启用，跳过字段添加")
        return
    
    db = DatabaseConnection()
    if not db:
        logger.error("无法连接数据库")
        return
    
    logger.info("开始添加period_type字段...")
    
    # A股历史数据表
    table_cn = 'stock_history_data'
    table_us = 'us_stock_history_data'
    
    try:
        # 检查表是否存在
        try:
            db.execute_query(f"SELECT 1 FROM `{table_cn}` LIMIT 1")
            cn_table_exists = True
        except:
            cn_table_exists = False
        
        try:
            db.execute_query(f"SELECT 1 FROM `{us_stock_history_data}` LIMIT 1")
            us_table_exists = True
        except:
            us_table_exists = False
        
        # 处理A股表
        if cn_table_exists:
            logger.info(f"处理表: {table_cn}")
            
            # 检查字段是否存在
            if not column_exists(db, table_cn, 'period_type'):
                logger.info(f"添加字段: {table_cn}.period_type")
                sql = f"""
                    ALTER TABLE `{table_cn}` 
                    ADD COLUMN `period_type` VARCHAR(10) DEFAULT 'daily' 
                    COMMENT '周期类型（daily=日线, weekly=周线, monthly=月线, yearly=年线）' 
                    AFTER `trade_date`
                """
                db.execute_update(sql)
                logger.info(f"字段添加成功: {table_cn}.period_type")
            else:
                logger.info(f"字段已存在，跳过: {table_cn}.period_type")
            
            # 更新现有数据
            logger.info(f"更新现有数据: {table_cn}")
            update_sql = f"""
                UPDATE `{table_cn}` 
                SET `period_type` = 'daily' 
                WHERE `period_type` IS NULL OR `period_type` = ''
            """
            try:
                affected = db.execute_update(update_sql)
                logger.info(f"更新了 {affected} 条记录")
            except Exception as e:
                logger.warning(f"更新数据失败: {str(e)}")
            
            # 添加索引
            if not index_exists(db, table_cn, 'idx_period_type'):
                logger.info(f"添加索引: {table_cn}.idx_period_type")
                index_sql = f"ALTER TABLE `{table_cn}` ADD INDEX `idx_period_type` (`period_type`)"
                db.execute_update(index_sql)
                logger.info(f"索引添加成功: {table_cn}.idx_period_type")
            else:
                logger.info(f"索引已存在，跳过: {table_cn}.idx_period_type")
        else:
            logger.warning(f"表不存在，跳过: {table_cn}")
        
        # 处理美股表
        if us_table_exists:
            logger.info(f"处理表: {table_us}")
            
            # 检查字段是否存在
            if not column_exists(db, table_us, 'period_type'):
                logger.info(f"添加字段: {table_us}.period_type")
                sql = f"""
                    ALTER TABLE `{table_us}` 
                    ADD COLUMN `period_type` VARCHAR(10) DEFAULT 'daily' 
                    COMMENT '周期类型（daily=日线, weekly=周线, monthly=月线, yearly=年线）' 
                    AFTER `trade_date`
                """
                db.execute_update(sql)
                logger.info(f"字段添加成功: {table_us}.period_type")
            else:
                logger.info(f"字段已存在，跳过: {table_us}.period_type")
            
            # 更新现有数据
            logger.info(f"更新现有数据: {table_us}")
            update_sql = f"""
                UPDATE `{table_us}` 
                SET `period_type` = 'daily' 
                WHERE `period_type` IS NULL OR `period_type` = ''
            """
            try:
                affected = db.execute_update(update_sql)
                logger.info(f"更新了 {affected} 条记录")
            except Exception as e:
                logger.warning(f"更新数据失败: {str(e)}")
            
            # 添加索引
            if not index_exists(db, table_us, 'idx_period_type'):
                logger.info(f"添加索引: {table_us}.idx_period_type")
                index_sql = f"ALTER TABLE `{table_us}` ADD INDEX `idx_period_type` (`period_type`)"
                db.execute_update(index_sql)
                logger.info(f"索引添加成功: {table_us}.idx_period_type")
            else:
                logger.info(f"索引已存在，跳过: {table_us}.idx_period_type")
        else:
            logger.warning(f"表不存在，跳过: {table_us}")
        
        logger.info("period_type字段添加完成")
        print("\nperiod_type字段添加完成")
        
    except Exception as e:
        logger.error(f"添加字段失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
