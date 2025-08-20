#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

time: 2022-03-18
description:
    根据需求统计数据
    医院、科室、医生oe 直接用病人表中，分子之和 除以 分母之和
update：2022-09-06
    1.修改OE的2-5的标准化
    2.每家省管医院取OE前20条

"""

import logging
import random
import pandas as pd
import numpy as np
from module.db_module import DatabaseClass, DBTable
from model import Model


def outlier(x, algorithm_type=1, std_times=3):
    """
    异常检测方式
    :param x:
    :param std_times: 标准差倍数
    :param algorithm_type: 1 = IQR，其他 = 均值、标准差
    :return:
    """
    if algorithm_type == 1:
        q1 = np.quantile(x, 0.25, interpolation='midpoint')
        q3 = np.quantile(x, 0.75, interpolation='midpoint')
        outlier_value = q3 + 1.5 * (q3 - q1)
    else:
        # ddof = 0时，计算的是总体标准偏差，标准差公式根号内除以 n。
        # ddof = 1时，计算的是样本标准差，标准差公式根号内除以 （n-1）。 默认。
        outlier_value = x.mean() + std_times * x.std()
    return outlier_value


def level_jbbm_ssbm_mean(start_time, end_time, jb, ss, min_num):
    """
    从病案首页提取一整年数据，且主要诊断前7位（A01.100），第一手术前5位，作为计算O/E值的E值
    保存至./data/other/
    :param jb: 疾病编码位数
    :param ss: 手术编码位数
    :param min_num： 计算E值需要最少的数据条数
    :return:
    """
    db = DatabaseClass()
    db.connect()
    db_table = DBTable(db.database)
    logging.info(f"提取数据，从病案首页提取{start_time}至{end_time}的数据")
    sql = """
            SELECT 
                basy_yydj, substr(basy_zyzd_jbbm, 1, {}) as jbbm, substr(basy_ssjczbm1, 1, {}) as ssbm,
                count(*) as num,
                (sum(basy_jcyyclf) + sum(basy_yyclf) + sum(basy_ssycxclf)) as haocai,
                (sum(basy_blzdf) + sum(basy_zdf) + sum(basy_yxxzdf) + sum(basy_lczdxmf)) as jiancha,
                (sum(basy_xyf) + sum(basy_zcyf) + sum(basy_zcyf1)) as yaopin,
                sum(basy_zfy) as zfy
            FROM zlk.t_basy
            WHERE basy_cysj BETWEEN '{}' AND '{}' 
            GROUP BY basy_yydj, substr(basy_zyzd_jbbm, 1, {}), substr(basy_ssjczbm1, 1, {})
            """.format(jb, ss, start_time, end_time, jb, ss)
    result = db_table.query(sql)
    df = pd.DataFrame(result, columns=['basy_yydj', 'ori_jbbm', 'ori_ssbm', 'num',
                                       '耗材费', '检查检验费', '药品费', '总费用'])

    # 数据清洗
    df['basy_yydj'] = df['basy_yydj'].replace('', '未评级未评等')
    df['basy_yydj'] = df['basy_yydj'].apply(
        lambda x: '一级未评等' if ('一' in x) and ('未' in x or '等' not in x) else (
            '二级未评等' if ('二' in x) and ('未' in x) else (
                '三级未评等' if ('三' in x) and ('未' in x) else (
                    '未评甲等' if ('甲' in x) and ('未' in x) else (
                        '未评乙等' if ('乙' in x) and ('未' in x) else (
                            '未评丙等' if ('丙' in x) and ('未' in x) else (
                                '未评级未评等' if '未' in x else x)))))))
    df = df[df['ori_jbbm'].astype(str).str.contains('^[a-zA-Z][0-9]{2}\\.')]
    df['jbbm'] = df['ori_jbbm'].str.upper()

    # df['is_ssbm'] = df['ori_ssbm'].astype(str).str.contains('^[0-9]{2}$')
    df['is_ssbm'] = df['ori_ssbm'].astype(str).str.contains('^[0-9]{2}\\.')
    df['ssbm'] = ''
    df['ssbm'] = df['ssbm'].mask(df['is_ssbm'] == 1, df['ori_ssbm'])
    df['ssbm'] = 'S' + df['ssbm'].astype(str)

    df = df.groupby(['basy_yydj', 'jbbm', 'ssbm']).agg({'num': 'sum',
                                                        '耗材费': 'sum',
                                                        '检查检验费': 'sum',
                                                        '药品费': 'sum',
                                                        '总费用': 'sum'}).reset_index()
    df['level_耗材费_mean'] = df['耗材费'] / df['num']
    df['level_检查检验费_mean'] = df['检查检验费'] / df['num']
    df['level_药品费_mean'] = df['药品费'] / df['num']
    df['level_总费用_mean'] = df['总费用'] / df['num']
    df = df[['basy_yydj', 'jbbm', 'ssbm', 'num',
             'level_耗材费_mean', 'level_检查检验费_mean', 'level_药品费_mean', 'level_总费用_mean']]
    for j in ['level_耗材费_mean', 'level_检查检验费_mean', 'level_药品费_mean', 'level_总费用_mean']:
        # df.loc[df[j] < 1, j] = 1
        df = df[df[j] >= 1]
    df = df[df['num'] >= min_num]
    df.reset_index(drop=True, inplace=True)

    df.to_csv("data/other/level_jbbm_ssbm_{}.csv".format(end_time.replace('-', '')))
    logging.info(f"保存数据，共计{df.shape[0]}条，"
                 f"保存至./data/other/level_jbbm_ssbm_{end_time.replace('-', '')}.csv")
    db.close()


def normalization(series, a, b, n):
    """
    （1）首先找到样本数据Y的最小值Min及最大值Max
    （2）计算系数为：k=（b-a)/(Max-Min)
    （3）得到归一化到[a,b]区间的数据：norY=a+k(Y-Min)
    :param series:
    :param a:
    :param b:
    :param n:
    :return:
    """
    random.seed(n)  # 保证每个项目区间起始值不同，但固定
    a = random.uniform(a + 0.01, a + 0.1)
    b = random.uniform(b - 0.1, b - 0.01)

    k = (b - a) / (series.max() - series.min())
    nor_series = a + k * (series - series.min())
    return nor_series


class Output(object):

    supplies_drug_dict = {'耗材费': 0, '药品费': 1, '总费用': 2, '检查检验费': 3}

    def __init__(self, year, month):
        """
        数据区间
        :param year: 数据年份
        :param month: 数据月份
        """
        self.year = year
        self.month = month

    def hospital_patient_result(self, df, e_value_df, min_cost):
        """
        按医院、临床学科、医生统计O/E值，
        O为各个患者的耗材费/药品费/检查检验费/总费用的均值，
        E为各个医院等级，疾病编码前四位（A01.1）耗材费/药品费/检查检验费/总费用的均值

        由于 dmiaes_map_hospital_diagnosis.csv, temp_scs_odd_supplies.csv, temp_scs_odd_zd.csv 这三张表与该表有关联，
        故此处一并统计生成。

        :return:
        """
        list_1 = ['dx1_1', 'dx2_2', 'dx3_3', 'dx4_4', 'dx5_5', 'dx6_6', 'dx7_7', 'dx8_8', 'dx9_9',
                  'dx10_10', 'dx11_11', 'dx12_12', 'dx13_13', 'dx14_14', 'dx15_15', 'dx16_16',
                  'px1_1', 'px2_2', 'px3_3', 'px4_4', 'px5_5', 'px6_6', 'px7_7']
        list_2 = ['basy_zyzd', 'basy_zyzd_jbbm', 'basy_qtzd1', 'basy_zyzd_jbbm1', 'basy_qtzd2', 'basy_zyzd_jbbm2',
                  'basy_qtzd3', 'basy_zyzd_jbbm3', 'basy_qtzd4', 'basy_zyzd_jbbm4', 'basy_qtzd5', 'basy_zyzd_jbbm5',
                  'basy_qtzd6', 'basy_zyzd_jbbm6', 'basy_qtzd7', 'basy_zyzd_jbbm7', 'basy_qtzd8', 'basy_zyzd_jbbm8',
                  'basy_qtzd9', 'basy_zyzd_jbbm9', 'basy_qtzd10', 'basy_zyzd_jbbm10',
                  'basy_qtzd11', 'basy_zyzd_jbbm11', 'basy_qtzd12', 'basy_zyzd_jbbm12',
                  'basy_qtzd13', 'basy_zyzd_jbbm13', 'basy_qtzd14', 'basy_zyzd_jbbm14', 'basy_qtzd15',
                  'basy_zyzd_jbbm15',
                  'basy_ssjczbm1', 'basy_ssjczmc1', 'basy_ssjczbm2', 'basy_ssjczmc2', 'basy_ssjczbm3', 'basy_ssjczmc3',
                  'basy_ssjczbm4', 'basy_ssjczmc4', 'basy_ssjczbm5', 'basy_ssjczmc5', 'basy_ssjczbm6', 'basy_ssjczmc6',
                  'basy_ssjczbm7', 'basy_ssjczmc7']

        hospital_patient_df = pd.DataFrame()

        e_value_df = e_value_df[['basy_yydj', 'jbbm', 'ssbm',
                                 'level_耗材费_mean', 'level_检查检验费_mean', 'level_药品费_mean', 'level_总费用_mean']]

        # 处理住院诊断与手术情况
        print("hospital_patient_result1", df.shape)
        df['dx1_1'] = df['basy_zyzd_jbbm'].str.cat(df['basy_zyzd'].map(str), sep=' ')
        for i in range(1, 16, 1):
            df['dx{}_{}'.format(i+1, i+1)] = df['basy_zyzd_jbbm{}'.format(i)].str.cat(
                df['basy_qtzd{}'.format(i)].map(str), sep=' ')
        for i in range(1, 17, 1):
            df.loc[df['dx{}_{}'.format(i, i)] == '', 'dx{}_{}'.format(i, i)] = np.NaN
            df.loc[df['dx{}_{}'.format(i, i)] == ' ', 'dx{}_{}'.format(i, i)] = np.NaN
            df.loc[df['dx{}_{}'.format(i, i)] == 'nan nan', 'dx{}_{}'.format(i, i)] = np.NaN
        # df['px1_1'] = df['basy_ssjczbm1'].map(str).str.cat(df['basy_ssjczmc1'].map(str), sep=' ')
        for j in range(1, 8, 1):
            df['px{}_{}'.format(j, j)] = df['basy_ssjczbm{}'.format(j)].astype(str).str.cat(
                df['basy_ssjczmc{}'.format(j)].astype(str).map(str), sep=' ')
            df.loc[df['px{}_{}'.format(j, j)] == '', 'px{}_{}'.format(j, j)] = np.NaN
            df.loc[df['px{}_{}'.format(j, j)] == ' ', 'px{}_{}'.format(j, j)] = np.NaN
            df.loc[df['px{}_{}'.format(j, j)] == 'nan nan', 'px{}_{}'.format(j, j)] = np.NaN

        # 省管医院
        province_hospital_df = pd.read_excel('docs/hospital.xlsx')
        province_hospital_list = province_hospital_df.loc[province_hospital_df['flag'] == 4,
                                                          'basy_yljgid'].astype(str).tolist()

        for i in Output.supplies_drug_dict.keys():
            df_g = df.loc[:, ['temp_id', 'temp_id',  'hospital_id', 'basy_yljgid', 'basy_caption', 'basy_yydj',
                              'jbbm', 'ssbm', 'ss_mark', 'discipline_id',
                              'discipline_name', 'zzys', 'dept_name', 'basy_bah', 'basy_zycs',
                              'basy_rysj', 'basy_cysj', 'basy_zfy', '{}'.format(i), 'dx1_1', 'dx2_2', 'dx3_3',
                              'dx4_4', 'dx5_5', 'dx6_6', 'dx7_7', 'dx8_8', 'dx9_9', 'dx10_10', 'dx11_11',
                              'dx12_12', 'dx13_13', 'dx14_14', 'dx15_15', 'dx16_16',
                              'px1_1', 'px2_2', 'px3_3', 'px4_4', 'px5_5', 'px6_6', 'px7_7',
                              'basy_ssjczbm1', 'basy_ssjczmc1', 'basy_ssjczbm2', 'basy_ssjczmc2',
                              'basy_ssjczbm3', 'basy_ssjczmc3', 'basy_ssjczbm4', 'basy_ssjczmc4',
                              'basy_ssjczbm5', 'basy_ssjczmc5', 'basy_ssjczbm6', 'basy_ssjczmc6',
                              'basy_ssjczbm7', 'basy_ssjczmc7',
                              'basy_zyzd', 'basy_zyzd_jbbm', 'basy_qtzd1',
                              'basy_zyzd_jbbm1', 'basy_qtzd2', 'basy_zyzd_jbbm2', 'basy_qtzd3', 'basy_zyzd_jbbm3',
                              'basy_qtzd4', 'basy_zyzd_jbbm4', 'basy_qtzd5', 'basy_zyzd_jbbm5', 'basy_qtzd6',
                              'basy_zyzd_jbbm6', 'basy_qtzd7', 'basy_zyzd_jbbm7', 'basy_qtzd8', 'basy_zyzd_jbbm8',
                              'basy_qtzd9', 'basy_zyzd_jbbm9', 'basy_qtzd10', 'basy_zyzd_jbbm10', 'basy_qtzd11',
                              'basy_zyzd_jbbm11', 'basy_qtzd12', 'basy_zyzd_jbbm12', 'basy_qtzd13',
                              'basy_zyzd_jbbm13', 'basy_qtzd14', 'basy_zyzd_jbbm14', 'basy_qtzd15',
                              'basy_zyzd_jbbm15']]
            df_g.columns = ['temp_id', 'encounter', 'hospital_id', 'hospital_wjw_id', 'hospital_name', 'basy_yydj',
                            'jbbm', 'ssbm', 'ss_mark', 'discipline_id', 'discipline_name', 'doctor_name', 'dept_name',
                            'patient_account', 'visit_id', 'in_hospital_time', 'out_hospital_time', 'total_charge',
                            'patient_charge', 'dx1_1', 'dx2_2', 'dx3_3',
                            'dx4_4', 'dx5_5', 'dx6_6', 'dx7_7', 'dx8_8', 'dx9_9', 'dx10_10', 'dx11_11',
                            'dx12_12', 'dx13_13', 'dx14_14', 'dx15_15', 'dx16_16',
                            'px1_1', 'px2_2', 'px3_3', 'px4_4', 'px5_5', 'px6_6', 'px7_7',
                            'basy_ssjczbm1', 'basy_ssjczmc1', 'basy_ssjczbm2', 'basy_ssjczmc2',
                            'basy_ssjczbm3', 'basy_ssjczmc3', 'basy_ssjczbm4', 'basy_ssjczmc4',
                            'basy_ssjczbm5', 'basy_ssjczmc5', 'basy_ssjczbm6', 'basy_ssjczmc6',
                            'basy_ssjczbm7', 'basy_ssjczmc7',
                            'basy_zyzd', 'basy_zyzd_jbbm', 'basy_qtzd1',
                            'basy_zyzd_jbbm1', 'basy_qtzd2', 'basy_zyzd_jbbm2', 'basy_qtzd3', 'basy_zyzd_jbbm3',
                            'basy_qtzd4', 'basy_zyzd_jbbm4', 'basy_qtzd5', 'basy_zyzd_jbbm5', 'basy_qtzd6',
                            'basy_zyzd_jbbm6', 'basy_qtzd7', 'basy_zyzd_jbbm7', 'basy_qtzd8', 'basy_zyzd_jbbm8',
                            'basy_qtzd9', 'basy_zyzd_jbbm9', 'basy_qtzd10', 'basy_zyzd_jbbm10', 'basy_qtzd11',
                            'basy_zyzd_jbbm11', 'basy_qtzd12', 'basy_zyzd_jbbm12', 'basy_qtzd13',
                            'basy_zyzd_jbbm13', 'basy_qtzd14', 'basy_zyzd_jbbm14', 'basy_qtzd15',
                            'basy_zyzd_jbbm15']

            if i in ['药品费', '总费用']:
                e_value_df["ssbm"] = e_value_df["ssbm"].astype(str)
                df_g["ssbm"] = df_g["ssbm"].astype(str)

                if "basy_yydj_str" in df.columns:
                    df_g["basy_yydj"] = df["basy_yydj_str"]
                print("df_g", df_g[['basy_yydj', 'jbbm', 'ssbm']])
                print("e_value_df", e_value_df[['basy_yydj', 'jbbm', 'ssbm']])
                df_g = pd.merge(df_g, e_value_df, on=['basy_yydj', 'jbbm', 'ssbm'], how='inner')
            else:
                # 替换为模型即可
                df_g['level_{}_mean'.format(i)] = Model(i).predict(df)

            df_g['patient_odd_oe'] = df_g['patient_charge'].astype(float) / df_g[
                'level_{}_mean'.format(i)].astype(float)
            df_g['supplies_drug'] = Output.supplies_drug_dict[i]
            df_g[['bsdrg_no', 'bsdrg_desc', 'model_no', 'exception_type', 'exception_desc']] = ''

            # 更新cleaned_data中各类对应的oe值
            df = pd.merge(df, df_g[['temp_id', 'patient_odd_oe', 'level_{}_mean'.format(i)]], how='left', on='temp_id')
            df.rename(columns={'patient_odd_oe': '{}_oe'.format(i)}, inplace=True)
            print("hospital_patient_result2", df.shape)

            # 异常点

            # 费用低于min_cost，排除
            df_g = df_g[(df_g['patient_charge'].astype(float) >= min_cost)]
            

            # update:2022-09-06 每家省管医院取前20条
            province_df_g = df_g[df_g['hospital_wjw_id'].astype(str).str[3:].isin(province_hospital_list)]
            province_df_g = province_df_g.sort_values(['hospital_wjw_id', 'patient_odd_oe'], ascending=[1, 0])  # 1为升序
            province_df_g = province_df_g.groupby(['hospital_wjw_id']).head(20).reset_index()
            # OE值归一化
            province_df_g['nor_patient_odd_oe'] = normalization(province_df_g['patient_odd_oe'],
                                                                province_df_g['patient_odd_oe'].min() + 1,
                                                                province_df_g['patient_odd_oe'].max() / 5,
                                                                Output.supplies_drug_dict[i])
            province_df_g.loc[:, 'ss_mark_1'] = 0
            province_df_g.loc[:, 'ss_mark_2'] = 0
            province_df_g.drop(columns=['index'], inplace=True)

            # 非省管医院按照以前的方式
            df_g = df_g[~df_g['hospital_wjw_id'].astype(str).str[3:].isin(province_hospital_list)]

            odd_value = outlier(df_g['patient_odd_oe'], algorithm_type=2, std_times=3)
            df_g = df_g[(df_g['patient_odd_oe'] >= odd_value)]

            # OE值归一化
            df_g['nor_patient_odd_oe'] = normalization(df_g['patient_odd_oe'],
                                                       df_g['patient_odd_oe'].min(),
                                                       df_g['patient_odd_oe'].max() / 10,
                                                       Output.supplies_drug_dict[i])

            # 手术费 > 0 但无第一手术编码 的异常样本，不连续出现
            df_g.sort_values(by='nor_patient_odd_oe', ascending=0, inplace=True)
            df_g['ss_mark_1'] = df_g['ss_mark'].shift(periods=1, fill_value=0)
            df_g['ss_mark_2'] = df_g['ss_mark'] - df_g['ss_mark_1']
            df_g = df_g[(df_g['ss_mark_2'] != 0) | (df_g['ss_mark'] == 0)]

            # 合并省管医院和非省管医院
            df_g = pd.concat([df_g, province_df_g], axis=0)

            # 更新cleaned_data中各类对应的oe值
            df = pd.merge(df, df_g[['temp_id', 'patient_odd_oe', 'nor_patient_odd_oe']], how='left', on='temp_id')
            print("hospital_patient_result3", df.shape)
            df.rename(columns={'patient_odd_oe': '{}_odd_oe'.format(i),
                               'nor_patient_odd_oe': '{}_odd_nor_oe'.format(i)}, inplace=True)

            # 更新cleaned_data中各类的异常患者标记
            df['{}_odd'.format(i)] = 0
            df.loc[df['temp_id'].isin(df_g['temp_id'].unique().tolist()), '{}_odd'.format(i)] = 1

            hospital_patient_df = pd.concat(
                [hospital_patient_df, df_g[['encounter', 'hospital_id', 'hospital_wjw_id', 'hospital_name',
                                            'discipline_id', 'discipline_name', 'doctor_name', 'dept_name',
                                            'patient_account', 'visit_id', 'in_hospital_time', 'out_hospital_time',
                                            'supplies_drug', 'nor_patient_odd_oe', 'patient_charge', 'total_charge',
                                            'bsdrg_no', 'bsdrg_desc', 'model_no', 'exception_type', 'exception_desc',
                                            'dx1_1', 'dx2_2', 'dx3_3', 'dx4_4', 'dx5_5', 'dx6_6', 'dx7_7', 'dx8_8',
                                            'dx9_9', 'dx10_10', 'dx11_11', 'dx12_12', 'dx13_13', 'dx14_14', 'dx15_15',
                                            'dx16_16',
                                            'px1_1', 'px2_2', 'px3_3', 'px4_4', 'px5_5', 'px6_6', 'px7_7',
                                            'basy_ssjczbm1', 'basy_ssjczmc1', 'basy_ssjczbm2', 'basy_ssjczmc2',
                                            'basy_ssjczbm3', 'basy_ssjczmc3', 'basy_ssjczbm4', 'basy_ssjczmc4',
                                            'basy_ssjczbm5', 'basy_ssjczmc5', 'basy_ssjczbm6', 'basy_ssjczmc6',
                                            'basy_ssjczbm7', 'basy_ssjczmc7',
                                            'basy_zyzd', 'basy_zyzd_jbbm',
                                            'basy_qtzd1', 'basy_zyzd_jbbm1', 'basy_qtzd2', 'basy_zyzd_jbbm2',
                                            'basy_qtzd3', 'basy_zyzd_jbbm3', 'basy_qtzd4', 'basy_zyzd_jbbm4',
                                            'basy_qtzd5', 'basy_zyzd_jbbm5', 'basy_qtzd6', 'basy_zyzd_jbbm6',
                                            'basy_qtzd7', 'basy_zyzd_jbbm7', 'basy_qtzd8', 'basy_zyzd_jbbm8',
                                            'basy_qtzd9', 'basy_zyzd_jbbm9', 'basy_qtzd10', 'basy_zyzd_jbbm10',
                                            'basy_qtzd11', 'basy_zyzd_jbbm11', 'basy_qtzd12', 'basy_zyzd_jbbm12',
                                            'basy_qtzd13', 'basy_zyzd_jbbm13', 'basy_qtzd14', 'basy_zyzd_jbbm14',
                                            'basy_qtzd15', 'basy_zyzd_jbbm15']]], axis=0)
        hospital_patient_df['hospital_wjw_id'] = hospital_patient_df['hospital_wjw_id'].str[3:]
        hospital_patient_df['patient_account'] = hospital_patient_df['patient_account'].str[4:]
        hospital_patient_df.rename(columns={'nor_patient_odd_oe': 'patient_odd_oe'}, inplace=True)
        hospital_patient_df['patient_odd_oe'] = round(hospital_patient_df['patient_odd_oe'], 2)
        hospital_patient_df.sort_values(by='patient_odd_oe', ascending=0, inplace=True)
        hospital_patient_df.reset_index(drop=True, inplace=True)
        hospital_patient_df.index = hospital_patient_df.index + 1

        df.drop(columns=list_1, inplace=True)
        print("hospital_patient_result4", df.shape)
        df.to_csv('data/cleaned/again_cleaned_{}{}.csv'.format(self.year, self.month))

        # dmiaes_map_hospital_diagnosis.csv
        list_3 = ['encounter']
        list_3.extend(list_2)
        diagnosis_df = hospital_patient_df.loc[:, list_3]
        diagnosis_df.rename(columns={'basy_zyzd_jbbm': 'basy_zyzd_jbbm0', 'basy_zyzd': 'basy_qtzd0'}, inplace=True)

        hospital_diagnosis_df = pd.DataFrame()
        for i in range(0, 16, 1):
            each_df = diagnosis_df.loc[:, ['encounter', 'basy_zyzd_jbbm{}'.format(i), 'basy_qtzd{}'.format(i)]]
            each_df.columns = ['encounter', 'diagnosis_code', 'diagnosis_name']
            if i == 0:
                each_df['is_main_diagnosis'] = 'Y'
            else:
                each_df['is_main_diagnosis'] = 'N'
            hospital_diagnosis_df = pd.concat([hospital_diagnosis_df, each_df], axis=0)
        hospital_diagnosis_df = hospital_diagnosis_df[(~hospital_diagnosis_df['diagnosis_code'].isnull()) &
                                                      (hospital_diagnosis_df['diagnosis_code'] != '')]
        hospital_diagnosis_df.drop_duplicates(subset=['encounter', 'diagnosis_code',
                                                      'diagnosis_name', 'is_main_diagnosis'], inplace=True)
        hospital_diagnosis_df.sort_values(by=['encounter', 'is_main_diagnosis'], ascending=[1, 0], inplace=True)
        hospital_diagnosis_df.reset_index(drop=True, inplace=True)
        hospital_diagnosis_df.index = hospital_diagnosis_df.index + 1

        # temp_scs_odd_supplies.csv
        # 只需要省管医院
        # province_hospital_df = pd.read_excel('docs/hospital.xlsx')
        # province_hospital_list = province_hospital_df.loc[province_hospital_df['flag'] == 4,
        #                                                   'basy_yljgid'].astype(str).tolist()
        hospital_patient_df.drop(columns=list_2, inplace=True)
        odd_supplies_df = hospital_patient_df[(hospital_patient_df['supplies_drug'] == 0) &
                                              (hospital_patient_df['hospital_wjw_id'].astype(str).isin(
                                                  province_hospital_list))]
        odd_supplies_df.reset_index(drop=True, inplace=True)
        odd_supplies_df.index = odd_supplies_df.index + 1

        # temp_scs_odd_zd.csv
        odd_zd_df = hospital_patient_df[(hospital_patient_df['supplies_drug'] == 3) &
                                        (hospital_patient_df['hospital_wjw_id'].astype(str).isin(
                                            province_hospital_list))]
        odd_zd_df.reset_index(drop=True, inplace=True)
        odd_zd_df.index = odd_zd_df.index + 1

        # dmiaes_map_hospital_patient.csv
        hospital_patient_df.drop(columns=list_1, inplace=True)

        return hospital_diagnosis_df, odd_supplies_df, odd_zd_df, hospital_patient_df, df

    def area_result(self, df):
        """
        按区域统计O/E值，
        O为各个区域耗材费/药品费/检查检验费/总费用的均值，
        E为整个各市级 耗材费/药品费/检查检验费/总费用的均值
        :return:
        """
        area_df = pd.DataFrame()

        df.loc[:, 'basy_yljgid'] = df['basy_yljgid'].str[3:]

        for i in Output.supplies_drug_dict.keys():
            # 县级
            df[i] = df[i].astype(float)
            df_g = df.groupby(['area_city_code', 'area_city_name', 'area_code', 'area_name']).agg(
                {i: ['mean', 'count'], '{}_odd'.format(i): 'sum'}).reset_index()
            df_g.columns = ['area_city_code', 'area_city_name', 'area_code', 'area_name',
                            'cost_mean', 'total_count', 'odd_count']

            df_oe = df.loc[df['{}_odd'.format(i)] == 1, :].copy()
            df_oe.loc[:, '{}_nor_e_value'.format(i)] = df_oe['{}'.format(i)] / df_oe['{}_odd_nor_oe'.format(i)]

            df_oe_g = df_oe.groupby(['area_city_code', 'area_city_name', 'area_code', 'area_name']).agg(
                {'{}'.format(i): 'sum', '{}_nor_e_value'.format(i): 'sum'}).reset_index()

            df_oe_g.columns = ['area_city_code', 'area_city_name', 'area_code', 'area_name', 'o_value', 'e_value']
            df_oe_g['patient_odd_oe'] = df_oe_g['o_value'] / df_oe_g['e_value']

            df_g = pd.merge(df_g, df_oe_g, how='left',
                            on=['area_city_code', 'area_city_name', 'area_code', 'area_name'])

            df_g['years_months'] = self.year + self.month
            df_g['patient_odd_prop'] = round((df_g['odd_count'] / df_g['total_count']), 4)
            df_g['supplies_drug'] = Output.supplies_drug_dict[i]

            # 异常病人所属的医院地区
            odd_area_list = df.loc[df['{}_odd'.format(i)] == 1, 'area_code'].unique().tolist()
            df_g = df_g[df_g['area_code'].isin(odd_area_list)]

            # 市级
            city_g = df.groupby(['area_city_code', 'area_city_name']).agg(
                {i: ['mean', 'count'], '{}_odd'.format(i): 'sum'}).reset_index()
            city_g.columns = ['area_code', 'area_name', 'cost_mean', 'total_count', 'odd_count']

            city_oe_g = df_oe.groupby(['area_city_code', 'area_city_name']).agg(
                {'{}'.format(i): 'sum', '{}_nor_e_value'.format(i): 'sum'}).reset_index()
            city_oe_g.columns = ['area_code', 'area_name', 'o_value', 'e_value']
            city_oe_g['patient_odd_oe'] = city_oe_g['o_value'] / city_oe_g['e_value']

            city_g = pd.merge(city_g, city_oe_g, how='left', on=['area_code', 'area_name'])

            if len(str(self.month)) == 1:
                city_g['years_months'] = str(self.year) + '0' + str(self.month)
            else:
                city_g['years_months'] = str(self.year) + str(self.month)

            city_g['patient_odd_prop'] = round((city_g['odd_count'] / city_g['total_count']), 4)
            city_g['supplies_drug'] = Output.supplies_drug_dict[i]

            city_g = city_g[city_g['area_code'].isin(df_g['area_city_code'].unique().tolist())]

            # 省级
            province_g = pd.DataFrame()
            province_g.loc[0, 'area_code'] = '510'
            province_g['area_name'] = '四川省'
            if len(str(self.month)) == 1:
                province_g['years_months'] = str(self.year) + '0' + str(self.month)
            else:
                province_g['years_months'] = str(self.year) + str(self.month)
            # province_g['patient_odd_oe'] = round(df_oe['{}'.format(i)].sum() / df_oe['level_{}_mean'.format(i)].sum(),
            #                                      2)
            province_g['patient_odd_oe'] = round(df_g['patient_odd_oe'].mean(), 2)
            province_g['patient_odd_prop'] = round(df['{}_odd'.format(i)].sum() / df.shape[0], 4)
            province_g['supplies_drug'] = Output.supplies_drug_dict[i]

            area_df = pd.concat([area_df,
                                 df_g[['area_code', 'area_name', 'years_months',
                                       'patient_odd_oe', 'patient_odd_prop', 'supplies_drug']],
                                 city_g[['area_code', 'area_name', 'years_months',
                                         'patient_odd_oe', 'patient_odd_prop', 'supplies_drug']],
                                 province_g], axis=0)

        area_df['patient_odd_oe'] = round(area_df['patient_odd_oe'], 2)
        area_df.reset_index(drop=True, inplace=True)
        area_df.index = area_df.index + 1
        return area_df

    def discipline_result(self, df):
        """
        按临床学科统计O/E值，
        O为各个临床学科耗材费/药品费/检查检验费/总费用的均值，
        E为四川省耗材费/药品费/检查检验费/总费用的均值
        :return:
        """
        discipline_df = pd.DataFrame()
        for i in Output.supplies_drug_dict.keys():
            cost_avg = df[i].mean()

            df_g = df.groupby(['discipline_id', 'discipline_name'])[i].mean().reset_index(name='cost_mean')

            df_g['years_months'] = self.year + self.month
            df_g['oe'] = round((df_g['cost_mean'] / cost_avg), 2)
            df_g['supplies_drug'] = Output.supplies_drug_dict[i]

            discipline_df = pd.concat(
                [discipline_df, df_g[['years_months', 'discipline_id', 'discipline_name', 'oe',
                                      'supplies_drug']]], axis=0)
        discipline_df.reset_index(drop=True, inplace=True)
        discipline_df.index = discipline_df.index + 1
        return discipline_df

    def hospital_result(self, df):
        """

        :return:
        """

        hospital_df = pd.DataFrame()

        for i in Output.supplies_drug_dict.keys():

            df_g = df.groupby(['area_code', 'hospital_id', 'basy_caption', 'basy_yydj']).agg(
                {i: ['mean', 'count'], '{}_odd'.format(i): 'sum'}).reset_index()
            df_g.columns = ['area_code', 'hospital_id', 'hospital_name', 'hospital_lv',
                            'cost_mean', 'patient_count', 'patient_odd_count']

            df_oe = df[df['{}_odd'.format(i)] == 1].copy()
            df_oe.loc[:, '{}_nor_e_value'.format(i)] = df_oe['{}'.format(i)] / df_oe['{}_odd_nor_oe'.format(i)]
            df_oe_g = df_oe.groupby(['area_code', 'hospital_id', 'basy_caption', 'basy_yydj']).agg(
                {'{}'.format(i): 'sum', '{}_nor_e_value'.format(i): 'sum'}).reset_index()
            df_oe_g.columns = ['area_code', 'hospital_id', 'hospital_name', 'hospital_lv', 'o_value', 'e_value']
            df_oe_g['patient_odd_oe'] = df_oe_g['o_value'] / df_oe_g['e_value']

            df_g = pd.merge(df_g, df_oe_g, how='left',
                            on=['area_code', 'hospital_id', 'hospital_name', 'hospital_lv'])

            df_g['years_months'] = self.year + self.month
            df_g['patient_odd_prop'] = round((df_g['patient_odd_count'] / df_g['patient_count']), 4)
            df_g['supplies_drug'] = Output.supplies_drug_dict[i]

            # 异常病人所属的医院
            odd_hospital_df = df.loc[df['{}_odd'.format(i)] == 1, ['hospital_id']]
            odd_hospital_df.drop_duplicates(inplace=True)
            df_g = pd.merge(df_g, odd_hospital_df, on=['hospital_id'], how='inner')

            hospital_df = pd.concat(
                [hospital_df,
                 df_g[['area_code', 'years_months', 'hospital_id', 'hospital_name', 'hospital_lv',
                       'patient_count', 'patient_odd_oe', 'patient_odd_count',
                       'patient_odd_prop', 'supplies_drug']]
                 ], axis=0)
        hospital_df['patient_odd_oe'] = round(hospital_df['patient_odd_oe'], 2)
        hospital_df.sort_values(by='patient_odd_oe', ascending=0, inplace=True)
        hospital_df.reset_index(drop=True, inplace=True)
        hospital_df.index = hospital_df.index + 1
        return hospital_df

    def hospital_dept_result(self, df):
        """
        按科室统计O/E值，
        O为各个医院里 各个临床学科中的 各科室的耗材费/药品费/检查检验费/总费用的均值，
        E为各个医院等级，各个临床学科耗材费/药品费/检查检验费/总费用的均值
        :return:
        """
        hospital_dept_df = pd.DataFrame()

        for i in Output.supplies_drug_dict.keys():
            df_g = df.groupby(['hospital_id', 'basy_caption', 'basy_yydj', 'discipline_id', 'discipline_name',
                               'dept_name'])['{}'.format(i)].mean().reset_index(name='cost_mean')

            df_g.columns = ['hospital_id', 'hospital_name', 'basy_yydj', 'discipline_id',
                            'discipline_name', 'dept_name', 'cost_mean']

            df_oe = df[df['{}_odd'.format(i)] == 1].copy()
            df_oe.loc[:, '{}_nor_e_value'.format(i)] = df_oe['{}'.format(i)] / df_oe['{}_odd_nor_oe'.format(i)]
            df_oe_g = df_oe.groupby(['hospital_id', 'basy_caption', 'basy_yydj', 'discipline_id', 'discipline_name',
                                     'dept_name']).agg(
                {'{}'.format(i): 'sum', '{}_nor_e_value'.format(i): 'sum'}).reset_index()
            df_oe_g.columns = ['hospital_id', 'hospital_name', 'basy_yydj', 'discipline_id',
                               'discipline_name', 'dept_name', 'o_value', 'e_value']
            df_oe_g['patient_odd_oe'] = df_oe_g['o_value'] / df_oe_g['e_value']

            df_g = pd.merge(df_g, df_oe_g, how='left',
                            on=['hospital_id', 'hospital_name', 'basy_yydj', 'discipline_id',
                                'discipline_name', 'dept_name'])

            df_g['years_months'] = self.year + self.month
            df_g['supplies_drug'] = Output.supplies_drug_dict[i]

            # 异常病人所属的医院的科室
            odd_dept_df = df.loc[df['{}_odd'.format(i)] == 1, ['hospital_id', 'discipline_id', 'dept_name']]
            odd_dept_df.drop_duplicates(inplace=True)
            df_g = pd.merge(df_g, odd_dept_df, on=['hospital_id', 'discipline_id', 'dept_name'], how='inner')

            hospital_dept_df = pd.concat(
                [hospital_dept_df, df_g[['hospital_id', 'hospital_name', 'years_months', 'discipline_id',
                                         'discipline_name', 'dept_name', 'patient_odd_oe', 'supplies_drug']]], axis=0)
        hospital_dept_df['patient_odd_oe'] = round(hospital_dept_df['patient_odd_oe'], 2)
        hospital_dept_df.sort_values(by='patient_odd_oe', ascending=0, inplace=True)
        hospital_dept_df.reset_index(drop=True, inplace=True)
        hospital_dept_df.index = hospital_dept_df.index + 1
        return hospital_dept_df

    def hospital_doctor_result(self, df):
        """

        按医院、临床学科、医生统计O/E值，
        O为各个医院里 各个临床学科中的 各医生的耗材费/药品费/检查检验费/总费用的均值，
        E为各个医院等级，各个临床学科耗材费/药品费/检查检验费/总费用的均值
        :return:
        """
        hospital_doctor_df = pd.DataFrame()

        for i in Output.supplies_drug_dict.keys():

            df_g = df.groupby(['hospital_id', 'basy_caption', 'basy_yydj', 'discipline_id',
                               'discipline_name', 'zzys']).agg(
                {i: ['mean', 'count'], '{}_odd'.format(i): 'sum'}).reset_index()

            df_g.columns = ['hospital_id', 'hospital_name', 'basy_yydj', 'discipline_id', 'discipline_name',
                            'doctor_name', 'cost_mean', 'patient_count', 'patient_odd_count']

            df_oe = df[df['{}_odd'.format(i)] == 1].copy()
            df_oe.loc[:, '{}_nor_e_value'.format(i)] = df_oe['{}'.format(i)] / df_oe['{}_odd_nor_oe'.format(i)]
            df_oe_g = df_oe.groupby(['hospital_id', 'basy_caption', 'basy_yydj', 'discipline_id',
                                     'discipline_name', 'zzys']).agg(
                {'{}'.format(i): 'sum', '{}_nor_e_value'.format(i): 'sum'}).reset_index()
            df_oe_g.columns = ['hospital_id', 'hospital_name', 'basy_yydj', 'discipline_id', 'discipline_name',
                               'doctor_name', 'o_value', 'e_value']
            df_oe_g['patient_odd_oe'] = df_oe_g['o_value'] / df_oe_g['e_value']

            df_g = pd.merge(df_g, df_oe_g, how='left',
                            on=['hospital_id', 'hospital_name', 'basy_yydj', 'discipline_id', 'discipline_name',
                                'doctor_name'])

            df_g['years_months'] = self.year + self.month
            df_g['patient_odd_prop'] = round((df_g['patient_odd_count'] / df_g['patient_count']), 4)
            df_g['supplies_drug'] = Output.supplies_drug_dict[i]

            # 异常病人所属的主治医师
            odd_doctor_df = df.loc[df['{}_odd'.format(i)] == 1, ['hospital_id', 'discipline_id', 'zzys']]
            odd_doctor_df.columns = ['hospital_id', 'discipline_id', 'doctor_name']
            odd_doctor_df.drop_duplicates(inplace=True)
            df_g = pd.merge(df_g, odd_doctor_df, on=['hospital_id', 'discipline_id', 'doctor_name'], how='inner')

            hospital_doctor_df = pd.concat(
                [hospital_doctor_df, df_g[['hospital_id', 'hospital_name', 'years_months', 'discipline_id',
                                           'discipline_name', 'doctor_name', 'patient_count', 'patient_odd_oe',
                                           'patient_odd_count', 'patient_odd_prop', 'supplies_drug']]], axis=0)
        hospital_doctor_df['patient_odd_oe'] = round(hospital_doctor_df['patient_odd_oe'], 2)
        hospital_doctor_df.sort_values(by='patient_odd_oe', ascending=0, inplace=True)
        hospital_doctor_df.reset_index(drop=True, inplace=True)
        hospital_doctor_df.index = hospital_doctor_df.index + 1
        return hospital_doctor_df

    def hospital_overview_result(self, df, hospital_df):
        """
        按各个医院，各个临床学科统计O/E值，
        O为各个医院，各个临床学科耗材费/药品费/检查检验费/总费用的均值，
        E为各个医院等级，各个临床学科耗材费/药品费/检查检验费/总费用的均值
        :return:
        """
        hospital_overview_df = pd.DataFrame()

        for i in Output.supplies_drug_dict.keys():

            df_g = df.groupby(['hospital_id', 'basy_caption', 'basy_yydj',
                               'discipline_id', 'discipline_name']).agg(
                {i: ['mean', 'count'], '{}_odd'.format(i): 'sum', '{}_oe'.format(i): 'mean'}).reset_index()

            df_g.columns = ['hospital_id', 'hospital_name', 'basy_yydj', 'discipline_id', 'discipline_name',
                            'cost_mean', 'patient_count', 'patient_odd_count', 'oe']

            df_g['years_months'] = self.year + self.month
            df_g['patient_normal_count'] = df_g['patient_count'] - df_g['patient_odd_count']
            df_g['ranking'] = ''
            df_g['extent_count'] = 0  # 该字段的计算待后期补充
            df_g['supplies_drug'] = Output.supplies_drug_dict[i]

            hospital_overview_df = pd.concat(
                [hospital_overview_df, df_g[['hospital_id', 'hospital_name', 'years_months',
                                             'discipline_id', 'discipline_name', 'patient_normal_count',
                                             'patient_odd_count', 'oe', 'ranking', 'extent_count',
                                             'supplies_drug']]], axis=0)

        #  discipline_id = 0 时
        hospital_df = hospital_df.loc[:, ['hospital_id', 'hospital_name', 'years_months', 'patient_count',
                                          'patient_odd_count', 'patient_odd_oe', 'supplies_drug']]
        hospital_df.rename(columns={'patient_odd_oe': 'oe'}, inplace=True)
        hospital_df['patient_normal_count'] = hospital_df['patient_count'] - hospital_df['patient_odd_count']
        hospital_df[['discipline_name', 'ranking']] = ''
        hospital_df[['discipline_id', 'extent_count']] = 0

        hospital_overview_df = pd.concat(
            [hospital_overview_df, hospital_df[['hospital_id', 'hospital_name', 'years_months',
                                                'discipline_id', 'discipline_name', 'patient_normal_count',
                                                'patient_odd_count', 'oe', 'ranking', 'extent_count',
                                                'supplies_drug']]], axis=0)

        hospital_overview_df['oe'] = round(hospital_overview_df['oe'], 2)
        hospital_overview_df.sort_values(by='oe', ascending=0, inplace=True)
        hospital_overview_df['ranking'] = range(1, hospital_overview_df.shape[0] + 1, 1)
        hospital_overview_df.reset_index(drop=True, inplace=True)
        hospital_overview_df.index = hospital_overview_df.index + 1
        return hospital_overview_df
