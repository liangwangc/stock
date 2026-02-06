#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自适应学习策略模块
实现自适应学习频率、触发式学习、动态学习范围等功能
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


class AdaptiveLearningStrategy:
    """自适应学习策略管理器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
    
    def calculate_market_volatility(self, days: int = 30) -> float:
        """
        计算市场波动率（用于自适应学习频率）
        
        Args:
            days: 计算天数
            
        Returns:
            波动率（0-1，越高表示波动越大）
        """
        try:
            # 获取大盘指数数据（使用上证指数）
            sql = """
                SELECT trade_date, close_price
                FROM stock_history_data
                WHERE symbol = '000001'
                  AND period_type = 'daily'
                  AND trade_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                ORDER BY trade_date ASC
            """
            data = self.db.execute_query(sql, (days,))
            
            if len(data) < 10:
                return 0.5  # 数据不足，返回中等波动率
            
            # 计算日收益率
            returns = []
            for i in range(1, len(data)):
                prev_price = float(data[i-1].get('close_price', 0))
                curr_price = float(data[i].get('close_price', 0))
                if prev_price > 0:
                    daily_return = abs((curr_price - prev_price) / prev_price)
                    returns.append(daily_return)
            
            if not returns:
                return 0.5
            
            # 计算波动率（标准差）
            import numpy as np
            volatility = np.std(returns)
            
            # 归一化到0-1范围（假设最大波动率为5%）
            normalized_volatility = min(volatility / 0.05, 1.0)
            
            return float(normalized_volatility)
            
        except Exception as e:
            self.logger.warning(f"计算市场波动率失败: {str(e)}")
            return 0.5  # 默认中等波动率
    
    def calculate_prediction_accuracy_trend(self, days: int = 30) -> Dict:
        """
        计算预测准确率趋势（用于触发式学习）
        
        Args:
            days: 计算天数
            
        Returns:
            {
                'current_accuracy': 当前准确率,
                'trend': '下降'/'上升'/'稳定',
                'should_trigger': 是否应该触发学习
            }
        """
        try:
            # 获取最近N天的预测准确率
            sql = """
                SELECT 
                    DATE(target_date) as date,
                    COUNT(*) as total,
                    SUM(CASE WHEN prediction_hit = '命中' THEN 1 ELSE 0 END) as hits
                FROM stock_predictions
                WHERE target_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                  AND prediction_hit IS NOT NULL
                GROUP BY DATE(target_date)
                ORDER BY date DESC
            """
            results = self.db.execute_query(sql, (days,))
            
            if len(results) < 7:  # 至少需要7天数据
                return {
                    'current_accuracy': 0.5,
                    'trend': '稳定',
                    'should_trigger': False
                }
            
            # 计算最近7天和之前7天的准确率
            recent_days = min(7, len(results))
            recent_hits = sum(r.get('hits', 0) for r in results[:recent_days])
            recent_total = sum(r.get('total', 0) for r in results[:recent_days])
            recent_accuracy = recent_hits / recent_total if recent_total > 0 else 0.5
            
            if len(results) >= 14:
                previous_hits = sum(r.get('hits', 0) for r in results[7:14])
                previous_total = sum(r.get('total', 0) for r in results[7:14])
                previous_accuracy = previous_hits / previous_total if previous_total > 0 else 0.5
            else:
                previous_accuracy = recent_accuracy
            
            # 判断趋势
            accuracy_diff = recent_accuracy - previous_accuracy
            if accuracy_diff < -0.05:  # 准确率下降超过5%
                trend = '下降'
                should_trigger = True
            elif accuracy_diff > 0.05:  # 准确率上升超过5%
                trend = '上升'
                should_trigger = False
            else:
                trend = '稳定'
                should_trigger = False
            
            return {
                'current_accuracy': recent_accuracy,
                'previous_accuracy': previous_accuracy,
                'trend': trend,
                'should_trigger': should_trigger,
                'accuracy_diff': accuracy_diff
            }
            
        except Exception as e:
            self.logger.warning(f"计算预测准确率趋势失败: {str(e)}")
            return {
                'current_accuracy': 0.5,
                'trend': '稳定',
                'should_trigger': False
            }
    
    def determine_learning_frequency(self, base_frequency_days: int = 7) -> Dict:
        """
        确定自适应学习频率
        
        Args:
            base_frequency_days: 基础学习频率（天数）
            
        Returns:
            {
                'frequency_days': 建议的学习频率（天数）,
                'reason': 原因说明,
                'volatility': 市场波动率
            }
        """
        try:
            volatility = self.calculate_market_volatility(days=30)
            
            # 根据波动率调整学习频率
            # 波动率越高，学习频率越高（天数越少）
            if volatility > 0.7:  # 高波动
                frequency_days = max(1, int(base_frequency_days * 0.5))  # 频率提高2倍
                reason = f"市场波动率高（{volatility:.1%}），建议提高学习频率"
            elif volatility > 0.4:  # 中等波动
                frequency_days = base_frequency_days
                reason = f"市场波动率中等（{volatility:.1%}），使用基础学习频率"
            else:  # 低波动
                frequency_days = int(base_frequency_days * 1.5)  # 频率降低
                reason = f"市场波动率低（{volatility:.1%}），可以降低学习频率"
            
            return {
                'frequency_days': frequency_days,
                'reason': reason,
                'volatility': volatility,
                'base_frequency_days': base_frequency_days
            }
            
        except Exception as e:
            self.logger.error(f"确定学习频率失败: {str(e)}")
            return {
                'frequency_days': base_frequency_days,
                'reason': '使用基础学习频率（计算失败）',
                'volatility': 0.5
            }
    
    def should_trigger_learning(self, min_accuracy_drop: float = 0.05) -> Dict:
        """
        判断是否应该触发学习（触发式学习）
        
        Args:
            min_accuracy_drop: 最小准确率下降阈值（默认5%）
            
        Returns:
            {
                'should_trigger': 是否应该触发,
                'reason': 原因,
                'accuracy_info': 准确率信息
            }
        """
        try:
            accuracy_info = self.calculate_prediction_accuracy_trend(days=30)
            
            should_trigger = accuracy_info.get('should_trigger', False)
            trend = accuracy_info.get('trend', '稳定')
            current_accuracy = accuracy_info.get('current_accuracy', 0.5)
            previous_accuracy = accuracy_info.get('previous_accuracy', 0.5)
            accuracy_diff = accuracy_info.get('accuracy_diff', 0)
            
            if should_trigger:
                reason = f"预测准确率下降（从{previous_accuracy:.1%}降至{current_accuracy:.1%}，下降{abs(accuracy_diff):.1%}）"
            else:
                reason = f"预测准确率{trend}（当前{current_accuracy:.1%}）"
            
            return {
                'should_trigger': should_trigger,
                'reason': reason,
                'accuracy_info': accuracy_info
            }
            
        except Exception as e:
            self.logger.error(f"判断是否触发学习失败: {str(e)}")
            return {
                'should_trigger': False,
                'reason': '判断失败',
                'accuracy_info': {}
            }
    
    def determine_learning_range(self, market_state: Optional[str] = None) -> Dict:
        """
        确定动态学习范围（根据市场状态）
        
        Args:
            market_state: 市场状态（bull_market/bear_market/sideways），如果为None则自动识别
            
        Returns:
            {
                'days': 建议的学习天数,
                'reason': 原因说明,
                'market_state': 市场状态
            }
        """
        try:
            # 如果没有提供市场状态，尝试识别
            if not market_state:
                try:
                    from utils.market_state_identifier import MarketStateIdentifier
                    identifier = MarketStateIdentifier()
                    # 获取大盘指数数据
                    from data_source.stock_data_source import StockDataSource
                    data_source = StockDataSource()
                    indices_data = data_source.get_all_market_indices(days=30)
                    if '000001.SH' in indices_data and not indices_data['000001.SH'].empty:
                        market_state_result = identifier.identify_market_state(indices_data['000001.SH'], '上证指数')
                        market_state = market_state_result.get('state', 'sideways')
                except Exception as e:
                    self.logger.debug(f"识别市场状态失败: {str(e)}")
                    market_state = 'sideways'
            
            # 根据市场状态确定学习范围
            if market_state == 'bull_market':
                days = 90  # 牛市使用较长历史
                reason = "牛市状态，使用较长历史数据（90天）进行学习"
            elif market_state == 'bear_market':
                days = 90  # 熊市也使用较长历史
                reason = "熊市状态，使用较长历史数据（90天）进行学习"
            else:  # sideways
                days = 30  # 震荡市使用较短历史
                reason = "震荡市状态，使用较短历史数据（30天）进行学习"
            
            return {
                'days': days,
                'reason': reason,
                'market_state': market_state
            }
            
        except Exception as e:
            self.logger.error(f"确定学习范围失败: {str(e)}")
            return {
                'days': 30,
                'reason': '使用默认学习范围（30天）',
                'market_state': 'unknown'
            }
    
    def calculate_weighted_learning_range(self, base_days: int = 30, 
                                          decay_factor: float = 0.95) -> Dict:
        """
        计算加权学习范围（近期数据权重更高）
        
        Args:
            base_days: 基础天数
            decay_factor: 衰减因子（每往前一天，权重乘以decay_factor）
            
        Returns:
            {
                'days': 学习天数,
                'weights': 每日权重列表（从最新到最旧）,
                'total_weight': 总权重
            }
        """
        try:
            weights = []
            total_weight = 0.0
            
            for i in range(base_days):
                weight = decay_factor ** i  # 指数衰减
                weights.append(weight)
                total_weight += weight
            
            return {
                'days': base_days,
                'weights': weights,
                'total_weight': total_weight,
                'decay_factor': decay_factor
            }
            
        except Exception as e:
            self.logger.error(f"计算加权学习范围失败: {str(e)}")
            return {
                'days': base_days,
                'weights': [1.0] * base_days,
                'total_weight': float(base_days)
            }
    
    def check_market_state_change(self, days: int = 7) -> Dict:
        """
        检查市场状态是否发生变化（用于触发式学习）
        
        Args:
            days: 检查天数
            
        Returns:
            {
                'has_changed': 是否发生变化,
                'current_state': 当前状态,
                'previous_state': 之前状态,
                'should_trigger': 是否应该触发学习
            }
        """
        try:
            # 获取最近N天的市场状态（从stock_predictions表）
            sql = """
                SELECT DISTINCT market_state, DATE(prediction_date) as date
                FROM stock_predictions
                WHERE prediction_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                  AND market_state IS NOT NULL
                ORDER BY date DESC
                LIMIT 10
            """
            results = self.db.execute_query(sql, (days,))
            
            if len(results) < 2:
                return {
                    'has_changed': False,
                    'current_state': None,
                    'previous_state': None,
                    'should_trigger': False
                }
            
            # 获取最近的状态
            current_state = results[0].get('market_state')
            
            # 获取之前的状态（跳过相同状态）
            previous_state = None
            for r in results[1:]:
                if r.get('market_state') != current_state:
                    previous_state = r.get('market_state')
                    break
            
            has_changed = previous_state is not None and previous_state != current_state
            should_trigger = has_changed
            
            return {
                'has_changed': has_changed,
                'current_state': current_state,
                'previous_state': previous_state,
                'should_trigger': should_trigger
            }
            
        except Exception as e:
            self.logger.warning(f"检查市场状态变化失败: {str(e)}")
            return {
                'has_changed': False,
                'current_state': None,
                'previous_state': None,
                'should_trigger': False
            }
