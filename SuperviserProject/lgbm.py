#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
LightGBM模型。--原生接口

@time: 2022-10-24
@description:
"""
import numpy as np
import pandas as pd
import lightgbm as lgb


def init_value(y):
    p = y.mean()
    return p


def lgbm_train(x_train, y_train, x_valid, y_valid,
               feature_list, categorical_feature_list, param, obj_func, eval_func,
               num_boost_round=50, early_stopping_rounds=200, verbose_eval=1):

    # lgb_train = lgb.Dataset(x_train, y_train, feature_name=feature_list, categorical_feature=categorical_feature_list,
    #                         init_score=np.full_like(y_train, init_value(y_train), dtype=float))
    # lgb_valid = lgb.Dataset(x_valid, y_valid, feature_name=feature_list, categorical_feature=categorical_feature_list,
    #                         reference=lgb_train, init_score=np.full_like(y_valid, init_value(y_valid), dtype=float))

    lgb_train = lgb.Dataset(x_train, y_train, feature_name=feature_list, categorical_feature=categorical_feature_list)
    lgb_valid = lgb.Dataset(x_valid, y_valid, feature_name=feature_list, categorical_feature=categorical_feature_list,
                            reference=lgb_train)

    gbm = lgb.train(param,
                    lgb_train,
                    num_boost_round,
                    valid_sets=[lgb_train, lgb_valid],
                    categorical_feature=categorical_feature_list,
                    fobj=obj_func,
                    feval=eval_func,
                    # early_stopping_rounds=early_stopping_rounds,
                    verbose_eval=verbose_eval)
    return gbm


def lgbm_predict(x_data, model):

    predict = model.predict(x_data, num_iteration=model.best_iteration)
    return predict


def model_load(model_file):
    return lgb.Booster(model_file=model_file)


def feature_importance(model, features_dict=None):

    importance_df = pd.DataFrame({
        'feature': model.feature_name(),
        'importance': model.feature_importance(importance_type='gain')
    }).sort_values(by='importance', ascending=False)
    if features_dict is not None:
        importance_df['feature'].replace(features_dict, inplace=True)
    return importance_df


def param_dict(p_objective='binary', p_metric='binary_logloss',
               p_max_depth=5, p_num_leaves=30, p_min_data_in_leaf=200, p_learning_rate=0.08,
               p_min_sum_hessian_in_leaf=5, p_lambda_l1=1, p_lambda_l2=0.1, p_min_gain_to_split=0.2):
    param = {
        'boosting_type': 'dart',
        # 'boosting_type': 'gbdt',
        'objective': p_objective,
        'metric': p_metric,
        'num_leaves': p_num_leaves,
        'max_depth': p_max_depth,
        'min_data_in_leaf': p_min_data_in_leaf,
        'learning_rate': p_learning_rate,
        # 'feature_fraction': 0.9,
        # 'bagging_fraction': 0.9,
        # 'bagging_freq': 5,
        'min_sum_hessian_in_leaf': p_min_sum_hessian_in_leaf,
        'lambda_l1': p_lambda_l1,
        'lambda_l2': p_lambda_l2,  # 越小l2正则程度越高
        'min_gain_to_split': p_min_gain_to_split,  # 如果一个节点的 gain 低于这个数，不再分裂
        'verbose': -1,  # <0 显示致命的, =0 显示错误 (警告), >0 显示信息
        # 'is_unbalance': True,
        'num_thread': 6  # 指定线程的个数
    }
    return param


def multiclass_param_dict(p_objective='multiclass', p_max_depth=5, p_num_leaves=30, p_min_data_in_leaf=200,
                          p_learning_rate=0.08, p_min_sum_hessian_in_leaf=5, p_lambda_l2=0.1, p_num_class=31):
    param = {
        'boosting_type': 'dart',
        'objective': p_objective,
        'num_class': p_num_class,
        'metric': {'multi_error'},
        'num_leaves': p_num_leaves,
        'max_depth': p_max_depth,
        'min_data_in_leaf': p_min_data_in_leaf,
        'learning_rate': p_learning_rate,
        'feature_fraction': 0.9,
        # 'bagging_fraction': 0.9,
        # 'bagging_freq': 5,
        'min_sum_hessian_in_leaf': p_min_sum_hessian_in_leaf,
        'lambda_l1': 1,
        'lambda_l2': p_lambda_l2,  # 越小l2正则程度越高
        'min_gain_to_split': 0.2,
        'verbose': -1,
        'is_unbalance': True,
        'num_thread': 6  # 指定线程的个数
    }
    return param
