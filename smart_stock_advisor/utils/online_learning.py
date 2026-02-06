#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在线学习模块
实现增量权重更新和在线学习算法
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import numpy as np

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger
from utils.prediction_config_manager import PredictionConfigManager

logger = get_logger(__name__)


class OnlineLearning:
    """在线学习管理器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
        self.config_manager = PredictionConfigManager()
        
        # 在线学习配置
        self.config = {
            'learning_rate': 0.01,  # 学习率（权重更新步长）
            'min_update_threshold': 0.001,  # 最小更新阈值（避免微小更新）
            'max_update_factor': 0.1,  # 最大更新因子（单次更新不超过10%）
            'decay_factor': 0.99,  # 衰减因子（每次更新后衰减学习率）
            'min_samples': 10  # 最少样本数（少于此数不更新）
        }
    
    def update_weights_incremental(self, prediction_result: Dict, 
                                  actual_result: Dict) -> Optional[Dict]:
        """
        增量更新权重（每次预测后调用）
        
        Args:
            prediction_result: 预测结果（包含factor_weights等）
            actual_result: 实际结果（包含actual_price, actual_direction等）
            
        Returns:
            更新后的权重配置（如果更新成功），否则返回None
        """
        try:
            # 检查是否有足够的预测结果
            symbol = prediction_result.get('symbol')
            if not symbol:
                return None
            
            # 获取该股票的历史预测记录数
            sql = """
                SELECT COUNT(*) as cnt
                FROM stock_predictions
                WHERE symbol = %s
                  AND prediction_hit IS NOT NULL
            """
            result = self.db.execute_query(sql, (symbol,))
            sample_count = result[0].get('cnt', 0) if result else 0
            
            if sample_count < self.config['min_samples']:
                self.logger.debug(f"股票 {symbol} 样本数不足（{sample_count} < {self.config['min_samples']}），跳过增量更新")
                return None
            
            # 获取当前权重配置
            current_config = self.config_manager.get_config()
            if not current_config:
                return None
            
            current_weights = current_config.get('prediction', {})
            
            # 获取因子权重快照
            factor_weights = prediction_result.get('factor_weights', {})
            if not factor_weights:
                return None
            
            # 判断预测是否命中
            prediction_hit = actual_result.get('prediction_hit')
            if prediction_hit not in ['命中', '未命中']:
                return None
            
            is_hit = (prediction_hit == '命中')
            
            # 计算权重调整
            weight_adjustments = {}
            total_adjustment = 0.0
            
            # 获取各因子得分
            factors = prediction_result.get('factors', {})
            factor_scores = {}
            for factor_name in ['technical', 'news', 'capital_flow', 'market', 
                              'sector_rotation', 'history', 'valuation', 'us_sector']:
                factor_data = factors.get(factor_name, {})
                factor_scores[factor_name] = factor_data.get('score', 0.0)
            
            # 根据预测结果调整权重
            # 如果命中：增加与预测方向一致的因子的权重
            # 如果未命中：降低与预测方向一致的因子的权重
            prediction = prediction_result.get('prediction', '震荡')
            prediction_direction = 1 if prediction == '上涨' else (-1 if prediction == '下跌' else 0)
            
            for factor_name, factor_score in factor_scores.items():
                weight_key = f'{factor_name}_weight'
                current_weight = current_weights.get(weight_key, 0.1)
                
                # 判断因子方向是否与预测方向一致
                factor_direction = 1 if factor_score > 0 else (-1 if factor_score < 0 else 0)
                is_consistent = (factor_direction == prediction_direction) if prediction_direction != 0 else False
                
                # 计算调整量
                if is_hit and is_consistent:
                    # 命中且一致：增加权重
                    adjustment = self.config['learning_rate'] * abs(factor_score) * current_weight
                elif not is_hit and is_consistent:
                    # 未命中且一致：降低权重
                    adjustment = -self.config['learning_rate'] * abs(factor_score) * current_weight
                else:
                    # 其他情况：小幅调整
                    adjustment = 0
                
                # 限制调整幅度
                max_adjustment = current_weight * self.config['max_update_factor']
                adjustment = max(-max_adjustment, min(max_adjustment, adjustment))
                
                # 如果调整量太小，忽略
                if abs(adjustment) < self.config['min_update_threshold']:
                    adjustment = 0
                
                weight_adjustments[weight_key] = adjustment
                total_adjustment += abs(adjustment)
            
            # 如果总调整量太小，不更新
            if total_adjustment < self.config['min_update_threshold']:
                return None
            
            # 应用调整
            new_weights = {}
            for weight_key, current_weight in current_weights.items():
                if 'weight' in weight_key:
                    adjustment = weight_adjustments.get(weight_key, 0)
                    new_weight = max(0.01, min(0.5, current_weight + adjustment))  # 限制在0.01-0.5之间
                    new_weights[weight_key] = new_weight
            
            # 归一化权重（确保总和为1）
            total_weight = sum(new_weights.values())
            if total_weight > 0:
                for weight_key in new_weights:
                    new_weights[weight_key] = new_weights[weight_key] / total_weight
            
            # 更新配置
            updated_config = current_config.copy()
            updated_config['prediction'].update(new_weights)
            
            self.logger.info(f"增量更新权重完成（股票: {symbol}, 样本数: {sample_count}, 调整量: {total_adjustment:.4f}）")
            
            return updated_config
            
        except Exception as e:
            self.logger.error(f"增量更新权重失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def online_gradient_descent(self, prediction_results: List[Dict], 
                               actual_results: List[Dict],
                               learning_rate: Optional[float] = None) -> Dict:
        """
        在线梯度下降算法（批量更新）
        
        Args:
            prediction_results: 预测结果列表
            actual_results: 实际结果列表
            learning_rate: 学习率（如果为None则使用配置值）
            
        Returns:
            更新后的权重配置
        """
        try:
            if len(prediction_results) != len(actual_results):
                self.logger.warning("预测结果和实际结果数量不匹配")
                return {}
            
            if len(prediction_results) < self.config['min_samples']:
                self.logger.warning(f"样本数不足（{len(prediction_results)} < {self.config['min_samples']}）")
                return {}
            
            # 获取当前权重配置
            current_config = self.config_manager.get_config()
            if not current_config:
                return {}
            
            current_weights = current_config.get('prediction', {})
            lr = learning_rate if learning_rate is not None else self.config['learning_rate']
            
            # 计算梯度
            weight_gradients = {}
            for weight_key in current_weights:
                if 'weight' in weight_key:
                    weight_gradients[weight_key] = 0.0
            
            # 遍历所有样本，计算梯度
            for pred_result, actual_result in zip(prediction_results, actual_results):
                prediction_hit = actual_result.get('prediction_hit')
                if prediction_hit not in ['命中', '未命中']:
                    continue
                
                is_hit = (prediction_hit == '命中')
                factors = pred_result.get('factors', {})
                prediction = pred_result.get('prediction', '震荡')
                prediction_direction = 1 if prediction == '上涨' else (-1 if prediction == '下跌' else 0)
                
                # 计算每个权重的梯度
                for factor_name in ['technical', 'news', 'capital_flow', 'market', 
                                  'sector_rotation', 'history', 'valuation', 'us_sector']:
                    weight_key = f'{factor_name}_weight'
                    if weight_key not in weight_gradients:
                        continue
                    
                    factor_data = factors.get(factor_name, {})
                    factor_score = factor_data.get('score', 0.0)
                    factor_direction = 1 if factor_score > 0 else (-1 if factor_score < 0 else 0)
                    is_consistent = (factor_direction == prediction_direction) if prediction_direction != 0 else False
                    
                    # 计算梯度（损失函数的负梯度）
                    if is_hit and is_consistent:
                        gradient = -abs(factor_score)  # 命中且一致，减小损失（负梯度）
                    elif not is_hit and is_consistent:
                        gradient = abs(factor_score)  # 未命中且一致，增加损失（正梯度）
                    else:
                        gradient = 0
                    
                    weight_gradients[weight_key] += gradient
            
            # 归一化梯度
            for weight_key in weight_gradients:
                weight_gradients[weight_key] /= len(prediction_results)
            
            # 更新权重
            new_weights = {}
            for weight_key, current_weight in current_weights.items():
                if 'weight' in weight_key:
                    gradient = weight_gradients.get(weight_key, 0)
                    new_weight = max(0.01, min(0.5, current_weight - lr * gradient))
                    new_weights[weight_key] = new_weight
            
            # 归一化权重
            total_weight = sum(new_weights.values())
            if total_weight > 0:
                for weight_key in new_weights:
                    new_weights[weight_key] = new_weights[weight_key] / total_weight
            
            self.logger.info(f"在线梯度下降更新完成（样本数: {len(prediction_results)}, 学习率: {lr}）")
            
            return new_weights
            
        except Exception as e:
            self.logger.error(f"在线梯度下降失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {}
    
    def batch_update_weights(self, days: int = 7) -> Dict:
        """
        批量更新权重（定期调用，如每天）
        
        Args:
            days: 使用最近N天的数据
            
        Returns:
            更新结果
        """
        try:
            # 获取最近N天的预测结果和实际结果
            # 从prediction_factors表关联获取权重信息（因为factor_weights和factors字段可能不存在）
            sql = """
                SELECT 
                    sp.symbol, sp.prediction_date, sp.target_date,
                    sp.prediction, sp.up_probability, sp.down_probability, sp.confidence,
                    sp.actual_price, sp.actual_change_pct, sp.actual_direction, sp.prediction_hit,
                    -- 从prediction_factors表获取权重信息
                    pf.technical_weight, pf.news_weight, pf.capital_flow_weight,
                    pf.market_weight, pf.history_weight,
                    pf.technical_score, pf.news_score, pf.capital_flow_score,
                    pf.market_score, pf.history_score
                FROM stock_predictions sp
                LEFT JOIN prediction_factors pf 
                    ON sp.symbol = pf.symbol 
                    AND sp.target_date = pf.date
                WHERE sp.target_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                  AND sp.prediction_hit IS NOT NULL
                  AND pf.technical_weight IS NOT NULL
                ORDER BY sp.target_date DESC
            """
            results = self.db.execute_query(sql, (days,))
            
            if len(results) < self.config['min_samples']:
                return {
                    'success': False,
                    'message': f'样本数不足（{len(results)} < {self.config["min_samples"]}）'
                }
            
            # 准备数据
            prediction_results = []
            actual_results = []
            
            for record in results:
                # 从prediction_factors表构建factor_weights字典
                factor_weights = {}
                if record.get('technical_weight') is not None:
                    factor_weights['technical_weight'] = float(record.get('technical_weight', 0))
                if record.get('news_weight') is not None:
                    factor_weights['news_weight'] = float(record.get('news_weight', 0))
                if record.get('capital_flow_weight') is not None:
                    factor_weights['capital_flow_weight'] = float(record.get('capital_flow_weight', 0))
                if record.get('market_weight') is not None:
                    factor_weights['market_weight'] = float(record.get('market_weight', 0))
                if record.get('history_weight') is not None:
                    factor_weights['history_weight'] = float(record.get('history_weight', 0))
                
                # 如果factor_weights为空，跳过这条记录
                if not factor_weights:
                    continue
                
                # 从prediction_factors表构建factors字典（因为factors字段可能不存在）
                factors = {}
                if record.get('technical_score') is not None:
                    factors['technical'] = {'score': float(record.get('technical_score', 0))}
                if record.get('news_score') is not None:
                    factors['news'] = {'score': float(record.get('news_score', 0))}
                if record.get('capital_flow_score') is not None:
                    factors['capital_flow'] = {'score': float(record.get('capital_flow_score', 0))}
                if record.get('market_score') is not None:
                    factors['market'] = {'score': float(record.get('market_score', 0))}
                if record.get('history_score') is not None:
                    factors['history'] = {'score': float(record.get('history_score', 0))}
                
                prediction_result = {
                    'symbol': record.get('symbol'),
                    'prediction': record.get('prediction'),
                    'up_probability': float(record.get('up_probability', 0)),
                    'down_probability': float(record.get('down_probability', 0)),
                    'confidence': float(record.get('confidence', 0)),
                    'factor_weights': factor_weights,
                    'factors': factors
                }
                
                actual_result = {
                    'actual_price': float(record.get('actual_price', 0)) if record.get('actual_price') else None,
                    'actual_change_pct': float(record.get('actual_change_pct', 0)) if record.get('actual_change_pct') is not None else None,
                    'actual_direction': record.get('actual_direction'),
                    'prediction_hit': record.get('prediction_hit')
                }
                
                prediction_results.append(prediction_result)
                actual_results.append(actual_result)
            
            # 执行在线梯度下降
            new_weights = self.online_gradient_descent(prediction_results, actual_results)
            
            if not new_weights:
                return {
                    'success': False,
                    'message': '权重更新失败'
                }
            
            # 保存新权重（可选：可以设置一个阈值，只有改进超过阈值才保存）
            # 这里暂时不自动保存，需要用户确认
            
            return {
                'success': True,
                'new_weights': new_weights,
                'sample_count': len(prediction_results),
                'message': f'批量更新完成，生成了新的权重配置（样本数: {len(prediction_results)}）'
            }
            
        except Exception as e:
            self.logger.error(f"批量更新权重失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'批量更新失败: {str(e)}'
            }
