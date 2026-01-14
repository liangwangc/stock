"""
创建 analysis_tasks 表的脚本
如果表不存在，则自动创建
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config_db import DB_CONFIG
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError as e:
    print(f"错误：导入配置失败: {e}")
    sys.exit(1)

def create_analysis_tasks_table():
    """创建 analysis_tasks 表"""
    print("=" * 60)
    print("正在创建 analysis_tasks 表...")
    print("=" * 60)
    
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS `analysis_tasks` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `task_id` VARCHAR(100) NOT NULL COMMENT '任务ID',
            `user_id` INT DEFAULT NULL COMMENT '执行用户ID',
            `username` VARCHAR(50) DEFAULT NULL COMMENT '执行用户名',
            `limit_count` INT DEFAULT NULL COMMENT '分析数量（NULL表示全部）',
            `sort_type` VARCHAR(20) DEFAULT NULL COMMENT '排序方式（turnover/random）',
            `status` VARCHAR(20) DEFAULT NULL COMMENT '任务状态（running/completed/cancelled/failed）',
            `total_stocks` INT DEFAULT 0 COMMENT '总股票数',
            `success_count` INT DEFAULT 0 COMMENT '成功数量',
            `fail_count` INT DEFAULT 0 COMMENT '失败数量',
            `progress` INT DEFAULT 0 COMMENT '当前进度',
            `start_time` DATETIME DEFAULT NULL COMMENT '开始时间',
            `end_time` DATETIME DEFAULT NULL COMMENT '结束时间',
            `duration_seconds` INT DEFAULT NULL COMMENT '耗时（秒）',
            `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            UNIQUE KEY `uk_task_id` (`task_id`),
            INDEX `idx_user_id` (`user_id`),
            INDEX `idx_start_time` (`start_time`),
            INDEX `idx_status` (`status`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票分析任务历史表';
    """
    
    try:
        # 连接数据库
        print(f"正在连接到数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        connection = pymysql.connect(cursorclass=DictCursor, **DB_CONFIG)
        
        with connection.cursor() as cursor:
            print("正在执行 CREATE TABLE 语句...")
            cursor.execute(create_table_sql)
        
        connection.commit()
        connection.close()
        
        print("=" * 60)
        print("✅ analysis_tasks 表创建成功！")
        print("=" * 60)
        return True
        
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower() or 'Duplicate table' in error_msg:
            print("=" * 60)
            print("⚠️  analysis_tasks 表已存在，跳过创建")
            print("=" * 60)
            return True
        else:
            print("=" * 60)
            print(f"❌ 创建表失败: {error_msg}")
            print("=" * 60)
            return False

if __name__ == '__main__':
    success = create_analysis_tasks_table()
    sys.exit(0 if success else 1)
