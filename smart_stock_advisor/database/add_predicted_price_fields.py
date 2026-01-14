"""
执行SQL脚本，为 stock_predictions 表添加预测价格和涨幅字段
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)

def execute_sql_script():
    """执行SQL脚本"""
    try:
        db = DatabaseConnection()
        
        sql_file = os.path.join(os.path.dirname(__file__), 'add_predicted_price_fields.sql')
        
        if not os.path.exists(sql_file):
            logger.error(f"SQL文件不存在: {sql_file}")
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句
        statements = []
        current_statement = []
        for line in sql_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            current_statement.append(line)
            if line.endswith(';'):
                statement = ' '.join(current_statement).rstrip(';').strip()
                if statement:
                    statements.append(statement)
                current_statement = []
        
        # 执行所有SQL语句
        for statement in statements:
            if not statement:
                continue
            try:
                db.execute_update(statement)
                logger.info(f"执行SQL成功: {statement[:50]}...")
            except Exception as e:
                error_msg = str(e).lower()
                # 如果字段已存在，忽略错误
                if "duplicate column" in error_msg or "already exists" in error_msg:
                    logger.warning(f"字段可能已存在，跳过: {str(e)}")
                else:
                    logger.error(f"执行SQL失败: {str(e)}")
                    logger.error(f"SQL语句: {statement}")
        
        logger.info("SQL脚本执行完成")
        return True
        
    except Exception as e:
        logger.error(f"执行SQL脚本失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    execute_sql_script()
