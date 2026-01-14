#!/usr/bin/env python3
"""
验证本地 MySQL 连接、数据库和表是否存在，以及默认管理员账号 admin 是否存在。
"""

import os
import sys

# 将 scripts/database 加入路径，导入 config
sys.path.insert(0, os.path.dirname(__file__))
import config  # scripts/database/config.py

import pymysql

def main():
    try:
        cfg = config.DatabaseConfig.MYSQL_CONFIG
        print(f"准备连接: host={cfg['host']} port={cfg['port']} user={cfg['user']} db={cfg['database']}", flush=True)
        conn = pymysql.connect(
            host=cfg['host'], port=cfg['port'], user=cfg['user'], password=cfg['password'],
            database=cfg['database'], charset=cfg['charset'], autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ 数据库连接成功", flush=True)
        try:
            with conn.cursor() as cur:
                print("检查现有表...", flush=True)
                cur.execute("SHOW TABLES")
                rows = cur.fetchall()
                tables = [list(row.values())[0] for row in rows]
                print(f"当前表数量: {len(tables)} -> {tables}", flush=True)
                required = {"users","departments","file_categories","audit_files","audit_logs","notifications"}
                missing = sorted(list(required - set(tables)))
                if missing:
                    print(f"❌ 缺失表: {', '.join(missing)}", flush=True)
                else:
                    print("✅ 所有关键表已存在", flush=True)

                print("检查默认管理员 admin ...", flush=True)
                cur.execute("SELECT id, username, role, status FROM users WHERE username=%s", ("admin",))
                admin = cur.fetchone()
                if admin:
                    print(f"✅ 默认管理员存在: id={admin['id']}, role={admin['role']}, status={admin['status']}", flush=True)
                else:
                    print("❌ 未找到默认管理员 admin", flush=True)
        finally:
            conn.close()
            print("🔌 已关闭连接", flush=True)
    except Exception as e:
        print(f"❌ 校验失败: {e}", flush=True)
        import traceback; traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
