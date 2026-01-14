"""
为stock_predictions表添加行业、板块等字段
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def check_and_add_fields():
    """检查并添加字段"""
    db = DatabaseConnection()
    
    try:
        # 检查表是否存在
        try:
            db.execute_query("SELECT 1 FROM stock_predictions LIMIT 1")
            logger.info("stock_predictions表存在")
        except Exception as e:
            logger.error(f"stock_predictions表不存在: {str(e)}")
            return False
        
        # 检查字段是否存在并添加
        fields_to_add = [
            {
                'name': 'industry',
                'definition': "VARCHAR(100) DEFAULT NULL COMMENT '所属行业'",
                'after': 'name'
            },
            {
                'name': 'concepts',
                'definition': "TEXT DEFAULT NULL COMMENT '概念板块（JSON数组格式）'",
                'after': 'industry'
            },
            {
                'name': 'main_concept',
                'definition': "VARCHAR(100) DEFAULT NULL COMMENT '主要概念板块'",
                'after': 'concepts'
            },
            {
                'name': 'market',
                'definition': "VARCHAR(20) DEFAULT 'A股' COMMENT '所属市场（A股/港股/美股）'",
                'after': 'main_concept'
            }
        ]
        
        # 检查每个字段是否存在
        existing_columns = []
        try:
            result = db.execute_query("SHOW COLUMNS FROM stock_predictions")
            existing_columns = [row['Field'] for row in result]
            logger.info(f"当前表字段: {', '.join(existing_columns)}")
        except Exception as e:
            logger.warning(f"无法获取字段列表: {str(e)}")
        
        added_count = 0
        for field in fields_to_add:
            if field['name'] in existing_columns:
                logger.info(f"字段 {field['name']} 已存在，跳过")
                continue
            
            try:
                sql = f"ALTER TABLE stock_predictions ADD COLUMN `{field['name']}` {field['definition']}"
                if field.get('after'):
                    sql += f" AFTER `{field['after']}`"
                
                db.execute_update(sql)
                logger.info(f"[OK] 成功添加字段: {field['name']}")
                added_count += 1
            except Exception as e:
                error_msg = str(e).lower()
                if "duplicate column name" in error_msg or "already exists" in error_msg:
                    logger.info(f"字段 {field['name']} 已存在（通过错误信息判断）")
                else:
                    logger.warning(f"添加字段 {field['name']} 失败: {str(e)}")
        
        # 添加索引
        indexes_to_add = [
            ('idx_industry', 'industry'),
            ('idx_main_concept', 'main_concept'),
            ('idx_market', 'market')
        ]
        
        # 检查现有索引
        existing_indexes = []
        try:
            result = db.execute_query("SHOW INDEXES FROM stock_predictions")
            existing_indexes = [row['Key_name'] for row in result]
        except Exception as e:
            logger.warning(f"无法获取索引列表: {str(e)}")
        
        for index_name, column_name in indexes_to_add:
            if index_name in existing_indexes:
                logger.info(f"索引 {index_name} 已存在，跳过")
                continue
            
            # 先检查字段是否存在
            if column_name not in existing_columns:
                logger.warning(f"字段 {column_name} 不存在，无法创建索引 {index_name}")
                continue
            
            try:
                sql = f"ALTER TABLE stock_predictions ADD INDEX `{index_name}` (`{column_name}`)"
                db.execute_update(sql)
                logger.info(f"[OK] 成功添加索引: {index_name} on {column_name}")
            except Exception as e:
                error_msg = str(e).lower()
                if "duplicate key name" in error_msg or "already exists" in error_msg:
                    logger.info(f"索引 {index_name} 已存在（通过错误信息判断）")
                else:
                    logger.warning(f"添加索引 {index_name} 失败: {str(e)}")
        
        logger.info(f"\n完成！共添加 {added_count} 个新字段")
        return True
        
    except Exception as e:
        logger.error(f"检查并添加字段失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("为stock_predictions表添加行业、板块字段")
    print("=" * 60)
    
    success = check_and_add_fields()
    
    if success:
        print("\n[OK] 字段添加完成！")
    else:
        print("\n[ERROR] 字段添加失败，请查看日志了解详情。")
    
    sys.exit(0 if success else 1)
