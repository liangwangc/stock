"""
创建美股数据库表的脚本
"""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)

def create_us_stock_tables():
    """创建美股相关的数据库表"""
    db = DatabaseConnection()
    sql_file = os.path.join(project_root, "database", "us_stock_tables.sql")

    logger.info("=" * 60)
    logger.info("创建美股数据库表")
    logger.info("=" * 60)

    if not os.path.exists(sql_file):
        logger.error(f"SQL文件不存在: {sql_file}")
        return False

    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            create_sql = f.read()

        # 分割SQL语句（按分号分割，但需要考虑CREATE TABLE语句可能跨多行）
        statements = []
        current_statement = []
        in_comment = False
        
        for line in create_sql.split('\n'):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('--'):
                continue
            
            # 检查多行注释
            if '/*' in line:
                in_comment = True
                continue
            if '*/' in line:
                in_comment = False
                continue
            if in_comment:
                continue
            
            current_statement.append(line)
            
            # 如果行以分号结尾，说明语句结束
            if line.endswith(';'):
                statement = ' '.join(current_statement).rstrip(';').strip()
                if statement:
                    statements.append(statement)
                current_statement = []

        # 执行每个SQL语句
        for statement in statements:
            if not statement:
                continue
            try:
                db.execute_update(statement)
                # 提取表名
                table_name = statement.split('`')[1] if '`' in statement else 'unknown'
                logger.info(f"[OK] 成功创建表: {table_name}")
            except Exception as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                    logger.info(f"[SKIP] 表已存在: {statement.split('`')[1] if '`' in statement else 'unknown'}")
                else:
                    logger.error(f"[ERROR] 创建表失败: {statement[:100]}...")
                    logger.error(f"错误: {error_msg}")
                    return False
        
        logger.info("\n[OK] 美股数据库表创建完成！")
        return True

    except Exception as e:
        logger.error(f"创建美股数据库表失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    if create_us_stock_tables():
        logger.info("\n所有表创建成功！")
    else:
        logger.error("\n表创建失败！")
