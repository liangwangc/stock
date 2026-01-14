"""
安全地添加数据库索引脚本

本脚本会检查索引是否已存在，避免重复添加导致错误。
使用方法：python database/add_indexes_safe.py
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


def index_exists(db, table_name, index_name):
    """检查索引是否存在"""
    try:
        sql = f"SHOW INDEX FROM `{table_name}` WHERE Key_name = %s"
        result = db.execute_query(sql, (index_name,))
        return len(result) > 0
    except Exception as e:
        logger.warning(f"检查索引失败: {table_name}.{index_name}, 错误: {str(e)}")
        return False


def add_index_if_not_exists(db, table_name, index_name, index_sql):
    """如果索引不存在，则添加索引"""
    try:
        if index_exists(db, table_name, index_name):
            logger.info(f"索引已存在，跳过: {table_name}.{index_name}")
            return False
        
        logger.info(f"添加索引: {table_name}.{index_name}")
        db.execute_update(index_sql)
        logger.info(f"索引添加成功: {table_name}.{index_name}")
        return True
    except Exception as e:
        logger.error(f"添加索引失败: {table_name}.{index_name}, 错误: {str(e)}")
        return False


def main():
    """主函数：添加所有索引"""
    if not USE_DATABASE:
        logger.warning("数据库未启用，跳过索引添加")
        return
    
    db = DatabaseConnection()
    if not db:
        logger.error("无法连接数据库")
        return
    
    logger.info("开始添加数据库索引...")
    
    # 定义要添加的索引列表
    indexes = [
        # stock_predictions 表
        {
            'table': 'stock_predictions',
            'name': 'idx_symbol_prediction_date',
            'sql': "ALTER TABLE `stock_predictions` ADD INDEX `idx_symbol_prediction_date` (`symbol`, `prediction_date`) COMMENT '股票代码+预测日期复合索引'"
        },
        {
            'table': 'stock_predictions',
            'name': 'idx_symbol_prediction_time',
            'sql': "ALTER TABLE `stock_predictions` ADD INDEX `idx_symbol_prediction_time` (`symbol`, `prediction_time`) COMMENT '股票代码+预测时间复合索引'"
        },
        {
            'table': 'stock_predictions',
            'name': 'idx_prediction_date_score',
            'sql': "ALTER TABLE `stock_predictions` ADD INDEX `idx_prediction_date_score` (`prediction_date`, `final_score`) COMMENT '预测日期+最终得分复合索引'"
        },
        
        # realtime_trading_decisions 表
        {
            'table': 'realtime_trading_decisions',
            'name': 'idx_symbol_date',
            'sql': "ALTER TABLE `realtime_trading_decisions` ADD INDEX `idx_symbol_date` (`symbol`, `date`) COMMENT '股票代码+日期复合索引'"
        },
        {
            'table': 'realtime_trading_decisions',
            'name': 'idx_date_timestamp',
            'sql': "ALTER TABLE `realtime_trading_decisions` ADD INDEX `idx_date_timestamp` (`date`, `timestamp`) COMMENT '日期+时间戳复合索引'"
        },
        {
            'table': 'realtime_trading_decisions',
            'name': 'idx_signal_strength',
            'sql': "ALTER TABLE `realtime_trading_decisions` ADD INDEX `idx_signal_strength` (`signal_strength`) COMMENT '信号强度索引'"
        },
        {
            'table': 'realtime_trading_decisions',
            'name': 'idx_action',
            'sql': "ALTER TABLE `realtime_trading_decisions` ADD INDEX `idx_action` (`action`) COMMENT '操作建议索引'"
        },
        
        # news_articles 表
        {
            'table': 'news_articles',
            'name': 'idx_symbol_publish_time',
            'sql': "ALTER TABLE `news_articles` ADD INDEX `idx_symbol_publish_time` (`symbol`, `publish_time`) COMMENT '股票代码+发布时间复合索引'"
        },
        {
            'table': 'news_articles',
            'name': 'idx_sentiment_score',
            'sql': "ALTER TABLE `news_articles` ADD INDEX `idx_sentiment_score` (`sentiment_score`) COMMENT '情感得分索引'"
        },
        
        # scheduled_task_history 表
        {
            'table': 'scheduled_task_history',
            'name': 'idx_task_id_start_time',
            'sql': "ALTER TABLE `scheduled_task_history` ADD INDEX `idx_task_id_start_time` (`task_id`, `start_time`) COMMENT '任务ID+开始时间复合索引'"
        },
        {
            'table': 'scheduled_task_history',
            'name': 'idx_status_start_time',
            'sql': "ALTER TABLE `scheduled_task_history` ADD INDEX `idx_status_start_time` (`status`, `start_time`) COMMENT '状态+开始时间复合索引'"
        },
        
        # news_notifications 表
        {
            'table': 'news_notifications',
            'name': 'idx_is_sent_created',
            'sql': "ALTER TABLE `news_notifications` ADD INDEX `idx_is_sent_created` (`is_sent`, `created_at`) COMMENT '是否已发送+创建时间复合索引'"
        },
    ]
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for idx in indexes:
        try:
            result = add_index_if_not_exists(db, idx['table'], idx['name'], idx['sql'])
            if result:
                success_count += 1
            else:
                skip_count += 1
        except Exception as e:
            logger.error(f"处理索引失败: {idx['table']}.{idx['name']}, 错误: {str(e)}")
            fail_count += 1
    
    logger.info(f"索引添加完成: 成功 {success_count} 个, 跳过 {skip_count} 个, 失败 {fail_count} 个")
    print(f"\n索引添加完成: 成功 {success_count} 个, 跳过 {skip_count} 个, 失败 {fail_count} 个")


if __name__ == '__main__':
    main()
