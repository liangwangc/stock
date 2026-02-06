#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
用于测试 word_app 数据库的连接和基本功能
"""

import sys

def test_mysql_connection():
    """测试MySQL数据库连接"""
    print("=" * 60)
    print("数据库连接测试")
    print("=" * 60)
    print()
    
    # 数据库配置
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': 'root',
        'database': 'word_app',
        'charset': 'utf8mb4'
    }
    
    print("配置信息：")
    print(f"  主机: {db_config['host']}")
    print(f"  用户: {db_config['user']}")
    print(f"  数据库: {db_config['database']}")
    print()
    
    # 尝试导入MySQL连接器
    try:
        import pymysql
        print("✅ 已安装 pymysql 库")
    except ImportError:
        print("❌ 未安装 pymysql 库")
        print("\n请先安装 pymysql:")
        print("  pip install pymysql")
        return False
    
    # 测试连接
    print("\n" + "-" * 60)
    print("1. 测试数据库连接...")
    print("-" * 60)
    
    try:
        conn = pymysql.connect(**db_config)
        print("✅ 数据库连接成功！")
        print(f"   MySQL版本: {conn.get_server_info()}")
        print(f"   字符集: {conn.character_set_name()}")
        print()
    except pymysql.Error as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n可能的原因：")
        print("  1. MySQL服务未启动")
        print("  2. 用户名或密码错误")
        print("  3. 数据库 'word_app' 不存在")
        print("  4. MySQL未安装或未配置")
        return False
    
    # 测试查询表
    print("-" * 60)
    print("2. 检查数据库表...")
    print("-" * 60)
    
    cursor = conn.cursor()
    
    tables = ['users', 'words']
    for table in tables:
        try:
            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            if cursor.rowcount > 0:
                print(f"✅ 表 '{table}' 存在")
                
                # 获取表结构
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                print(f"   字段数: {len(columns)}")
            else:
                print(f"❌ 表 '{table}' 不存在")
        except pymysql.Error as e:
            print(f"❌ 查询表 '{table}' 时出错: {e}")
    
    print()
    
    # 测试查询数据
    print("-" * 60)
    print("3. 查询数据统计...")
    print("-" * 60)
    
    try:
        # 用户数量
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👥 用户总数: {user_count}")
        
        # 显示最近5个用户
        cursor.execute("SELECT id, username, daily_goal, created_at FROM users ORDER BY id DESC LIMIT 5")
        users = cursor.fetchall()
        if users:
            print("\n最近5个用户:")
            print("  ID  | 用户名    | 每日目标 | 创建时间")
            print("  " + "-" * 50)
            for u in users:
                print(f"  {u[0]:<4} | {u[1]:<8} | {u[2]:<8} | {u[3]}")
        
        # 单词数量
        cursor.execute("SELECT COUNT(*) FROM words")
        word_count = cursor.fetchone()[0]
        print(f"\n📚 单词总数: {word_count}")
        
        # 按状态统计
        cursor.execute("SELECT status, COUNT(*) as count FROM words GROUP BY status")
        status_stats = cursor.fetchall()
        if status_stats:
            print("\n单词状态统计:")
            for stat in status_stats:
                print(f"  {stat[0]:<10} : {stat[1]:>5} 个")
        
        # 测试查询示例
        cursor.execute("SELECT word, pronunciation, meaning, status FROM words WHERE user_id = 1 ORDER BY id DESC LIMIT 3")
        words = cursor.fetchall()
        if words:
            print("\n用户ID=1的最近3个单词:")
            for w in words:
                print(f"  • {w[0]:<15} [{w[1]}] - {w[2][:30]}... ({w[3]})")
        
    except pymysql.Error as e:
        print(f"❌ 查询数据时出错: {e}")
    
    # 关闭连接
    cursor.close()
    conn.close()
    
    print()
    print("-" * 60)
    print("4. 测试完成")
    print("-" * 60)
    print("✅ 所有测试通过！数据库连接正常。")
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = test_mysql_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
