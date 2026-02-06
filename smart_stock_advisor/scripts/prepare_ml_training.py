#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ML模型训练准备脚本
检查数据完整性、创建表、验证环境
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)


def check_dependencies():
    """检查依赖库"""
    logger.info("检查依赖库...")
    
    missing = []
    
    try:
        import sklearn
        logger.info("  [OK] scikit-learn")
    except ImportError:
        logger.warning("  [X] scikit-learn 未安装")
        missing.append("scikit-learn")
    
    try:
        import xgboost
        logger.info("  [OK] xgboost")
    except ImportError:
        logger.warning("  [X] xgboost 未安装")
        missing.append("xgboost")
    
    try:
        import lightgbm
        logger.info("  [OK] lightgbm")
    except ImportError:
        logger.warning("  [X] lightgbm 未安装")
        missing.append("lightgbm")
    
    try:
        import pandas
        logger.info("  [OK] pandas")
    except ImportError:
        logger.warning("  [X] pandas 未安装")
        missing.append("pandas")
    
    try:
        import numpy
        logger.info("  [OK] numpy")
    except ImportError:
        logger.warning("  ❌ numpy 未安装")
        missing.append("numpy")
    
    if missing:
        logger.warning(f"\n需要安装以下库: pip install {' '.join(missing)}")
        return False
    
    logger.info("  [OK] 所有依赖库已安装")
    return True


def create_table():
    """创建trained_models表"""
    try:
        db = DatabaseConnection()
        
        logger.info("\n检查trained_models表...")
        
        # 检查表是否存在
        check_sql = "SHOW TABLES LIKE 'trained_models'"
        results = db.execute_query(check_sql)
        
        if results:
            logger.info("  [OK] trained_models表已存在")
            return True
        
        logger.info("  创建trained_models表...")
        
        # 读取SQL文件
        sql_file = os.path.join(project_root, 'database', 'trained_models_table.sql')
        
        if not os.path.exists(sql_file):
            logger.error(f"  [X] SQL文件不存在: {sql_file}")
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        # 执行SQL
        db.execute_update(sql)
        
        logger.info("  [OK] trained_models表创建成功")
        return True
        
    except Exception as e:
        logger.error(f"  创建表失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def check_data():
    """检查数据完整性"""
    try:
        db = DatabaseConnection()
        
        logger.info("\n检查训练数据...")
        
        # 1. 检查stock_predictions表
        sql = """
            SELECT 
                COUNT(*) as total_count,
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
            total = result['total_count']
            valid = result['valid_count']
            earliest = result['earliest_date']
            latest = result['latest_date']
            
            logger.info(f"  总预测记录: {total}")
            logger.info(f"  有效记录（有实际结果）: {valid}")
            logger.info(f"  日期范围: {earliest} 到 {latest}")
            
            if valid < 100:
                logger.warning(f"  [WARN] 有效记录不足100条，建议至少1000+条")
                return False
            elif valid < 1000:
                logger.warning(f"  [WARN] 有效记录较少（{valid}条），可以使用小规模数据测试")
            else:
                logger.info(f"  [OK] 有效记录充足（{valid}条）")
        
        # 2. 检查stock_history_data表
        sql = """
            SELECT 
                COUNT(*) as total_count,
                COUNT(DISTINCT symbol) as stock_count,
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date
            FROM stock_history_data
            WHERE period_type = 'daily'
        """
        
        results = db.execute_query(sql)
        if results:
            result = results[0]
            total = result['total_count']
            stock_count = result['stock_count']
            earliest = result['earliest_date']
            latest = result['latest_date']
            
            logger.info(f"  历史数据记录: {total}")
            logger.info(f"  股票数量: {stock_count}")
            logger.info(f"  日期范围: {earliest} 到 {latest}")
            
            if total < 10000:
                logger.warning(f"  [WARN] 历史数据量较少")
            else:
                logger.info(f"  [OK] 历史数据量充足")
        
        # 3. 检查可训练样本数
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
                  LIMIT 1
              )
        """
        
        results = db.execute_query(sql)
        if results:
            count = results[0]['count']
            logger.info(f"  可训练样本数: {count}")
            
            if count < 100:
                logger.warning(f"  [WARN] 可训练样本不足100条")
                return False
            elif count < 1000:
                logger.warning(f"  [WARN] 可训练样本较少（{count}条），建议至少1000+条")
            else:
                logger.info(f"  [OK] 可训练样本充足（{count}条）")
        
        return True
        
    except Exception as e:
        logger.error(f"检查数据失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("ML模型训练准备检查")
    logger.info("=" * 60)
    
    all_ok = True
    
    # 1. 检查依赖库
    if not check_dependencies():
        all_ok = False
    
    # 2. 创建表
    if not create_table():
        all_ok = False
    
    # 3. 检查数据
    if not check_data():
        all_ok = False
    
    logger.info("\n" + "=" * 60)
    if all_ok:
        logger.info("[OK] 准备完成，可以开始训练模型")
        logger.info("\n开始训练:")
        logger.info("  python scripts/train_ml_models.py --models xgb_classifier")
    else:
        logger.warning("[WARN] 部分检查未通过，请根据上述提示解决问题")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
