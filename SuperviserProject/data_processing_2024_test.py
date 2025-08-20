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
from module.db_module import DatabaseClass, DBTable, db_pg_config

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s  %(levelname)s  %(message)s')


class DataProcessing:

    def __init__(self, year, month, get_hos_info_in_year=2023):
        """

        :param year: 数据年份
        :param month: 数据月份
        """
        self.year = year
        self.month = month
        self.get_hos_info_in_year = get_hos_info_in_year

    def get_data(self):
        """
        从病案首页提取所需数据
        从大数据平台的t_basy提取最新（按照出院时间）的医院信息。
        用出院时间（basy_cysj）选择时间区间
        保存至./data/original/
        :return:
        """

        # db = DatabaseClass()
        # db.pg_connect()
        # db_table = DBTable(db.database)
        
        # t_basy提取最新（按照出院时间）的医院信息
        # logging.info(f"医院信息，提取{self.get_hos_info_in_year}年的数据")
        # sql_1 = """
                # SELECT t2.basy_yljgid, t2.basy_caption, t2.basy_dept_adrresscode, t2.basy_yydj
                # FROM (
                    # SELECT basy_yljgid, MAX(basy_cysj) as basy_cysj
                    # FROM t_basy
                    # WHERE basy_nian = '{}'
                    # GROUP BY basy_yljgid) as t1
                # INNER JOIN t_basy as t2
                # ON t1.basy_yljgid = t2.basy_yljgid AND t1.basy_cysj = t2.basy_cysj
                # WHERE t2.basy_nian = '{}'
                # """.format(self.get_hos_info_in_year, self.get_hos_info_in_year)
        # result_1 = db_table.query(sql_1)
        # df_1 = pd.DataFrame(result_1, columns=['basy_yljgid', 'basy_caption', 'basy_dept_adrresscode', 'basy_yydj'])
        # df_1.drop_duplicates(subset=['basy_yljgid'], inplace=True)
        # df_1['basy_yydj'] = df_1['basy_yydj'].fillna(value='未评级未评等')
        # df_1['basy_yydj'] = df_1['basy_yydj'].replace('', '未评级未评等')
        # df_1['basy_yydj'] = df_1['basy_yydj'].apply(
            # lambda x: '一级未评等' if ('一' in x) and ('未' in x or '等' not in x) else (
                # '二级未评等' if ('二' in x) and ('未' in x) else (
                    # '三级未评等' if ('三' in x) and ('未' in x) else (
                        # '未评甲等' if ('甲' in x) and ('未' in x) else (
                            # '未评乙等' if ('乙' in x) and ('未' in x) else (
                                # '未评丙等' if ('丙' in x) and ('未' in x) else (
                                    # '未评级未评等' if '未' in x else x)))))))
        # df_1['basy_yljgid'] = 'JG_' + df_1['basy_yljgid']
        
        # df_1.to_csv("data/original/hospital_info_V1.csv")
        # logging.info(f"保存数据，共计{df_1.shape[0]}条，"
                     # f"保存至./data/original/hospital_info.csv")
        # exit()
        df_1 = pd.read_csv("data/original/hospital_info_V1.csv")
        
        oralce_db = DatabaseClass()
        oralce_db.oracle_connect()
        oralce_db_table = DBTable(oralce_db.database)

        logging.info(f"提取数据，提取{self.year}{self.month}的数据")
        # 西医病案
        # 主治医生zzys 改为 主诊医生zznys
        xy_col = """
                    sfzh, yljgid, bah, xb, csrq, rysj, cysj, cykb, rykb, sjzyts, zycs,
                    zyzd, jbdm, qtzd1, jbdm1, qtzd2, jbdm2, qtzd3, jbdm3, qtzd4, jbdm4, qtzd5, jbdm5, qtzd6, jbdm6,
                    qtzd7, jbdm7, qtzd8, jbdm8, qtzd9, jbdm9, qtzd10, jbdm10, qtzd11, jbdm11, qtzd12, jbdm12,
                    qtzd13, jbdm13, qtzd14, jbdm14, qtzd15, jbdm15,
                    ssjczbm1, ssjb1, ssjczmc1, ssjczbm2, ssjb2, ssjczmc2, ssjczbm3, ssjb3, ssjczmc3,
                    ssjczbm4, ssjb4, ssjczmc4, ssjczbm5, ssjb5, ssjczmc5, ssjczbm6, ssjb6, ssjczmc6,
                    ssjczbm7, ssjb7, ssjczmc7,
                    zfy, blzdf, syszdf, yxxzdf, lczdxmf, 
                    xyf, zcyf, zcyf1,
                    hcyyclf, yyclf, ycxyyclf,
                    ssf,
                    zznys, zznys_sfzh
                    """
        sql_2 = """
                SELECT {} FROM WCL.syoe_xyba_view_n WHERE substr(cysj, 1, 6) = '{}{}'
                """.format(xy_col, self.year, self.month)
        # sql_2 = """
                # SELECT {} FROM WCL.xyba_syb_n WHERE substr(cysj, 1, 6) = '{}{}'
                # """.format(xy_col, self.year, self.month)
        result_2 = oralce_db_table.query(sql_2)
        xy_names = ['basy_sfzh_md5', 'basy_yljgid', 'basy_bah', 'basy_xb', 'basy_csrq', 'basy_rysj', 'basy_cysj',
                    'basy_cykb', 'basy_rykb', 'basy_sjzy', 'basy_zycs',
                    'basy_zyzd', 'basy_zyzd_jbbm',
                    'basy_qtzd1', 'basy_zyzd_jbbm1', 'basy_qtzd2', 'basy_zyzd_jbbm2', 'basy_qtzd3', 'basy_zyzd_jbbm3',
                    'basy_qtzd4', 'basy_zyzd_jbbm4', 'basy_qtzd5', 'basy_zyzd_jbbm5', 'basy_qtzd6', 'basy_zyzd_jbbm6',
                    'basy_qtzd7', 'basy_zyzd_jbbm7', 'basy_qtzd8', 'basy_zyzd_jbbm8', 'basy_qtzd9', 'basy_zyzd_jbbm9',
                    'basy_qtzd10', 'basy_zyzd_jbbm10', 'basy_qtzd11', 'basy_zyzd_jbbm11',
                    'basy_qtzd12', 'basy_zyzd_jbbm12', 'basy_qtzd13', 'basy_zyzd_jbbm13',
                    'basy_qtzd14', 'basy_zyzd_jbbm14', 'basy_qtzd15', 'basy_zyzd_jbbm15',
                    'basy_ssjczbm1', 'basy_shjb1', 'basy_ssjczmc1', 'basy_ssjczbm2', 'basy_shjb2', 'basy_ssjczmc2',
                    'basy_ssjczbm3', 'basy_shjb3', 'basy_ssjczmc3', 'basy_ssjczbm4', 'basy_shjb4', 'basy_ssjczmc4',
                    'basy_ssjczbm5', 'basy_shjb5', 'basy_ssjczmc5', 'basy_ssjczbm6', 'basy_shjb6', 'basy_ssjczmc6',
                    'basy_ssjczbm7', 'basy_shjb7', 'basy_ssjczmc7',
                    'basy_zfy', 'basy_blzdf', 'basy_zdf', 'basy_yxxzdf', 'basy_lczdxmf',
                    'basy_xyf', 'basy_zcyf', 'basy_zcyf1',
                    'basy_jcyyclf', 'basy_yyclf', 'basy_ssycxclf',
                    'ssf',
                    'zzys', 'zzys_sfzh']
        df_2 = pd.DataFrame(result_2, columns=xy_names)
        logging.info(f"西医数据，共计{df_2.shape[0]}条")

        # 中医病案
        # 主治医生zzys 改为 主诊医生zznys
        zy_col = """
                    sfzh, yljgid, bah, xb, csrq, rysj, cysj, cykb, rykb, sjzy, zycs,
                    zyzd, zyzd_jbbm, qtzd1, zyzd_jbbm1, qtzd2, zyzd_jbbm2, qtzd3, zyzd_jbbm3, qtzd4, zyzd_jbbm4, 
                    qtzd5, zyzd_jbbm5, qtzd6, zyzd_jbbm6, qtzd7, zyzd_jbbm7, 
                    ssjczbm1, shjb1, ssjczmc1, ssjczbm2, shjb2, ssjczmc2, ssjczbm3, shjb3, ssjczmc3,
                    ssjczbm4, shjb4, ssjczmc4, ssjczbm5, shjb5, ssjczmc5, ssjczbm6, shjb6, ssjczmc6,
                    zfy, blzdf, zdf, yxxzdf, lczdxmf, 
                    xyf, zcyf, zcyf1,
                    jcyyclf, yyclf, ssycxclf,
                    ssf,
                    zznys, zznys_sfzh
                    """
        sql_3 = """
                SELECT {} FROM WCL.syoe_zyba_view_n WHERE substr(cysj, 1, 6) = '{}{}'
                """.format(zy_col, self.year, self.month)
        # sql_3 = """
                # SELECT {} FROM WCL.zyba_syb_n WHERE substr(cysj, 1, 6) = '{}{}'
                # """.format(zy_col, self.year, self.month)
        result_3 = oralce_db_table.query(sql_3)
        zy_names = ['basy_sfzh_md5', 'basy_yljgid', 'basy_bah', 'basy_xb', 'basy_csrq', 'basy_rysj', 'basy_cysj',
                    'basy_cykb', 'basy_rykb', 'basy_sjzy', 'basy_zycs',
                    'basy_zyzd', 'basy_zyzd_jbbm',
                    'basy_qtzd1', 'basy_zyzd_jbbm1', 'basy_qtzd2', 'basy_zyzd_jbbm2', 'basy_qtzd3', 'basy_zyzd_jbbm3',
                    'basy_qtzd4', 'basy_zyzd_jbbm4', 'basy_qtzd5', 'basy_zyzd_jbbm5', 'basy_qtzd6', 'basy_zyzd_jbbm6',
                    'basy_qtzd7', 'basy_zyzd_jbbm7',
                    'basy_ssjczbm1', 'basy_shjb1', 'basy_ssjczmc1', 'basy_ssjczbm2', 'basy_shjb2', 'basy_ssjczmc2',
                    'basy_ssjczbm3', 'basy_shjb3', 'basy_ssjczmc3', 'basy_ssjczbm4', 'basy_shjb4', 'basy_ssjczmc4',
                    'basy_ssjczbm5', 'basy_shjb5', 'basy_ssjczmc5', 'basy_ssjczbm6', 'basy_shjb6', 'basy_ssjczmc6',
                    'basy_zfy', 'basy_blzdf', 'basy_zdf', 'basy_yxxzdf', 'basy_lczdxmf',
                    'basy_xyf', 'basy_zcyf', 'basy_zcyf1',
                    'basy_jcyyclf', 'basy_yyclf', 'basy_ssycxclf',
                    'ssf',
                    'zzys', 'zzys_sfzh']
        df_3 = pd.DataFrame(result_3, columns=zy_names)
        logging.info(f"中医数据，共计{df_3.shape[0]}条")

        df = pd.concat([df_2, df_3], axis=0)

        df['basy_yljgid'] = 'JG_' + df['basy_yljgid']
        df['basy_bah'] = 'BAH_' + df['basy_bah']

        df = pd.merge(df, df_1, how='inner', on='basy_yljgid')
        # df = df[df["basy_sjzy"] > 1]  # 去除实际住院时间太短的case
        df.reset_index(drop=True, inplace=True)

        df.to_csv("data/original/original_{}{}.csv".format(self.year, self.month))
        logging.info(f"保存数据，共计{df.shape[0]}条，"
                     f"保存至./data/original/original_{self.year}{self.month}.csv")
        # db_table.close()
        # db.close()
        oralce_db_table.close()
        oralce_db.close()
        # return df

    def clean_data(self):
        """
        数据清洗,并保存至./data/cleaned/
        :return:
        """
        DataProcessing.get_data(self)
        # quit()

        logging.info(f"清洗数据")
        df = pd.read_csv("data/original/original_{}{}.csv".format(self.year, self.month), index_col=0,
                         dtype={'basy_cykb': str, 'basy_rykb': str, 'basy_rysj': str, 'basy_cysj': str})
        print("clean_data1", df.shape)

        # 数据去重，病案首页原始数据存在重复数据，故用'basy_sfzh_md5', 'basy_cysj', 'basy_zfy'三个字段去重
        df.drop_duplicates(subset=['basy_sfzh_md5', 'basy_cysj', 'basy_zfy'], inplace=True)

        if df[df['basy_dept_adrresscode'].astype(str).str.len() != 6].shape[0] > 0:
            logging.error("basy_dept_adrresscode 存在长度不等于6的记录")
        # basy_dept_adrresscode（医院行政区划代码）的长度应该等于6
        # 使用./docs/区县字典.xlsx 转化为中文
        area_df = pd.read_excel('docs/区县字典.xlsx').loc[:, ['counties_code6', 'all_name', 'counties_sign']]
        area_df = area_df[area_df['counties_sign'].isin([1, 2, 3, 4])]
        area_dict_1 = dict(zip(list(area_df['counties_code6']), list(area_df['all_name'])))

        df = df[df['basy_dept_adrresscode'].astype(str).str.len() == 6]
        
        print("clean_data2", df.shape)
        df['area_name'] = df['basy_dept_adrresscode'].astype(int).map(lambda a: area_dict_1.get(a, '未知'))
        print("clean_data3", df.shape)

        unknown_area_name_num = df[df['area_name'] == '未知'].shape[0]
        if unknown_area_name_num > 0:
            logging.error(f"医疗机构地区未知，共计{unknown_area_name_num}条")
            # df = df[~df['area_name'].isin(['未知'])]
            sys.exit()

        area_df_2 = area_df[area_df['counties_sign'].isin([1, 4])]
        area_dict_2 = dict(zip(list(area_df_2['all_name']), list(area_df_2['counties_code6'])))
        df['area_code'] = df['area_name'].map(lambda a: area_dict_2.get(a, '未知'))

        df['area_city_code'] = df['area_code'].astype(str).str[0:4] + '00'
        df['area_city_name'] = df['area_city_code'].astype(int).map(lambda a: area_dict_1.get(a, '四川省'))

        # 医院等级
        df['basy_yydj'] = df['basy_yydj'].fillna(value='未评级未评等')
        df['basy_yydj'] = df['basy_yydj'].apply(
            lambda x: '一级未评等' if ('一' in x) and ('未' in x or '等' not in x) else (
                '二级未评等' if ('二' in x) and ('未' in x) else (
                    '三级未评等' if ('三' in x) and ('未' in x) else (
                        '未评甲等' if ('甲' in x) and ('未' in x) else (
                            '未评乙等' if ('乙' in x) and ('未' in x) else (
                                '未评丙等' if ('丙' in x) and ('未' in x) else (
                                    '未评级未评等' if '未' in x else x)))))))

        # # 医院级别
        # df['basy_yyjb'] = df['basy_yydj'].apply(
        #     lambda x: '一级' if '一级' in x else (
        #         '二级' if '二级' in x else (
        #             '三级' if '三级' in x else (
        #                 '未评级' if '未评级' in x else x))))

        # 临床学科
        
        df['basy_cykb'] = df['basy_cykb'].fillna(value='69')  # 69为 其他业务科室
        df['basy_cykb'] = df['basy_cykb'].map(lambda a: '69' if a == '-' else a)
        # print(df['basy_cykb'])
        df['basy_cykb_new'] = df['basy_cykb'].map(
            lambda a: str(int(a)) if len(a.split('.')) == 1 else "-".join([str(int(i)) for i in a.split('.')]))
        df['discipline_id'] = df['basy_cykb_new'].map(lambda x: x[0:x.find('-')] if '-' in x else x[0:2])

        # 使用./docs/临床学科字典.xlsx 清洗
        discipline_df = pd.read_excel('docs/临床学科字典.xlsx', sheet_name='科室分类与代码')
        discipline_df['代码'] = discipline_df['代码'].map(
            lambda a: str(int(a)) if len(a.split('.')) == 1 else "-".join([str(int(i)) for i in a.split('.')]))
        discipline_dict = dict(zip(list(discipline_df['代码']), list(discipline_df['诊疗科目'])))
        df['discipline_name'] = df['discipline_id'].map(lambda a: discipline_dict.get(a, '其他业务科室'))
        df['dept_name'] = df['basy_cykb_new'].map(lambda a: discipline_dict.get(a, '其他业务科室'))

        #  Remove some records from psychiatry departments temporarily
        df = df[~df['dept_name'].isin(['精神卫生专业', '精神康复专业', '精神病专业', '精神科'])]

        # 主诊断 疾病编码前四位
        df['jbbm'] = df['basy_zyzd_jbbm'].astype(str).str[0:7].str.upper()
        df = df[df['jbbm'].astype(str).str.contains('^[a-zA-Z][0-9]{2}\\.')]

        # 手术编码 疾病编码前两位
        df['ori_ssbm'] = df['basy_ssjczbm1'].astype(str).str[0:4]
        # df['is_ssbm'] = df['ori_ssbm'].astype(str).str.contains('^[0-9]{2}$')
        df['is_ssbm'] = df['ori_ssbm'].astype(str).str.contains('^[0-9]{2}\\.')

        df['ssbm'] = ''
        df['ssbm'] = df['ssbm'].mask(df['is_ssbm'] == 1, df['ori_ssbm'])
        df['ssbm'] = 'S' + df['ssbm'].astype(str)

        # 手术费 > 0 但无第一手术编码, 标记
        df['ss_mark'] = 0
        df.loc[(df['ssbm'] == 'S') & (df['ssf'].astype(float) > 0), 'ss_mark'] = 1

        # 医生 缺失
        df['zzys'].fillna('未写', inplace=True)
        df['zzys'].replace('-', '未写', inplace=True)

        # 各项费用计算
        cost_list = ['basy_jcyyclf', 'basy_yyclf', 'basy_ssycxclf',
                     'basy_blzdf', 'basy_zdf', 'basy_yxxzdf', 'basy_lczdxmf',
                     'basy_xyf', 'basy_zcyf', 'basy_zcyf1']
        df[cost_list] = df[cost_list].fillna(0).astype(float)

        # 耗材费 = basy_jcyyclf(检查用一次性医用材料费) + basy_yyclf(治疗用一次性医用材料) + basy_ssycxclf(手术用一次性医用材料费)
        # 检查检验费 = basy_blzdf(病理诊断费) + basy_zdf(实验室诊断费) + basy_yxxzdf(影像学诊断费) + basy_lczdxmf(临床诊断项目费)
        # 药品费 = basy_xyf(西药费) + basy_zcyf(中成药费) + basy_zcyf1(中草药费)
        df['耗材费'] = df['basy_jcyyclf'] + df['basy_yyclf'] + df['basy_ssycxclf']
        df['检查检验费'] = df['basy_blzdf'] + df['basy_zdf'] + df['basy_yxxzdf'] + df['basy_lczdxmf']
        df['药品费'] = df['basy_xyf'] + df['basy_zcyf'] + df['basy_zcyf1']
        df['总费用'] = df['basy_zfy']
        df = df[(df['耗材费'] >= 0) & (df['检查检验费'] >= 0) & (df['药品费'] >= 0)]
        print("clean_data4", df.shape)

        # hospital_id
        hospital_id_df = pd.read_excel('docs/hospital_id.xlsx')
        hospiatl_id_dict = dict(zip(list(hospital_id_df['basy_yljgid_1']), list(hospital_id_df['hospital_id'])))
        df['hospital_id'] = df['basy_yljgid'].map(lambda a: hospiatl_id_dict.get(a, 0))

        # 调整日期格式
        df['basy_rysj'] = df['basy_rysj'].astype(str).astype(np.datetime64)
        df['basy_cysj'] = df['basy_cysj'].astype(str).astype(np.datetime64)

        df.replace('-', '', inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.insert(loc=0, column='temp_id', value=df.index)
        print("clean_data5", df.shape)
        df.to_csv("data/cleaned/cleaned_{}{}.csv".format(self.year, self.month))
        logging.info(f"保存数据，共计{df.shape[0]}条，"
                     f"保存至./data/cleaned/cleaned_{self.year}{self.month}.csv")
        return df
