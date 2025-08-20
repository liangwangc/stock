import lightgbm as gbm
import pandas as pd
import json
from report import Report
import lgbm


class Model(object):

    def __init__(self, label_type):
        self.basy_list = ["age", "basy_yydj", "basy_xb", "basy_cykb", "basy_rykb"]
        self.disease_encode_list = ["basy_zyzd_jbbm_3", "basy_zyzd_jbbm_5", "basy_zyzd_jbbm_6", "basy_zyzd_jbbm_7",
                                    "basy_zyzd_jbbm_8",
                                    "basy_zyzd_jbbm_9"]
        self.operation_encode_list = ["basy_ssjczbm1_3", "basy_ssjczbm1_5", "basy_ssjczbm1_6", "basy_ssjczbm1_7",
                                      "basy_ssjczbm1_8", "basy_ssjczbm1_9"]

        self.haocai_disease_e_list = ["HAOCAI-3-3-E", "HAOCAI-4-4-E", "HAOCAI-5-5-E", "HAOCAI-6-6-E", "HAOCAI-7-7-E",
                                      "HAOCAI-8-8-E", "HAOCAI-9-9-E",
                                      "HAOCAI-3-only_disease-E", "HAOCAI-4-only_disease-E", "HAOCAI-5-only_disease-E",
                                      "HAOCAI-6-only_disease-E",
                                      "HAOCAI-7-only_disease-E", "HAOCAI-8-only_disease-E", "HAOCAI-9-only_disease-E",
                                      "HAOCAI-only_operation-3-E",
                                      "HAOCAI-only_operation-4-E", "HAOCAI-only_operation-5-E",
                                      "HAOCAI-only_operation-6-E",
                                      "HAOCAI-only_operation-7-E",
                                      "HAOCAI-only_operation-8-E", "HAOCAI-only_operation-9-E",
                                      "AGE-HAOCAI-3-3-E", "AGE-HAOCAI-4-4-E", "AGE-HAOCAI-5-5-E", "AGE-HAOCAI-6-6-E",
                                      "AGE-HAOCAI-7-7-E",
                                      "AGE-HAOCAI-8-8-E", "AGE-HAOCAI-9-9-E",
                                      "AGE-HAOCAI-3-only_disease-E", "AGE-HAOCAI-4-only_disease-E",
                                      "AGE-HAOCAI-5-only_disease-E",
                                      "AGE-HAOCAI-6-only_disease-E",
                                      "AGE-HAOCAI-7-only_disease-E", "AGE-HAOCAI-8-only_disease-E",
                                      "AGE-HAOCAI-9-only_disease-E",
                                      "AGE-HAOCAI-only_operation-3-E",
                                      "AGE-HAOCAI-only_operation-4-E", "AGE-HAOCAI-only_operation-5-E",
                                      "AGE-HAOCAI-only_operation-6-E",
                                      "AGE-HAOCAI-only_operation-7-E",
                                      "AGE-HAOCAI-only_operation-8-E", "AGE-HAOCAI-only_operation-9-E"]

        self.jcjy_disease_e_list = ["JCJY-3-3-E", "JCJY-4-4-E", "JCJY-5-5-E", "JCJY-6-6-E", "JCJY-7-7-E", "JCJY-8-8-E",
                                    "JCJY-9-9-E",
                                    "JCJY-3-only_disease-E", "JCJY-4-only_disease-E", "JCJY-5-only_disease-E",
                                    "JCJY-6-only_disease-E",
                                    "JCJY-7-only_disease-E", "JCJY-8-only_disease-E", "JCJY-9-only_disease-E",
                                    "JCJY-only_operation-3-E",
                                    "JCJY-only_operation-4-E", "JCJY-only_operation-5-E", "JCJY-only_operation-6-E",
                                    "JCJY-only_operation-7-E",
                                    "JCJY-only_operation-8-E", "JCJY-only_operation-9-E",
                                    "AGE-JCJY-3-only_disease-E", "AGE-JCJY-4-only_disease-E",
                                    "AGE-JCJY-5-only_disease-E",
                                    "AGE-JCJY-6-only_disease-E",
                                    "AGE-JCJY-7-only_disease-E", "AGE-JCJY-8-only_disease-E",
                                    "AGE-JCJY-9-only_disease-E",
                                    "AGE-JCJY-only_operation-3-E",
                                    "AGE-JCJY-only_operation-4-E", "AGE-JCJY-only_operation-5-E",
                                    "AGE-JCJY-only_operation-6-E",
                                    "AGE-JCJY-only_operation-7-E",
                                    "AGE-JCJY-only_operation-8-E", "AGE-JCJY-only_operation-9-E"]

        self.label_type = label_type

        if self.label_type == "耗材费":
            self.feature_list = self.basy_list + self.disease_encode_list + self.haocai_disease_e_list + self.operation_encode_list + ["basy_sjzy", "basy_yljgid_feature"]
        elif self.label_type == "检查检验费":
            self.feature_list = self.basy_list + self.disease_encode_list + self.jcjy_disease_e_list + self.operation_encode_list + ["basy_sjzy", "basy_yljgid_feature"]

    def add_e_info(self, df):
        for i in range(3, 10, 1):
            temp = pd.read_csv("online_model_2024/%s_%s_%s_1.csv" % (self.label_type, i, i), index_col=0, nrows=1)
            dtype_dict = {"basy_ssjczbm1_for_str_%s" % i: str, "basy_yydj": int, "basy_zyzd_jbbm_for_str_%s" % i: str}
            for column in temp.columns:
                if "E" in column:
                    dtype_dict[column] = float
                elif "条数" in column:
                    continue
            e_df = pd.read_csv("online_model_2024/%s_%s_%s_1.csv" % (self.label_type, i, i), index_col=0, usecols=list(dtype_dict.keys()), dtype=dtype_dict)

            before_columns_set = set(df.columns.tolist())
            df = pd.merge(df, e_df, how='left', on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj", "basy_ssjczbm1_for_str_%s" % i], copy=False)
            print(set(df.columns.tolist()) - before_columns_set)
            print(df.shape)

            temp = pd.read_csv("online_model_2024/%s_%s_%s_2.csv" % (self.label_type, i, "only_disease"), index_col=0, nrows=1)
            dtype_dict = {"basy_zyzd_jbbm_for_str_%s" % i: str, "basy_yydj": int}
            for column in temp.columns:
                if "E" in column:
                    dtype_dict[column] = float
                elif "条数" in column:
                    continue
            e_df = pd.read_csv("online_model_2024/%s_%s_%s_2.csv" % (self.label_type, i, "only_disease"), index_col=0, usecols=list(dtype_dict.keys()), dtype=dtype_dict)
            df = pd.merge(df, e_df, how='left', on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj"], copy=False)
            print(df.shape)

            temp = pd.read_csv("online_model_2024/%s_%s_%s_3.csv" % (self.label_type, "only_operation", i), index_col=0, nrows=1)
            dtype_dict = {"basy_ssjczbm1_for_str_%s" % i: str, "basy_yydj": int}
            for column in temp.columns:
                if "E" in column:
                    dtype_dict[column] = float
                elif "条数" in column:
                    continue
            e_df = pd.read_csv("online_model_2024/%s_%s_%s_3.csv" % (self.label_type, "only_operation", i), index_col=0, usecols=list(dtype_dict.keys()), dtype=dtype_dict)
            df = pd.merge(df, e_df, how='left', on=["basy_yydj", "basy_ssjczbm1_for_str_%s" % i], copy=False)
            print(df.shape)
            # age

            temp = pd.read_csv("online_model_2024/%s_%s_%s_4.csv" % (self.label_type, i, i), index_col=0, nrows=1)
            dtype_dict = {"basy_ssjczbm1_for_str_%s" % i: str, "basy_yydj": int, "age_group": int, "basy_zyzd_jbbm_for_str_%s" % i: str}
            for column in temp.columns:
                if "E" in column:
                    dtype_dict[column] = float
                elif "条数" in column:
                    continue
            e_df = pd.read_csv("online_model_2024/%s_%s_%s_4.csv" % (self.label_type, i, i), index_col=0, usecols=list(dtype_dict.keys()), dtype=dtype_dict)
            df = pd.merge(df, e_df, how='left', on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj", "basy_ssjczbm1_for_str_%s" % i, "age_group"], copy=False)
            print(df.shape)

            temp = pd.read_csv("online_model_2024/%s_%s_%s_5.csv" % (self.label_type, i, "only_disease"), index_col=0, nrows=1)
            dtype_dict = {"basy_zyzd_jbbm_for_str_%s" % i: str, "basy_yydj": int, "age_group": int}
            for column in temp.columns:
                if "E" in column:
                    dtype_dict[column] = float
                elif "条数" in column:
                    continue
            e_df = pd.read_csv("online_model_2024/%s_%s_%s_5.csv" % (self.label_type, i, "only_disease"), index_col=0, usecols=list(dtype_dict.keys()), dtype=dtype_dict)
            df = pd.merge(df, e_df, how='left', on=["basy_zyzd_jbbm_for_str_%s" % i, "basy_yydj", "age_group"], copy=False)
            print(df.shape)

            temp = pd.read_csv("online_model_2024/%s_%s_%s_6.csv" % (self.label_type, "only_operation", i), index_col=0, nrows=1)
            dtype_dict = {"basy_ssjczbm1_for_str_%s" % i: str, "basy_yydj": int, "age_group": int}
            for column in temp.columns:
                if "E" in column:
                    dtype_dict[column] = float
                elif "条数" in column:
                    continue
            e_df = pd.read_csv("online_model_2024/%s_%s_%s_6.csv" % (self.label_type, "only_operation", i), index_col=0, usecols=list(dtype_dict.keys()), dtype=dtype_dict)
            df = pd.merge(df, e_df, how='left', on=["basy_yydj", "basy_ssjczbm1_for_str_%s" % i, "age_group"], copy=False)
            print(df.shape)
        return df

    def predict(self, df):
        df["basy_yydj_str"] = df["basy_yydj"]
        if "HAOCAI-3-3-E" not in df.columns:
            f = open('online_model_2024/encode_for_category_dict.txt', 'r')
            encode_for_category_dict = json.loads(f.read())
            f.close()

            f = open('online_model_2024/yydj_dict.txt', 'r')
            yydj_dict = json.loads(f.read())
            f.close()
            df = Report.feature_process(df, encode_for_category_dict, yydj_dict)
            # df.to_csv('.....')
            df = self.add_e_info(df)
        if self.label_type == "耗材费":
            lgb_model = lgbm.model_load("online_model_2024/lgbm_model_haocai.model")
        elif self.label_type == "检查检验费":
            lgb_model = lgbm.model_load("online_model_2024/lgbm_model_jcjy.model")
        train_df = df[self.feature_list]
        print("feature list len:", len(self.feature_list))
        print(train_df.shape, df.shape)
        print("need", set(self.feature_list) - set(list(train_df.columns.tolist())))
        df["basy_yydj"] = df["basy_yydj_str"]
        return lgbm.lgbm_predict(train_df, lgb_model)