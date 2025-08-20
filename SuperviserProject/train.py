import pandas as pd
import os
import numpy as np
import lgbm
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from scipy import special


def oe_loss_objective(preds, train_data):
    y = train_data.get_label()

    # p = special.expit(preds)
    # grad = 0.01*2*y*(preds-y)/(preds**3 + 1) + preds-y
    # grad = preds-y  #  + 0.4 * preds
    # grad = preds - y  #  + 0.4 * preds
    # hess = [1 for _ in range(len(y))]
    grad = (preds - y)
    hess = [1 for _ in range(len(y))]
    # hess = 1
    # hess = 0.01*(-4*y/(preds**3 + 1) + 6*(y**2)/(preds**4 + 1)) + 1
    return grad, hess


def oe_loss_metric(preds, train_data):
    y = train_data.get_label()
    # print("O", y, len(y), type(y))
    # print("E", preds, len(preds), type(preds))

    # p = special.expit(preds)

    # ll = np.sqrt(np.mean((y/preds-1)**2))
    ll = np.sqrt(mean_squared_error(y, preds))

    return 'oeloss', ll, False


def get_all_data():
    all_df = None
    for i in os.listdir("E:/work_space/yuanjun/SuperviserProject/data/cleaned/"):
        if "again" in i:
            continue
        df = pd.read_csv("E:/work_space/yuanjun/SuperviserProject/data/cleaned/" + i, usecols=[
            "basy_yydj", "basy_xb", "basy_csrq", "basy_zyzd_jbbm", "basy_zyzd_jbbm1", "basy_zyzd_jbbm2",
            "basy_zyzd_jbbm3", "basy_zyzd_jbbm4", "basy_ssjczbm1", "basy_rysj", "basy_cysj", "basy_sjzy",
            "耗材费", "检查检验费", "药品费", "总费用"])
        df = df[~df['basy_yydj'].isin(['未评级未评等', '一级甲等', '一级乙等', '一级未评等'])]
        print(i, df.shape)
        if all_df is None:
            all_df = df
        else:
            all_df = pd.concat([all_df, df], axis=0)
        break
    return all_df


def get_category_vary_encode(df, level):
    jbbm_list = list(filter(lambda a: isinstance(a, str), list(set(df["basy_zyzd_jbbm"].map(lambda a: a[:level]).tolist()))))
    sorted(jbbm_list)

    jbbm_list_3 = list(
        filter(lambda a: isinstance(a, str), list(set(df["basy_zyzd_jbbm"].map(lambda a: a[:3]).tolist()))))
    sorted(jbbm_list_3)

    basy_ssjczbm1_list = list(filter(lambda a: isinstance(a, str), list(set(df["basy_ssjczbm1"].map(lambda a: a[:level] if isinstance(a, str) else "0").tolist()))))
    sorted(basy_ssjczbm1_list)

    basy_ssjczbm1_list_4 = list(filter(lambda a: isinstance(a, str), list(
        set(df["basy_ssjczbm1"].map(lambda a: a[:4] if isinstance(a, str) else "0").tolist()))))
    sorted(basy_ssjczbm1_list_4)

    basy_yydj_list = list(filter(lambda a: isinstance(a, str), list(
        set(df["basy_yydj"].map(lambda a: a[:level] if isinstance(a, str) else "0").tolist()))))
    sorted(basy_yydj_list)
    jbbm_dict = dict()
    jbbm_dict_3 = dict()
    ssbm_dict = dict()
    ssbm_dict_4 = dict()
    yydj_dict = dict()
    for i in range(len(jbbm_list)):
        jbbm_dict[jbbm_list[i]] = i+1

    for i in range(len(jbbm_list_3)):
        jbbm_dict_3[jbbm_list_3[i]] = i+1

    for i in range(len(basy_ssjczbm1_list)):
        ssbm_dict[basy_ssjczbm1_list[i]] = i+1

    for i in range(len(basy_ssjczbm1_list_4)):
        ssbm_dict_4[basy_ssjczbm1_list_4[i]] = i+1

    for i in range(len(basy_yydj_list)):
        yydj_dict[basy_yydj_list[i]] = i+1
    return jbbm_dict, jbbm_dict_3, ssbm_dict, ssbm_dict_4, yydj_dict


def clean_sex(sex):
    if not isinstance(sex, str):
        return 0
    if '男' in sex:
        return 1
    elif '女' in sex:
        return 2
    else:
        return 0


def clean_birthday(birthday, year=2022):
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


def yydj_jbbm_ssbm_model(train, valibation, label, jb_length, ss_length):

    statis_train = train.copy()
    statis_train["basy_zyzd_jbbm"] = train["basy_zyzd_jbbm"].map(lambda a: a[:jb_length] if isinstance(a, str) else "")
    statis_train["basy_ssjczbm1"] = train["basy_ssjczbm1"].map(lambda a: a[:ss_length] if isinstance(a, str) else "")

    statis_valibation = valibation.copy()
    statis_valibation["basy_zyzd_jbbm"] = valibation["basy_zyzd_jbbm"].map(lambda a: a[:jb_length] if isinstance(a, str) else "")
    statis_valibation["basy_ssjczbm1"] = valibation["basy_ssjczbm1"].map(lambda a: a[:ss_length] if isinstance(a, str) else "")

    e_df = statis_train.groupby(["basy_zyzd_jbbm", "basy_yydj", "basy_ssjczbm1"]).agg({
                                                        '耗材费': 'mean',
                                                        '检查检验费': 'mean',
                                                        '药品费': 'mean',
                                                        '总费用': 'mean',
                                                        'count': 'count'}).reset_index()
    e_df = e_df.rename(columns={"耗材费": "耗材费-E", "检查检验费": "检查检验费-E", "药品费": "药品费-E", "总费用": "总费用-E", "count": "记录条数"})
    print("e_df 0:", e_df.shape)
    e_df = e_df[e_df["记录条数"] > 20]
    print("e_df 1:", e_df.shape)
    print("valibation:", statis_valibation.shape)
    val_result = pd.merge(statis_valibation, e_df, how='inner', on=['basy_zyzd_jbbm', "basy_yydj", "basy_ssjczbm1"])
    print("val_result:", val_result.shape)
    val_rmse = np.sqrt(mean_squared_error(val_result[label], val_result["%s-E" % label]))
    val_moe = (val_result[label] / val_result["%s-E" % label]).mean()
    val_std = (val_result[label] / val_result["%s-E" % label]).std()
    val_max = (val_result[label] / val_result["%s-E" % label]).max()

    print("train:", statis_train.shape)
    train_result = pd.merge(statis_train, e_df, how='inner', on=['basy_zyzd_jbbm', "basy_yydj", "basy_ssjczbm1"])
    print("train_result", train_result.shape)
    train_rmse = np.sqrt(mean_squared_error(train_result[label], train_result["%s-E" % label]))
    train_moe = (train_result[label] / train_result["%s-E" % label]).mean()
    train_std = (train_result[label] / train_result["%s-E" % label]).std()
    train_max = (train_result[label] / train_result["%s-E" % label]).max()

    result_dict = {
        "E_0":  e_df.shape, "E_1": e_df.shape, "V_0": statis_valibation.shape, "V_1": val_result.shape,
        "VAL_RMSE": val_rmse, "VAL_MOE": val_moe, "VAL_STD": val_std, "VAL_MAX": val_max,
        "T_0": statis_train.shape, "T_1": train_result.shape,
        "TRAIN_RMSE": train_rmse, "TRAIN_MOE": train_moe, "TRAIN_STD": train_std, "TRAIN_MAX": train_max
    }

    return train_result, val_result, result_dict


def train_model(train, validation, label_col):

    temp_feature_list = [label_col]
    temp_feature_list.extend(feature_list)

    train = train.loc[:, temp_feature_list]
    y_train = train.pop(label_col)

    x_valid = validation.loc[:, feature_list]
    y_valid = validation.loc[:, label_col]

    # 参数配置
    # param = lgbm.param_dict(p_objective='mean_squared_error', p_metric='rmse', p_max_depth=6, p_num_leaves=32,
    #                         p_min_data_in_leaf=20, p_learning_rate=0.2, p_min_sum_hessian_in_leaf=5,
    #                         p_lambda_l2=0.1)
    param = lgbm.param_dict(p_objective='oe_loss_objective', p_metric='oe_loss_metric', p_max_depth=9, p_num_leaves=128,
                            p_min_data_in_leaf=15, p_learning_rate=1, p_min_sum_hessian_in_leaf=15,
                            p_lambda_l1=0.01, p_lambda_l2=0.02, p_min_gain_to_split=0.01)
    # 模型训练
    lgbm_model = lgbm.lgbm_train(train, y_train, x_valid, y_valid,
                                 feature_list=feature_list,
                                 categorical_feature_list=category_feature,
                                 param=param,
                                 num_boost_round=300,
                                 obj_func=oe_loss_objective,
                                 # obj_func=None,
                                 eval_func=oe_loss_metric,
                                 # eval_func=None,
                                 verbose_eval=1)
    # 计算特征重要性
    importance_df = lgbm.feature_importance(lgbm_model)

    # lgbm_model.save_model('model/lgbm_model_{}.model'.format(label_col))
    label_dict = {
        "药品费": "yp", "检查检验费": "jcjy", "耗材费": "hc", "总费用": "zfy"
    }
    lgbm_model.save_model('model/lgbm_model_{}.model'.format(label_dict[label_col]))
    # importance_df.to_csv('model/feature_importance_df_{}.csv'.format(label_col))
    importance_df.to_csv('model/feature_importance_df_{}.csv'.format(label_dict[label_col]))
    val_rmse = np.sqrt(mean_squared_error(lgbm_model.predict(x_valid[feature_list]), y_valid))

    # print("Final O", y_train.to_numpy(), len(y_train))
    # print("Final E", lgbm_model.predict(train[feature_list], num_iteration=-1), train.shape)
    train_rmse = np.sqrt(mean_squared_error(lgbm_model.predict(train[feature_list]), y_train))

    val_moe = (y_valid/lgbm_model.predict(x_valid[feature_list])).mean()
    val_std = (y_valid/lgbm_model.predict(x_valid[feature_list])).std()
    val_max = (y_valid/lgbm_model.predict(x_valid[feature_list])).max()

    train_moe = (y_train / lgbm_model.predict(train[feature_list])).mean()
    train_std = (y_train / lgbm_model.predict(train[feature_list])).std()
    train_max = (y_train / lgbm_model.predict(train[feature_list])).max()

    return {"MODEL_VAL_RMSE": val_rmse, "MODEL_TRAIN_RMSE": train_rmse, "MODEL_TRAIN_MAX": train_max,
            "MODEL_VAL_MOE": val_moe, "MODEL_VAL_STD": val_std, "MODEL_VAL_MAX": val_max,
            "MODEL_TRAIN_MOE": train_moe, "MODEL_TRAIN_STD": train_std}


if __name__ == "__main__":
    all_df = get_all_data()
    level = 8
    jbbm_dict, jbbm_dict_3, ssbm_dict, ssbm_dict_4, _ = get_category_vary_encode(all_df, level)

    yydj_dict = {'二级未评等': 1, '二级乙等': 2, '二级甲等': 3, '三级未评等': 4, '三级乙等': 5, '三级甲等': 6}
    all_df["basy_zyzd_jbbm_6"] = all_df["basy_zyzd_jbbm"].map(lambda a: jbbm_dict.get(a[:level], 0))
    all_df["basy_zyzd_jbbm_3"] = all_df["basy_zyzd_jbbm"].map(lambda a: jbbm_dict_3.get(a[:3], 0))
    all_df["basy_zyzd_jbbm1"] = all_df["basy_zyzd_jbbm1"].map(lambda a: jbbm_dict.get(a[:level], 0) if isinstance(a, str) else 0)
    all_df["basy_zyzd_jbbm2"] = all_df["basy_zyzd_jbbm2"].map(lambda a: jbbm_dict.get(a[:level], 0) if isinstance(a, str) else 0)
    all_df["basy_zyzd_jbbm3"] = all_df["basy_zyzd_jbbm3"].map(lambda a: jbbm_dict.get(a[:level], 0) if isinstance(a, str) else 0)
    all_df["basy_zyzd_jbbm4"] = all_df["basy_zyzd_jbbm4"].map(lambda a: jbbm_dict.get(a[:level], 0) if isinstance(a, str) else 0)
    all_df["basy_ssjczbm1_6"] = all_df["basy_ssjczbm1"].map(lambda a: ssbm_dict.get(a[:level], 0) if isinstance(a, str) else 0)
    all_df["basy_ssjczbm1_4"] = all_df["basy_ssjczbm1"].map(lambda a: ssbm_dict_4.get(a[:4], 0) if isinstance(a, str) else 0)

    all_df["basy_yydj"] = all_df["basy_yydj"].map(lambda a: yydj_dict.get(a, 0))
    all_df["age"] = all_df["basy_csrq"].map(lambda a: clean_birthday(a))
    all_df["count"] = 1
    all_df["basy_xb"] = all_df["basy_xb"].map(lambda a: clean_sex(a))

    # feature_list = ["age", "basy_yydj", "basy_xb", "basy_zyzd_jbbm_6", "basy_zyzd_jbbm_3", "basy_zyzd_jbbm1", "basy_zyzd_jbbm2",
    #                 "basy_zyzd_jbbm3", "basy_zyzd_jbbm4", "basy_ssjczbm1_6", "basy_ssjczbm1_4", "basy_sjzy"]
    # category_feature = ["basy_xb", "basy_zyzd_jbbm_6", "basy_zyzd_jbbm_3", "basy_zyzd_jbbm1", "basy_zyzd_jbbm2",
    #                     "basy_zyzd_jbbm3", "basy_zyzd_jbbm4", "basy_ssjczbm1_6", "basy_ssjczbm1_4"]  # 测试医院等级

    feature_list = ["age", "basy_yydj", "basy_xb", "basy_zyzd_jbbm_6", "basy_zyzd_jbbm_3", "basy_ssjczbm1_6", "basy_ssjczbm1_4"]
    category_feature = ["basy_xb", "basy_zyzd_jbbm_6", "basy_zyzd_jbbm_3", "basy_ssjczbm1_6", "basy_ssjczbm1_4"]

    # print(train[feature_list])
    for label in ["检查检验费", "药品费", "耗材费", "总费用"]:
    # for label in ["耗材费"]:
        if label == "耗材费":
            df = all_df[all_df["耗材费"] > 200]
        elif label == "药品费":
            df = all_df[all_df["药品费"] > 200]
        elif label == "检查检验费":
            df = all_df[all_df["检查检验费"] > 200]
        else:
            df = all_df[all_df["总费用"] > 200]

        train, test = train_test_split(df, test_size=0.2, random_state=1)
        print(label, train.shape, test.shape)
        train_result, test_1, result_dict = yydj_jbbm_ssbm_model(train, test, label, 8, 7)
        model_result = train_model(train_result, test_1, label)
        print("###############################%s##################################" % label)
        for key in result_dict:
            print(key, result_dict[key])
        for key in model_result:
            print(key, model_result[key])
        print("###############################%s##################################" % label)

