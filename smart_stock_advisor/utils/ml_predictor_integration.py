"""
ML模型预测集成模块
将训练好的ML模型集成到股票预测流程中
"""
import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.ml_model_manager import MLModelManager
from utils.ml_feature_engineering import MLFeatureEngineering
from utils.ml_data_loader import MLDataLoader

logger = get_logger(__name__)


class MLPredictorIntegration:
    """ML模型预测集成类"""
    
    def __init__(self):
        self.model_manager = MLModelManager()
        self.feature_engineering = MLFeatureEngineering()
        self.data_loader = MLDataLoader()
        self.logger = logger
        self._active_models = {}  # 缓存激活的模型
    
    def get_ml_prediction(self, symbol: str, stock_data: pd.DataFrame) -> Dict:
        """
        使用ML模型进行预测
        
        Args:
            symbol: 股票代码
            stock_data: 股票历史数据（DataFrame，包含close, volume等字段）
        
        Returns:
            预测结果字典，包含：
            - ml_score: ML模型得分
            - ml_up_probability: ML模型预测的上涨概率
            - ml_prediction: ML模型预测方向
            - ml_confidence: ML模型置信度
            - model_type: 使用的模型类型
            - available: 是否成功获取预测
        """
        try:
            # 1. 尝试加载激活的分类器模型（优先使用）
            classifier_model = self._load_active_model('xgb_classifier')
            if not classifier_model:
                classifier_model = self._load_active_model('lgb_classifier')
            
            if classifier_model:
                return self._predict_with_classifier(symbol, stock_data, classifier_model)
            
            # 2. 如果没有分类器，尝试回归模型
            regressor_model = self._load_active_model('xgb_regressor')
            if not regressor_model:
                regressor_model = self._load_active_model('lgb_regressor')
            
            if regressor_model:
                return self._predict_with_regressor(symbol, stock_data, regressor_model)
            
            # 3. 没有可用的模型
            self.logger.debug(f"未找到激活的ML模型，跳过ML预测")
            return {
                'available': False,
                'ml_score': 0.0,
                'ml_up_probability': 0.5,
                'ml_prediction': '震荡',
                'ml_confidence': 0.0,
                'model_type': None
            }
            
        except Exception as e:
            self.logger.error(f"ML模型预测失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'available': False,
                'ml_score': 0.0,
                'ml_up_probability': 0.5,
                'ml_prediction': '震荡',
                'ml_confidence': 0.0,
                'model_type': None,
                'error': str(e)
            }
    
    def _load_active_model(self, model_type: str) -> Optional[object]:
        """加载激活的模型"""
        try:
            if model_type in self._active_models:
                return self._active_models[model_type]
            
            model = self.model_manager.load_model(model_type, use_cache=True)
            if model:
                self._active_models[model_type] = model
            return model
        except Exception as e:
            self.logger.debug(f"加载模型失败 {model_type}: {str(e)}")
            return None
    
    def _get_active_model_id(self, model_type: str) -> Optional[int]:
        """获取激活的模型ID"""
        try:
            model_info = self.model_manager.get_model_info(model_type)
            if model_info and 'id' in model_info:
                return model_info['id']
        except Exception as e:
            self.logger.debug(f"获取模型ID失败 {model_type}: {str(e)}")
        return None
    
    def _predict_with_classifier(self, symbol: str, stock_data: pd.DataFrame, model: object) -> Dict:
        """使用分类器模型进行预测"""
        try:
            # 1. 准备特征
            features_df = self._prepare_features_for_prediction(symbol, stock_data)
            
            if features_df.empty:
                return {
                    'available': False,
                    'ml_score': 0.0,
                    'ml_up_probability': 0.5,
                    'ml_prediction': '震荡',
                    'ml_confidence': 0.0,
                    'model_type': None
                }
            
            # 2. 获取模型信息以确定特征顺序
            model_info = self.model_manager.get_model_info('xgb_classifier') or \
                        self.model_manager.get_model_info('lgb_classifier')
            
            if model_info and model_info.get('feature_list'):
                feature_list = model_info['feature_list']
                # 确保特征顺序与训练时一致
                missing_features = set(feature_list) - set(features_df.columns)
                if missing_features:
                    for feat in missing_features:
                        features_df[feat] = 0.0
                features_df = features_df[feature_list]
            
            # 3. 检查并移除object类型列（模型不支持）
            object_cols = features_df.select_dtypes(include=['object']).columns.tolist()
            if object_cols:
                self.logger.warning(f"ML预测：发现object类型列，将被排除: {object_cols}")
                features_df = features_df.drop(columns=object_cols).copy()
            
            # 4. 预测
            if hasattr(model, 'predict_proba'):
                # XGBoost/LightGBM分类器
                proba = model.predict_proba(features_df)
                if proba.shape[1] == 2:
                    up_probability = float(proba[0][1])  # 上涨概率
                else:
                    up_probability = float(proba[0][0])
            else:
                # 其他类型的模型
                pred = model.predict(features_df)
                up_probability = float(pred[0]) if isinstance(pred[0], (int, float)) else 0.5
            
            # 4. 计算得分和方向
            ml_score = (up_probability - 0.5) * 2  # 转换为-1到1的得分
            
            if up_probability > 0.6:
                ml_prediction = '上涨'
            elif up_probability < 0.4:
                ml_prediction = '下跌'
            else:
                ml_prediction = '震荡'
            
            # 5. 计算置信度（基于概率的确定性）
            ml_confidence = abs(up_probability - 0.5) * 2  # 0到1之间
            
            # 6. 确定模型类型
            model_type = 'xgb_classifier' if 'xgb' in str(type(model)).lower() else 'lgb_classifier'
            
            # 7. 获取模型ID
            model_id = self._get_active_model_id(model_type)
            
            return {
                'available': True,
                'ml_score': ml_score,
                'ml_up_probability': up_probability,
                'ml_down_probability': 1.0 - up_probability,
                'ml_prediction': ml_prediction,
                'ml_confidence': ml_confidence,
                'model_type': model_type,
                'model_id': model_id
            }
            
        except Exception as e:
            self.logger.error(f"分类器预测失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'available': False,
                'ml_score': 0.0,
                'ml_up_probability': 0.5,
                'ml_prediction': '震荡',
                'ml_confidence': 0.0,
                'model_type': None,
                'error': str(e)
            }
    
    def _predict_with_regressor(self, symbol: str, stock_data: pd.DataFrame, model: object) -> Dict:
        """使用回归模型进行预测"""
        try:
            # 1. 准备特征
            features_df = self._prepare_features_for_prediction(symbol, stock_data)
            
            if features_df.empty:
                return {
                    'available': False,
                    'ml_score': 0.0,
                    'ml_up_probability': 0.5,
                    'ml_prediction': '震荡',
                    'ml_confidence': 0.0,
                    'model_type': None
                }
            
            # 2. 获取模型信息
            model_info = self.model_manager.get_model_info('xgb_regressor') or \
                        self.model_manager.get_model_info('lgb_regressor')
            
            if model_info and model_info.get('feature_list'):
                feature_list = model_info['feature_list']
                missing_features = set(feature_list) - set(features_df.columns)
                if missing_features:
                    for feat in missing_features:
                        features_df[feat] = 0.0
                features_df = features_df[feature_list]
            
            # 3. 检查并移除object类型列（模型不支持）
            object_cols = features_df.select_dtypes(include=['object']).columns.tolist()
            if object_cols:
                self.logger.warning(f"ML回归预测：发现object类型列，将被排除: {object_cols}")
                features_df = features_df.drop(columns=object_cols).copy()
            
            # 4. 预测涨跌幅
            predicted_change_pct = model.predict(features_df)[0]
            
            # 4. 转换为概率
            # 假设涨跌幅在-10%到10%之间，转换为0-1的概率
            up_probability = 0.5 + (predicted_change_pct / 20.0)  # 归一化
            up_probability = max(0.0, min(1.0, up_probability))  # 限制在0-1之间
            
            # 5. 计算得分和方向
            ml_score = predicted_change_pct / 10.0  # 归一化到-1到1
            
            if predicted_change_pct > 0.5:
                ml_prediction = '上涨'
            elif predicted_change_pct < -0.5:
                ml_prediction = '下跌'
            else:
                ml_prediction = '震荡'
            
            # 6. 计算置信度
            ml_confidence = min(abs(predicted_change_pct) / 5.0, 1.0)  # 基于预测幅度
            
            # 7. 确定模型类型
            model_type = 'xgb_regressor' if 'xgb' in str(type(model)).lower() else 'lgb_regressor'
            
            # 8. 获取模型ID
            model_id = self._get_active_model_id(model_type)
            
            return {
                'available': True,
                'ml_score': ml_score,
                'ml_up_probability': up_probability,
                'ml_down_probability': 1.0 - up_probability,
                'ml_prediction': ml_prediction,
                'ml_confidence': ml_confidence,
                'model_type': model_type,
                'model_id': model_id,
                'predicted_change_pct': predicted_change_pct
            }
            
        except Exception as e:
            self.logger.error(f"回归器预测失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'available': False,
                'ml_score': 0.0,
                'ml_up_probability': 0.5,
                'ml_prediction': '震荡',
                'ml_confidence': 0.0,
                'model_type': None,
                'error': str(e)
            }
    
    def _prepare_features_for_prediction(self, symbol: str, stock_data: pd.DataFrame) -> pd.DataFrame:
        """为预测准备特征"""
        try:
            # 转换为DataLoader需要的格式
            # stock_data应该包含：date, close, open, high, low, volume等字段
            
            # 构建历史记录格式（用于特征提取）
            history_records = []
            for idx, row in stock_data.iterrows():
                record = {
                    'symbol': symbol,
                    'trade_date': row.get('date', idx),
                    'close_price': float(row.get('close', 0)),
                    'open_price': float(row.get('open', row.get('close', 0))),
                    'high_price': float(row.get('high', row.get('close', 0))),
                    'low_price': float(row.get('low', row.get('close', 0))),
                    'volume': float(row.get('volume', 0)),
                    'amount': float(row.get('amount', 0)) if 'amount' in row else 0.0,
                    'change_pct': float(row.get('change_pct', 0)) if 'change_pct' in row else 0.0,
                    'pre_close': float(row.get('pre_close', row.get('close', 0))) if 'pre_close' in row else float(row.get('close', 0))
                }
                history_records.append(record)
            
            # 降低最小数据量要求：从60条降低到30条，以支持数据量较少的股票
            # 特征提取方法实际只需要至少20条数据，设置30条作为安全阈值
            min_required = 30
            if len(history_records) < min_required:
                self.logger.warning(f"历史数据不足（{len(history_records)}条，需要至少{min_required}条），无法提取特征")
                return pd.DataFrame()
            
            # 提取特征：如果数据量>=60条，使用最后60条；如果数据量<60但>=30，使用所有数据
            # 这样可以充分利用可用数据，同时保持特征提取的一致性
            if len(history_records) >= 60:
                features = self.data_loader._extract_features_from_history(history_records[-60:])
            else:
                # 数据量在30-59条之间，使用所有可用数据
                self.logger.debug(f"数据量较少（{len(history_records)}条），使用所有可用数据提取特征")
                features = self.data_loader._extract_features_from_history(history_records)
            
            if not features:
                return pd.DataFrame()
            
            # 转换为DataFrame
            features_df = pd.DataFrame([features])
            
            return features_df
            
        except Exception as e:
            self.logger.error(f"准备特征失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def clear_cache(self):
        """清除模型缓存"""
        self._active_models.clear()
        self.model_manager._model_cache.clear()
