#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

time: 2022-05-05
description:
    从大数据平台的t_basy提取最新（按照出院时间）的 basy_yljgid, basy_caption, basy_dept_class, basy_dept_adrresscode, basy_yydj
    从大数据平台的t_xyba、t_zyba提取所需时间区间的数据，数据清洗后保存至./data/cleaned/

"""

import sys
import logging
import pandas as pd
import numpy as np
import cx_Oracle as cx

database = cx.connect(user="JGM", password="jgm@123", dsn="11.0.32.116:1521/scwjw")
# cr = database.cursor()

sql = "SELECT * FROM WCL.syoe_xyba_view where rownum=100"

df = pd.read_sql(sql, database)
print(df.shape)
df.to_csv("wcj.csv")
print(df)
