#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化模型因子质量优化脚本
对当前全部因子做重要性分析，筛选高质量因子，提高模型稳定性和预测能力。
"""
import sys
import os
import pickle

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

from utils.logger import get_logger
from utils.ml_data_loader import MLDataLoader
from utils.ml_feature_engineering import MLFeatureEngineering

logger = get_logger(__name__)

# 默认数据区间（与 train_ml_models 一致）
DEFAULT_TRAIN_START = '2014-01-01'
DEFAULT_TRAIN_END = '2022-12-31'
DEFAULT_VAL_START = '2023-01-01'
DEFAULT_VAL_END = '2023-12-31'

# 筛选阈值：删除 importance==0 或 importance < max_importance * 0.01
IMPORTANCE_MIN_RATIO = 0.01

# 保存路径
SELECTED_FEATURES_PATH = os.path.join(project_root, 'models', 'selected_features.pkl')


def _lgbm_default_params():
    """与现有 LGB 分类器一致的默认参数（sklearn API）"""
    return {
        'objective': 'binary',
        'num_leaves': 31,
        'learning_rate': 0.1,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'random_state': 42,
        'n_estimators': 100,
    }


def _evaluate(y_true, y_pred, y_proba):
    """计算 accuracy, precision, recall, AUC（二分类）"""
    acc = accuracy_score(y_true, y_pred)
    try:
        prec = precision_score(y_true, y_pred, zero_division=0)
    except Exception:
        prec = 0.0
    try:
        rec = recall_score(y_true, y_pred, zero_division=0)
    except Exception:
        rec = 0.0
    try:
        auc = roc_auc_score(y_true, y_proba) if len(np.unique(y_true)) >= 2 else 0.0
    except Exception:
        auc = 0.0
    return {'accuracy': acc, 'precision': prec, 'recall': rec, 'AUC': auc}


def run_optimization(
    train_start_date: str = DEFAULT_TRAIN_START,
    train_end_date: str = DEFAULT_TRAIN_END,
    val_start_date: str = DEFAULT_VAL_START,
    val_end_date: str = DEFAULT_VAL_END,
    use_history_data: bool = True,
    importance_min_ratio: float = IMPORTANCE_MIN_RATIO,
    save_path: str = SELECTED_FEATURES_PATH,
):
    """
    执行因子质量优化全流程（步骤 1～9）。
    """
    try:
        import lightgbm as lgb
        from lightgbm import LGBMClassifier
    except ImportError:
        logger.error("请安装 lightgbm: pip install lightgbm")
        return

    logger.info("=" * 60)
    logger.info("量化模型因子质量优化")
    logger.info("=" * 60)

    # ---------- 数据加载与特征准备 ----------
    data_loader = MLDataLoader()
    feature_engineering = MLFeatureEngineering()

    if use_history_data:
        logger.info(f"从 stock_history_data 加载训练数据：{train_start_date} ~ {train_end_date}")
        train_df = data_loader.load_training_data_from_history(
            start_date=train_start_date, end_date=train_end_date
        )
        logger.info(f"加载验证数据：{val_start_date} ~ {val_end_date}")
        val_df = data_loader.load_training_data_from_history(
            start_date=val_start_date, end_date=val_end_date
        )
    else:
        logger.info(f"从 stock_predictions 加载训练数据：{train_start_date} ~ {train_end_date}")
        train_df = data_loader.load_training_data(
            start_date=train_start_date, end_date=train_end_date
        )
        logger.info(f"加载验证数据：{val_start_date} ~ {val_end_date}")
        val_df = data_loader.load_training_data(
            start_date=val_start_date, end_date=val_end_date
        )

    if train_df.empty:
        logger.error("训练数据为空，无法继续")
        return

    if 'target_date' in train_df.columns:
        train_df = train_df.sort_values('target_date').reset_index(drop=True)

    logger.info("准备特征和标签（全部因子）...")
    X_train, y_train, feature_names = feature_engineering.prepare_features(
        train_df, label_column='label_up'
    )
    X_val, y_val, _ = feature_engineering.prepare_features(
        val_df, label_column='label_up'
    )

    if X_train.empty or not feature_names:
        logger.error("特征准备失败，无法继续")
        return

    # 移除 object 列（LGBM 需要）
    object_cols = X_train.select_dtypes(include=['object']).columns.tolist()
    if object_cols:
        X_train = X_train.drop(columns=object_cols)
        X_val = X_val.drop(columns=object_cols, errors='ignore')
        feature_names = [c for c in feature_names if c not in object_cols]
    X_val = X_val.reindex(columns=feature_names, fill_value=0.0)

    original_feature_count = len(feature_names)
    logger.info(f"原始因子数量: {original_feature_count}")

    # ========== 第一步：训练完整模型（LGBMClassifier，当前全部 feature_cols）==========
    logger.info("\n" + "=" * 60)
    logger.info("第一步：训练完整模型（LGBMClassifier，全部因子）")
    logger.info("=" * 60)

    params = _lgbm_default_params()
    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())
    if n_pos > 0:
        params['scale_pos_weight'] = n_neg / n_pos

    clf_full = LGBMClassifier(**params)
    clf_full.fit(X_train, y_train)

    # ========== 第二步：获取特征重要性 -> feature_importance_df ==========
    logger.info("\n第二步：获取特征重要性")
    imp = clf_full.feature_importances_
    feature_importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': imp,
    }).sort_values('importance', ascending=False).reset_index(drop=True)

    # ========== 第三步：打印前 50 名因子 ==========
    logger.info("\n第三步：重要性排名（前50名）")
    top50 = feature_importance_df.head(50)
    for i, row in top50.iterrows():
        logger.info(f"  {int(row.name) + 1:3d}. {row['feature']}: {row['importance']:.6f}")

    # ========== 第四步：删除低重要性因子 -> selected_features ==========
    logger.info("\n第四步：删除低重要性因子")
    max_imp = feature_importance_df['importance'].max()
    threshold = max(1e-10, max_imp * importance_min_ratio)
    # 保留：importance > 0 且 importance >= max_importance * 1%
    selected = feature_importance_df[
        (feature_importance_df['importance'] > 0) &
        (feature_importance_df['importance'] >= threshold)
    ]
    selected_features = selected['feature'].tolist()
    removed_count = original_feature_count - len(selected_features)
    logger.info(f"  阈值: importance >= {threshold:.6f} (max 的 {importance_min_ratio*100:.0f}%)")
    logger.info(f"  保留因子数: {len(selected_features)}, 删除因子数: {removed_count}")

    # 优化前验证集表现（全因子模型）
    y_val_pred_full = clf_full.predict(X_val)
    y_val_proba_full = clf_full.predict_proba(X_val)[:, 1]
    metrics_before = _evaluate(y_val, y_val_pred_full, y_val_proba_full)
    logger.info(f"  优化前（验证集）: accuracy={metrics_before['accuracy']:.4f}, AUC={metrics_before['AUC']:.4f}")

    # ========== 第五步：用筛选后因子重新训练 ==========
    logger.info("\n第五步：用筛选后因子重新训练模型")
    X_train_sel = X_train[selected_features].copy()
    X_val_sel = X_val[selected_features].copy()

    clf_sel = LGBMClassifier(**params)
    clf_sel.fit(X_train_sel, y_train)

    y_val_pred_sel = clf_sel.predict(X_val_sel)
    y_val_proba_sel = clf_sel.predict_proba(X_val_sel)[:, 1]
    metrics_after = _evaluate(y_val, y_val_pred_sel, y_val_proba_sel)

    logger.info(f"  优化后（验证集）: accuracy={metrics_after['accuracy']:.4f}, "
                f"precision={metrics_after['precision']:.4f}, recall={metrics_after['recall']:.4f}, AUC={metrics_after['AUC']:.4f}")

    # ========== 第六步：对比优化前后性能 ==========
    logger.info("\n第六步：对比优化前后性能")
    logger.info(f"  优化前 AUC:     {metrics_before['AUC']:.4f}")
    logger.info(f"  优化后 AUC:     {metrics_after['AUC']:.4f}")
    logger.info(f"  优化前 accuracy: {metrics_before['accuracy']:.4f}")
    logger.info(f"  优化后 accuracy: {metrics_after['accuracy']:.4f}")

    # ========== 第七步：保存最佳特征列表 ==========
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'wb') as f:
        pickle.dump(selected_features, f)
    logger.info(f"\n第七步：已保存最佳特征列表 -> {save_path}")

    # ========== 第九步：输出总结 ==========
    logger.info("\n" + "=" * 60)
    logger.info("第九步：总结")
    logger.info("=" * 60)
    logger.info(f"  原始因子数量:     {original_feature_count}")
    logger.info(f"  筛选后因子数量:   {len(selected_features)}")
    logger.info(f"  删除因子数量:     {removed_count}")
    logger.info("  模型性能变化（验证集）:")
    logger.info(f"    AUC:      {metrics_before['AUC']:.4f} -> {metrics_after['AUC']:.4f}")
    logger.info(f"    accuracy: {metrics_before['accuracy']:.4f} -> {metrics_after['accuracy']:.4f}")
    logger.info("=" * 60)
    logger.info("因子质量优化完成。预测脚本将优先使用 selected_features，保证训练与预测特征一致。")
    return {
        'original_count': original_feature_count,
        'selected_count': len(selected_features),
        'removed_count': removed_count,
        'metrics_before': metrics_before,
        'metrics_after': metrics_after,
        'selected_features': selected_features,
        'feature_importance_df': feature_importance_df,
    }


if __name__ == '__main__':
    run_optimization()
