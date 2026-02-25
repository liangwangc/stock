#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
机器学习模型训练脚本
使用10年历史数据训练XGBoost、LightGBM等模型
"""
import sys
import os
import pickle
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

# 因子筛选结果路径（与 optimize_factor_quality.py 一致）
SELECTED_FEATURES_PATH = os.path.join(project_root, 'models', 'selected_features.pkl')
from utils.ml_data_loader import MLDataLoader
from utils.ml_feature_engineering import MLFeatureEngineering
from utils.ml_model_trainer import MLModelTrainer
from utils.ml_model_manager import MLModelManager

logger = get_logger(__name__)


def train_models(train_start_date: str = '2014-01-01',
                 train_end_date: str = '2022-12-31',
                 val_start_date: str = '2023-01-01',
                 val_end_date: str = '2023-12-31',
                 test_start_date: str = '2024-01-01',
                 test_end_date: str = '2024-12-31',
                 model_types: list = ['xgb_classifier', 'lgb_classifier'],
                 is_active: bool = True,
                 use_history_data: bool = True):
    """
    训练机器学习模型
    
    Args:
        train_start_date: 训练集开始日期
        train_end_date: 训练集结束日期
        val_start_date: 验证集开始日期
        val_end_date: 验证集结束日期
        test_start_date: 测试集开始日期
        test_end_date: 测试集结束日期
        model_types: 要训练的模型类型列表
        is_active: 是否激活训练好的模型
    """
    try:
        logger.info("=" * 60)
        logger.info("开始训练机器学习模型")
        logger.info("=" * 60)
        
        # 1. 初始化组件
        data_loader = MLDataLoader()
        feature_engineering = MLFeatureEngineering()
        model_trainer = MLModelTrainer()
        model_manager = MLModelManager()
        
        # 2. 加载训练数据
        if use_history_data:
            logger.info(f"从stock_history_data表加载训练数据：{train_start_date} 到 {train_end_date}")
            train_df = data_loader.load_training_data_from_history(
                start_date=train_start_date,
                end_date=train_end_date
            )
            
            logger.info(f"加载验证数据：{val_start_date} 到 {val_end_date}")
            val_df = data_loader.load_training_data_from_history(
                start_date=val_start_date,
                end_date=val_end_date
            )
        else:
            logger.info(f"从stock_predictions表加载训练数据：{train_start_date} 到 {train_end_date}")
            train_df = data_loader.load_training_data(
                start_date=train_start_date,
                end_date=train_end_date
            )
            
            logger.info(f"加载验证数据：{val_start_date} 到 {val_end_date}")
            val_df = data_loader.load_training_data(
                start_date=val_start_date,
                end_date=val_end_date
            )
        
        if train_df.empty:
            logger.error("训练数据为空，无法继续训练")
            return
        
        logger.info(f"训练数据加载完成：{len(train_df)} 条样本")
        logger.info(f"验证数据加载完成：{len(val_df)} 条样本")
        
        # 3.5 按时间排序（TimeSeriesSplit 要求训练数据按 target_date 有序）
        if 'target_date' in train_df.columns:
            train_df = train_df.sort_values('target_date').reset_index(drop=True)
            logger.info("训练数据已按 target_date 排序")
        
        # 4. 准备特征和标签
        logger.info("准备特征和标签...")
        X_train, y_train, feature_names = feature_engineering.prepare_features(
            train_df, label_column='label_up'
        )
        
        if X_train.empty:
            logger.error("特征准备失败，无法继续训练")
            return
        
        X_val, y_val, _ = feature_engineering.prepare_features(
            val_df, label_column='label_up'
        )
        
        # 4.5 若存在筛选后的因子列表，则仅使用 selected_features（与预测一致）
        if os.path.isfile(SELECTED_FEATURES_PATH):
            try:
                with open(SELECTED_FEATURES_PATH, 'rb') as f:
                    selected_features = pickle.load(f)
                available = [c for c in selected_features if c in X_train.columns]
                if available:
                    X_train = X_train[available].copy()
                    X_val = X_val.reindex(columns=available, fill_value=0.0)
                    feature_names = available
                    logger.info(f"已加载因子筛选结果：使用 {len(feature_names)} 个筛选因子（selected_features.pkl）")
            except Exception as e:
                logger.warning(f"加载 selected_features.pkl 失败，使用全部特征: {e}")
        
        # 5. 特征标准化（可选）
        # X_train, X_val, _ = feature_engineering.normalize_features(
        #     X_train, X_val, method='standard'
        # )
        
        # 6. 训练模型（性能优化：使用多线程并行训练多个模型类型）
        import os
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # 定义训练单个模型的函数（用于并行处理）
        def train_single_model(model_type):
            """训练单个模型"""
            try:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"训练模型: {model_type}")
                logger.info(f"{'=' * 60}")
                
                model = None
                metrics = {}
                model_feature_names = feature_names  # 回归器等非 CV 路径使用
                
                if model_type == 'xgb_classifier':
                    model, metrics, model_feature_names = model_trainer.train_xgb_classifier_timeseries_cv(
                        X_train, y_train, X_val=X_val, y_val=y_val, n_splits=5
                    )
                elif model_type == 'lgb_classifier':
                    model, metrics, model_feature_names = model_trainer.train_lgb_classifier_timeseries_cv(
                        X_train, y_train, X_val=X_val, y_val=y_val, n_splits=5
                    )
                elif model_type == 'xgb_regressor':
                    # 使用涨跌幅作为标签（需要重新准备特征）
                    X_train_reg, y_train_reg, feature_names_reg = feature_engineering.prepare_features(
                        train_df, label_column='label_change_pct'
                    )
                    X_val_reg, y_val_reg, _ = feature_engineering.prepare_features(
                        val_df, label_column='label_change_pct'
                    )
                    model_feature_names = feature_names_reg
                    model, metrics = model_trainer.train_xgb_regressor(
                        X_train_reg, y_train_reg, X_val_reg, y_val_reg
                    )
                else:
                    logger.warning(f"未知的模型类型: {model_type}")
                    return {'success': False, 'model_type': model_type, 'error': '未知的模型类型'}
                
                if model is None:
                    logger.error(f"模型训练失败: {model_type}")
                    return {'success': False, 'model_type': model_type, 'error': '模型训练失败'}
                
                # 获取特征重要性
                feature_importance = feature_engineering.get_feature_importance(
                    model, model_feature_names
                )
                
                # 保存模型
                model_version = datetime.now().strftime('v%Y%m%d_%H%M%S')
                model_name = f"{model_type}_{model_version}"
                model_dir = os.path.join(project_root, 'models', model_type)
                os.makedirs(model_dir, exist_ok=True)
                model_file_path = os.path.join(model_dir, f"{model_name}.pkl")
                model_relative_path = os.path.join('models', model_type, f"{model_name}.pkl")
                
                success = model_trainer.save_model(
                    model=model,
                    model_path=model_file_path,
                    feature_names=model_feature_names,
                    feature_importance=feature_importance,
                    metrics=metrics,
                    config={'model_type': model_type}
                )
                
                if not success:
                    logger.error(f"模型保存失败: {model_type}")
                    return {'success': False, 'model_type': model_type, 'error': '模型保存失败'}
                
                # 保存模型信息到数据库
                model_id = model_manager.save_model_info(
                    model_name=model_name,
                    model_type=model_type,
                    model_version=model_version,
                    model_file_path=model_relative_path,
                    feature_list=model_feature_names,
                    feature_importance=feature_importance,
                    training_config={'model_type': model_type},
                    training_metrics=metrics,
                    train_start_date=train_start_date,
                    train_end_date=train_end_date,
                    val_start_date=val_start_date,
                    val_end_date=val_end_date,
                    test_start_date=test_start_date,
                    test_end_date=test_end_date,
                    sample_count=len(train_df),
                    is_active=is_active,
                    description=f"使用 {train_start_date} 到 {train_end_date} 的数据训练"
                )
                
                if model_id > 0:
                    logger.info(f"模型信息保存成功: {model_name} (ID: {model_id})")
                    
                    # 如果激活，则激活该模型
                    if is_active:
                        model_manager.activate_model(model_id)
                        logger.info(f"模型已激活: {model_name}")
                else:
                    logger.warning(f"模型信息保存失败: {model_name}")
                
                return {
                    'success': True,
                    'model_type': model_type,
                    'model_name': model_name,
                    'model_id': model_id,
                    'metrics': metrics
                }
            except Exception as e:
                logger.error(f"训练模型 {model_type} 时发生异常: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return {'success': False, 'model_type': model_type, 'error': str(e)}
        
        # 根据模型数量决定是否使用并行训练
        # 注意：如果模型需要不同的特征准备（如xgb_regressor），并行训练可能不太适合
        # 但分类器模型可以并行训练
        classifier_models = [mt for mt in model_types if mt in ['xgb_classifier', 'lgb_classifier']]
        regressor_models = [mt for mt in model_types if mt == 'xgb_regressor']
        
        trained_models = []
        
        # 并行训练分类器模型（它们使用相同的特征）
        if len(classifier_models) > 1:
            logger.info(f"使用多线程并行训练分类器模型（{len(classifier_models)} 个模型）...")
            # 性能优化：使用更多线程（最多使用CPU核心数）
            cpu_count = os.cpu_count() or 2
            max_workers = min(len(classifier_models), cpu_count)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_model = {
                    executor.submit(train_single_model, model_type): model_type
                    for model_type in classifier_models
                }
                
                for future in as_completed(future_to_model):
                    model_type = future_to_model[future]
                    try:
                        result = future.result()
                        trained_models.append(result)
                    except Exception as e:
                        logger.error(f"获取模型 {model_type} 的训练结果失败: {str(e)}")
                        trained_models.append({'success': False, 'model_type': model_type, 'error': str(e)})
        else:
            # 单个分类器模型，直接训练
            for model_type in classifier_models:
                result = train_single_model(model_type)
                trained_models.append(result)
        
        # 串行训练回归器模型（它们需要不同的特征准备）
        for model_type in regressor_models:
            result = train_single_model(model_type)
            trained_models.append(result)
        
        # 输出训练结果汇总
        logger.info(f"\n{'=' * 60}")
        logger.info("模型训练完成汇总")
        logger.info(f"{'=' * 60}")
        success_count = sum(1 for r in trained_models if r.get('success'))
        fail_count = len(trained_models) - success_count
        logger.info(f"成功: {success_count} 个模型")
        logger.info(f"失败: {fail_count} 个模型")
        for result in trained_models:
            if result.get('success'):
                logger.info(f"  ✅ {result['model_type']}: {result.get('model_name', 'N/A')}")
            else:
                logger.error(f"  ❌ {result['model_type']}: {result.get('error', '未知错误')}")
        
        # 旧代码（已替换为并行训练）
        # for model_type in model_types:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"训练模型: {model_type}")
            logger.info(f"{'=' * 60}")
            
            model = None
            metrics = {}
            
            if model_type == 'xgb_classifier':
                model, metrics = model_trainer.train_xgb_classifier(
                    X_train, y_train, X_val, y_val
                )
            elif model_type == 'lgb_classifier':
                model, metrics = model_trainer.train_lgb_classifier(
                    X_train, y_train, X_val, y_val
                )
            elif model_type == 'xgb_regressor':
                # 使用涨跌幅作为标签
                X_train_reg, y_train_reg, _ = feature_engineering.prepare_features(
                    train_df, label_column='label_change_pct'
                )
                X_val_reg, y_val_reg, _ = feature_engineering.prepare_features(
                    val_df, label_column='label_change_pct'
                )
                model, metrics = model_trainer.train_xgb_regressor(
                    X_train_reg, y_train_reg, X_val_reg, y_val_reg
                )
            else:
                logger.warning(f"未知的模型类型: {model_type}")
                continue
            
            if model is None:
                logger.error(f"模型训练失败: {model_type}")
                continue
            
            # 7. 获取特征重要性
            feature_importance = feature_engineering.get_feature_importance(
                model, feature_names
            )
            
            # 8. 保存模型
            model_version = datetime.now().strftime('v%Y%m%d_%H%M%S')
            model_name = f"{model_type}_{model_version}"
            model_dir = os.path.join(project_root, 'models', model_type)
            os.makedirs(model_dir, exist_ok=True)
            model_file_path = os.path.join(model_dir, f"{model_name}.pkl")
            model_relative_path = os.path.join('models', model_type, f"{model_name}.pkl")
            
            success = model_trainer.save_model(
                model=model,
                model_path=model_file_path,
                feature_names=feature_names,
                feature_importance=feature_importance,
                metrics=metrics,
                config={'model_type': model_type}
            )
            
            if not success:
                logger.error(f"模型保存失败: {model_type}")
                continue
            
            # 9. 保存模型信息到数据库
            model_id = model_manager.save_model_info(
                model_name=model_name,
                model_type=model_type,
                model_version=model_version,
                model_file_path=model_relative_path,
                feature_list=feature_names,
                feature_importance=feature_importance,
                training_config={'model_type': model_type},
                training_metrics=metrics,
                train_start_date=train_start_date,
                train_end_date=train_end_date,
                val_start_date=val_start_date,
                val_end_date=val_end_date,
                test_start_date=test_start_date,
                test_end_date=test_end_date,
                sample_count=len(train_df),
                is_active=is_active,
                description=f"使用 {train_start_date} 到 {train_end_date} 的数据训练"
            )
            
            if model_id > 0:
                logger.info(f"模型信息保存成功: {model_name} (ID: {model_id})")
                
                # 如果激活，则激活该模型
                if is_active:
                    model_manager.activate_model(model_id)
                    logger.info(f"模型已激活: {model_name}")
            else:
                logger.warning(f"模型信息保存失败: {model_name}")
        
        logger.info("\n" + "=" * 60)
        logger.info("模型训练完成")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"训练过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='训练机器学习模型')
    parser.add_argument('--train-start', type=str, default='2014-01-01', help='训练集开始日期')
    parser.add_argument('--train-end', type=str, default='2022-12-31', help='训练集结束日期')
    parser.add_argument('--val-start', type=str, default='2023-01-01', help='验证集开始日期')
    parser.add_argument('--val-end', type=str, default='2023-12-31', help='验证集结束日期')
    parser.add_argument('--test-start', type=str, default='2024-01-01', help='测试集开始日期')
    parser.add_argument('--test-end', type=str, default='2024-12-31', help='测试集结束日期')
    parser.add_argument('--models', type=str, nargs='+', 
                       default=['xgb_classifier', 'lgb_classifier'],
                       help='要训练的模型类型')
    parser.add_argument('--no-activate', action='store_true', help='不激活训练好的模型')
    parser.add_argument('--use-predictions', action='store_true', 
                       help='使用stock_predictions表的数据（默认使用stock_history_data表）')
    
    args = parser.parse_args()
    
    train_models(
        train_start_date=args.train_start,
        train_end_date=args.train_end,
        val_start_date=args.val_start,
        val_end_date=args.val_end,
        test_start_date=args.test_start,
        test_end_date=args.test_end,
        model_types=args.models,
        is_active=not args.no_activate,
        use_history_data=not args.use_predictions
    )
