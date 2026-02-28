#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
训练基础模型（使用stock_history_data表全量数据）
这是第一阶段：使用10年历史数据训练稳定的基础模型
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.ml_data_loader import MLDataLoader
from utils.ml_feature_engineering import MLFeatureEngineering
from utils.ml_model_trainer import MLModelTrainer
from utils.ml_model_manager import MLModelManager

logger = get_logger(__name__)


def train_base_models(train_start_date: str = '2014-01-01',
                     train_end_date: str = '2022-12-31',
                     val_start_date: str = '2023-01-01',
                     val_end_date: str = '2023-12-31',
                     test_start_date: str = '2024-01-01',
                     test_end_date: str = '2024-12-31',
                     model_types: list = ['xgb_classifier', 'lgb_classifier'],
                     is_active: bool = True,
                     progress_callback=None):
    """
    训练基础模型（使用stock_history_data表全量数据）
    
    Args:
        train_start_date: 训练集开始日期
        train_end_date: 训练集结束日期
        val_start_date: 验证集开始日期
        val_end_date: 验证集结束日期
        test_start_date: 测试集开始日期
        test_end_date: 测试集结束日期
        model_types: 要训练的模型类型列表
        is_active: 是否激活训练好的模型
        progress_callback: 可选，签名为 (progress: int, message: str, log: Optional[str])，用于页面进度与日志
    """
    def _progress(progress: int, message: str, log: str = None):
        if progress_callback:
            try:
                progress_callback(progress, message, log)
            except Exception:
                pass
    try:
        _progress(5, "正在加载训练数据...", "开始训练基础模型（使用stock_history_data表全量数据）")
        logger.info("=" * 60)
        logger.info("开始训练基础模型（使用stock_history_data表全量数据）")
        logger.info("=" * 60)
        
        # 1. 初始化组件
        data_loader = MLDataLoader()
        feature_engineering = MLFeatureEngineering()
        model_trainer = MLModelTrainer()
        model_manager = MLModelManager()
        
        import time
        total_start_time = time.time()
        
        # 2. 加载训练数据（从stock_history_data表）
        logger.info(f"\n{'=' * 60}")
        logger.info(f"步骤 1/5: 加载训练数据")
        logger.info(f"{'=' * 60}")
        logger.info(f"时间范围：{train_start_date} 到 {train_end_date}")
        logger.info("数据源：stock_history_data表（全量历史数据）")
        
        train_start_time = time.time()
        train_df = data_loader.load_training_data_from_history(
            start_date=train_start_date,
            end_date=train_end_date
        )
        train_load_time = time.time() - train_start_time
        
        if train_df.empty:
            logger.error("训练数据为空，无法继续训练")
            _progress(0, "训练失败：训练数据为空", "训练数据为空，无法继续训练。请检查：1) stock_history_data 表是否有数据；2) 训练/验证日期范围是否在表内。")
            raise RuntimeError("训练数据为空，无法继续训练")
        
        _progress(10, "训练数据加载完成，正在加载验证数据...", f"✓ 训练数据加载完成：{len(train_df):,} 条样本")
        logger.info(f"✓ 训练数据加载完成：{len(train_df):,} 条样本，耗时 {train_load_time:.1f}秒 ({train_load_time/60:.1f}分钟)")
        
        # 3. 加载验证数据
        logger.info(f"\n{'=' * 60}")
        logger.info(f"步骤 2/5: 加载验证数据")
        logger.info(f"{'=' * 60}")
        logger.info(f"时间范围：{val_start_date} 到 {val_end_date}")
        
        val_start_time = time.time()
        val_df = data_loader.load_training_data_from_history(
            start_date=val_start_date,
            end_date=val_end_date
        )
        val_load_time = time.time() - val_start_time
        
        logger.info(f"✓ 验证数据加载完成：{len(val_df):,} 条样本，耗时 {val_load_time:.1f}秒 ({val_load_time/60:.1f}分钟)")
        _progress(20, "验证数据加载完成，正在准备特征...", "步骤 2/5: 加载验证数据 完成")
        
        # 4. 准备特征和标签
        logger.info(f"\n{'=' * 60}")
        logger.info(f"步骤 3/5: 准备特征和标签")
        logger.info(f"{'=' * 60}")
        _progress(25, "正在准备特征和标签（可能需数分钟）...", "步骤 3/5: 准备特征和标签")
        
        feature_start_time = time.time()
        logger.info("正在提取训练集特征...")
        X_train, y_train, feature_names = feature_engineering.prepare_features(
            train_df, label_column='label_up', use_selected_features=True
        )
        
        if X_train.empty:
            logger.error("特征准备失败，无法继续训练")
            _progress(25, "特征准备失败", "特征准备失败，无法继续训练")
            raise RuntimeError("特征准备失败，无法继续训练")
        
        logger.info("正在提取验证集特征...")
        X_val, y_val, _ = feature_engineering.prepare_features(
            val_df, label_column='label_up', use_selected_features=True
        )
        feature_time = time.time() - feature_start_time
        
        logger.info(f"✓ 特征准备完成：{len(feature_names)} 个特征，耗时 {feature_time:.1f}秒")
        logger.info(f"  训练集：{len(X_train):,} 条样本")
        logger.info(f"  验证集：{len(X_val):,} 条样本")
        
        # 显示标签分布
        train_up_count = int(y_train.sum())
        train_down_count = len(y_train) - train_up_count
        val_up_count = int(y_val.sum()) if len(y_val) > 0 else 0
        val_down_count = len(y_val) - val_up_count if len(y_val) > 0 else 0
        
        logger.info(f"  训练集标签分布：上涨 {train_up_count:,} ({train_up_count/len(y_train)*100:.1f}%), 下跌 {train_down_count:,} ({train_down_count/len(y_train)*100:.1f}%)")
        if len(y_val) > 0:
            logger.info(f"  验证集标签分布：上涨 {val_up_count:,} ({val_up_count/len(y_val)*100:.1f}%), 下跌 {val_down_count:,} ({val_down_count/len(y_val)*100:.1f}%)")
        
        _progress(45, "特征准备完成，正在训练模型...", f"✓ 特征准备完成：{len(feature_names)} 个特征")
        
        # 5. 训练模型
        total_models = len(model_types)
        for model_idx, model_type in enumerate(model_types, 1):
            _progress(45 + int(35 * (model_idx - 1) / max(1, total_models)), f"正在训练模型 ({model_idx}/{total_models})...", f"步骤 4/5: 训练基础模型 ({model_idx}/{total_models})")
            logger.info(f"\n{'=' * 60}")
            logger.info(f"步骤 4/5: 训练基础模型 ({model_idx}/{total_models})")
            logger.info(f"{'=' * 60}")
            logger.info(f"模型类型: {model_type}")
            
            model_start_time = time.time()
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
                # 使用涨跌幅作为标签（严格按 selected_features.pkl 选取特征）
                X_train_reg, y_train_reg, _ = feature_engineering.prepare_features(
                    train_df, label_column='label_change_pct', use_selected_features=True
                )
                X_val_reg, y_val_reg, _ = feature_engineering.prepare_features(
                    val_df, label_column='label_change_pct', use_selected_features=True
                )
                model, metrics = model_trainer.train_xgb_regressor(
                    X_train_reg, y_train_reg, X_val_reg, y_val_reg
                )
            elif model_type == 'lgb_regressor_return':
                # 回归模型：预测 future_return（涨跌幅小数=(future_close - close)/close），用于涨幅预测增强
                X_train_reg, y_train_reg, _ = feature_engineering.prepare_features(
                    train_df, label_column='future_return', use_selected_features=True
                )
                X_val_reg, y_val_reg, _ = feature_engineering.prepare_features(
                    val_df, label_column='future_return', use_selected_features=True
                )
                model, metrics = model_trainer.train_lgb_regressor_return(
                    X_train_reg, y_train_reg, X_val_reg, y_val_reg
                )
            else:
                logger.warning(f"未知的模型类型: {model_type}")
                continue
            
            if model is None:
                logger.error(f"✗ 模型训练失败: {model_type}")
                continue
            
            model_train_time = time.time() - model_start_time
            logger.info(f"✓ 模型训练完成，耗时 {model_train_time:.1f}秒 ({model_train_time/60:.1f}分钟)")
            
            # 显示训练指标
            if metrics:
                logger.info(f"训练指标:")
                for key, value in metrics.items():
                    if isinstance(value, float):
                        logger.info(f"  {key}: {value:.4f}")
                    else:
                        logger.info(f"  {key}: {value}")
            
            # 回归涨跌幅模型：仅保存到 models/lgb_regressor_return.pkl，不写数据库
            if model_type == 'lgb_regressor_return':
                reg_return_path = os.path.join(project_root, 'models', 'lgb_regressor_return.pkl')
                os.makedirs(os.path.dirname(reg_return_path), exist_ok=True)
                try:
                    import pickle
                    with open(reg_return_path, 'wb') as f:
                        pickle.dump(model, f)
                    # 打印规范化成功信息（英文 + 相对路径），便于脚本/日志检测
                    logger.info("✓ Regression model trained successfully")
                    logger.info("✓ Saved to models/lgb_regressor_return.pkl")
                    # 训练完成后进行文件存在性校验
                    rel_path = os.path.join('models', 'lgb_regressor_return.pkl')
                    assert os.path.exists(os.path.join(project_root, rel_path)), \
                        f"Regression model file not found after saving: {rel_path}"
                except Exception as e:
                    logger.error(f"✗ 涨跌幅回归模型保存失败: {e}")
                    raise
                model_total_time = time.time() - model_start_time
                logger.info(f"模型 {model_type} 处理完成，总耗时: {model_total_time:.1f}秒")
                continue
            
            # 6. 获取特征重要性
            logger.info("正在计算特征重要性...")
            feature_importance = feature_engineering.get_feature_importance(
                model, feature_names
            )
            
            # 显示Top 10特征
            if feature_importance:
                top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
                logger.info(f"Top 10 重要特征:")
                for feat_name, importance in top_features:
                    logger.info(f"  {feat_name}: {importance:.4f}")
            
            # 7. 保存模型（标记为基础模型）
            _progress(85, "正在保存模型...", "步骤 5/5: 保存模型")
            logger.info(f"\n{'=' * 60}")
            logger.info(f"步骤 5/5: 保存模型")
            logger.info(f"{'=' * 60}")
            
            save_start_time = time.time()
            model_version = datetime.now().strftime('v%Y%m%d_%H%M%S')
            model_name = f"{model_type}_base_{model_version}"
            model_dir = os.path.join(project_root, 'models', model_type)
            os.makedirs(model_dir, exist_ok=True)
            model_file_path = os.path.join(model_dir, f"{model_name}.pkl")
            model_relative_path = os.path.join('models', model_type, f"{model_name}.pkl")
            
            logger.info(f"正在保存模型文件: {model_file_path}")
            success = model_trainer.save_model(
                model=model,
                model_path=model_file_path,
                feature_names=feature_names,
                feature_importance=feature_importance,
                metrics=metrics,
                config={
                    'model_type': model_type,
                    'model_category': 'base',
                    'data_source': 'stock_history_data'
                }
            )
            
            if not success:
                logger.error(f"✗ 模型文件保存失败: {model_type}")
                _progress(90, f"模型文件保存失败: {model_type}", f"✗ 模型文件保存失败: {model_type}")
                raise RuntimeError(
                    f"模型文件保存失败: {model_type}。请检查：1) 目录 models/{model_type} 是否有写权限；"
                    "2) 磁盘空间是否充足；3) 查看 logs 中的详细错误"
                )
            
            save_time = time.time() - save_start_time
            logger.info(f"✓ 模型文件保存成功，耗时 {save_time:.1f}秒")
            _progress(88, "模型文件已保存，正在写入数据库...", "✓ 模型文件保存成功")
            
            # 8. 保存模型信息到数据库（标记为base模型）
            logger.info("正在保存模型信息到数据库...")
            _progress(89, "正在保存模型信息到数据库...", "正在保存模型信息到数据库...")
            model_id = model_manager.save_model_info(
                model_name=model_name,
                model_type=model_type,
                model_version=model_version,
                model_file_path=model_relative_path,
                feature_list=feature_names,
                feature_importance=feature_importance,
                training_config={
                    'model_type': model_type,
                    'model_category': 'base',
                    'data_source': 'stock_history_data'
                },
                training_metrics=metrics,
                train_start_date=train_start_date,
                train_end_date=train_end_date,
                val_start_date=val_start_date,
                val_end_date=val_end_date,
                test_start_date=test_start_date,
                test_end_date=test_end_date,
                sample_count=len(train_df),
                is_active=is_active,
                description=f"基础模型：使用 {train_start_date} 到 {train_end_date} 的stock_history_data表数据训练"
            )
            
            if model_id > 0:
                logger.info(f"✓ 基础模型信息保存成功: {model_name} (ID: {model_id})")
                _progress(90 + int(10 * model_idx / max(1, total_models)), f"已保存: {model_name}", f"✓ 基础模型信息保存成功: {model_name} (ID: {model_id})")
                # 如果激活，则激活该模型
                if is_active:
                    model_manager.activate_model(model_id)
                    logger.info(f"✓ 基础模型已激活: {model_name}")
            else:
                logger.error(f"✗ 基础模型信息保存失败: {model_name}，数据库未写入记录")
                _progress(90, "模型信息保存失败，数据库未写入", f"✗ 基础模型信息保存失败: {model_name}")
                raise RuntimeError(
                    "模型信息保存失败，数据库未写入记录。请检查：1) config_db 中 USE_DATABASE=True；"
                    "2) 数据库连接正常；3) trained_models 表已创建；4) 查看 logs 中的详细错误"
                )
            
            model_total_time = time.time() - model_start_time
            logger.info(f"\n模型 {model_type} 处理完成，总耗时: {model_total_time:.1f}秒 ({model_total_time/60:.1f}分钟)")
        
        total_time = time.time() - total_start_time
        _progress(100, "训练完成", "✓ 基础模型训练完成")
        logger.info("\n" + "=" * 60)
        logger.info("✓ 基础模型训练完成")
        logger.info("=" * 60)
        logger.info(f"\n总耗时统计:")
        logger.info(f"  数据加载: {train_load_time + val_load_time:.1f}秒 ({(train_load_time + val_load_time)/60:.1f}分钟)")
        logger.info(f"  特征提取: {feature_time:.1f}秒 ({feature_time/60:.1f}分钟)")
        logger.info(f"  模型训练: {total_time - train_load_time - val_load_time - feature_time:.1f}秒 ({(total_time - train_load_time - val_load_time - feature_time)/60:.1f}分钟)")
        logger.info(f"  总计: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
        logger.info(f"\n训练结果:")
        logger.info(f"  训练样本数: {len(train_df):,} 条")
        logger.info(f"  验证样本数: {len(val_df):,} 条")
        logger.info(f"  特征数量: {len(feature_names)} 个")
        logger.info(f"  训练模型数: {len(model_types)} 个")
        logger.info(f"\n下一步：")
        logger.info("  1. 等待预测数据积累（至少1000+条有实际结果的预测记录）")
        logger.info("  2. 运行微调脚本：python scripts/fine_tune_model.py")
        
    except Exception as e:
        logger.error(f"训练过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            _progress(0, f"训练失败: {str(e)}", f"训练过程出错: {str(e)}")
        except Exception:
            pass
        raise  # 重新抛出，便于 Web 端将任务标记为失败


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='训练基础模型（使用stock_history_data表）')
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
    
    args = parser.parse_args()
    
    train_base_models(
        train_start_date=args.train_start,
        train_end_date=args.train_end,
        val_start_date=args.val_start,
        val_end_date=args.val_end,
        test_start_date=args.test_start,
        test_end_date=args.test_end,
        model_types=args.models,
        is_active=not args.no_activate
    )
