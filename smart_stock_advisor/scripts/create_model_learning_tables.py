"""
创建模型学习系统数据库表
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def create_tables():
    """创建模型学习系统相关表"""
    db = DatabaseConnection()
    
    sql_file = os.path.join(project_root, "database", "model_learning_tables.sql")
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            create_sql = f.read()
        
        # 分割SQL语句
        statements = []
        current_statement = []
        for line in create_sql.split('\n'):
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
                logger.info(f"成功创建表: {statement[:50]}...")
            except Exception as e:
                error_msg = str(e).lower()
                if "already exists" not in error_msg and "duplicate" not in error_msg:
                    logger.warning(f"创建表时出错: {str(e)}")
        
        logger.info("模型学习系统数据库表创建完成")
        return True
        
    except Exception as e:
        logger.error(f"创建表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("创建模型学习系统数据库表")
    print("=" * 60)
    
    success = create_tables()
    
    if success:
        print("\n[OK] 表创建完成！")
    else:
        print("\n[ERROR] 表创建失败，请查看日志了解详情。")
    
    sys.exit(0 if success else 1)
