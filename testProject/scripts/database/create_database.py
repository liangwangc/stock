#!/usr/bin/env python3
"""
根据 scripts/database/config.py 中的 MySQL 配置，自动创建数据库（如果不存在）。
"""

import os
import sys
import pymysql

# 直接将 scripts/database 加入路径后导入 config
sys.path.insert(0, os.path.dirname(__file__))
import config  # scripts/database/config.py


def create_database_if_not_exists():
    try:
        db_name = config.DatabaseConfig.MYSQL_CONFIG["database"]
        host = config.DatabaseConfig.MYSQL_CONFIG["host"]
        port = config.DatabaseConfig.MYSQL_CONFIG["port"]
        user = config.DatabaseConfig.MYSQL_CONFIG["user"]
        password = config.DatabaseConfig.MYSQL_CONFIG["password"]
        charset = config.DatabaseConfig.MYSQL_CONFIG["charset"]

        print(f"🔧 正在连接到 MySQL 服务器 {host}:{port} ...", flush=True)
        conn = pymysql.connect(host=host, port=port, user=user, password=password, charset=charset, autocommit=True)
        print("✅ 连接成功", flush=True)
        try:
            with conn.cursor() as cur:
                sql = f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4"
                print(f"➡️ 执行: {sql}", flush=True)
                cur.execute(sql)
                print(f"✅ 数据库 `{db_name}` 已确保存在", flush=True)
        finally:
            conn.close()
            print("🔌 已关闭连接", flush=True)
        return True
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}", flush=True)
        import traceback; traceback.print_exc()
        return False


if __name__ == "__main__":
    ok = create_database_if_not_exists()
    if not ok:
        sys.exit(1)
