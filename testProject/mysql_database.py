#!/usr/bin/env python3
"""
MySQL数据库连接示例

使用你的MySQL配置进行数据库操作
"""

import pymysql
from config import config
from typing import List, Dict, Any


class MySQLDatabaseManager:
    """MySQL数据库管理器"""
    
    def __init__(self):
        self.config = config.DATABASE_CONFIG
        self.connection = None
    
    def connect(self) -> pymysql.Connection:
        """连接到MySQL数据库"""
        try:
            self.connection = pymysql.connect(
                host=self.config.MYSQL_CONFIG["host"],
                port=self.config.MYSQL_CONFIG["port"],
                user=self.config.MYSQL_CONFIG["user"],
                password=self.config.MYSQL_CONFIG["password"],
                database=self.config.MYSQL_CONFIG["database"],
                charset=self.config.MYSQL_CONFIG["charset"],
                autocommit=True
            )
            print(f"✅ 成功连接到MySQL数据库: {self.config.MYSQL_CONFIG['host']}:{self.config.MYSQL_CONFIG['port']}")
            print(f"📊 数据库: {self.config.MYSQL_CONFIG['database']}")
            return self.connection
        except Exception as e:
            print(f"❌ 连接MySQL数据库失败: {e}")
            raise
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                print(f"🐬 MySQL版本: {version[0]}")
                return True
        except Exception as e:
            print(f"❌ 连接测试失败: {e}")
            return False
    
    def show_tables(self) -> List[str]:
        """显示所有表"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]
                print(f"📋 数据库中的表: {tables}")
                return tables
        except Exception as e:
            print(f"❌ 获取表列表失败: {e}")
            return []
    
    def create_sample_table(self):
        """创建示例表"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                # 创建用户表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                ''')
                
                # 创建文章表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS articles (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(200) NOT NULL,
                        content TEXT,
                        user_id INT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                ''')
            
            print("✅ 示例表创建成功")
        except Exception as e:
            print(f"❌ 创建表失败: {e}")
    
    def insert_sample_data(self):
        """插入示例数据"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                # 插入用户
                cursor.execute('''
                    INSERT IGNORE INTO users (username, email) VALUES (%s, %s)
                ''', ("admin", "admin@example.com"))
                
                cursor.execute('''
                    INSERT IGNORE INTO users (username, email) VALUES (%s, %s)
                ''', ("user1", "user1@example.com"))
                
                # 插入文章
                cursor.execute('''
                    INSERT IGNORE INTO articles (title, content, user_id) VALUES (%s, %s, %s)
                ''', ("第一篇文章", "这是第一篇文章的内容", 1))
            
            print("✅ 示例数据插入成功")
        except Exception as e:
            print(f"❌ 插入数据失败: {e}")
    
    def query_data(self):
        """查询数据示例"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor() as cursor:
                # 查询用户和文章
                cursor.execute('''
                    SELECT u.username, a.title, a.created_at
                    FROM users u
                    LEFT JOIN articles a ON u.id = a.user_id
                    ORDER BY a.created_at DESC
                ''')
                
                results = cursor.fetchall()
                print("\n📊 查询结果:")
                for row in results:
                    print(f"用户: {row[0]}, 文章: {row[1]}, 时间: {row[2]}")
        except Exception as e:
            print(f"❌ 查询数据失败: {e}")
    
    def execute_custom_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行自定义查询"""
        try:
            if not self.connection:
                self.connect()
            
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                return results
        except Exception as e:
            print(f"❌ 执行查询失败: {e}")
            return []
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("🔒 MySQL数据库连接已关闭")


def main():
    """主函数 - 演示MySQL数据库操作"""
    print("=" * 60)
    print("MySQL数据库连接演示")
    print("=" * 60)
    
    # 显示配置信息
    print(f"数据库类型: {config.DATABASE_CONFIG.DATABASE_TYPE}")
    print(f"数据库主机: {config.DATABASE_CONFIG.MYSQL_CONFIG['host']}")
    print(f"数据库端口: {config.DATABASE_CONFIG.MYSQL_CONFIG['port']}")
    print(f"数据库名称: {config.DATABASE_CONFIG.MYSQL_CONFIG['database']}")
    print(f"用户名: {config.DATABASE_CONFIG.MYSQL_CONFIG['user']}")
    print()
    
    # 创建数据库管理器
    db_manager = MySQLDatabaseManager()
    
    try:
        # 测试连接
        if db_manager.test_connection():
            # 显示现有表
            db_manager.show_tables()
            
            # 创建示例表
            db_manager.create_sample_table()
            
            # 插入数据
            db_manager.insert_sample_data()
            
            # 查询数据
            db_manager.query_data()
            
            # 执行自定义查询示例
            print("\n🔍 执行自定义查询:")
            results = db_manager.execute_custom_query("SELECT COUNT(*) as user_count FROM users")
            if results:
                print(f"用户总数: {results[0]['user_count']}")
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
    
    finally:
        # 关闭连接
        db_manager.close()
    
    print("=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main() 