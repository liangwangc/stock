#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查并添加预测价格字段脚本
如果 stock_predictions 表中缺少 predicted_close_price 和 predicted_change_pct 字段，则自动添加
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def check_and_add_fields():
    """检查并添加预测价格字段"""
    db = None
    try:
        db = DatabaseConnection()
        
        # 检查字段是否存在
        logger.info("检查 stock_predictions 表字段...")
        result = db.execute_query("SHOW COLUMNS FROM stock_predictions")
        existing_columns = [row['Field'] for row in result]
        logger.info(f"当前表字段: {', '.join(existing_columns)}")
        
        # 需要添加的字段
        fields_to_add = [
            {
                'name': 'predicted_close_price',
                'definition': 'DECIMAL(10,2) DEFAULT NULL COMMENT "明日大概收盘价格"',
                'after': 'current_price'
            },
            {
                'name': 'predicted_change_pct',
                'definition': 'DECIMAL(6,2) DEFAULT NULL COMMENT "明日大概涨幅百分比"',
                'after': 'predicted_close_price'
            }
        ]
        
        added_count = 0
        for field in fields_to_add:
            if field['name'] in existing_columns:
                logger.info(f"✅ 字段 {field['name']} 已存在，跳过")
                continue
            
            try:
                sql = f"ALTER TABLE stock_predictions ADD COLUMN `{field['name']}` {field['definition']}"
                if field.get('after'):
                    sql += f" AFTER `{field['after']}`"
                
                db.execute_update(sql)
                logger.info(f"✅ 成功添加字段: {field['name']}")
                added_count += 1
            except Exception as e:
                error_msg = str(e).lower()
                if "duplicate column name" in error_msg or "already exists" in error_msg:
                    logger.info(f"字段 {field['name']} 已存在（通过错误信息判断）")
                else:
                    logger.error(f"❌ 添加字段 {field['name']} 失败: {str(e)}")
                    raise
        
        # 检查并添加索引
        logger.info("检查索引...")
        result = db.execute_query("SHOW INDEXES FROM stock_predictions")
        existing_indexes = [row['Key_name'] for row in result]
        
        if 'idx_predicted_change_pct' not in existing_indexes:
            try:
                db.execute_update("ALTER TABLE stock_predictions ADD INDEX idx_predicted_change_pct (predicted_change_pct)")
                logger.info("✅ 成功添加索引: idx_predicted_change_pct")
            except Exception as e:
                error_msg = str(e).lower()
                if "duplicate key name" in error_msg or "already exists" in error_msg:
                    logger.info("索引 idx_predicted_change_pct 已存在")
                else:
                    logger.warning(f"添加索引失败: {str(e)}")
        else:
            logger.info("✅ 索引 idx_predicted_change_pct 已存在")
        
        if added_count > 0:
            logger.info(f"\n✅ 成功添加 {added_count} 个字段")
        else:
            logger.info("\n✅ 所有字段都已存在，无需添加")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 检查并添加字段失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        if db:
            db.close_connection()


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("检查并添加预测价格字段")
    logger.info("=" * 60)
    
    success = check_and_add_fields()
    
    if success:
        logger.info("\n✅ 检查完成！")
        sys.exit(0)
    else:
        logger.error("\n❌ 检查失败！")
        sys.exit(1)
