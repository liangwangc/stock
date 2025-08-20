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

from output_result_2024 import level_jbbm_ssbm_mean, Output
from data_processing_2024_test import DataProcessing

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s  %(levelname)s  %(message)s')


if __name__ == "__main__":

    s_time = '2021-01-01'
    e_time = '2022-08-31'
    kb_dict = {'骨科专业': '骨科专业', '康复医学科': '康复医学科', '血液内科专业': '血液内科专业', '神经外科专业': '神经外科专业', '核医学专业': '核医学专业', 
               '免疫学专业': '免疫学专业', '精神科': '精神科', '胸外科专业': '胸外科专业', '肾病学专业': '肾病学专业', '外科_其他': '其他', '眼科': '眼科', 
               '其他业务科室': '其他业务科室', '消化内科专业': '消化内科专业', '全科医疗科': '全科医疗科', '心血管内科专业': '心血管内科专业', '传染科_其它': '传染科', 
               '小儿外科': '小儿外科', '肿瘤科': '肿瘤科', '急诊医学科': '急诊医学科', '普通外科专业': '普通外科专业', '呼吸内科专业': '呼吸内科专业', 
               '重症医学科': '重症医学科', '耳鼻咽喉科': '耳鼻咽喉科', '心脏大血管外科专业': '心脏大血管外科专业', '疼痛科': '疼痛科', 
               '内分泌专业': '内分泌专业', '皮肤科': '皮肤科', '结核病科': '结核病科', '放射治疗专业': '放射治疗专业', '神经内科专业': '神经内科专业', 
               '泌尿外科专业': '泌尿外科专业'}
    discipline_df = pd.read_excel('D:/yuanjun/SuperviserProject/docs/临床学科字典.xlsx', sheet_name='科室分类与代码')
    # discipline_df['代码'] = discipline_df['代码'].map(lambda a: str(int(a)) if len(a.split('.')) == 1 else "-".join([str(int(i)) for i in a.split('.')]))
    discipline_dict = dict(zip(list(discipline_df['诊疗科目']), list(discipline_df['代码'])))
    column_dict = {"病案号": 'basy_bah', '入院时间':'basy_rysj', '出院时间': 'basy_cysj', '性别': "basy_xb", 
               '出生日期': "basy_csrq", '入院科别': 'basy_rykb', "出院科别": "basy_cykb", 
               "主要手术操作编码": "basy_ssjczbm1", 
               "其他手术操作编码1": "basy_ssjczbm2", "其他手术操作编码2": "basy_ssjczbm3",
               "其他手术操作编码3": "basy_ssjczbm4", "其他手术操作编码4": "basy_ssjczbm5",
               "其他手术操作编码5": "basy_ssjczbm6", "其他手术操作编码6": "basy_ssjczbm7",
               "其他手术操作编码7": "basy_ssjczbm8", "其他手术操作编码8": "basy_ssjczbm9",
               "主要手术操作名称": "basy_ssjczmc1", "其他手术操作名称1": "basy_ssjczmc2",
               "其他手术操作名称2": "basy_ssjczmc3", "其他手术操作名称6": "basy_ssjczmc7",
               "其他手术操作名称3": "basy_ssjczmc4", "其他手术操作名称7": "basy_ssjczmc8",
               "其他手术操作名称4": "basy_ssjczmc5", "其他手术操作名称8": "basy_ssjczmc9",
               "其他手术操作名称5": "basy_ssjczmc6", "其他手术操作名称9": "basy_ssjczmc10",
               "实际住院（天）": "basy_sjzy",
               "出院主要诊断编码": "basy_zyzd_jbbm", "出院主要诊断名称": "basy_zyzd",
               "出院其他诊断编码1": "basy_zyzd_jbbm1", "出院其他诊断名称1": "basy_qtzd1", 
               "出院其他诊断编码2": "basy_zyzd_jbbm2", "出院其他诊断名称2": "basy_qtzd2", 
               "出院其他诊断编码3": "basy_zyzd_jbbm3", "出院其他诊断名称3": "basy_qtzd3", 
               "出院其他诊断编码4": "basy_zyzd_jbbm4", "出院其他诊断名称4": "basy_qtzd4", 
               "出院其他诊断编码5": "basy_zyzd_jbbm5", "出院其他诊断名称5": "basy_qtzd5", 
               "出院其他诊断编码6": "basy_zyzd_jbbm6", "出院其他诊断名称6": "basy_qtzd6", 
               "出院其他诊断编码7": "basy_zyzd_jbbm7", "出院其他诊断名称7": "basy_qtzd7", 
               "出院其他诊断编码8": "basy_zyzd_jbbm8", "出院其他诊断名称8": "basy_qtzd8", 
               "出院其他诊断编码9": "basy_zyzd_jbbm9", "出院其他诊断名称9": "basy_qtzd9", 
               "出院其他诊断编码10": "basy_zyzd_jbbm10", "出院其他诊断名称10": "basy_qtzd10", 
               "出院其他诊断编码11": "basy_zyzd_jbbm11", "出院其他诊断名称11": "basy_qtzd11", 
               "出院其他诊断编码12": "basy_zyzd_jbbm12", "出院其他诊断名称12": "basy_qtzd12", 
               "出院其他诊断编码13": "basy_zyzd_jbbm13", "出院其他诊断名称13": "basy_qtzd13", 
               "出院其他诊断编码14": "basy_zyzd_jbbm14", "出院其他诊断名称14": "basy_qtzd14", 
               "出院其他诊断编码15": "basy_zyzd_jbbm15", "出院其他诊断名称15": "basy_qtzd15"}
    cleaned_data = pd.read_csv("D:/huaxi.csv", encoding='gbk')
    cleaned_data = cleaned_data.rename(columns=column_dict)
    cleaned_data['basy_rykb'] = cleaned_data['basy_rykb'].map(lambda a: discipline_dict[kb_dict[a]])
    cleaned_data['basy_cykb'] = cleaned_data['basy_cykb'].map(lambda a: discipline_dict[kb_dict[a]])

    cleaned_data['总费用'] = cleaned_data['住院总费用']
    cleaned_data['耗材费'] = cleaned_data['21.检查用一次性医用材料费'] + cleaned_data['22.治疗用一次性医用材料费'] + cleaned_data['23.手术用一次性医用材料费']
    cleaned_data['检查检验费'] = cleaned_data['5.病理诊断费'] + cleaned_data['6.实验室诊断费'] + cleaned_data['7.影像学诊断费'] + cleaned_data['8.临床诊断项目费']
    cleaned_data['药品费'] = cleaned_data['13.西药费'] + cleaned_data['14.中成药费'] + cleaned_data['15.中草药费']
    cleaned_data['basy_yydj'] = '三级甲等'
    cleaned_data['basy_yljgid'] = '510000000956'
    cleaned_data['basy_caption'] = '华西'
    cleaned_data['jbbm'] = cleaned_data['basy_zyzd_jbbm'].map(lambda a: a[:7])
    cleaned_data['ssbm'] = cleaned_data['basy_ssjczbm1'].map(lambda a: 'S'+a[:4])
    cleaned_data['ss_mark'] = 0
    cleaned_data['zzys'] = '白求恩'
    cleaned_data['discipline_id'] = "测试"
    cleaned_data['discipline_name'] = "测试"
    cleaned_data['temp_id'] = cleaned_data.apply(lambda a: str(a['basy_bah'])+a['basy_rysj'], axis=1)     #['basy_bah'].str + cleaned_data['basy_rysj']
    # cleaned_data['temp_id'] = cleaned_data['basy_bah']
    cleaned_data['hospital_id'] = "510000000956"
    cleaned_data['basy_zycs'] = 1
    cleaned_data['basy_zfy'] = cleaned_data['总费用']
    cleaned_data['dept_name'] = '测试'
    # print(cleaned_data[['basy_yydj', 'jbbm', 'ssbm']])
    # exit()
    # cleaned_data = cleaned_data.rename(columns=column_dict)

    # cleaned_data = pd.read_csv('', index_col=0)
    print("cleaned_data1", cleaned_data.shape)

    cleaned_data = cleaned_data.drop_duplicates('temp_id')
    print("cleaned_data1", cleaned_data.shape)
    # exit()
    load_data = Output("huaxi", "_oe")

    level_jbbm_ssbm = pd.read_csv('data/other/level_jbbm_ssbm_{}.csv'.format(e_time.replace('-', '')), index_col=0)
    # print(level_jbbm_ssbm)
    again_clean_data = load_data.hospital_patient_resultV2(cleaned_data, level_jbbm_ssbm)
    # print(again_clean_data.shape)
    use_columns = ['temp_id', '总费用', '耗材费', '检查检验费', '药品费', '耗材费_oe', 'level_耗材费_mean', '耗材费_odd_oe', '耗材费_odd_nor_oe', '药品费_oe', 'level_药品费_mean', '药品费_odd_oe', '药品费_odd_nor_oe', '总费用_oe', 'level_总费用_mean', '总费用_odd_oe', '总费用_odd_nor_oe', '检查检验费_oe', 'level_检查检验费_mean', '检查检验费_odd_oe', '检查检验费_odd_nor_oe']
    again_clean_data = again_clean_data[use_columns]
    # print(again_clean_data.columns.tolist())
    cleaned_data = pd.read_csv("D:/huaxi.csv", encoding='gbk')
    cleaned_data['temp_id'] = cleaned_data.apply(lambda a: str(a['病案号'])+a['入院时间'], axis=1)
    print(cleaned_data.shape)
    cleaned_data = pd.merge(left=cleaned_data, right=again_clean_data, on='temp_id', how='left')
    print(cleaned_data.shape)
    del cleaned_data['temp_id']
    cleaned_data.to_csv('国家线索.csv')
    

