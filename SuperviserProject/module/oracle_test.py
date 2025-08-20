import oracledb
import getpass
# cx.connect(user="JGM", password="jgm@123", dsn="11.0.32.116:1521/scwjw")
oracledb.init_oracle_client(lib_dir=r"D:\yuanjun\oracle_dll")
connection = oracledb.connect(user="JGM", password='jgm@123',
                              dsn="11.0.32.116:1521/scwjw")

print(connection)
connection.close()



# import cx_Oracle as cx
# database = cx.connect(user="JGM", password="jgm@123", dsn="11.0.32.116:1521/scwjw")
# print(database)
