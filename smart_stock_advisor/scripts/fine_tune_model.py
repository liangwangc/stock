#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微调基础模型（使用stock_predictions表数据）
这是第二阶段：使用预测数据对基础模型进行微调
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.ml_data_loader import MLDataLoader
from utils.ml_feature_engineering import MLFeatureEngineering
from utils.ml_model_trainer import MLModelTrainer
from utils.ml_model_manager import MLModelManager

logger = get_logger(__name__)


def fine_tune_models(start_date: str, end_date: str, min_samples: int = 1000):
    """
    微调模型（批量微调所有基础模型）
    
    Args:
        start_date: 微调数据开始日期
        end_date: 微调数据结束日期
        min_samples: 最少样本数（默认1000）
    """
    try:
        logger.info("=" * 60)
        logger.info("开始批量微调模型")
        logger.info("=" * 60)
        
        # 1. 初始化模型管理器
        model_manager = MLModelManager()
        
        # 2. 获取所有基础模型
        all_models = model_manager.list_models()
        base_models = [m for m in all_models if 'base' in m.get('model_name', '').lower() and m.get('is_active', False)]
        
        if not base_models:
            logger.error("未找到激活的基础模型")
            logger.info("请先训练基础模型，或激活一个基础模型")
            return
        
        # 3. 按版本排序，选择最新的基础模型
        base_models.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        latest_base_model = base_models[0]
        base_model_name = latest_base_model['model_name']
        
        logger.info(f"找到 {len(base_models)} 个基础模型")
        logger.info(f"使用最新的基础模型进行微调: {base_model_name}")
        
        # 4. 检查数据样本数
        data_loader = MLDataLoader()
        fine_tune_df = data_loader.load_training_data(
            start_date=start_date,
            end_date=end_date
        )
        
        if fine_tune_df.empty:
            logger.error(f"微调数据为空（{start_date} 到 {end_date}），无法继续微调")
            logger.info("可能的原因：")
            logger.info("  1. 指定日期范围内没有有实际结果的预测记录")
            logger.info("     - 需要 actual_price, actual_direction, prediction_hit 都不为空")
            logger.info("     - 通常需要等待股票收盘后更新实际结果")
            logger.info("  2. 预测记录缺少对应的历史数据（stock_history_data表）")
            logger.info("     - 需要至少60-90天的历史数据才能构建特征")
            logger.info("  3. 日期范围设置不合理")
            logger.info("     - 建议使用最近90天的数据")
            logger.info("")
            logger.info("解决方案：")
            logger.info("  1. 检查 stock_predictions 表中是否有实际结果数据")
            logger.info("  2. 检查 stock_history_data 表中是否有足够的历史数据")
            logger.info("  3. 调整日期范围，使用有数据的日期范围")
            logger.info("  4. 等待更多预测记录的实际结果更新")
            return
        
        sample_count = len(fine_tune_df)
        logger.info(f"微调数据加载完成：{sample_count} 条样本")
        
        if sample_count < min_samples:
            logger.warning(f"微调样本数不足（{sample_count} < {min_samples}），建议至少 {min_samples} 条")
            logger.warning("微调可能效果不佳，但将继续执行...")
        
        # 5. 调用 fine_tune_base_model 进行微调
        logger.info(f"\n开始微调基础模型: {base_model_name}")
        fine_tune_base_model(
            base_model_name=base_model_name,
            fine_tune_start_date=start_date,
            fine_tune_end_date=end_date,
            learning_rate_multiplier=0.1,
            n_estimators=50,
            is_active=True
        )
        
        logger.info("\n" + "=" * 60)
        logger.info("批量微调完成")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"批量微调过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def fine_tune_base_model(base_model_name: str,
                        fine_tune_start_date: str = None,
                        fine_tune_end_date: str = None,
                        learning_rate_multiplier: float = 0.1,
                        n_estimators: int = 50,
                        is_active: bool = True):
    """
    微调基础模型
    
    Args:
        base_model_name: 基础模型名称（如：xgb_classifier_base_v1.0）
        fine_tune_start_date: 微调数据开始日期（None表示最近90天）
        fine_tune_end_date: 微调数据结束日期（None表示今天）
        learning_rate_multiplier: 学习率倍数（降低学习率）
        n_estimators: 微调时的树数量
        is_active: 是否激活微调后的模型
    """
    try:
        logger.info("=" * 60)
        logger.info("开始微调基础模型")
        logger.info("=" * 60)
        
        # 1. 初始化组件
        data_loader = MLDataLoader()
        feature_engineering = MLFeatureEngineering()
        model_trainer = MLModelTrainer()
        model_manager = MLModelManager()
        
        # 2. 加载基础模型
        logger.info(f"\n加载基础模型: {base_model_name}")
        base_model_info = model_manager.get_model_info(base_model_name.split('_base_')[0], 
                                                       version=base_model_name.split('_base_')[-1] if '_base_' in base_model_name else None)
        
        if not base_model_info:
            logger.error(f"未找到基础模型: {base_model_name}")
            logger.info("可用的基础模型：")
            models = model_manager.list_models()
            base_models = [m for m in models if 'base' in m.get('model_name', '').lower()]
            for m in base_models:
                logger.info(f"  - {m['model_name']}")
            return
        
        # 加载模型对象
        model_type = base_model_info['model_type']
        base_model = model_manager.load_model(model_type, version=base_model_info['model_version'])
        
        if base_model is None:
            logger.error("基础模型加载失败")
            return
        
        logger.info(f"基础模型加载成功: {base_model_info['model_name']}")
        logger.info(f"基础模型准确率: {base_model_info['training_metrics'].get('val_accuracy', 'N/A')}")
        
        # 3. 确定微调数据时间范围
        if fine_tune_end_date is None:
            fine_tune_end_date = datetime.now().strftime('%Y-%m-%d')
        
        if fine_tune_start_date is None:
            # 默认使用最近90天
            end_date_obj = datetime.strptime(fine_tune_end_date, '%Y-%m-%d')
            start_date_obj = end_date_obj - timedelta(days=90)
            fine_tune_start_date = start_date_obj.strftime('%Y-%m-%d')
        
        logger.info(f"\n加载微调数据：{fine_tune_start_date} 到 {fine_tune_end_date}")
        logger.info("数据源：stock_predictions表（有实际结果的预测记录）")
        
        # 4. 加载微调数据（从stock_predictions表）
        fine_tune_df = data_loader.load_training_data(
            start_date=fine_tune_start_date,
            end_date=fine_tune_end_date
        )
        
        if fine_tune_df.empty:
            logger.error("微调数据为空，无法继续微调")
            logger.info("建议：等待更多预测记录的实际结果更新")
            return
        
        logger.info(f"微调数据加载完成：{len(fine_tune_df)} 条样本")
        
        if len(fine_tune_df) < 100:
            logger.warning(f"微调样本数较少（{len(fine_tune_df)}条），建议至少1000+条")
        
        # 5. 准备特征和标签（严格使用 selected_features.pkl）
        logger.info("\n准备特征和标签（严格使用 selected_features.pkl）...")
        X_finetune, y_finetune, feature_names = feature_engineering.prepare_features(
            fine_tune_df, label_column='label_up', use_selected_features=True
        )
        
        if X_finetune.empty:
            logger.error("特征准备失败，无法继续微调")
            return
        
        # 确保特征顺序与基础模型一致
        base_feature_list = base_model_info.get('feature_list', [])
        if base_feature_list:
            # 只使用基础模型使用的特征
            missing_features = [f for f in base_feature_list if f not in X_finetune.columns]
            if missing_features:
                logger.warning(f"缺少特征: {missing_features}，将使用0填充")
                for feat in missing_features:
                    X_finetune[feat] = 0.0
            
            # 按基础模型的特征顺序排列
            X_finetune = X_finetune[base_feature_list]
            feature_names = base_feature_list
        
        logger.info(f"特征准备完成：{len(feature_names)} 个特征")
        
        # 6. 微调模型
        logger.info(f"\n开始微调模型...")
        logger.info(f"学习率倍数: {learning_rate_multiplier}")
        logger.info(f"树数量: {n_estimators}")
        
        fine_tuned_model, metrics = model_trainer.fine_tune_model(
            base_model=base_model,
            X_finetune=X_finetune,
            y_finetune=y_finetune,
            learning_rate_multiplier=learning_rate_multiplier,
            n_estimators=n_estimators,
            model_type=model_type  # 传递模型类型，确保正确识别
        )
        
        if fine_tuned_model is None:
            logger.error("模型微调失败")
            return
        
        logger.info(f"模型微调完成")
        logger.info(f"微调后准确率: {metrics.get('train_accuracy', 'N/A'):.4f}")
        
        # 7. 获取特征重要性
        feature_importance = feature_engineering.get_feature_importance(
            fine_tuned_model, feature_names
        )
        
        # 8. 保存微调模型
        model_version = datetime.now().strftime('v%Y%m%d_%H%M%S')
        model_name = f"{model_type}_finetuned_{model_version}"
        model_dir = os.path.join(project_root, 'models', model_type)
        os.makedirs(model_dir, exist_ok=True)
        model_file_path = os.path.join(model_dir, f"{model_name}.pkl")
        model_relative_path = os.path.join('models', model_type, f"{model_name}.pkl")
        
        success = model_trainer.save_model(
            model=fine_tuned_model,
            model_path=model_file_path,
            feature_names=feature_names,
            feature_importance=feature_importance,
            metrics=metrics,
            config={
                'model_type': model_type,
                'model_category': 'finetuned',
                'base_model_name': base_model_info['model_name'],
                'base_model_id': base_model_info['id'],
                'data_source': 'stock_predictions',
                'learning_rate_multiplier': learning_rate_multiplier,
                'n_estimators': n_estimators
            }
        )
        
        if not success:
            logger.error(f"微调模型保存失败")
            return
        
        # 9. 保存模型信息到数据库（标记为finetuned模型）
        model_id = model_manager.save_model_info(
            model_name=model_name,
            model_type=model_type,
            model_version=model_version,
            model_file_path=model_relative_path,
            feature_list=feature_names,
            feature_importance=feature_importance,
            training_config={
                'model_type': model_type,
                'model_category': 'finetuned',
                'base_model_name': base_model_info['model_name'],
                'base_model_id': base_model_info['id'],
                'data_source': 'stock_predictions',
                'learning_rate_multiplier': learning_rate_multiplier,
                'n_estimators': n_estimators
            },
            training_metrics=metrics,
            train_start_date=fine_tune_start_date,
            train_end_date=fine_tune_end_date,
            sample_count=len(fine_tune_df),
            is_active=is_active,
            description=f"微调模型：基于 {base_model_info['model_name']}，使用 {fine_tune_start_date} 到 {fine_tune_end_date} 的预测数据微调"
        )
        
        if model_id > 0:
            logger.info(f"微调模型信息保存成功: {model_name} (ID: {model_id})")
            
            # 如果激活，则激活该模型
            if is_active:
                model_manager.activate_model(model_id)
                logger.info(f"微调模型已激活: {model_name}")
        else:
            logger.warning(f"微调模型信息保存失败: {model_name}")
        
        logger.info("\n" + "=" * 60)
        logger.info("模型微调完成")
        logger.info("=" * 60)
        logger.info(f"\n对比结果：")
        logger.info(f"  基础模型准确率: {base_model_info['training_metrics'].get('val_accuracy', 'N/A'):.4f}")
        logger.info(f"  微调模型准确率: {metrics.get('train_accuracy', 'N/A'):.4f}")
        
    except Exception as e:
        logger.error(f"微调过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='微调基础模型（使用stock_predictions表数据）')
    parser.add_argument('--base-model', type=str, required=True,
                       help='基础模型名称（如：xgb_classifier_base_v1.0）')
    parser.add_argument('--start-date', type=str, default=None,
                       help='微调数据开始日期（默认：最近90天）')
    parser.add_argument('--end-date', type=str, default=None,
                       help='微调数据结束日期（默认：今天）')
    parser.add_argument('--lr-multiplier', type=float, default=0.1,
                       help='学习率倍数（默认：0.1，即降低10倍）')
    parser.add_argument('--n-estimators', type=int, default=50,
                       help='微调时的树数量（默认：50）')
    parser.add_argument('--no-activate', action='store_true',
                       help='不激活微调后的模型')
    
    args = parser.parse_args()
    
    fine_tune_base_model(
        base_model_name=args.base_model,
        fine_tune_start_date=args.start_date,
        fine_tune_end_date=args.end_date,
        learning_rate_multiplier=args.lr_multiplier,
        n_estimators=args.n_estimators,
        is_active=not args.no_activate
    )
