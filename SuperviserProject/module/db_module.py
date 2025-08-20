#!/usr/bin/python
# -*- coding: utf-8 -*-

from impala.dbapi import connect
import cx_Oracle as cx
import psycopg2
import pandas as pd

db_impala_config = {
    'host': '11.0.32.193',
    'port': 21050,
    'user': 'hdfs',
    'password': '',
    'db_name': 'zlk',
    'charset': 'utf8'
}

db_pg_config = {
    'host': '11.0.32.133',
    'port': 5432,
    'user': 'gpadmin',
    'password': 'cdslyk912',
    'db_name': 'cis',
    'charset': 'utf8'
}


class DatabaseClass:
    """数据库链接"""
    def __init__(self,
                 host=db_impala_config['host'],
                 port=db_impala_config['port'],
                 user=db_impala_config['user'],
                 password=db_impala_config['password'],
                 db_name=db_impala_config['db_name']
                 ):
        self.database = None
        self.connected = False
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name

    def connect(self):
        # 创建链接
        self.connected = False
        try:
            self.database = connect(
                host=self.host, port=self.port, database=self.db_name)
            self.connected = True
        except Exception as error:
            print('connect database failed!', error)
        return self.connected

    def oracle_connect(self):
        try:
            oracledb.init_oracle_client(lib_dir=r"D:\yuanjun\oracle_dll")
            self.database = oracledb.connect(user="JGM", password='jgm@123', dsn="11.0.32.116:1521/scwjw")
            # self.database = cx.connect(user="JGM", password="jgm@123", dsn="11.0.32.116:1521/scwjw")
            self.connected = True
        except Exception as error:
            print('connect database failed!', error)
        return self.connected

    def pg_connect(self):
        # pg
        self.connected = False
        try:
            self.database = psycopg2.connect(
                host=db_pg_config["host"], port=db_pg_config["port"], database=db_pg_config["db_name"], 
                user=db_pg_config["user"], password=db_pg_config["password"])
            self.connected = True
        except Exception as error:
            print('connect database failed!', error)
        return self.connected

    def close(self):
        if self.database is not None:
            self.database.close()
            self.database = None


class DBTable:
    """数据表操作"""
    def __init__(self, database):
        self.database = database
        self.cursor = database.cursor()
        self.tableName = None

    def query(self, sql, size=0):
        try:
            self.cursor.execute(sql)
            if size == 0:
                return self.cursor.fetchall()
            elif size == 1:
                return self.cursor.fetchone()
            else:
                return self.cursor.fetchmany(size)
        except Exception as error:
            print('failed!', error)

    def update(self, sql):
        try:
            self.cursor.execute(sql)
            self.database.commit()
        except Exception as error:
            print('failed!...', error)
            self.database.rollback()

    def get_columns(self, sql):
        try:
            self.cursor.execute(sql)
            columns = []
            for i in range(0, len(self.cursor.description)):
                columns.append(self.cursor.description[i][0])
            return columns
        except Exception as error:
            print('failed!', error)

    def close(self):
        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None


if __name__ == "__main__":
    db = DatabaseClass()
    if db.connect():
        print('database ok................')
        get_info_impala = DBTable(db.database)
        # get_info_impala_sql = """
        #     SELECT bah, csrq, sfzh, rysj, cysj, yljgid, jbdm, zfy, zzys, zzys_sfzh
        #     FROM zlk_raw.t_xyba"""
        # # get_info_impala_sql = """
        # #     SELECT bah, csrq, sfzh, rysj, cysj, yljgid, ZYZD_JBBM, zfy, zzys, zzys_sfzh
        # #     FROM zlk_raw.t_zyba"""
        # print(get_info_impala_sql)
        # result = get_info_impala.query(get_info_impala_sql)
        # df = pd.DataFrame(result, columns=['basy_bah', 'basy_csrq', 'basy_sfzh_md5', 'basy_rysj', 'basy_cysj',
        #                                    'basy_yljgid', 'basy_zyzd_jbbm', 'basy_zfy', 'zzys', 'zzys_sfzh'])
        #
        # df['basy_yljgid'] = 'JG_' + df['basy_yljgid']
        # df['basy_bah'] = 'BAH_' + df['basy_bah']
        #
        # df.to_csv('../data/other/t_xyba.csv')
        sql1 = """SELECT
                    t1.bah, t1.yljgid, t1.sfzh, t1.xb, t1.rysj, t1.cysj, t1.zfy, t1.zyzd, t1.jbdm
                FROM zlk_raw.t_xyba as t1
                WHERE LENGTH(cysj) = 8 LIMIT 10
                UNION all
                SELECT
                    t2.bah, t2.yljgid, t2.sfzh, t2.xb, t2.rysj, t2.cysj, t2.zfy, t2.zyzd, t2.zyzd_jbbm
                FROM zlk_raw.t_zyba as t2
                WHERE LENGTH(cysj) = 8 LIMIT 10"""
        result = get_info_impala.query(sql1)
        df = pd.DataFrame(result, columns=['bah', 'yljgid', 'sfzh', 'xb', 'rysj',
                                           'cysj', 'zfy',
                                           'zyzd', 'jbdm'])
        df.to_csv('../data/report/t_basy_2022_TEST.csv')
