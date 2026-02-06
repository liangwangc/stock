#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自适应学习集成模块
将自适应学习策略、在线学习和增强评估整合到定时任务系统中
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger
from utils.adaptive_learning_strategy import AdaptiveLearningStrategy
from utils.online_learning import OnlineLearning
from utils.model_performance_evaluator import ModelPerformanceEvaluator
from utils.model_optimizer import ModelOptimizer
from utils.prediction_config_manager import PredictionConfigManager

logger = get_logger(__name__)


class AdaptiveLearningIntegration:
    """自适应学习集成管理器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
        self.adaptive_strategy = AdaptiveLearningStrategy()
        self.online_learning = OnlineLearning()
        self.evaluator = ModelPerformanceEvaluator()
        self.optimizer = ModelOptimizer()
        self.config_manager = PredictionConfigManager()
    
    def check_and_trigger_learning(self) -> Dict:
        """
        检查是否应该触发学习（触发式学习）
        
        Returns:
            检查结果和建议
        """
        try:
            # 1. 检查预测准确率趋势
            accuracy_check = self.adaptive_strategy.should_trigger_learning()
            
            # 2. 检查市场状态变化
            market_state_check = self.adaptive_strategy.check_market_state_change(days=7)
            
            # 3. 综合判断
            should_trigger = (
                accuracy_check.get('should_trigger', False) or
                market_state_check.get('should_trigger', False)
            )
            
            reasons = []
            if accuracy_check.get('should_trigger'):
                reasons.append(accuracy_check.get('reason', ''))
            if market_state_check.get('should_trigger'):
                reasons.append(f"市场状态变化（从{market_state_check.get('previous_state')}变为{market_state_check.get('current_state')}）")
            
            return {
                'should_trigger': should_trigger,
                'reasons': reasons,
                'accuracy_info': accuracy_check.get('accuracy_info', {}),
                'market_state_info': market_state_check
            }
            
        except Exception as e:
            self.logger.error(f"检查触发学习失败: {str(e)}")
            return {
                'should_trigger': False,
                'reasons': [],
                'error': str(e)
            }
    
    def execute_adaptive_optimization(self, base_frequency_days: int = 7) -> Dict:
        """
        执行自适应优化（根据市场状态和学习策略自动调整参数）
        
        Args:
            base_frequency_days: 基础学习频率（天数）
            
        Returns:
            优化结果
        """
        try:
            # 1. 确定学习频率
            frequency_info = self.adaptive_strategy.determine_learning_frequency(base_frequency_days)
            
            # 2. 确定学习范围
            learning_range_info = self.adaptive_strategy.determine_learning_range()
            
            # 3. 执行优化
            days = learning_range_info.get('days', 30)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            self.logger.info(f"开始自适应优化（学习范围: {days}天, 频率: {frequency_info.get('frequency_days')}天）")
            
            # 使用网格搜索或贝叶斯优化
            optimization_config = {
                'use_cross_validation': True,
                'train_ratio': 0.8,
                'auto_apply_threshold': 0.05  # 5%改进自动应用
            }
            
            result = self.optimizer.optimize_weights_grid_search(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                optimization_config=optimization_config
            )
            
            return {
                'success': result.get('success', False),
                'optimization_result': result,
                'learning_range': learning_range_info,
                'frequency_info': frequency_info,
                'message': f"自适应优化完成（范围: {days}天）"
            }
            
        except Exception as e:
            self.logger.error(f"执行自适应优化失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'自适应优化失败: {str(e)}'
            }
    
    def execute_comprehensive_evaluation(self, days: int = 30) -> Dict:
        """
        执行综合评估（多指标、分市场状态、置信度校准）
        
        Args:
            days: 评估天数
            
        Returns:
            综合评估结果
        """
        try:
            # 1. 多指标综合评估
            comprehensive_result = self.evaluator.evaluate_comprehensive_performance(days=days)
            
            # 2. 分市场状态评估
            market_state_result = self.evaluator.evaluate_by_market_state(days=days)
            
            # 3. 置信度校准评估
            calibration_result = self.evaluator.evaluate_confidence_calibration(days=days)
            
            return {
                'success': True,
                'evaluation_date': datetime.now().date().strftime('%Y-%m-%d'),
                'comprehensive_evaluation': comprehensive_result,
                'market_state_evaluation': market_state_result,
                'confidence_calibration': calibration_result
            }
            
        except Exception as e:
            self.logger.error(f"执行综合评估失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'综合评估失败: {str(e)}'
            }
    
    def execute_online_learning_batch(self, days: int = 7) -> Dict:
        """
        执行批量在线学习（定期调用）
        
        Args:
            days: 使用最近N天的数据
            
        Returns:
            在线学习结果
        """
        try:
            result = self.online_learning.batch_update_weights(days=days)
            
            if result.get('success') and result.get('new_weights'):
                # 可选：自动应用新权重（需要用户确认）
                # 这里暂时不自动应用，返回新权重供用户确认
                self.logger.info(f"在线学习完成，生成了新权重配置（样本数: {result.get('sample_count', 0)}）")
            
            return result
            
        except Exception as e:
            self.logger.error(f"执行在线学习失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'在线学习失败: {str(e)}'
            }
    
    def get_learning_recommendations(self) -> Dict:
        """
        获取学习建议（综合各种策略）
        
        Returns:
            学习建议
        """
        try:
            recommendations = {
                'frequency': self.adaptive_strategy.determine_learning_frequency(),
                'range': self.adaptive_strategy.determine_learning_range(),
                'trigger_check': self.check_and_trigger_learning(),
                'market_volatility': self.adaptive_strategy.calculate_market_volatility(),
                'accuracy_trend': self.adaptive_strategy.calculate_prediction_accuracy_trend()
            }
            
            return {
                'success': True,
                'recommendations': recommendations,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            self.logger.error(f"获取学习建议失败: {str(e)}")
            return {
                'success': False,
                'message': f'获取学习建议失败: {str(e)}'
            }
