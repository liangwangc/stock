#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查训练数据完整性
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


def check_training_data():
    """检查训练数据完整性"""
    try:
        db = DatabaseConnection()
        
        logger.info("=" * 60)
        logger.info("检查训练数据完整性")
        logger.info("=" * 60)
        
        # 1. 检查stock_predictions表
        logger.info("\n1. 检查stock_predictions表...")
        
        sql = """
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN actual_price IS NOT NULL THEN 1 END) as has_actual_price,
                COUNT(CASE WHEN actual_direction IS NOT NULL THEN 1 END) as has_actual_direction,
                COUNT(CASE WHEN prediction_hit IS NOT NULL THEN 1 END) as has_prediction_hit,
                COUNT(CASE WHEN actual_price IS NOT NULL 
                          AND actual_direction IS NOT NULL 
                          AND prediction_hit IS NOT NULL THEN 1 END) as valid_count,
                MIN(target_date) as earliest_date,
                MAX(target_date) as latest_date
            FROM stock_predictions
        """
        
        results = db.execute_query(sql)
        if results:
            result = results[0]
            logger.info(f"  总预测记录数: {result['total_count']}")
            logger.info(f"  有实际价格: {result['has_actual_price']}")
            logger.info(f"  有实际方向: {result['has_actual_direction']}")
            logger.info(f"  有预测命中: {result['has_prediction_hit']}")
            logger.info(f"  有效记录数: {result['valid_count']}")
            logger.info(f"  最早日期: {result['earliest_date']}")
            logger.info(f"  最新日期: {result['latest_date']}")
            
            if result['valid_count'] < 100:
                logger.warning(f"  ⚠️  有效记录数不足100条，建议至少1000+条")
            else:
                logger.info(f"  ✅ 有效记录数充足")
        
        # 2. 检查stock_history_data表
        logger.info("\n2. 检查stock_history_data表...")
        
        sql = """
            SELECT 
                COUNT(*) as total_count,
                COUNT(DISTINCT symbol) as stock_count,
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date,
                COUNT(CASE WHEN ma5 IS NOT NULL THEN 1 END) as has_ma5,
                COUNT(CASE WHEN rsi IS NOT NULL THEN 1 END) as has_rsi,
                COUNT(CASE WHEN macd IS NOT NULL THEN 1 END) as has_macd
            FROM stock_history_data
            WHERE period_type = 'daily'
        """
        
        results = db.execute_query(sql)
        if results:
            result = results[0]
            logger.info(f"  总历史记录数: {result['total_count']}")
            logger.info(f"  股票数量: {result['stock_count']}")
            logger.info(f"  最早日期: {result['earliest_date']}")
            logger.info(f"  最新日期: {result['latest_date']}")
            logger.info(f"  有MA5数据: {result['has_ma5']}")
            logger.info(f"  有RSI数据: {result['has_rsi']}")
            logger.info(f"  有MACD数据: {result['has_macd']}")
            
            if result['total_count'] < 10000:
                logger.warning(f"  ⚠️  历史数据量较少，建议至少10万+条")
            else:
                logger.info(f"  ✅ 历史数据量充足")
        
        # 3. 检查可以用于训练的样本数
        logger.info("\n3. 检查可训练样本数...")
        
        sql = """
            SELECT COUNT(*) as count
            FROM stock_predictions sp
            WHERE sp.actual_price IS NOT NULL
              AND sp.actual_direction IS NOT NULL
              AND sp.prediction_hit IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM stock_history_data shd
                  WHERE shd.symbol = sp.symbol
                    AND shd.trade_date < sp.target_date
                    AND shd.period_type = 'daily'
                    AND shd.ma5 IS NOT NULL
                    AND shd.rsi IS NOT NULL
                  LIMIT 1
              )
        """
        
        results = db.execute_query(sql)
        if results:
            count = results[0]['count']
            logger.info(f"  可训练样本数: {count}")
            
            if count < 100:
                logger.warning(f"  ⚠️  可训练样本数不足100条，无法训练")
                logger.warning(f"  建议：")
                logger.warning(f"    1. 等待更多预测记录的实际结果更新")
                logger.warning(f"    2. 或者先运行预测任务生成更多预测记录")
            elif count < 1000:
                logger.warning(f"  ⚠️  可训练样本数较少（{count}条），建议至少1000+条")
                logger.info(f"  可以使用小规模数据先测试训练")
            else:
                logger.info(f"  ✅ 可训练样本数充足，可以开始训练")
        
        # 4. 检查trained_models表是否存在
        logger.info("\n4. 检查trained_models表...")
        
        sql = "SHOW TABLES LIKE 'trained_models'"
        results = db.execute_query(sql)
        
        if results:
            logger.info(f"  ✅ trained_models表已存在")
            
            # 检查表中是否有数据
            sql = "SELECT COUNT(*) as count FROM trained_models"
            results = db.execute_query(sql)
            if results:
                count = results[0]['count']
                logger.info(f"  已有模型数: {count}")
        else:
            logger.warning(f"  ⚠️  trained_models表不存在，需要创建")
            logger.info(f"  执行: mysql -u root -p stock_data < database/trained_models_table.sql")
        
        logger.info("\n" + "=" * 60)
        logger.info("检查完成")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"检查失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    check_training_data()
