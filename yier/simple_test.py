# -*- coding: utf-8 -*-
import sys
print("Python版本:", sys.version)
print("开始测试数据库连接...")

try:
    import pymysql
    print("✅ pymysql 已导入")
    
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='root',
        database='word_app',
        charset='utf8mb4'
    )
    print("✅ 数据库连接成功！")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"✅ 用户数量: {count}")
    
    cursor.close()
    conn.close()
    print("✅ 测试完成，数据库连接正常！")
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请安装: pip install pymysql")
except Exception as e:
    print(f"❌ 连接错误: {e}")
    print("\n可能的原因：")
    print("1. MySQL服务未启动")
    print("2. 用户名或密码错误（当前: root/root）")
    print("3. 数据库 'word_app' 不存在")
    print("4. MySQL未安装")
