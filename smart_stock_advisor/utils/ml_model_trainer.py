"""
机器学习模型训练模块
用于训练XGBoost、LightGBM等模型
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import pickle
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.ml_feature_engineering import MLFeatureEngineering

logger = get_logger(__name__)


class MLModelTrainer:
    """机器学习模型训练器"""
    
    def __init__(self):
        self.logger = logger
        self.feature_engineering = MLFeatureEngineering()
    
    def train_xgb_classifier(self,
                            X_train: pd.DataFrame,
                            y_train: pd.Series,
                            X_val: Optional[pd.DataFrame] = None,
                            y_val: Optional[pd.Series] = None,
                            params: Optional[Dict] = None) -> Tuple[object, Dict]:
        """
        训练XGBoost分类器
        
        Args:
            X_train: 训练集特征
            y_train: 训练集标签
            X_val: 验证集特征（可选）
            y_val: 验证集标签（可选）
            params: 模型参数
        
        Returns:
            (model, metrics)
        """
        try:
            import xgboost as xgb
            
            # 默认参数
            default_params = {
                'objective': 'binary:logistic',
                'eval_metric': 'logloss',
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'n_jobs': -1
            }
            
            if params:
                default_params.update(params)
            
            # 检查并移除object类型的列（XGBoost不支持）
            # 注意：必须创建副本，确保drop操作生效
            object_cols = X_train.select_dtypes(include=['object']).columns.tolist()
            if object_cols:
                self.logger.warning(f"发现object类型列，将被排除: {object_cols}")
                X_train = X_train.drop(columns=object_cols).copy()  # 创建副本确保操作生效
                if X_val is not None:
                    X_val = X_val.drop(columns=object_cols).copy()  # 创建副本确保操作生效
            
            # 再次检查，确保没有遗漏
            remaining_object_cols = X_train.select_dtypes(include=['object']).columns.tolist()
            if remaining_object_cols:
                self.logger.error(f"仍有object类型列未被移除: {remaining_object_cols}")
                raise ValueError(f"无法移除object类型列: {remaining_object_cols}")
            
            # 创建模型
            model = xgb.XGBClassifier(**default_params)
            
            self.logger.info(f"开始训练XGBoost分类器...")
            self.logger.info(f"  训练集大小: {len(X_train):,} 条样本")
            if X_val is not None:
                self.logger.info(f"  验证集大小: {len(X_val):,} 条样本")
            self.logger.info(f"  特征数量: {X_train.shape[1]}")
            self.logger.info(f"  参数: n_estimators={default_params['n_estimators']}, max_depth={default_params['max_depth']}, learning_rate={default_params['learning_rate']}")
            
            import time
            train_start_time = time.time()
            
            # 训练
            if X_val is not None and y_val is not None:
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_train, y_train), (X_val, y_val)],
                    verbose=10  # 每10轮显示一次进度
                )
            else:
                model.fit(X_train, y_train, verbose=10)
            
            train_elapsed = time.time() - train_start_time
            self.logger.info(f"XGBoost训练完成，耗时: {train_elapsed:.1f}秒 ({train_elapsed/60:.1f}分钟)")
            
            # 评估
            train_pred = model.predict(X_train)
            train_pred_proba = model.predict_proba(X_train)[:, 1]
            train_accuracy = np.mean(train_pred == y_train)
            
            metrics = {
                'train_accuracy': float(train_accuracy),
                'train_logloss': float(self._calculate_logloss(y_train, train_pred_proba))
            }
            
            if X_val is not None and y_val is not None:
                val_pred = model.predict(X_val)
                val_pred_proba = model.predict_proba(X_val)[:, 1]
                val_accuracy = np.mean(val_pred == y_val)
                metrics['val_accuracy'] = float(val_accuracy)
                metrics['val_logloss'] = float(self._calculate_logloss(y_val, val_pred_proba))
            
            self.logger.info(f"XGBoost分类器训练完成：训练准确率 {train_accuracy:.4f}")
            
            return model, metrics
            
        except ImportError:
            self.logger.error("XGBoost未安装，请运行: pip install xgboost")
            return None, {}
        except Exception as e:
            self.logger.error(f"训练XGBoost分类器失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None, {}
    
    def train_lgb_classifier(self,
                            X_train: pd.DataFrame,
                            y_train: pd.Series,
                            X_val: Optional[pd.DataFrame] = None,
                            y_val: Optional[pd.Series] = None,
                            params: Optional[Dict] = None) -> Tuple[object, Dict]:
        """
        训练LightGBM分类器
        
        Args:
            X_train: 训练集特征
            y_train: 训练集标签
            X_val: 验证集特征（可选）
            y_val: 验证集标签（可选）
            params: 模型参数
        
        Returns:
            (model, metrics)
        """
        try:
            import lightgbm as lgb
            
            # 默认参数
            default_params = {
                'objective': 'binary',
                'metric': 'binary_logloss',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.1,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1,
                'random_state': 42
            }
            
            if params:
                default_params.update(params)
            
            # 检查并移除object类型的列（LightGBM不支持）
            # 注意：必须创建副本，确保drop操作生效
            object_cols = X_train.select_dtypes(include=['object']).columns.tolist()
            if object_cols:
                self.logger.warning(f"发现object类型列，将被排除: {object_cols}")
                X_train = X_train.drop(columns=object_cols).copy()  # 创建副本确保操作生效
                if X_val is not None:
                    X_val = X_val.drop(columns=object_cols).copy()  # 创建副本确保操作生效
            
            # 再次检查，确保没有遗漏
            remaining_object_cols = X_train.select_dtypes(include=['object']).columns.tolist()
            if remaining_object_cols:
                self.logger.error(f"仍有object类型列未被移除: {remaining_object_cols}")
                raise ValueError(f"无法移除object类型列: {remaining_object_cols}")
            
            # 创建数据集
            train_data = lgb.Dataset(X_train, label=y_train)
            
            self.logger.info(f"开始训练LightGBM分类器...")
            self.logger.info(f"  训练集大小: {len(X_train):,} 条样本")
            if X_val is not None:
                self.logger.info(f"  验证集大小: {len(X_val):,} 条样本")
            self.logger.info(f"  特征数量: {X_train.shape[1]}")
            self.logger.info(f"  参数: num_boost_round=100, num_leaves={default_params['num_leaves']}, learning_rate={default_params['learning_rate']}")
            
            import time
            train_start_time = time.time()
            
            if X_val is not None and y_val is not None:
                val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
                model = lgb.train(
                    default_params,
                    train_data,
                    valid_sets=[train_data, val_data],
                    num_boost_round=100,
                    callbacks=[
                        lgb.early_stopping(stopping_rounds=10), 
                        lgb.log_evaluation(10)  # 每10轮显示一次进度
                    ]
                )
            else:
                model = lgb.train(
                    default_params,
                    train_data,
                    num_boost_round=100,
                    callbacks=[lgb.log_evaluation(10)]  # 每10轮显示一次进度
                )
            
            train_elapsed = time.time() - train_start_time
            self.logger.info(f"LightGBM训练完成，耗时: {train_elapsed:.1f}秒 ({train_elapsed/60:.1f}分钟)")
            
            # 评估
            train_pred_proba = model.predict(X_train, num_iteration=model.best_iteration if hasattr(model, 'best_iteration') else None)
            train_pred = (train_pred_proba > 0.5).astype(int)
            train_accuracy = np.mean(train_pred == y_train)
            
            metrics = {
                'train_accuracy': float(train_accuracy),
                'train_logloss': float(self._calculate_logloss(y_train, train_pred_proba))
            }
            
            if X_val is not None and y_val is not None:
                val_pred_proba = model.predict(X_val, num_iteration=model.best_iteration if hasattr(model, 'best_iteration') else None)
                val_pred = (val_pred_proba > 0.5).astype(int)
                val_accuracy = np.mean(val_pred == y_val)
                metrics['val_accuracy'] = float(val_accuracy)
                metrics['val_logloss'] = float(self._calculate_logloss(y_val, val_pred_proba))
            
            self.logger.info(f"LightGBM分类器训练完成：训练准确率 {train_accuracy:.4f}")
            
            return model, metrics
            
        except ImportError:
            self.logger.error("LightGBM未安装，请运行: pip install lightgbm")
            return None, {}
        except Exception as e:
            self.logger.error(f"训练LightGBM分类器失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None, {}
    
    def train_xgb_regressor(self,
                           X_train: pd.DataFrame,
                           y_train: pd.Series,
                           X_val: Optional[pd.DataFrame] = None,
                           y_val: Optional[pd.Series] = None,
                           params: Optional[Dict] = None) -> Tuple[object, Dict]:
        """
        训练XGBoost回归器（预测涨跌幅）
        
        Args:
            X_train: 训练集特征
            y_train: 训练集标签（涨跌幅）
            X_val: 验证集特征（可选）
            y_val: 验证集标签（可选）
            params: 模型参数
        
        Returns:
            (model, metrics)
        """
        try:
            import xgboost as xgb
            
            # 默认参数
            default_params = {
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse',
                'max_depth': 6,
                'learning_rate': 0.1,
                'n_estimators': 100,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'n_jobs': -1
            }
            
            if params:
                default_params.update(params)
            
            # 检查并移除object类型的列（XGBoost不支持）
            # 注意：必须创建副本，确保drop操作生效
            object_cols = X_train.select_dtypes(include=['object']).columns.tolist()
            if object_cols:
                self.logger.warning(f"发现object类型列，将被排除: {object_cols}")
                X_train = X_train.drop(columns=object_cols).copy()  # 创建副本确保操作生效
                if X_val is not None:
                    X_val = X_val.drop(columns=object_cols).copy()  # 创建副本确保操作生效
            
            # 再次检查，确保没有遗漏
            remaining_object_cols = X_train.select_dtypes(include=['object']).columns.tolist()
            if remaining_object_cols:
                self.logger.error(f"仍有object类型列未被移除: {remaining_object_cols}")
                raise ValueError(f"无法移除object类型列: {remaining_object_cols}")
            
            # 创建模型
            model = xgb.XGBRegressor(**default_params)
            
            # 训练
            if X_val is not None and y_val is not None:
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_train, y_train), (X_val, y_val)],
                    verbose=False
                )
            else:
                model.fit(X_train, y_train)
            
            # 评估
            train_pred = model.predict(X_train)
            train_mae = np.mean(np.abs(train_pred - y_train))
            train_rmse = np.sqrt(np.mean((train_pred - y_train) ** 2))
            
            metrics = {
                'train_mae': float(train_mae),
                'train_rmse': float(train_rmse)
            }
            
            if X_val is not None and y_val is not None:
                val_pred = model.predict(X_val)
                val_mae = np.mean(np.abs(val_pred - y_val))
                val_rmse = np.sqrt(np.mean((val_pred - y_val) ** 2))
                metrics['val_mae'] = float(val_mae)
                metrics['val_rmse'] = float(val_rmse)
            
            self.logger.info(f"XGBoost回归器训练完成：训练MAE {train_mae:.4f}")
            
            return model, metrics
            
        except ImportError:
            self.logger.error("XGBoost未安装，请运行: pip install xgboost")
            return None, {}
        except Exception as e:
            self.logger.error(f"训练XGBoost回归器失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None, {}
    
    def _calculate_logloss(self, y_true: pd.Series, y_pred_proba: np.ndarray) -> float:
        """计算对数损失"""
        from sklearn.metrics import log_loss
        try:
            return log_loss(y_true, y_pred_proba)
        except:
            return 0.0
    
    def fine_tune_model(self,
                       base_model: object,
                       X_finetune: pd.DataFrame,
                       y_finetune: pd.Series,
                       learning_rate_multiplier: float = 0.1,
                       n_estimators: int = 50,
                       model_type: str = None) -> Tuple[object, Dict]:
        """
        微调基础模型
        
        Args:
            base_model: 基础模型
            X_finetune: 微调数据特征
            y_finetune: 微调数据标签
            learning_rate_multiplier: 学习率倍数（降低学习率）
            n_estimators: 微调时的树数量
            model_type: 模型类型（xgb_classifier/lgb_classifier等），如果为None则自动检测
        
        Returns:
            (fine_tuned_model, metrics)
        """
        try:
            # 如果提供了模型类型，直接使用；否则尝试自动检测
            if model_type is None:
                model_type_name = type(base_model).__name__
                self.logger.debug(f"自动检测模型类型，对象类型: {model_type_name}")
                
                # 尝试通过模型对象的属性判断类型
                if hasattr(base_model, 'get_booster'):
                    # XGBoost模型有get_booster方法
                    model_type = 'xgb_classifier'
                    self.logger.debug("通过get_booster方法识别为XGBoost模型")
                elif hasattr(base_model, 'params') and hasattr(base_model, 'predict'):
                    # 可能是LightGBM Booster对象
                    try:
                        import lightgbm as lgb
                        if isinstance(base_model, lgb.Booster):
                            model_type = 'lgb_classifier'
                            self.logger.debug("识别为LightGBM Booster对象")
                        else:
                            # 检查是否是LGBMClassifier
                            if 'lgbm' in model_type_name.lower() or 'lightgbm' in model_type_name.lower():
                                model_type = 'lgb_classifier'
                            else:
                                model_type = model_type_name.lower()
                    except ImportError:
                        self.logger.warning("无法导入lightgbm，尝试其他方式识别")
                        if 'lgbm' in model_type_name.lower() or 'lightgbm' in model_type_name.lower():
                            model_type = 'lgb_classifier'
                        else:
                            model_type = model_type_name.lower()
                else:
                    # 根据类型名称判断
                    if 'xgb' in model_type_name.lower() or 'xgboost' in model_type_name.lower():
                        model_type = 'xgb_classifier'
                    elif 'lgbm' in model_type_name.lower() or 'lightgbm' in model_type_name.lower() or 'lgb' in model_type_name.lower():
                        model_type = 'lgb_classifier'
                    else:
                        model_type = model_type_name.lower()
            else:
                model_type_name = model_type
            
            self.logger.info(f"识别模型类型: {model_type} (对象类型: {type(base_model).__name__})")
            
            if 'xgb' in model_type.lower():
                # XGBoost微调（warm start）
                import xgboost as xgb
                
                # 检查并移除object类型的列
                object_cols = X_finetune.select_dtypes(include=['object']).columns.tolist()
                if object_cols:
                    self.logger.warning(f"微调：发现object类型列，将被排除: {object_cols}")
                    X_finetune = X_finetune.drop(columns=object_cols).copy()
                
                # 获取原始参数
                original_params = base_model.get_params()
                original_lr = original_params.get('learning_rate', 0.1)
                
                # 创建新模型，使用降低的学习率
                fine_tuned_model = xgb.XGBClassifier(
                    **{k: v for k, v in original_params.items() if k != 'n_estimators'},
                    learning_rate=original_lr * learning_rate_multiplier,
                    n_estimators=n_estimators
                )
                
                # Warm start：使用基础模型的booster初始化
                fine_tuned_model.fit(
                    X_finetune, y_finetune,
                    xgb_model=base_model.get_booster()  # warm start
                )
                
                # 评估
                train_pred = fine_tuned_model.predict(X_finetune)
                train_pred_proba = fine_tuned_model.predict_proba(X_finetune)[:, 1]
                train_accuracy = np.mean(train_pred == y_finetune)
                
                metrics = {
                    'train_accuracy': float(train_accuracy),
                    'train_logloss': float(self._calculate_logloss(y_finetune, train_pred_proba))
                }
                
                self.logger.info(f"XGBoost模型微调完成：准确率 {train_accuracy:.4f}")
                
                return fine_tuned_model, metrics
                
            elif 'lgb' in model_type.lower():
                # LightGBM微调（继续训练）
                import lightgbm as lgb
                
                # 检查并移除object类型的列
                object_cols = X_finetune.select_dtypes(include=['object']).columns.tolist()
                if object_cols:
                    self.logger.warning(f"微调：发现object类型列，将被排除: {object_cols}")
                    X_finetune = X_finetune.drop(columns=object_cols).copy()
                
                # 获取原始参数
                original_params = base_model.params if hasattr(base_model, 'params') else {}
                
                # 创建微调数据集
                fine_tune_data = lgb.Dataset(X_finetune, label=y_finetune)
                
                # 继续训练（从基础模型继续）
                fine_tuned_model = lgb.train(
                    original_params,
                    fine_tune_data,
                    num_boost_round=n_estimators,
                    init_model=base_model,  # 从基础模型继续
                    callbacks=[lgb.log_evaluation(0)]
                )
                
                # 评估
                train_pred_proba = fine_tuned_model.predict(X_finetune)
                train_pred = (train_pred_proba > 0.5).astype(int)
                train_accuracy = np.mean(train_pred == y_finetune)
                
                metrics = {
                    'train_accuracy': float(train_accuracy),
                    'train_logloss': float(self._calculate_logloss(y_finetune, train_pred_proba))
                }
                
                self.logger.info(f"LightGBM模型微调完成：准确率 {train_accuracy:.4f}")
                
                return fine_tuned_model, metrics
            else:
                self.logger.warning(f"不支持的模型类型进行微调: {model_type}")
                return None, {}
                
        except Exception as e:
            self.logger.error(f"微调模型失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None, {}
    
    def save_model(self, model: object, model_path: str, 
                   feature_names: List[str],
                   feature_importance: Dict[str, float],
                   metrics: Dict,
                   config: Dict) -> bool:
        """
        保存模型
        
        Args:
            model: 训练好的模型
            model_path: 模型保存路径
            feature_names: 特征名称列表
            feature_importance: 特征重要性字典
            metrics: 训练指标
            config: 训练配置
        
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # 保存模型文件
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            # 保存特征列表
            feature_list_path = model_path.replace('.pkl', '_features.json')
            with open(feature_list_path, 'w', encoding='utf-8') as f:
                json.dump(feature_names, f, ensure_ascii=False, indent=2)
            
            # 保存特征重要性
            importance_path = model_path.replace('.pkl', '_importance.json')
            with open(importance_path, 'w', encoding='utf-8') as f:
                json.dump(feature_importance, f, ensure_ascii=False, indent=2)
            
            # 保存配置和指标
            config_path = model_path.replace('.pkl', '_config.json')
            config_data = {
                'metrics': metrics,
                'config': config,
                'feature_count': len(feature_names),
                'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"模型保存成功: {model_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存模型失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
