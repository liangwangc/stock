# 11.0.32.116 1520  USERNAME: JGM password:jgm123 DB:WCL.syoe_zyba_view WCL.syoe_xyba_view 


import pandas as pd
import os
import numpy as np
import lgbm
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import json

class Report(object):
    """
    Be used in jupyter notebook

    参考Pearson相关系数对rs进行等级划分：当0.9</r/<1，为高度相关；当0.7</r/<0.9，为强相关；0.4</r/<0.7，为中度相关；0.2</r/<0.4，为弱相关性；0</r/<0.2，为极弱相关或无相关性。
    """
    def __init__(self, label_type, all_data, statistic_min_record=20):
        self.statistic_min_record = statistic_min_record
        self.all_df = all_data
        self.label_type = label_type
        # self.get_all_data()
        self.all_df = self.all_df[self.all_df[label_type] > 200]
        self.encode_for_category_dict = None
        self.yydj_dict = None
        # self.get_category_vary_encode()
        # self.feature_process()
        self.train, self.validation = train_test_split(self.all_df, test_size=0.2, random_state=1)
        self.add_e_info()
        self.statistic_train = None
        self.statistic_val = None
        self.loss_metric = None
        self.out_of_statistic_val = None
        self.out_of_statistic_train = None

    @classmethod
    def get_all_data(cls):
        all_df = None
        for i in os.listdir("D:/yuanjun/SuperviserProject/data/cleaned/"):
            # if "again" in i:
            #     continue
            # if i in ["cleaned_202202.csv", "cleaned_202203.csv", "cleaned_202204.csv", "cleaned_202205.csv",
            #          "cleaned_202206.csv", "cleaned_202207.csv"]:
            if i in ["cleaned_202310.csv", "cleaned_202312.csv"]:
                df = pd.read_csv("D:/yuanjun/SuperviserProject/data/cleaned/" + i, usecols=[
                    "basy_yydj", "basy_xb", "basy_csrq", "basy_zyzd_jbbm", "basy_zyzd_jbbm1", "basy_zyzd_jbbm2",
                    "basy_zyzd_jbbm3", "basy_zyzd_jbbm4", "basy_ssjczbm1", "basy_rysj", "basy_cysj", "basy_sjzy",
                    "耗材费", "检查检验费", "药品费", "总费用", "basy_cykb", "basy_rykb", "basy_yljgid"])
                # df = df[~df['basy_yydj'].isin(['未评级未评等', '一级甲等', '一级乙等', '一级未评等'])]
                df = df[~df['basy_yydj'].isin(['一级甲等', '一级乙等', '一级未评等'])]
                df = df.sample(frac=0.8)
                print(i, df.shape)
                if all_df is None:
                    all_df = df
                else:
                    all_df = pd.concat([all_df, df], axis=0)
                # break
                # self.all_df.sort_values()
        encode_for_category_dict, yydj_dict = cls.get_category_vary_encode(all_df)
        f = open('encode_for_category_dict.txt', 'w')
        f.write(json.dumps(encode_for_category_dict))
        f.close()

        f = open('yydj_dict.txt', 'w')
        f.write(json.dumps(yydj_dict))
        f.close()

        all_df = cls.feature_process(all_df, encode_for_category_dict, yydj_dict)
        return all_df

    @classmethod
    def age_group(cls, age):
        if age >= 0 and age < 10:
            return 0
        elif age >= 10 and age < 20:
            return 1
        elif age >= 20 and age < 30:
            return 2
        elif age >= 30 and age < 40:
            return 3
        elif age >= 40 and age < 50:
            return 4
        elif age >= 50 and age < 60:
            return 5
        elif age >= 60 and age < 70:
            return 6
        elif age >= 70 and age < 80:
            return 8
        else:
            return 9


    @classmethod
    def feature_process(cls, all_df, encode_for_category_dict, yydj_dict):
        yydj_dict = {'二级未评等': 1, '二级乙等': 2, '二级甲等': 3, '三级未评等': 4, '三级乙等': 5, '三级甲等': 6,
                     '未评级未评等': 7, '一级甲等': 8, '一级乙等': 9, "一级未评等": 10
        }
        for i in range(3, 10, 1):
            all_df["basy_zyzd_jbbm_%s" % i] = all_df["basy_zyzd_jbbm"].map(
                lambda a: encode_for_category_dict.get(a[:i], 0))
            all_df["basy_zyzd_jbbm_for_str_%s" % i] = all_df["basy_zyzd_jbbm"].map(
                lambda a: a[:i] if isinstance(a, str) else "")

            all_df["basy_ssjczbm1_%s" % i] = all_df["basy_ssjczbm1"].map(
                lambda a: encode_for_category_dict.get(a[:i], 0) if isinstance(a, str) else 0)
            all_df["basy_ssjczbm1_for_str_%s" % i] = all_df["basy_ssjczbm1"].map(
                lambda a: a[:i] if isinstance(a, str) else "")

        all_df["basy_yydj"] = all_df["basy_yydj"].map(lambda a: yydj_dict.get(a, 0))
        # print(all_df["basy_yydj"])
        # exit()
        all_df["age"] = all_df["basy_csrq"].map(lambda a: cls.clean_birthday(a))
        all_df["age_group"] = all_df["age"].map(lambda a: cls.age_group(a))
        all_df["count"] = 1
        all_df["basy_xb"] = all_df["basy_xb"].map(lambda a: cls.clean_sex(a))
        all_df["basy_rykb"] = all_df["basy_rykb"].fillna("101")
        all_df["basy_rykb"] = all_df["basy_rykb"].map(lambda a: int(str(a).split('.')[0]))
        all_df["basy_cykb"] = all_df["basy_cykb"].fillna("101")
        all_df["basy_cykb"] = all_df["basy_cykb"].map(lambda a: int(str(a).split('.')[0]))
        hos_list = list(set(pd.read_csv("D:/yuanjun/SuperviserProject/data/original/hospital_info_V1.csv", usecols=["basy_yljgid"])["basy_yljgid"].tolist()))
        hos_list.sort()
        hos_dict = dict(zip(hos_list, range(len(hos_list) + 1)))
        all_df["basy_yljgid_feature"] = all_df["basy_yljgid"].map(lambda a: hos_dict.get(a, 0))
        return all_df

    def add_e_info(self):
        for i in range(3, 10, 1):
            e_df = self.calculate_e(i, i)
            e_df = e_df[e_df["记录条数-%s-%s" % (i, i)] > self.statistic_min_record]
            e_df.to_csv("%s_%s_%s_1.csv" % (self.label_type, i, i))
            self.validation = pd.merge(self.validation, e_df, how='left', on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj", "basy_ssjczbm1_for_str_%s" % i])
            self.train = pd.merge(self.train, e_df, how='left', on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj", "basy_ssjczbm1_for_str_%s" % i])

            e_df = self.calculate_e(jb_length=i)
            e_df = e_df[e_df["记录条数-%s-%s" % (i, "only_disease")] > self.statistic_min_record]
            e_df.to_csv("%s_%s_%s_2.csv" % (self.label_type, i, "only_disease"))
            self.validation = pd.merge(self.validation, e_df, how='left',
                                       on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj"])
            self.train = pd.merge(self.train, e_df, how='left',
                                  on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj"])

            e_df = self.calculate_e(ss_length=i)
            e_df = e_df[e_df["记录条数-%s-%s" % ("only_operation", i)] > self.statistic_min_record]
            e_df.to_csv("%s_%s_%s_3.csv" % (self.label_type, "only_operation", i))
            self.validation = pd.merge(self.validation, e_df, how='left',
                                       on=["basy_yydj", "basy_ssjczbm1_for_str_%s" % i])
            self.train = pd.merge(self.train, e_df, how='left',
                                  on=["basy_yydj", "basy_ssjczbm1_for_str_%s" % i])

            # age 

            e_df = self.calculate_age_e(i, i)
            e_df = e_df[e_df["记录条数-%s-%s" % (i, i)] > self.statistic_min_record]
            e_df.to_csv("%s_%s_%s_4.csv" % (self.label_type, i, i))
            self.validation = pd.merge(self.validation, e_df, how='left', on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj", "basy_ssjczbm1_for_str_%s" % i, "age_group"])
            self.train = pd.merge(self.train, e_df, how='left', on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj", "basy_ssjczbm1_for_str_%s" % i, "age_group"])

            e_df = self.calculate_age_e(jb_length=i)
            e_df = e_df[e_df["记录条数-%s-%s" % (i, "only_disease")] > self.statistic_min_record]
            e_df.to_csv("%s_%s_%s_5.csv" % (self.label_type, i, "only_disease"))
            self.validation = pd.merge(self.validation, e_df, how='left',
                                       on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj", "age_group"])
            self.train = pd.merge(self.train, e_df, how='left',
                                  on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj", "age_group"])

            e_df = self.calculate_age_e(ss_length=i)
            e_df = e_df[e_df["记录条数-%s-%s" % ("only_operation", i)] > self.statistic_min_record]
            e_df.to_csv("%s_%s_%s_6.csv" % (self.label_type, "only_operation", i))
            self.validation = pd.merge(self.validation, e_df, how='left',
                                       on=["basy_yydj", "basy_ssjczbm1_for_str_%s" % i, "age_group"])
            self.train = pd.merge(self.train, e_df, how='left',
                                  on=["basy_yydj", "basy_ssjczbm1_for_str_%s" % i, "age_group"])

    @classmethod
    def get_category_vary_encode(cls, all_df):

        encode_for_category_dict = dict()
        encode_code = 1
        for i in range(3, 10, 1):
            encode_for_disease_list = list(
                filter(lambda a: isinstance(a, str), list(set(all_df["basy_zyzd_jbbm"].map(lambda a: a[:i]).tolist()))))
            for disease in encode_for_disease_list:
                if disease not in encode_for_category_dict:
                    encode_for_category_dict[disease] = encode_code
                    encode_code = encode_code + 1

            encode_for_operation_list = list(filter(lambda a: isinstance(a, str), list(
                set(all_df["basy_ssjczbm1"].map(lambda a: a[:3] if isinstance(a, str) else "0").tolist()))))
            # print(set(encode_for_operation_list))
            # print(len(set(encode_for_operation_list)))
            # exit()
            for operation in encode_for_operation_list:
                if operation not in encode_for_category_dict:
                    encode_for_category_dict[operation] = encode_code
                    encode_code = encode_code + 1

        basy_yydj_list = list(filter(lambda a: isinstance(a, str), list(
            set(all_df["basy_yydj"].map(lambda a: a[:9] if isinstance(a, str) else "0").tolist()))))
        sorted(basy_yydj_list)

        yydj_dict = dict()

        for i in range(len(basy_yydj_list)):
            yydj_dict[basy_yydj_list[i]] = i + 1
        # self.encode_for_category_dict = encode_for_category_dict
        # self.yydj_dict = yydj_dict
        return encode_for_category_dict, yydj_dict

    @classmethod
    def clean_sex(cls, sex):
        if not isinstance(sex, str):
            return 0
        if '男' in sex:
            return 1
        elif '女' in sex:
            return 2
        else:
            return 0

    @classmethod
    def clean_birthday(cls, birthday, year=2022):
        """
        生日清洗，转化为年龄，大于100岁默认100岁,其余不合法的默认为空
        :param birthday: 出生日期（value_feature_353）
        :param year: 当前年份
        :return: 当前年份的年龄
        """
        birthday = str(birthday)
        if len(birthday) > 4:
            age = year - int(birthday[:4])
            if age >= 100:
                return 100
            elif age >= 0:
                return age
            else:
                return np.nan
        else:
            return np.nan

    def show_age_distribution(self):
        age_s = self.all_df["basy_csrq"].map(lambda a: 2023 - int(str(a)[:4]))
        age_s = age_s[age_s.index < 90]
        age_value_count_s = age_s.value_counts(normalize=True).sort_index()
        age_value_count_s[age_value_count_s.index < 80].plot(xlabel="AGE", ylabel="RATIO")

    def data_profile(self):
        pass

    def oe_loss_objective(self, preds, train_data):
        y = train_data.get_label()

        # p = special.expit(preds)
        # grad = 0.01*2*y*(preds-y)/(preds**3 + 1) + preds-y
        # grad = preds-y  #  + 0.4 * preds
        # grad = preds - y  #  + 0.4 * preds
        # hess = [1 for _ in range(len(y))]
        # grad = (preds - y)
        # hess = [1 for _ in range(len(y))]
        grad = (preds - y)/y + (preds - y)*0.01
        hess = 1/y + 0.01
        # hess = 1
        # hess = 0.01*(-4*y/(preds**3 + 1) + 6*(y**2)/(preds**4 + 1)) + 1
        return grad, hess

    def oe_loss_metric(self, preds, train_data):

        y = train_data.get_label()
        # print("O", y, len(y), type(y))
        # print("E", preds, len(preds), type(preds))

        # p = special.expit(preds)

        # ll = np.sqrt(np.mean((y/preds-1)**2))
        ll = np.sqrt(mean_squared_error(y, preds))
        self.loss_metric[len(preds)].append(ll)

        return 'oeloss', ll, False

    def calculate_age_e(self, jb_length=None, ss_length=None):
        if jb_length is not None and ss_length is not None:
            e_df = self.train.groupby(["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj", "basy_ssjczbm1_for_str_%s" % ss_length, "age_group"]).agg({
                '耗材费': 'mean',
                '检查检验费': 'mean',
                '药品费': 'mean',
                '总费用': 'mean',
                'count': 'count'}).reset_index()
            e_df = e_df.rename(
                columns={"耗材费": "AGE-HAOCAI-%s-%s-E" % (jb_length, ss_length),
                         "检查检验费": "AGE-JCJY-%s-%s-E" % (jb_length, ss_length),
                         "药品费": "AGE-YP-%s-%s-E" % (jb_length, ss_length),
                         "总费用": "AGE-ZFY-%s-%s-E" % (jb_length, ss_length), "count": "记录条数-%s-%s" % (jb_length, ss_length)})
            return e_df
        elif jb_length is not None and ss_length is None:
            ss_length = "only_disease"
            e_df = self.train.groupby(
                ["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj", "age_group"]).agg({
                    '耗材费': 'mean',
                    '检查检验费': 'mean',
                    '药品费': 'mean',
                    '总费用': 'mean',
                    'count': 'count'}).reset_index()
            e_df = e_df.rename(
                columns={"耗材费": "AGE-HAOCAI-%s-%s-E" % (jb_length, ss_length),
                         "检查检验费": "AGE-JCJY-%s-%s-E" % (jb_length, ss_length),
                         "药品费": "AGE-YP-%s-%s-E" % (jb_length, ss_length),
                         "总费用": "AGE-ZFY-%s-%s-E" % (jb_length, ss_length), "count": "记录条数-%s-%s" % (jb_length, ss_length)})
            return e_df
        elif jb_length is None and ss_length is not None:
            jb_length = "only_operation"
            e_df = self.train.groupby(
                ["basy_yydj", "basy_ssjczbm1_for_str_%s" % ss_length, "age_group"]).agg({
                '耗材费': 'mean',
                '检查检验费': 'mean',
                '药品费': 'mean',
                '总费用': 'mean',
                'count': 'count'}).reset_index()
            e_df = e_df.rename(
                columns={"耗材费": "AGE-HAOCAI-%s-%s-E" % (jb_length, ss_length),
                         "检查检验费": "AGE-JCJY-%s-%s-E" % (jb_length, ss_length),
                         "药品费": "AGE-YP-%s-%s-E" % (jb_length, ss_length),
                         "总费用": "AGE-ZFY-%s-%s-E" % (jb_length, ss_length), "count": "记录条数-%s-%s" % (jb_length, ss_length)})
            return e_df
        else:
            return "parameter error"

    def calculate_e(self, jb_length=None, ss_length=None):
        if jb_length is not None and ss_length is not None:
            e_df = self.train.groupby(["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj", "basy_ssjczbm1_for_str_%s" % ss_length]).agg({
                '耗材费': 'mean',
                '检查检验费': 'mean',
                '药品费': 'mean',
                '总费用': 'mean',
                'count': 'count'}).reset_index()
            e_df = e_df.rename(
                columns={"耗材费": "HAOCAI-%s-%s-E" % (jb_length, ss_length),
                         "检查检验费": "JCJY-%s-%s-E" % (jb_length, ss_length),
                         "药品费": "YP-%s-%s-E" % (jb_length, ss_length),
                         "总费用": "ZFY-%s-%s-E" % (jb_length, ss_length), "count": "记录条数-%s-%s" % (jb_length, ss_length)})
            return e_df
        elif jb_length is not None and ss_length is None:
            ss_length = "only_disease"
            e_df = self.train.groupby(
                ["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj"]).agg({
                    '耗材费': 'mean',
                    '检查检验费': 'mean',
                    '药品费': 'mean',
                    '总费用': 'mean',
                    'count': 'count'}).reset_index()
            e_df = e_df.rename(
                columns={"耗材费": "HAOCAI-%s-%s-E" % (jb_length, ss_length),
                         "检查检验费": "JCJY-%s-%s-E" % (jb_length, ss_length),
                         "药品费": "YP-%s-%s-E" % (jb_length, ss_length),
                         "总费用": "ZFY-%s-%s-E" % (jb_length, ss_length), "count": "记录条数-%s-%s" % (jb_length, ss_length)})
            return e_df
        elif jb_length is None and ss_length is not None:
            jb_length = "only_operation"
            e_df = self.train.groupby(
                ["basy_yydj", "basy_ssjczbm1_for_str_%s" % ss_length]).agg({
                '耗材费': 'mean',
                '检查检验费': 'mean',
                '药品费': 'mean',
                '总费用': 'mean',
                'count': 'count'}).reset_index()
            e_df = e_df.rename(
                columns={"耗材费": "HAOCAI-%s-%s-E" % (jb_length, ss_length),
                         "检查检验费": "JCJY-%s-%s-E" % (jb_length, ss_length),
                         "药品费": "YP-%s-%s-E" % (jb_length, ss_length),
                         "总费用": "ZFY-%s-%s-E" % (jb_length, ss_length), "count": "记录条数-%s-%s" % (jb_length, ss_length)})
            return e_df
        else:
            return "parameter error"

    def yydj_jbbm_ssbm_model(self, label, jb_length, ss_length):
        e_column_name = "%s-%s-%s-E" % (label, jb_length, ss_length)
        print("valibation:", self.validation.shape)
        self.statistic_val = self.validation[~self.validation[e_column_name].isnull()]
        self.out_of_statistic_val = self.validation[self.validation[e_column_name].isnull()]
        print("val_result:",  self.statistic_val.shape)

        self.validation = self.validation.rename(
            columns={"耗材费": "HAOCAI", "检查检验费": "JCJY", "药品费": "YP", "总费用": "ZFY", "count": "记录条数"})
        self.statistic_val = self.statistic_val.rename(
            columns={"耗材费": "HAOCAI", "检查检验费": "JCJY", "药品费": "YP", "总费用": "ZFY", "count": "记录条数"})
        self.out_of_statistic_val = self.out_of_statistic_val.rename(
            columns={"耗材费": "HAOCAI", "检查检验费": "JCJY", "药品费": "YP", "总费用": "ZFY", "count": "记录条数"})

        val_rmse = np.sqrt(mean_squared_error(self.statistic_val[label],  self.statistic_val[e_column_name]))
        val_moe = (self.statistic_val[label] / self.statistic_val[e_column_name]).mean()
        val_std = (self.statistic_val[label] / self.statistic_val[e_column_name]).std()
        val_max = (self.statistic_val[label] / self.statistic_val[e_column_name]).max()

        print("train:", self.train.shape)
        self.statistic_train = self.train[~self.train[e_column_name].isnull()]
        self.out_of_statistic_train = self.train[self.train[e_column_name].isnull()]
        print("train_result", self.statistic_train.shape)

        self.train = self.train.rename(
            columns={"耗材费": "HAOCAI", "检查检验费": "JCJY", "药品费": "YP", "总费用": "ZFY", "count": "记录条数"})
        self.statistic_train = self.statistic_train.rename(
            columns={"耗材费": "HAOCAI", "检查检验费": "JCJY", "药品费": "YP", "总费用": "ZFY", "count": "记录条数"})
        self.out_of_statistic_train = self.out_of_statistic_train.rename(
            columns={"耗材费": "HAOCAI", "检查检验费": "JCJY", "药品费": "YP", "总费用": "ZFY", "count": "记录条数"})

        train_rmse = np.sqrt(mean_squared_error(self.statistic_train[label], self.statistic_train[e_column_name]))
        train_moe = (self.statistic_train[label] / self.statistic_train[e_column_name]).mean()
        train_std = (self.statistic_train[label] / self.statistic_train[e_column_name]).std()
        train_max = (self.statistic_train[label] / self.statistic_train[e_column_name]).max()

        result_dict = {
            "V_0": self.validation.shape, "V_1": self.statistic_val.shape,
            "VAL_RMSE": val_rmse, "VAL_MOE": val_moe, "VAL_STD": val_std, "VAL_MAX": val_max,
            "T_0": self.train.shape, "T_1": self.statistic_train.shape,
            "TRAIN_RMSE": train_rmse, "TRAIN_MOE": train_moe, "TRAIN_STD": train_std, "TRAIN_MAX": train_max
        }

        return self.statistic_train, self.statistic_val, result_dict

    def show_train_model(self, train, validation, feature_list, category_feature, label_col, p_objective='mean_squared_error',
                         p_metric='rmse', p_max_depth=6, p_num_leaves=32, p_min_data_in_leaf=10, p_learning_rate=0.2,
                         p_min_sum_hessian_in_leaf=5,  p_lambda_l2=0.1, num_boost_round=300):
        self.loss_metric = {
            train.shape[0]: list(),
            validation.shape[0]: list()
        }
        train_info = {
            "feature_list": feature_list, "category_feature": category_feature, "label_col": label_col,
            "p_objective": p_objective, "p_metric": p_metric, "p_max_depth": p_max_depth, "p_num_leaves": p_num_leaves,
            "p_min_data_in_leaf": p_min_data_in_leaf, "p_learning_rate": p_learning_rate,
            "p_min_sum_hessian_in_leaf": p_min_sum_hessian_in_leaf, "p_lambda_l2": p_lambda_l2,
            "num_boost_round": num_boost_round
        }

        # temp_feature_list = [label_col]
        # temp_feature_list.extend(feature_list)

        x_train = train.loc[:, feature_list]
        y_train = train.loc[:, label_col]

        train_info["train_data"] = train.shape

        x_valid = validation.loc[:, feature_list]
        y_valid = validation.loc[:, label_col]

        train_info["valid_data"] = x_valid.shape

        # 参数配置
        param = lgbm.param_dict(p_objective=p_objective, p_metric=p_metric, p_max_depth=p_max_depth, p_num_leaves=p_num_leaves,
                                p_min_data_in_leaf=p_min_data_in_leaf, p_learning_rate=p_learning_rate,
                                p_min_sum_hessian_in_leaf=p_min_sum_hessian_in_leaf, p_lambda_l2=p_lambda_l2)
        # param = lgbm.param_dict(p_objective='oe_loss_objective', p_metric='oe_loss_metric', p_max_depth=9,
        #                         p_num_leaves=128,
        #                         p_min_data_in_leaf=15, p_learning_rate=1, p_min_sum_hessian_in_leaf=15,
        #                         p_lambda_l1=0.01, p_lambda_l2=0.02, p_min_gain_to_split=0.01)
        # 模型训练
        lgbm_model = lgbm.lgbm_train(x_train, y_train, x_valid, y_valid,
                                     feature_list=feature_list,
                                     categorical_feature_list=category_feature,
                                     param=param,
                                     num_boost_round=num_boost_round,
                                     # obj_func=oe_loss_objective,
                                     obj_func=None,
                                     eval_func=self.oe_loss_metric,
                                     # eval_func=None,
                                     verbose_eval=1)
        # 计算特征重要性
        importance_df = lgbm.feature_importance(lgbm_model)

        # lgbm_model.save_model('model/lgbm_model_{}.model'.format(label_col))
        # label_dict = {
        #     "药品费": "yp", "检查检验费": "jcjy", "耗材费": "hc", "总费用": "zfy"
        # }
        lgbm_model.save_model('model/lgbm_model_{}.model'.format(label_col))
        # importance_df.to_csv('model/feature_importance_df_{}.csv'.format(label_col))
        importance_df.to_csv('model/feature_importance_df_{}.csv'.format(label_col))
        val_rmse = np.sqrt(mean_squared_error(lgbm_model.predict(x_valid[feature_list]), y_valid))

        # print("Final O", y_train.to_numpy(), len(y_train))
        # print("Final E", lgbm_model.predict(train[feature_list], num_iteration=-1), train.shape)
        train_rmse = np.sqrt(mean_squared_error(lgbm_model.predict(x_train[feature_list]), y_train))

        val_moe = (y_valid / lgbm_model.predict(x_valid[feature_list])).mean()
        val_std = (y_valid / lgbm_model.predict(x_valid[feature_list])).std()
        val_max = (y_valid / lgbm_model.predict(x_valid[feature_list])).max()

        train_moe = (y_train / lgbm_model.predict(x_train[feature_list])).mean()
        train_std = (y_train / lgbm_model.predict(x_train[feature_list])).std()
        train_max = (y_train / lgbm_model.predict(x_train[feature_list])).max()
        result_info = {"MODEL_VAL_RMSE": val_rmse, "MODEL_TRAIN_RMSE": train_rmse, "MODEL_TRAIN_MAX": train_max,
                        "MODEL_VAL_MOE": val_moe, "MODEL_VAL_STD": val_std, "MODEL_VAL_MAX": val_max,
                        "MODEL_TRAIN_MOE": train_moe, "MODEL_TRAIN_STD": train_std}
        return train_info, result_info


    def show_train_model_v2(self, train, validation, feature_list, category_feature, label_col, p_objective='mean_squared_error',
                         p_metric='rmse', p_max_depth=6, p_num_leaves=32, p_min_data_in_leaf=10, p_learning_rate=0.2,
                         p_min_sum_hessian_in_leaf=5,  p_lambda_l2=0.1, num_boost_round=300):
        self.loss_metric = {
            train.shape[0]: list(),
            validation.shape[0]: list()
        }
        train_info = {
            "feature_list": feature_list, "category_feature": category_feature, "label_col": label_col,
            "p_objective": p_objective, "p_metric": p_metric, "p_max_depth": p_max_depth, "p_num_leaves": p_num_leaves,
            "p_min_data_in_leaf": p_min_data_in_leaf, "p_learning_rate": p_learning_rate,
            "p_min_sum_hessian_in_leaf": p_min_sum_hessian_in_leaf, "p_lambda_l2": p_lambda_l2,
            "num_boost_round": num_boost_round
        }

        # temp_feature_list = [label_col]
        # temp_feature_list.extend(feature_list)

        x_train = train.loc[:, feature_list]
        y_train = train.loc[:, label_col]

        train_info["train_data"] = train.shape

        x_valid = validation.loc[:, feature_list]
        y_valid = validation.loc[:, label_col]

        x_train_predictable = self.statistic_train.loc[:, feature_list]
        y_train_predictable = self.statistic_train.loc[:, label_col]

        outta_x_train_predictable = self.out_of_statistic_train.loc[:, feature_list]
        outta_y_train_predictable = self.out_of_statistic_train.loc[:, label_col]

        x_val_predictable = self.statistic_val.loc[:, feature_list]
        y_val_predictable = self.statistic_val.loc[:, label_col]

        outta_x_val_predictable = self.out_of_statistic_val.loc[:, feature_list]
        outta_y_val_predictable = self.out_of_statistic_val.loc[:, label_col]


        train_info["valid_data"] = x_valid.shape

        # 参数配置
        param = lgbm.param_dict(p_objective=p_objective, p_metric=p_metric, p_max_depth=p_max_depth, p_num_leaves=p_num_leaves,
                                p_min_data_in_leaf=p_min_data_in_leaf, p_learning_rate=p_learning_rate,
                                p_min_sum_hessian_in_leaf=p_min_sum_hessian_in_leaf, p_lambda_l2=p_lambda_l2)
        # param = lgbm.param_dict(p_objective='oe_loss_objective', p_metric='oe_loss_metric', p_max_depth=9,
        #                         p_num_leaves=128,
        #                         p_min_data_in_leaf=15, p_learning_rate=1, p_min_sum_hessian_in_leaf=15,
        #                         p_lambda_l1=0.01, p_lambda_l2=0.02, p_min_gain_to_split=0.01)
        # 模型训练
        lgbm_model = lgbm.lgbm_train(x_train, y_train, x_valid, y_valid,
                                     feature_list=feature_list,
                                     categorical_feature_list=category_feature,
                                     param=param,
                                     num_boost_round=num_boost_round,
                                     # obj_func=oe_loss_objective,
                                     obj_func=None,
                                     eval_func=self.oe_loss_metric,
                                     # eval_func=None,
                                     verbose_eval=1)
        # 计算特征重要性
        importance_df = lgbm.feature_importance(lgbm_model)

        # lgbm_model.save_model('model/lgbm_model_{}.model'.format(label_col))
        # label_dict = {
        #     "药品费": "yp", "检查检验费": "jcjy", "耗材费": "hc", "总费用": "zfy"
        # }
        lgbm_model.save_model('model/lgbm_model_{}.model'.format(label_col))
        # importance_df.to_csv('model/feature_importance_df_{}.csv'.format(label_col))
        importance_df.to_csv('model/feature_importance_df_{}.csv'.format(label_col))
        val_rmse = np.sqrt(mean_squared_error(lgbm_model.predict(x_valid[feature_list]), y_valid))

        # print("Final O", y_train.to_numpy(), len(y_train))
        # print("Final E", lgbm_model.predict(train[feature_list], num_iteration=-1), train.shape)
        train_rmse = np.sqrt(mean_squared_error(lgbm_model.predict(x_train[feature_list]), y_train))

        val_moe = (y_valid / lgbm_model.predict(x_valid[feature_list])).mean()
        val_std = (y_valid / lgbm_model.predict(x_valid[feature_list])).std()
        val_max = (y_valid / lgbm_model.predict(x_valid[feature_list])).max()

        train_moe = (y_train / lgbm_model.predict(x_train[feature_list])).mean()
        train_std = (y_train / lgbm_model.predict(x_train[feature_list])).std()
        train_max = (y_train / lgbm_model.predict(x_train[feature_list])).max()

        y_train_predictable_predict = lgbm_model.predict(x_train_predictable[feature_list])
        y_train_predictable_oe_list = y_train_predictable / y_train_predictable_predict
        y_train_predictable_moe = y_train_predictable_oe_list.mean()
        y_train_predictable_std = y_train_predictable_oe_list.std()
        y_train_predictable_max = y_train_predictable_oe_list.max()
        y_train_predictable_rmse = np.sqrt(mean_squared_error(y_train_predictable_predict, y_train_predictable))

        outta_y_train_predictable_predict = lgbm_model.predict(outta_x_train_predictable[feature_list])
        outta_y_train_predictable_oe_list = outta_y_train_predictable / outta_y_train_predictable_predict
        outta_y_train_predictable_moe = outta_y_train_predictable_oe_list.mean()
        outta_y_train_predictable_std = outta_y_train_predictable_oe_list.std()
        outta_y_train_predictable_max = outta_y_train_predictable_oe_list.max()
        outta_y_train_predictable_rmse = np.sqrt(mean_squared_error(outta_y_train_predictable_predict, outta_y_train_predictable))

        y_val_predictable_predcit = lgbm_model.predict(x_val_predictable[feature_list])
        y_val_predictable_oe_list = y_val_predictable / y_val_predictable_predcit
        y_val_predictable_moe = y_val_predictable_oe_list.mean()
        y_val_predictable_std = y_val_predictable_oe_list.std()
        y_val_predictable_max = y_val_predictable_oe_list.max()
        y_val_predictable_rmse = np.sqrt(mean_squared_error(y_val_predictable_predcit, y_val_predictable))

        outta_y_val_predictable_predict = lgbm_model.predict(outta_x_val_predictable[feature_list])
        outta_y_val_predictable_oe_list = outta_y_val_predictable / outta_y_val_predictable_predict
        outta_y_val_predictable_moe = outta_y_val_predictable_oe_list.mean()
        outta_y_val_predictable_std = outta_y_val_predictable_oe_list.std()
        outta_y_val_predictable_max = outta_y_val_predictable_oe_list.max()
        outta_y_val_predictable_rmse = np.sqrt(mean_squared_error(outta_y_val_predictable_predict, outta_y_val_predictable))

        result_info = {"MODEL_VAL_RMSE": val_rmse, "MODEL_TRAIN_RMSE": train_rmse, "MODEL_TRAIN_MAX": train_max,
                        "MODEL_VAL_MOE": val_moe, "MODEL_VAL_STD": val_std, "MODEL_VAL_MAX": val_max,
                        "MODEL_TRAIN_MOE": train_moe, "MODEL_TRAIN_STD": train_std,
                        "y_train_predictable_moe": y_train_predictable_moe, "y_train_predictable_std": y_train_predictable_std,
                        "y_train_predictable_max": y_train_predictable_max, "y_train_predictable_rmse": y_train_predictable_rmse,
                        "outta_y_train_predictable_moe": outta_y_train_predictable_moe, "outta_y_train_predictable_std": outta_y_train_predictable_std,
                        "outta_y_train_predictable_max": outta_y_train_predictable_max,  "outta_y_train_predictable_rmse": outta_y_train_predictable_rmse,
                        "y_val_predictable_moe": y_val_predictable_moe, "y_val_predictable_std": y_val_predictable_std, 
                        "y_val_predictable_max": y_val_predictable_max, "y_val_predictable_rmse": y_val_predictable_rmse,
                        "outta_y_val_predictable_moe": outta_y_val_predictable_moe, "outta_y_val_predictable_std": outta_y_val_predictable_std,
                        "outta_y_val_predictable_max": outta_y_val_predictable_max, "outta_y_val_predictable_rmse": outta_y_val_predictable_rmse,
                        "y_train_predictable_oe_list": [y_train_predictable, lgbm_model.predict(x_train_predictable[feature_list])],
                        "outta_y_train_predictable_oe_list": [outta_y_train_predictable, lgbm_model.predict(outta_x_train_predictable[feature_list])],
                        "y_val_predictable_oe_list": [y_val_predictable, lgbm_model.predict(x_val_predictable[feature_list])],
                        "outta_y_val_predictable_oe_list": [outta_y_val_predictable, lgbm_model.predict(outta_x_val_predictable[feature_list])]
                        }
        return train_info, result_info


    def show_train_model_v3(self, train, validation, feature_list, category_feature, label_col, p_objective='mean_squared_error',
                         p_metric='rmse', p_max_depth=6, p_num_leaves=32, p_min_data_in_leaf=10, p_learning_rate=0.2,
                         p_min_sum_hessian_in_leaf=5,  p_lambda_l2=0.1, num_boost_round=300):
        self.loss_metric = {
            train.shape[0]: list(),
            validation.shape[0]: list()
        }
        train_info = {
            "feature_list": feature_list, "category_feature": category_feature, "label_col": label_col,
            "p_objective": p_objective, "p_metric": p_metric, "p_max_depth": p_max_depth, "p_num_leaves": p_num_leaves,
            "p_min_data_in_leaf": p_min_data_in_leaf, "p_learning_rate": p_learning_rate,
            "p_min_sum_hessian_in_leaf": p_min_sum_hessian_in_leaf, "p_lambda_l2": p_lambda_l2,
            "num_boost_round": num_boost_round
        }

        # temp_feature_list = [label_col]
        # temp_feature_list.extend(feature_list)

        x_train = train.loc[:, feature_list]
        y_train = train.loc[:, label_col]

        train_info["train_data"] = train.shape

        x_valid = validation.loc[:, feature_list]
        y_valid = validation.loc[:, label_col]

        x_train_predictable = self.statistic_train.loc[:, feature_list]
        y_train_predictable = self.statistic_train.loc[:, label_col]

        outta_x_train_predictable = self.out_of_statistic_train.loc[:, feature_list]
        outta_y_train_predictable = self.out_of_statistic_train.loc[:, label_col]

        x_val_predictable = self.statistic_val.loc[:, feature_list]
        y_val_predictable = self.statistic_val.loc[:, label_col]

        outta_x_val_predictable = self.out_of_statistic_val.loc[:, feature_list]
        outta_y_val_predictable = self.out_of_statistic_val.loc[:, label_col]


        train_info["valid_data"] = x_valid.shape

        # 参数配置
        param = lgbm.param_dict(p_objective=p_objective, p_metric=p_metric, p_max_depth=p_max_depth, p_num_leaves=p_num_leaves,
                                p_min_data_in_leaf=p_min_data_in_leaf, p_learning_rate=p_learning_rate,
                                p_min_sum_hessian_in_leaf=p_min_sum_hessian_in_leaf, p_lambda_l2=p_lambda_l2)
        # param = lgbm.param_dict(p_objective='oe_loss_objective', p_metric='oe_loss_metric', p_max_depth=9,
        #                         p_num_leaves=128,
        #                         p_min_data_in_leaf=15, p_learning_rate=1, p_min_sum_hessian_in_leaf=15,
        #                         p_lambda_l1=0.01, p_lambda_l2=0.02, p_min_gain_to_split=0.01)
        # 模型训练
        lgbm_model = lgbm.lgbm_train(x_train, y_train, x_valid, y_valid,
                                     feature_list=feature_list,
                                     categorical_feature_list=category_feature,
                                     param=param,
                                     num_boost_round=num_boost_round,
                                     # obj_func=self.oe_loss_objective,
                                     obj_func=None,
                                     eval_func=self.oe_loss_metric,
                                     # eval_func=None,
                                     verbose_eval=1)

        train["predict_0"] = lgbm_model.predict(train[feature_list])

        train["O/E"] = train[label_col] / train["predict_0"]
        train_O_E_list = train["O/E"].tolist()
        train_O_E_list.sort()
        min_o_e = train_O_E_list[int(len(train_O_E_list)/1000)]
        max_o_e = train_O_E_list[int(999*len(train_O_E_list)/1000)]
        print("O/E,PRE最小值和最大值", train["O/E"].min(), train["O/E"].max(), train.shape)
        train_1 = train[(train["O/E"] > min_o_e) & (train["O/E"] < max_o_e)]
        print("O/E,POST最小值和最大值", train_1["O/E"].min(), train_1["O/E"].max(), train_1["O/E"].mean(), train_1.shape)

        remove_train = train[~((train["O/E"] > min_o_e) & (train["O/E"] < max_o_e))]
        remove_predict_list = remove_train["predict_0"]
        remove_practice_list = remove_train[label_col]

        x_train = train_1.loc[:, feature_list]
        y_train = train_1.loc[:, label_col]
        self.loss_metric= {
            x_train.shape[0]: [],
            x_valid.shape[0]: []
        }

        param_1 = lgbm.param_dict(p_objective=p_objective, p_metric=p_metric, p_max_depth=p_max_depth, p_num_leaves=p_num_leaves,
                                p_min_data_in_leaf=p_min_data_in_leaf, p_learning_rate=p_learning_rate,
                                p_min_sum_hessian_in_leaf=p_min_sum_hessian_in_leaf, p_lambda_l2=p_lambda_l2)

        lgbm_model = lgbm.lgbm_train(x_train, y_train, x_valid, y_valid,
                                     feature_list=feature_list,
                                     categorical_feature_list=category_feature,
                                     param=param_1,
                                     num_boost_round=num_boost_round,
                                     # obj_func=self.oe_loss_objective,
                                     obj_func=None,
                                     eval_func=self.oe_loss_metric,
                                     # eval_func=None,
                                     verbose_eval=1)
        
        # validation["O/E"] = validation[label_col] / validation["predict_0"]
        # train.sort_values(by="O/E", inplace=True)
        # validation.sort_values(by="O/E", inplace=True)


        # 计算特征重要性
        importance_df = lgbm.feature_importance(lgbm_model)

        # lgbm_model.save_model('model/lgbm_model_{}.model'.format(label_col))
        # label_dict = {
        #     "药品费": "yp", "检查检验费": "jcjy", "耗材费": "hc", "总费用": "zfy"
        # }
        lgbm_model.save_model('model/lgbm_model_{}.model'.format(label_col))
        # importance_df.to_csv('model/feature_importance_df_{}.csv'.format(label_col))
        importance_df.to_csv('model/feature_importance_df_{}.csv'.format(label_col))
        val_rmse = np.sqrt(mean_squared_error(lgbm_model.predict(x_valid[feature_list]), y_valid))

        # print("Final O", y_train.to_numpy(), len(y_train))
        # print("Final E", lgbm_model.predict(train[feature_list], num_iteration=-1), train.shape)
        train_rmse = np.sqrt(mean_squared_error(lgbm_model.predict(x_train[feature_list]), y_train))



        val_moe = (y_valid / lgbm_model.predict(x_valid[feature_list])).mean()
        val_std = (y_valid / lgbm_model.predict(x_valid[feature_list])).std()
        val_max = (y_valid / lgbm_model.predict(x_valid[feature_list])).max()

        y_train_oe_list = y_train / lgbm_model.predict(x_train[feature_list])
        train_moe = y_train_oe_list.mean()
        train_std = y_train_oe_list.std()
        train_max = y_train_oe_list.max()
        print("After:", y_train_oe_list.min(), y_train_oe_list.max(), y_train_oe_list.mean())

        y_train_predictable_predict = lgbm_model.predict(x_train_predictable[feature_list])
        y_train_predictable_oe_list = y_train_predictable / y_train_predictable_predict
        y_train_predictable_moe = y_train_predictable_oe_list.mean()
        y_train_predictable_std = y_train_predictable_oe_list.std()
        y_train_predictable_max = y_train_predictable_oe_list.max()
        y_train_predictable_rmse = np.sqrt(mean_squared_error(y_train_predictable_predict, y_train_predictable))

        outta_y_train_predictable_predict = lgbm_model.predict(outta_x_train_predictable[feature_list])
        outta_y_train_predictable_oe_list = outta_y_train_predictable / outta_y_train_predictable_predict
        outta_y_train_predictable_moe = outta_y_train_predictable_oe_list.mean()
        outta_y_train_predictable_std = outta_y_train_predictable_oe_list.std()
        outta_y_train_predictable_max = outta_y_train_predictable_oe_list.max()
        outta_y_train_predictable_rmse = np.sqrt(mean_squared_error(outta_y_train_predictable_predict, outta_y_train_predictable))

        y_val_predictable_predcit = lgbm_model.predict(x_val_predictable[feature_list])
        y_val_predictable_oe_list = y_val_predictable / y_val_predictable_predcit
        y_val_predictable_moe = y_val_predictable_oe_list.mean()
        y_val_predictable_std = y_val_predictable_oe_list.std()
        y_val_predictable_max = y_val_predictable_oe_list.max()
        y_val_predictable_rmse = np.sqrt(mean_squared_error(y_val_predictable_predcit, y_val_predictable))

        outta_y_val_predictable_predict = lgbm_model.predict(outta_x_val_predictable[feature_list])
        outta_y_val_predictable_oe_list = outta_y_val_predictable / outta_y_val_predictable_predict
        outta_y_val_predictable_moe = outta_y_val_predictable_oe_list.mean()
        outta_y_val_predictable_std = outta_y_val_predictable_oe_list.std()
        outta_y_val_predictable_max = outta_y_val_predictable_oe_list.max()
        outta_y_val_predictable_rmse = np.sqrt(mean_squared_error(outta_y_val_predictable_predict, outta_y_val_predictable))

        result_info = {"MODEL_VAL_RMSE": val_rmse, "MODEL_TRAIN_RMSE": train_rmse, "MODEL_TRAIN_MAX": train_max,
                        "MODEL_VAL_MOE": val_moe, "MODEL_VAL_STD": val_std, "MODEL_VAL_MAX": val_max,
                        "MODEL_TRAIN_MOE": train_moe, "MODEL_TRAIN_STD": train_std,
                        "y_train_predictable_moe": y_train_predictable_moe, "y_train_predictable_std": y_train_predictable_std,
                        "y_train_predictable_max": y_train_predictable_max, "y_train_predictable_rmse": y_train_predictable_rmse,
                        "outta_y_train_predictable_moe": outta_y_train_predictable_moe, "outta_y_train_predictable_std": outta_y_train_predictable_std,
                        "outta_y_train_predictable_max": outta_y_train_predictable_max,  "outta_y_train_predictable_rmse": outta_y_train_predictable_rmse,
                        "y_val_predictable_moe": y_val_predictable_moe, "y_val_predictable_std": y_val_predictable_std, 
                        "y_val_predictable_max": y_val_predictable_max, "y_val_predictable_rmse": y_val_predictable_rmse,
                        "outta_y_val_predictable_moe": outta_y_val_predictable_moe, "outta_y_val_predictable_std": outta_y_val_predictable_std,
                        "outta_y_val_predictable_max": outta_y_val_predictable_max, "outta_y_val_predictable_rmse": outta_y_val_predictable_rmse,
                        # "y_train_predictable_oe_list": [y_train_predictable, lgbm_model.predict(x_train_predictable[feature_list])],
                        # "outta_y_train_predictable_oe_list": [outta_y_train_predictable, lgbm_model.predict(outta_x_train_predictable[feature_list])],
                        # "y_val_predictable_oe_list": [y_val_predictable, lgbm_model.predict(x_val_predictable[feature_list])],
                        # "outta_y_val_predictable_oe_list": [outta_y_val_predictable, lgbm_model.predict(outta_x_val_predictable[feature_list])],
                        # "y_train_oe_list": [y_train, lgbm_model.predict(x_train[feature_list])],
                        # "remove_oe_list": [remove_practice_list, remove_predict_list]
                        }
        return train_info, result_info

    def draw_loss(self):
        keys = self.loss_metric.keys()
        rename_dict = dict()
        if keys[0] > keys[1]:
            rename_dict = {
                keys[0]: "train",
                keys[1]: "val"
            }

        pd.DataFrame(self.loss_metric).rename(columns=rename_dict).plot(xlabel="epoch", ylabel="rmse", title="LOSS")

    @classmethod
    def statistic_method_problem_show(cls):
        all_df = None
        result_info = {
            "label": [],
            "sample_min_count": [],
            "total_record_count": [],
            "feature_length": [],
            "origin_train_count": [],
            "origin_val_count": [],

            "predictable_train_rmse": [],
            "predictable_train_oe_std": [],
            "predictable_train_oe_mean": [],
            "predictable_train_count": [],
            "predictable_train_series": [],

            "predictable_val_rmse": [],
            "predictable_val_oe_std": [],
            "predictable_val_oe_mean": [],
            "predictable_val_count": [],
            "predictable_val_series": [],

        }
        for i in os.listdir("E:/work_space/yuanjun/SuperviserProject/data/cleaned/"):
            if "again" in i:
                continue
            df = pd.read_csv("E:/work_space/yuanjun/SuperviserProject/data/cleaned/" + i, usecols=[
                "basy_yydj", "basy_xb", "basy_csrq", "basy_zyzd_jbbm", "basy_ssjczbm1", "basy_rysj", "basy_cysj", "basy_sjzy",
                "耗材费", "检查检验费", "药品费", "总费用"])
            df = df[~df['basy_yydj'].isin(['未评级未评等', '一级甲等', '一级乙等', '一级未评等'])]
            print(i, df.shape)
            if all_df is None:
                all_df = df
            else:
                all_df = pd.concat([all_df, df], axis=0)
            # break
        all_df["basy_cysj"] = all_df["basy_cysj"].map(lambda a: a[:7])
        all_df["count"] = 1
        for i in range(3, 10, 1):
            all_df["basy_zyzd_jbbm_for_str_%s" % i] = all_df["basy_zyzd_jbbm"].map(
                lambda a: a[:i] if isinstance(a, str) else "")
            all_df["basy_ssjczbm1_for_str_%s" % i] = all_df["basy_ssjczbm1"].map(
                lambda a: a[:i] if isinstance(a, str) else "")
        cysj_list = list()
        for month in range(2, 13, 1):
            if month < 10:
                cysj_list.append("2022-0%s" % month)
            else:
                cysj_list.append("2022-%s" % month)
            current_analysis_df = all_df[all_df["basy_cysj"].isin(cysj_list)]
            print("month", month, current_analysis_df.shape)
            for label in ["耗材费", "检查检验费", "药品费", "总费用"]:
                print(label)
                for jb_length in range(3, 10, 1):
                    ss_length = jb_length
                    rename_dict = {"耗材费": "HAOCAI-%s-%s-E" % (jb_length, ss_length),
                                     "检查检验费": "JCJY-%s-%s-E" % (jb_length, ss_length),
                                     "药品费": "YP-%s-%s-E" % (jb_length, ss_length),
                                     "总费用": "ZFY-%s-%s-E" % (jb_length, ss_length),
                                     "count": "记录条数-%s-%s" % (jb_length, ss_length)}

                    current_label_analysis_df = current_analysis_df[current_analysis_df[label] > 200]
                    current_label_analysis_df = current_label_analysis_df[current_label_analysis_df["basy_sjzy"] > 1]
                    print(label, month, current_label_analysis_df.shape)

                    train, validation = train_test_split(current_label_analysis_df, test_size=0.2, random_state=1)
                    e_df = train.groupby(
                        ["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj", "basy_ssjczbm1_for_str_%s" % jb_length]).agg(
                        {
                            '耗材费': 'mean',
                            '检查检验费': 'mean',
                            '药品费': 'mean',
                            '总费用': 'mean',
                            'count': 'count'}).reset_index()
                    e_df = e_df.rename(columns=rename_dict)
                    for min_count in [5, 10, 15, 20, 30, 50, 100]:
                        _e_df_meet_min_count_condition = e_df[e_df["记录条数-%s-%s" % (jb_length, ss_length)] > min_count]
                        label_train_result = pd.merge(
                            train, _e_df_meet_min_count_condition, how='inner', on=["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj", "basy_ssjczbm1_for_str_%s" % jb_length])
                        label_val_result = pd.merge(
                            validation, _e_df_meet_min_count_condition, how='inner', on=["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj",
                                                          "basy_ssjczbm1_for_str_%s" % jb_length])

                        e_column_name = rename_dict[label]
                        train_oe_series = label_train_result[label]/label_train_result[e_column_name]
                        val_oe_series = label_val_result[label]/label_val_result[e_column_name]

                        result_info["sample_min_count"].append(min_count)
                        result_info["label"].append(label)
                        result_info["total_record_count"].append(current_label_analysis_df.shape[0])
                        result_info["feature_length"].append(jb_length)
                        result_info["origin_train_count"].append(train.shape[0])
                        result_info["origin_val_count"].append(validation.shape[0])

                        result_info["predictable_train_count"].append(label_train_result.shape[0])
                        result_info["predictable_train_rmse"].append(np.sqrt(mean_squared_error(label_train_result[label], label_train_result[e_column_name])))
                        result_info["predictable_train_oe_std"].append(train_oe_series.std())
                        result_info["predictable_train_oe_mean"].append(train_oe_series.mean())

                        result_info["predictable_train_series"].append("predictable_train_series")

                        result_info["predictable_val_count"].append(label_val_result.shape[0])
                        result_info["predictable_val_rmse"].append(
                            np.sqrt(mean_squared_error(label_val_result[label], label_val_result[e_column_name])))
                        result_info["predictable_val_oe_std"].append(val_oe_series.std())
                        result_info["predictable_val_oe_mean"].append(val_oe_series.mean())
                        result_info["predictable_val_series"].append("predictable_val_series")

                        result_rename_dict = {
                            'sample_min_count': "最小样本数量",
                            "label": "费用类型",
                            "total_record_count": "记录总数",
                            "feature_length": "统计特征长度",
                            "origin_train_count": "原始训练数据量",
                            "origin_val_count": "原始验证数据量",
                            "predictable_train_count": "训练数据可预测数据量",
                            "predictable_train_rmse": "训练数据可预测数据的均方差",
                            "predictable_train_oe_std": "训练数据可预测数据的O/E标准差",
                            "predictable_train_oe_mean": "训练数据可预测数据O/E均值",
                            "predictable_val_count": "测试数据可预测数据量",
                            "predictable_val_rmse": "测试数据可预测数据的均方差",
                            "predictable_val_oe_std": "测试数据可预测数据的O/E标准差",
                            "predictable_val_oe_mean": "测试数据可预测数据O/E均值"
                        }
                        result_df = pd.DataFrame(result_info)
                        result_df = result_df.rename(columns=result_rename_dict)
                        columns_orders = ["最小样本数量", "费用类型", "记录总数", "统计特征长度", "原始训练数据量", "原始验证数据量",
                                          "训练数据可预测数据量", "测试数据可预测数据量",
                                          "训练数据可预测数据的均方差", "测试数据可预测数据的均方差",
                                          "训练数据可预测数据的O/E标准差", "测试数据可预测数据的O/E标准差",
                                          "训练数据可预测数据O/E均值", "测试数据可预测数据O/E均值"]
                        result_df = result_df[columns_orders]

                        result_df.to_csv("statistic_result.csv")

    @classmethod
    def statistic_method_sample_problem_show(cls):
        all_df = None
        result_info = {
            "label": [],
            "sample_min_count": [],
            "total_record_count": [],
            "feature_length": [],
            "origin_train_count": [],
            "origin_val_count": [],

            "predictable_train_rmse": [],
            "predictable_train_oe_std": [],
            "predictable_train_oe_mean": [],
            "predictable_train_count": [],
            "predictable_train_series": [],

            "predictable_val_rmse": [],
            "predictable_val_oe_std": [],
            "predictable_val_oe_mean": [],
            "predictable_val_count": [],
            "predictable_val_series": [],

        }
        for i in os.listdir("E:/work_space/yuanjun/SuperviserProject/data/cleaned/"):
            if "again" in i:
                continue
            df = pd.read_csv("E:/work_space/yuanjun/SuperviserProject/data/cleaned/" + i, usecols=[
                "basy_yydj", "basy_xb", "basy_csrq", "basy_zyzd_jbbm", "basy_ssjczbm1", "basy_rysj", "basy_cysj",
                "basy_sjzy",
                "耗材费", "检查检验费", "药品费", "总费用"])
            df = df[~df['basy_yydj'].isin(['未评级未评等', '一级甲等', '一级乙等', '一级未评等'])]
            print(i, df.shape)
            if all_df is None:
                all_df = df
            else:
                all_df = pd.concat([all_df, df], axis=0)
            # break
        all_df["basy_cysj"] = all_df["basy_cysj"].map(lambda a: a[:7])
        all_df["count"] = 1
        for i in range(3, 10, 1):
            all_df["basy_zyzd_jbbm_for_str_%s" % i] = all_df["basy_zyzd_jbbm"].map(
                lambda a: a[:i] if isinstance(a, str) else "")
            all_df["basy_ssjczbm1_for_str_%s" % i] = all_df["basy_ssjczbm1"].map(
                lambda a: a[:i] if isinstance(a, str) else "")
        cysj_list = list()
        for month in range(2, 13, 1):
            if month < 10:
                cysj_list.append("2022-0%s" % month)
            else:
                cysj_list.append("2022-%s" % month)
        current_analysis_df = all_df[all_df["basy_cysj"].isin(cysj_list)]
        # print("month", month, current_analysis_df.shape)
        for label in ["耗材费", "检查检验费", "药品费", "总费用"]:
            print(label)
            for jb_length in range(3, 10, 1):
                # jb_length = 6
                ss_length = jb_length
                rename_dict = {"耗材费": "HAOCAI-%s-%s-E" % (jb_length, ss_length),
                               "检查检验费": "JCJY-%s-%s-E" % (jb_length, ss_length),
                               "药品费": "YP-%s-%s-E" % (jb_length, ss_length),
                               "总费用": "ZFY-%s-%s-E" % (jb_length, ss_length),
                               "count": "记录条数-%s-%s" % (jb_length, ss_length)}

                current_label_analysis_df = current_analysis_df[current_analysis_df[label] > 200]
                current_label_analysis_df = current_label_analysis_df[current_label_analysis_df["basy_sjzy"] > 1]
                # print(label, month, current_label_analysis_df.shape)

                train, validation = train_test_split(current_label_analysis_df, test_size=0.2, random_state=1)
                e_df = train.groupby(
                    ["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj",
                     "basy_ssjczbm1_for_str_%s" % jb_length]).agg(
                    {
                        '耗材费': 'mean',
                        '检查检验费': 'mean',
                        '药品费': 'mean',
                        '总费用': 'mean',
                        'count': 'count'}).reset_index()
                e_df = e_df.rename(columns=rename_dict)
                min_sample_list = [5, 10, 15, 20, 30, 50, 100, 1000000]
                for index in range(len(min_sample_list)-1):
                    sample_scope = [min_sample_list[index], min_sample_list[index+1]]
                    _e_df_meet_min_count_condition = e_df[
                        (e_df["记录条数-%s-%s" % (jb_length, ss_length)] >= sample_scope[0]) & (e_df["记录条数-%s-%s" % (jb_length, ss_length)] < sample_scope[1])]
                    label_train_result = pd.merge(
                        train, _e_df_meet_min_count_condition, how='inner',
                        on=["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj",
                            "basy_ssjczbm1_for_str_%s" % jb_length])
                    label_val_result = pd.merge(
                        validation, _e_df_meet_min_count_condition, how='inner',
                        on=["basy_zyzd_jbbm_for_str_%s" % jb_length, "basy_yydj",
                            "basy_ssjczbm1_for_str_%s" % jb_length])

                    e_column_name = rename_dict[label]
                    train_oe_series = label_train_result[label] / label_train_result[e_column_name]
                    val_oe_series = label_val_result[label] / label_val_result[e_column_name]

                    result_info["sample_min_count"].append("%s###%s" % (sample_scope[0], sample_scope[1]))
                    result_info["label"].append(label)
                    result_info["total_record_count"].append(current_label_analysis_df.shape[0])
                    result_info["feature_length"].append(jb_length)
                    result_info["origin_train_count"].append(train.shape[0])
                    result_info["origin_val_count"].append(validation.shape[0])

                    result_info["predictable_train_count"].append(label_train_result.shape[0])
                    result_info["predictable_train_rmse"].append(
                        np.sqrt(mean_squared_error(label_train_result[label], label_train_result[e_column_name])))
                    result_info["predictable_train_oe_std"].append(train_oe_series.std())
                    result_info["predictable_train_oe_mean"].append(train_oe_series.mean())

                    result_info["predictable_train_series"].append("predictable_train_series")

                    result_info["predictable_val_count"].append(label_val_result.shape[0])
                    result_info["predictable_val_rmse"].append(
                        np.sqrt(mean_squared_error(label_val_result[label], label_val_result[e_column_name])))
                    result_info["predictable_val_oe_std"].append(val_oe_series.std())
                    result_info["predictable_val_oe_mean"].append(val_oe_series.mean())
                    result_info["predictable_val_series"].append("predictable_val_series")

                    result_rename_dict = {
                        'sample_min_count': "最小样本数量",
                        "label": "费用类型",
                        "total_record_count": "记录总数",
                        "feature_length": "统计特征长度",
                        "origin_train_count": "原始训练数据量",
                        "origin_val_count": "原始验证数据量",
                        "predictable_train_count": "训练数据可预测数据量",
                        "predictable_train_rmse": "训练数据可预测数据的均方差",
                        "predictable_train_oe_std": "训练数据可预测数据的O/E标准差",
                        "predictable_train_oe_mean": "训练数据可预测数据O/E均值",
                        "predictable_val_count": "测试数据可预测数据量",
                        "predictable_val_rmse": "测试数据可预测数据的均方差",
                        "predictable_val_oe_std": "测试数据可预测数据的O/E标准差",
                        "predictable_val_oe_mean": "测试数据可预测数据O/E均值"
                    }
                    result_df = pd.DataFrame(result_info)
                    result_df = result_df.rename(columns=result_rename_dict)
                    columns_orders = ["最小样本数量", "费用类型", "记录总数", "统计特征长度", "原始训练数据量", "原始验证数据量",
                                      "训练数据可预测数据量", "测试数据可预测数据量",
                                      "训练数据可预测数据的均方差", "测试数据可预测数据的均方差",
                                      "训练数据可预测数据的O/E标准差", "测试数据可预测数据的O/E标准差",
                                      "训练数据可预测数据O/E均值", "测试数据可预测数据O/E均值"]
                    result_df = result_df[columns_orders]

                    result_df.to_csv("statistic_sample_problem_result.csv")


if __name__ == "__main__":
    # Report.statistic_method_problem_show()
    Report.statistic_method_sample_problem_show()
    # report_tool = Report()

