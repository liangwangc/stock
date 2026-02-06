"""
初始化财联社新闻数据库
创建数据库和表结构
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine, text
from src.config.config import DB_CONFIG, MAIN_DB_CONFIG

def init_database():
    """初始化数据库"""
    print("=" * 80)
    print("初始化财联社新闻数据库")
    print("=" * 80)
    
    # 使用财联社数据库配置来创建数据库
    try:
        import pymysql
        
        # 连接到MySQL服务器（不指定数据库，使用DB_CONFIG的端口）
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port'],
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # 1. 创建数据库
        print("\n1. 创建数据库 cls_news_db...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS `cls_news_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print("   [成功] 数据库创建完成")
        
        # 2. 选择数据库
        cursor.execute("USE `cls_news_db`")
        
        # 3. 创建news表
        print("\n2. 创建news表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `news` (
               `id` int unsigned NOT NULL AUTO_INCREMENT,
               `title` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
               `content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
               `publish_date` date DEFAULT NULL,
               `publish_time` time DEFAULT NULL,
               `content_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
               `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
               PRIMARY KEY (`id`),
               UNIQUE KEY `hash` (`content_hash`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("   [成功] news表创建完成")
        
        # 4. 创建analysis_results表
        print("\n3. 创建analysis_results表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `analysis_results` (
               `id` int NOT NULL AUTO_INCREMENT,
               `news_index` int DEFAULT NULL,
               `date` date DEFAULT NULL,
               `category` text,
               `subcategory` text,
               `is_market_relevant` int DEFAULT NULL,
               `keywords` text,
               `sentiment` float DEFAULT NULL,
               `impact_markets` text,
               `summary` text,
               PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("   [成功] analysis_results表创建完成")
        
        # 5. 创建processed_hashes表
        print("\n4. 创建processed_hashes表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `processed_hashes` (
               `id` int unsigned NOT NULL AUTO_INCREMENT,
               `hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
               `processed_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
               PRIMARY KEY (`id`,`hash`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("   [成功] processed_hashes表创建完成")
        
        # 6. 创建summary表
        print("\n5. 创建summary表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `summary` (
               `id` int unsigned NOT NULL AUTO_INCREMENT,
               `date` date DEFAULT NULL,
               `category` text,
               `summary` text,
               PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("   [成功] summary表创建完成")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # 7. 执行扩展脚本添加股票关联字段
        print("\n6. 添加股票关联字段...")
        # 重新连接到cls_news_db数据库（使用DB_CONFIG的端口）
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port'],
            database='cls_news_db',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        try:
            # 添加symbol字段
            try:
                cursor.execute("ALTER TABLE `news` ADD COLUMN `symbol` VARCHAR(10) DEFAULT NULL COMMENT '关联股票代码'")
                print("   [成功] 添加symbol字段")
            except Exception as e:
                if "Duplicate column name" in str(e) or "1060" in str(e):
                    print("   [跳过] symbol字段已存在")
                else:
                    raise
            
            # 添加sector字段
            try:
                cursor.execute("ALTER TABLE `news` ADD COLUMN `sector` VARCHAR(100) DEFAULT NULL COMMENT '关联板块'")
                print("   [成功] 添加sector字段")
            except Exception as e:
                if "Duplicate column name" in str(e) or "1060" in str(e):
                    print("   [跳过] sector字段已存在")
                else:
                    raise
            
            # 添加industry字段
            try:
                cursor.execute("ALTER TABLE `news` ADD COLUMN `industry` VARCHAR(100) DEFAULT NULL COMMENT '关联行业'")
                print("   [成功] 添加industry字段")
            except Exception as e:
                if "Duplicate column name" in str(e) or "1060" in str(e):
                    print("   [跳过] industry字段已存在")
                else:
                    raise
            
            # 添加concept字段
            try:
                cursor.execute("ALTER TABLE `news` ADD COLUMN `concept` VARCHAR(200) DEFAULT NULL COMMENT '关联概念'")
                print("   [成功] 添加concept字段")
            except Exception as e:
                if "Duplicate column name" in str(e) or "1060" in str(e):
                    print("   [跳过] concept字段已存在")
                else:
                    raise
            
            # 添加source字段
            try:
                cursor.execute("ALTER TABLE `news` ADD COLUMN `source` VARCHAR(50) DEFAULT '财联社' COMMENT '新闻来源'")
                print("   [成功] 添加source字段")
            except Exception as e:
                if "Duplicate column name" in str(e) or "1060" in str(e):
                    print("   [跳过] source字段已存在")
                else:
                    raise
            
            # 添加source_url字段
            try:
                cursor.execute("ALTER TABLE `news` ADD COLUMN `source_url` VARCHAR(1000) DEFAULT NULL COMMENT '新闻URL'")
                print("   [成功] 添加source_url字段")
            except Exception as e:
                if "Duplicate column name" in str(e) or "1060" in str(e):
                    print("   [跳过] source_url字段已存在")
                else:
                    raise
            
            # 添加索引
            try:
                cursor.execute("ALTER TABLE `news` ADD INDEX `idx_symbol` (`symbol`)")
                print("   [成功] 添加idx_symbol索引")
            except Exception as e:
                if "Duplicate key name" in str(e) or "1061" in str(e):
                    print("   [跳过] idx_symbol索引已存在")
                else:
                    raise
            
            try:
                cursor.execute("ALTER TABLE `news` ADD INDEX `idx_sector` (`sector`)")
                print("   [成功] 添加idx_sector索引")
            except Exception as e:
                if "Duplicate key name" in str(e) or "1061" in str(e):
                    print("   [跳过] idx_sector索引已存在")
                else:
                    raise
            
            try:
                cursor.execute("ALTER TABLE `news` ADD INDEX `idx_industry` (`industry`)")
                print("   [成功] 添加idx_industry索引")
            except Exception as e:
                if "Duplicate key name" in str(e) or "1061" in str(e):
                    print("   [跳过] idx_industry索引已存在")
                else:
                    raise
            
            # 创建news_stock_relation表
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS `news_stock_relation` (
                       `id` int unsigned NOT NULL AUTO_INCREMENT,
                       `news_id` int unsigned NOT NULL COMMENT '新闻ID',
                       `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
                       `relevance_score` DECIMAL(5,4) DEFAULT 1.0 COMMENT '相关性得分（0-1）',
                       `relation_type` VARCHAR(20) DEFAULT 'direct' COMMENT '关联类型（direct/industry/market）',
                       `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
                       PRIMARY KEY (`id`),
                       UNIQUE KEY `uk_news_symbol` (`news_id`, `symbol`),
                       INDEX `idx_symbol` (`symbol`),
                       INDEX `idx_news_id` (`news_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻股票关联表'
                """)
                print("   [成功] 创建news_stock_relation表")
            except Exception as e:
                if "already exists" in str(e).lower() or "1050" in str(e):
                    print("   [跳过] news_stock_relation表已存在")
                else:
                    raise
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            cursor.close()
            conn.close()
            raise
        
        print("\n" + "=" * 80)
        print("[成功] 数据库初始化完成！")
        print("=" * 80)
        print("\n现在可以运行测试：")
        print("  py test_get_news_once.py")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n[失败] 数据库初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
