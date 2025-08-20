#!/usr/bin/python
# -*- coding: utf-8 -*-

"""

time: 2022-03-18
description:
    根据需求统计数据，结果保存至./result/

"""

import logging
import os

import pandas as pd

from output_result_1219 import level_jbbm_ssbm_mean, Output
from data_processing import DataProcessing

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s  %(levelname)s  %(message)s')


if __name__ == "__main__":

    supplies_drug_dict = {0: '耗材费', 1: '药品费', 2: '总费用', 3: '检查检验费'}
    min_patient_num = 50
    year = '2024'
    month = '01'
    s_time = '2021-01-01'
    e_time = '2022-08-31'

    # # 获取一整年的数据，作为计算O/E值的E值
    # level_jbbm_ssbm_mean(s_time, e_time, 7, 4, 10)
    #
    # # 根据需求，获取并清洗数据
    # logging.info(f"获取{year}{month}的数据")
    data = DataProcessing(year, month)

    cleaned_data = data.clean_data()
    # exit()
    # quit()
    cleaned_data = pd.read_csv('data/cleaned/cleaned_{}{}.csv'.format(year, month), index_col=0)

    cleaned_data = cleaned_data[~cleaned_data['basy_yydj'].isin(['未评级未评等', '一级甲等',
                                                                 '一级乙等', '一级未评等'])]
    # hospital_id == 0，删除，每隔一段时间更新hospital_id.xlsx
    logging.info(f"hospital_id == 0，共计{cleaned_data[cleaned_data['hospital_id'] == 0].shape[0]}条")
    cleaned_data = cleaned_data[cleaned_data['hospital_id'] != 0]
    logging.info(f"cleaned_data，共计{cleaned_data.shape[0]}条")

    # temp_df = cleaned_data.groupby(['basy_yljgid'])['basy_yljgid'].count().reset_index(name='num')
    # # 医院的住院人次需要 >= min_patient_num，才进入后续统计
    # id_list = temp_df.loc[temp_df['num'] >= min_patient_num, 'basy_yljgid'].tolist()
    # cleaned_data = cleaned_data[cleaned_data['basy_yljgid'].isin(id_list)]
    # logging.info(f"排除住院人次小于{min_patient_num}的医院，剩余{len(id_list)}家，共计{cleaned_data.shape[0]}条")

    load_data = Output(year, month)

    # ------------------- dmiaes_map_hospital_diagnosis.csv -------------------
    # ------------------- temp_scs_odd_supplies.csv -------------------
    # ------------------- temp_scs_odd_supplies.csv -------------------
    # ------------------- dmiaes_map_hospital_patient.csv -------------------.
    level_jbbm_ssbm = pd.read_csv('data/other/level_jbbm_ssbm_{}.csv'.format(e_time.replace('-', '')),
                                  index_col=0)
    hospital_diagnosis_res, odd_supplies_res, odd_zd_res, hospital_patient_result, again_clean_data = \
        load_data.hospital_patient_result(cleaned_data, level_jbbm_ssbm, 500)

    hospital_diagnosis_res.to_csv('result/{}{}/dmiaes_map_hospital_diagnosis.csv'.format(year, month),
                                  index_label='diagnosis_id')
    logging.info(f"dmiaes_map_hospital_diagnosis.csv完成，共计{hospital_diagnosis_res.shape[0]}条,"
                 f"保存至./result/{year}{month}/dmiaes_map_hospital_diagnosis.csv")

    odd_supplies_res.to_csv('result/{}{}/temp_scs_odd_supplies.csv'.format(year, month),
                            index_label='patient_id')
    logging.info(f"temp_scs_odd_supplies.csv完成，共计{odd_supplies_res.shape[0]}条,"
                 f"保存至./result/{year}{month}/temp_scs_odd_supplies.csv")

    odd_zd_res.to_csv('result/{}{}/temp_scs_odd_zd.csv'.format(year, month), index_label='patient_id')
    logging.info(f"temp_scs_odd_zd.csv完成，共计{odd_zd_res.shape[0]}条,"
                 f"保存至./result/{year}{month}/temp_scs_odd_zd.csv")

    hospital_patient_result.to_csv('result/{}{}/dmiaes_map_hospital_patient.csv'.format(year, month),
                                   index_label='patient_id')
    logging.info(f"dmiaes_map_hospital_patient.csv完成，共计{hospital_patient_result.shape[0]}条,"
                 f"保存至./result/{year}{month}/dmiaes_map_hospital_patient.csv")

    # quit()

    # again_clean_data = pd.read_csv('data/cleaned/again_cleaned_{}{}.csv'.format(year, month), index_col=0)

    # ------------------- dmiaes_map.csv -------------------
    area_result = load_data.area_result(again_clean_data)
    area_result.to_csv('result/{}{}/dmiaes_map.csv'.format(year, month), index_label='map_id')
    logging.info(f"dmiaes_map.csv完成，共计{area_result.shape[0]}条，"
                 f"保存至./result/{year}{month}/dmiaes_map.csv")

    # ------------------- dmiaes_map_area.csv -------------------
    discipline_result = load_data.discipline_result(again_clean_data)
    discipline_result.to_csv('result/{}{}/dmiaes_map_area.csv'.format(year, month), index_label='area_id')
    logging.info(f"dmiaes_map_area.csv完成，共计{discipline_result.shape[0]}条，"
                 f"保存至./result/{year}{month}/dmiaes_map_area.csv")

    # ------------------- dmiaes_map_hospital.csv -------------------
    hospital_result = load_data.hospital_result(again_clean_data)
    hospital_result.to_csv('result/{}{}/dmiaes_map_hospital.csv'.format(year, month),
                           index_label='hospital_ranking_id')
    logging.info(f"dmiaes_map_hospital.csv完成，共计{hospital_result.shape[0]}条，"
                 f"保存至./result/{year}{month}/dmiaes_map_hospital.csv")

    # ------------------- dmiaes_map_hospital_dept.csv -------------------
    hospital_dept_result = load_data.hospital_dept_result(again_clean_data)
    hospital_dept_result.to_csv('result/{}{}/dmiaes_map_hospital_dept.csv'.format(year, month),
                                index_label='dept_ranking_id')
    logging.info(f"dmiaes_map_hospital_dept.csv完成，共计{hospital_dept_result.shape[0]}条，"
                 f"保存至./result/{year}{month}/dmiaes_map_hospital_dept.csv")

    # ------------------- dmiaes_map_hospital_doctor.csv -------------------
    hospital_doctor_result = load_data.hospital_doctor_result(again_clean_data)
    hospital_doctor_result.to_csv('result/{}{}/dmiaes_map_hospital_doctor.csv'.format(year, month),
                                  index_label='doctor_ranking_id')
    logging.info(f"dmiaes_map_hospital_doctor.csv完成，共计{hospital_doctor_result.shape[0]}条,"
                 f"保存至./result/{year}{month}/dmiaes_map_hospital_doctor.csv")

    # ------------------- dmiaes_map_hospital_overview.csv -------------------
    hospital_overview_result = load_data.hospital_overview_result(again_clean_data, hospital_result)
    hospital_overview_result.to_csv('result/{}{}/dmiaes_map_hospital_overview.csv'.format(year, month),
                                    index_label='overview_ranking_id')
    logging.info(f"dmiaes_map_hospital_overview.csv完成，共计{hospital_overview_result.shape[0]}条,"
                 f"保存至./result/{year}{month}/dmiaes_map_hospital_overview.csv")
