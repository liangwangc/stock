#!/usr/bin/env python3
"""
数据库连接示例

展示如何使用配置文件连接不同的数据库
"""

from config import config
import sqlite3
from typing import Optional


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.config = config.DATABASE_CONFIG
        self.connection = None
    
    def connect_sqlite(self) -> sqlite3.Connection:
        """连接SQLite数据库"""
        try:
            # 从配置获取数据库路径
            db_path = self.config.SQLITE_DATABASE_URL.replace("sqlite:///", "")
            self.connection = sqlite3.connect(db_path)
            print(f"✅ 成功连接到SQLite数据库: {db_path}")
            return self.connection
        except Exception as e:
            print(f"❌ 连接SQLite数据库失败: {e}")
            raise
    
    def create_tables(self):
        """创建示例表"""
        if not self.connection:
            self.connect_sqlite()
        
        cursor = self.connection.cursor()
        
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建文章表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        self.connection.commit()
        print("✅ 数据库表创建成功")
    
    def insert_sample_data(self):
        """插入示例数据"""
        if not self.connection:
            self.connect_sqlite()
        
        cursor = self.connection.cursor()
        
        # 插入示例用户
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, email) VALUES (?, ?)
        ''', ("admin", "admin@example.com"))
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, email) VALUES (?, ?)
        ''', ("user1", "user1@example.com"))
        
        # 插入示例文章
        cursor.execute('''
            INSERT OR IGNORE INTO articles (title, content, user_id) VALUES (?, ?, ?)
        ''', ("第一篇文章", "这是第一篇文章的内容", 1))
        
        self.connection.commit()
        print("✅ 示例数据插入成功")
    
    def query_data(self):
        """查询数据示例"""
        if not self.connection:
            self.connect_sqlite()
        
        cursor = self.connection.cursor()
        
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
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("🔒 数据库连接已关闭")


def main():
    """主函数 - 演示数据库操作"""
    print("=" * 50)
    print("数据库连接演示")
    print("=" * 50)
    
    # 显示配置信息
    print(f"数据库类型: {config.DATABASE_CONFIG.DATABASE_TYPE}")
    print(f"数据库URL: {config.DATABASE_CONFIG.get_database_url()}")
    print()
    
    # 创建数据库管理器
    db_manager = DatabaseManager()
    
    try:
        # 连接数据库
        db_manager.connect_sqlite()
        
        # 创建表
        db_manager.create_tables()
        
        # 插入数据
        db_manager.insert_sample_data()
        
        # 查询数据
        db_manager.query_data()
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
    
    finally:
        # 关闭连接
        db_manager.close()
    
    print("=" * 50)
    print("演示完成")
    print("=" * 50)


if __name__ == "__main__":
    main() 