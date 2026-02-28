"""
ML模型预测集成模块
将训练好的ML模型集成到股票预测流程中
"""
import os
import sys
import pickle
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.ml_model_manager import MLModelManager
from utils.ml_feature_engineering import MLFeatureEngineering
from utils.ml_data_loader import MLDataLoader

logger = get_logger(__name__)

# 因子筛选结果路径（与 optimize_factor_quality.py / train_ml_models.py 一致）
SELECTED_FEATURES_PATH = os.path.join(project_root, 'models', 'selected_features.pkl')
# 涨跌幅回归模型路径（与 train_base_model lgb_regressor_return 保存路径一致）
LGB_REGESSOR_RETURN_PATH = os.path.join(project_root, 'models', 'lgb_regressor_return.pkl')


class MLPredictorIntegration:
    """ML模型预测集成类"""
    
    def __init__(self):
        self.model_manager = MLModelManager()
        self.feature_engineering = MLFeatureEngineering()
        self.data_loader = MLDataLoader()
        self.logger = logger
        self._active_models = {}  # 缓存激活的模型
        self._selected_features_cache: Optional[List[str]] = None  # 缓存筛选因子列表
    
    def _get_model_feature_names(self, model: object) -> Optional[List[str]]:
        """
        从已加载的模型对象获取特征名（与 XGBoost/LightGBM 内部校验一致，避免 feature_names mismatch）。
        """
        if model is None:
            return None
        try:
            if hasattr(model, 'get_booster'):
                names = model.get_booster().feature_names
                return list(names) if names is not None else None
            if hasattr(model, 'feature_name_'):
                return list(model.feature_name_) if model.feature_name_ else None
            if hasattr(model, 'booster_') and hasattr(model.booster_, 'feature_name'):
                fn = model.booster_.feature_name()
                return list(fn) if fn else None
            return None
        except Exception as e:
            self.logger.debug(f"从模型获取特征名失败: {e}")
            return None
    
    def _get_feature_list_for_prediction(self, model_type: str = 'classifier') -> Optional[List[str]]:
        """
        获取预测时使用的特征列表。优先使用 selected_features.pkl，保证与训练一致。
        """
        if os.path.isfile(SELECTED_FEATURES_PATH):
            try:
                if self._selected_features_cache is None:
                    with open(SELECTED_FEATURES_PATH, 'rb') as f:
                        self._selected_features_cache = pickle.load(f)
                if self._selected_features_cache:
                    return self._selected_features_cache
            except Exception as e:
                self.logger.debug(f"加载 selected_features.pkl 失败: {e}")
        model_info = None
        if model_type == 'classifier':
            model_info = self.model_manager.get_model_info('xgb_classifier') or \
                        self.model_manager.get_model_info('lgb_classifier')
        else:
            model_info = self.model_manager.get_model_info('xgb_regressor') or \
                        self.model_manager.get_model_info('lgb_regressor')
        if model_info and model_info.get('feature_list'):
            return model_info['feature_list']
        return None

    def _normalize_breakout_feature(self, value: Optional[float],
                                    vmin: float,
                                    vmax: float,
                                    default: float = 0.5) -> float:
        """
        将特征值压缩到 [0, 1] 区间，用于 ML 爆发评分。
        """
        try:
            v = float(value)
        except (TypeError, ValueError):
            return default
        if np.isnan(v):
            return default
        if v < vmin:
            v = vmin
        elif v > vmax:
            v = vmax
        if vmax <= vmin:
            return default
        return float((v - vmin) / (vmax - vmin))

    def _calculate_ml_breakout_score(self,
                                     features_row: pd.Series,
                                     ml_predicted_return: float,
                                     ml_up_probability: float) -> float:
        """
        计算 ML 爆发评分（0-1），用于识别涨停启动/主升浪/高爆发潜力。
        """
        try:
            # 回归涨跌幅：假设主要落在 [-20%, 20%] 小数区间
            ret_norm = self._normalize_breakout_feature(ml_predicted_return, -0.20, 0.20)
            # 概率：天然在 [0, 1]
            prob_norm = self._normalize_breakout_feature(ml_up_probability, 0.0, 1.0)

            # 成交量放大：volume_ratio_5d，常见范围 [0.5, 5]
            vol_ratio_5d = features_row.get('volume_ratio_5d', np.nan)
            vol_norm = self._normalize_breakout_feature(vol_ratio_5d, 0.5, 5.0)

            # 短期均线斜率：ma5_slope，典型区间 [-10%, 10%]
            ma5_slope = features_row.get('ma5_slope', np.nan)
            ma_norm = self._normalize_breakout_feature(ma5_slope, -0.10, 0.10)

            # 短周期加速度：acceleration_3d，典型区间 [-10%, 10%]
            accel_3d = features_row.get('acceleration_3d', np.nan)
            accel_norm = self._normalize_breakout_feature(accel_3d, -0.10, 0.10)

            breakout_score = (
                0.35 * ret_norm +
                0.25 * prob_norm +
                0.15 * vol_norm +
                0.15 * ma_norm +
                0.10 * accel_norm
            )
            breakout_score = max(0.0, min(1.0, float(breakout_score)))
            return breakout_score
        except Exception as e:
            self.logger.debug(f\"计算 ML 爆发评分失败: {e}\")
            return 0.0
    
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
            
            result = None
            if classifier_model:
                result = self._predict_with_classifier(symbol, stock_data, classifier_model)
            if result is None or not result.get('available'):
                regressor_model = self._load_active_model('xgb_regressor')
                if not regressor_model:
                    regressor_model = self._load_active_model('lgb_regressor')
                if regressor_model:
                    result = self._predict_with_regressor(symbol, stock_data, regressor_model)
            if result is None or not result.get('available'):
                self.logger.debug("未找到激活的ML模型，跳过ML预测")
                return {
                    'available': False,
                    'ml_score': 0.0,
                    'ml_up_probability': 0.5,
                    'ml_prediction': '震荡',
                    'ml_confidence': 0.0,
                    'model_type': None
                }
            # 涨幅预测增强：若存在涨跌幅回归模型，预测 future_return 并写入结果
            result = self._add_regressor_return_prediction(symbol, stock_data, result)
            return result

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
    
    def _add_regressor_return_prediction(self, symbol: str, stock_data: pd.DataFrame, result: Dict) -> Dict:
        """若存在涨跌幅回归模型，预测 future_return（小数）并写入 result['ml_predicted_return']。"""
        if not os.path.isfile(LGB_REGESSOR_RETURN_PATH):
            return result
        try:
            with open(LGB_REGESSOR_RETURN_PATH, 'rb') as f:
                reg_model = pickle.load(f)
            features_df = self._prepare_features_for_prediction(symbol, stock_data)
            if features_df.empty:
                return result
            # 保留原始特征行用于爆发评分计算
            features_row = features_df.iloc[-1].copy()
            feature_list = self._get_model_feature_names(reg_model) or self._get_feature_list_for_prediction(model_type='classifier')
            if feature_list:
                missing = set(feature_list) - set(features_df.columns)
                for feat in missing:
                    features_df[feat] = 0.0
                features_df = features_df[feature_list]
            object_cols = features_df.select_dtypes(include=['object']).columns.tolist()
            if object_cols:
                features_df = features_df.drop(columns=object_cols).copy()
            pred = reg_model.predict(features_df)
            base_return = float(pred[0])
            result['ml_predicted_return'] = base_return

            # 计算 ML 爆发评分并写入结果（用于后续涨幅增强）
            try:
                ml_up_prob = result.get('ml_up_probability', 0.5)
                breakout_score = self._calculate_ml_breakout_score(
                    features_row, base_return, ml_up_prob
                )
                result['ml_breakout_score'] = breakout_score
            except Exception as e:
                self.logger.debug(f\"ML 爆发评分计算失败（不影响主流程）: {e}\")
        except Exception as e:
            self.logger.debug(f"涨跌幅回归模型预测未使用: {e}")
        return result

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
            
            # 2. 获取特征列表（优先用模型内部 feature_names，与 XGBoost/LightGBM 校验一致）
            feature_list = self._get_model_feature_names(model) or self._get_feature_list_for_prediction(model_type='classifier')
            if feature_list:
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
            
            # 2. 获取特征列表（优先用模型内部 feature_names）
            feature_list = self._get_model_feature_names(model) or self._get_feature_list_for_prediction(model_type='regressor')
            if feature_list:
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
        """
        为预测准备特征，与训练管线一致：先构建多行样本（每行=截止某日的截面特征），
        再经 prepare_features（含 _add_enhanced_factors）得到与训练相同的特征列与顺序。
        """
        try:
            # 构建历史记录格式（与 DataLoader 一致）
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
            
            min_required = 30
            if len(history_records) < min_required:
                self.logger.warning(f"历史数据不足（{len(history_records)}条，需要至少{min_required}条），无法提取特征")
                return pd.DataFrame()
            
            # 与训练一致：按“截止日”构建多行样本，再走 prepare_features（含增强因子）
            # 从第 min_required 条开始，每条对应一行“截止该日的特征”
            use_records = history_records[-60:] if len(history_records) >= 60 else history_records
            start_i = max(0, len(use_records) - 1 - max(0, 60 - 1))  # 最多 60 行，从 start_i 到末尾
            start_i = max(start_i, 19)  # _extract_features_from_history 至少 20 条
            if start_i >= len(use_records):
                return pd.DataFrame()
            
            all_rows = []
            for i in range(start_i, len(use_records)):
                chunk = use_records[: i + 1]
                features = self.data_loader._extract_features_from_history(chunk)
                if not features:
                    continue
                row_dict = dict(features)
                row_dict['symbol'] = symbol
                row_dict['target_date'] = use_records[i].get('trade_date')
                all_rows.append(row_dict)
            
            if not all_rows:
                return pd.DataFrame()
            
            df_samples = pd.DataFrame(all_rows)
            df_samples['label_up'] = 0  # 预测时无标签，占位即可
            X, _y, _names = self.feature_engineering.prepare_features(
                df_samples, label_column='label_up', filter_by_completeness=False
            )
            if X.empty:
                return pd.DataFrame()
            # 取最后一行作为当前截面特征（与训练时“最新一日”一致）
            return X.iloc[[-1]].copy()
            
        except Exception as e:
            self.logger.error(f"准备特征失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def clear_cache(self):
        """清除模型缓存"""
        self._active_models.clear()
        self.model_manager._model_cache.clear()
