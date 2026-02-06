#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查登录历史表
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection

db = DatabaseConnection()

# 检查表
sql = "SHOW TABLES LIKE 'user_login_history'"
result = db.execute_query(sql)

if result:
    print("表已创建")
    
    # 查看表结构
    sql2 = "DESCRIBE user_login_history"
    fields = db.execute_query(sql2)
    print(f"\n表结构（共 {len(fields)} 个字段）：")
    for f in fields:
        print(f"  {f['Field']:30s} {f['Type']:20s} {f['Null']:5s} {f['Key']:5s}")
    
    # 查看记录数
    sql3 = "SELECT COUNT(*) as cnt FROM user_login_history"
    count = db.execute_query(sql3)
    print(f"\n当前记录数：{count[0]['cnt'] if count else 0}")
else:
    print("表不存在")
