import pandas as pd
from impala.dbapi import connect
# from impala.util import as_pandas
from module.db_module import DatabaseClass, DBTable, db_pg_config

def extract_table_data_to_local(sql, save_path):
    print(sql)
    conn = connect(host="11.0.32.193", port=21050)
    cur = conn.cursor()
    # database = cx.connect(user="JGM", password="jgm@123", dsn="11.0.32.116:1521/scwjw")
    
    print("Execute")
    cur.execute(sql)
    df = as_pandas(cur)
    # logging.info("%s, %s" % (birthday, df.shape[0]))
    df.to_csv(save_path)

def extract_table_data_to_local_V2(sql, xy_col, save_path):
    print(sql)
    oralce_db = DatabaseClass()
    oralce_db.oracle_connect()
    oralce_db_table = DBTable(oralce_db.database)
    result = oralce_db_table.query(sql)
    df = pd.DataFrame(result, columns=xy_col)
    df.to_csv(save_path)


# xy_col = """YLFKFS,ZYCS,BAH,XB,CSRQ,NL,ZY,XZZ_XZQH,RYTJ,RYSJ,CYSJ,CYKB,SJZYTS,JBBM1,BWHBZ,ZYZD,JBDM,RYBQ,LYFS,SFZZYJH"""
xy_col = """CT,PETCT,SYCT,BC,XP,CSXDT,MRI,TWSJC"""

for month in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]:
    # sql_2 = """SELECT {} FROM zlk_raw.t_xyba WHERE substr(cysj, 1, 6) = '{}{}'""".format(xy_col, 2023, month)

    sql_2 = """SELECT {} FROM WCL.syoe_xyba_view WHERE substr(cysj, 1, 6) = '{}{}'""".format(xy_col, 2023, month)
    columns = xy_col.split(',')
    extract_table_data_to_local_V2(sql_2, columns, "D:/yuanjun/SuperviserProject/data/ab_normal_1/%s.csv" % ("2023" + month))

    # extract_table_data_to_local(sql_2, "D:/yuanjun/SuperviserProject/data/ab_normal/%s.csv" % ("2023" + month))