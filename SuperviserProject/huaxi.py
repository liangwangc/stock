import os
import pandas as pd
from tqdm import tqdm

# huaxi_df = pd.read_csv("D:/huaxi.csv", encoding='gbk')
# bah = set(["BAH_%s" % i for i in huaxi_df['病案号'].tolist()])

result_df = pd.DataFrame()
column_list = ['basy_yljgid',  'basy_bah', 'basy_zyzd_jbbm', 'basy_zyzd', 'basy_csrq', 'basy_rysj', 'basy_cysj',  '耗材费', '检查检验费', '药品费', '总费用', 'hospital_id', 
'耗材费_oe', 'level_耗材费_mean', '耗材费_odd_oe', '耗材费_odd_nor_oe', '耗材费_odd', '药品费_oe', 
'level_药品费_mean', '药品费_odd_oe', '药品费_odd_nor_oe', '药品费_odd', '总费用_oe', 'level_总费用_mean', '总费用_odd_oe', '总费用_odd_nor_oe', '总费用_odd', '检查检验费_oe', 'level_检查检验费_mean', '检查检验费_odd_oe', '检查检验费_odd_nor_oe', '检查检验费_odd']
huaxi_id_dict = {'JG_510000000956': '四川大学华西医院', 'JG_510000000942': '四川大学华西第二医院', 
                 'JG_510000000954': '四川大学华西第四医院', 'JG_510000000952': '四川大学华西口腔医院'}
huaxi_id_set = set(list(huaxi_id_dict.keys()))
for file_path in tqdm(os.listdir("D:/yuanjun/SuperviserProject/data/cleaned")):
    if "again" in file_path and ('2023' in file_path or '2024' in file_path):
        print(file_path)
        df = pd.read_csv("D:/yuanjun/SuperviserProject/data/cleaned/" + file_path)
        # print(df.columns.tolist())
        # print(df['basy_yljgid'])
        # exit()
        df = df[df['basy_yljgid'].isin(huaxi_id_set)]
        df = df[column_list]
        result_df = pd.concat([result_df, df])
        print(result_df.shape)

result_df.to_csv('huaxi_oeV1.csv')


