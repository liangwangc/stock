"""
权重优化模块
实现基于历史准确率的自动权重优化、根据市场状态和个股特性调整权重策略
"""
import os
import sys
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)


class WeightOptimizer:
    """权重优化器"""
    
    def __init__(self):
        self.logger = logger
        self.db = DBConnection()
        self.use_database = USE_DATABASE
    
    def optimize_weights_by_accuracy(self, days: int = 30, min_samples: int = 50) -> Dict:
        """
        基于历史准确率自动优化权重
        
        Args:
            days: 评估时间范围（天数）
            min_samples: 最小样本数
        
        Returns:
            优化后的权重配置和建议
        """
        if not self.use_database:
            return {
                'success': False,
                'message': '数据库未启用，无法进行权重优化'
            }
        
        try:
            # 获取历史预测数据
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 修改SQL：从stock_predictions表查询，通过JOIN关联prediction_factors表获取因子数据
            # 使用symbol + prediction_date来关联（prediction_factors表的date字段对应prediction_date）
            sql = """
                SELECT 
                    sp.symbol, sp.prediction, sp.up_probability, sp.down_probability, sp.confidence,
                    sp.actual_direction, sp.prediction_hit, sp.target_date, sp.prediction_date,
                    pf.technical_score, pf.news_score, pf.capital_flow_score, pf.market_score,
                    pf.history_score
                    -- 【已优化移除】以下三个因子已从预测模型中移除：pf.sector_rotation_score, pf.valuation_score, pf.us_sector_score
                FROM stock_predictions sp
                LEFT JOIN prediction_factors pf ON sp.symbol = pf.symbol 
                    AND sp.prediction_date = pf.date
                WHERE sp.target_date >= %s 
                  AND sp.target_date <= %s
                  AND sp.actual_direction IS NOT NULL
                  AND sp.prediction_hit IS NOT NULL
                ORDER BY sp.target_date DESC
            """
            
            results = self.db.execute_query(sql, (start_date, end_date))
            
            if len(results) < min_samples:
                return {
                    'success': False,
                    'message': f'样本数量不足（{len(results)} < {min_samples}），无法进行权重优化'
                }
            
            # 分析各因子的准确率
            factor_accuracies = self._analyze_factor_accuracy(results)
            
            # 基于准确率计算最优权重
            optimal_weights = self._calculate_optimal_weights(factor_accuracies)
            
            # 生成权重调整建议
            suggestions = self._generate_weight_suggestions(optimal_weights, factor_accuracies)
            
            return {
                'success': True,
                'optimization_date': end_date.strftime('%Y-%m-%d'),
                'sample_count': len(results),
                'time_period': f'{days}d',
                'factor_accuracies': factor_accuracies,
                'optimal_weights': optimal_weights,
                'suggestions': suggestions
            }
            
        except Exception as e:
            self.logger.error(f"权重优化失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'权重优化失败: {str(e)}'
            }
    
    def _analyze_factor_accuracy(self, results: List[Dict]) -> Dict:
        """
        分析各因子的准确率
        
        Args:
            results: 历史预测结果列表
        
        Returns:
            各因子的准确率字典
        """
        factor_performances = {
            'technical': {'hit': 0, 'total': 0, 'score_sum': 0.0},
            'news': {'hit': 0, 'total': 0, 'score_sum': 0.0},
            'capital_flow': {'hit': 0, 'total': 0, 'score_sum': 0.0},
            'market': {'hit': 0, 'total': 0, 'score_sum': 0.0},
            'history': {'hit': 0, 'total': 0, 'score_sum': 0.0}
            # 【已优化移除】以下三个因子已从预测模型中移除：'sector_rotation', 'valuation', 'us_sector'
        }
        
        for r in results:
            try:
                # 检查是否有因子数据（通过JOIN获取的字段）
                has_factor_data = (
                    r.get('technical_score') is not None or
                    r.get('news_score') is not None or
                    r.get('capital_flow_score') is not None
                )
                
                if not has_factor_data:
                    # 如果没有因子数据，跳过这条记录
                    continue
                
                is_hit = r.get('prediction_hit') == '命中'
                prediction = r.get('prediction', '')
                
                # 分析各因子得分与预测准确性的关系
                # 【已优化移除】以下三个因子已从预测模型中移除：'sector_rotation', 'valuation', 'us_sector'
                factor_mapping = {
                    'technical': 'technical_score',
                    'news': 'news_score',
                    'capital_flow': 'capital_flow_score',
                    'market': 'market_score',
                    'history': 'history_score'
                }
                
                for factor_name, score_key in factor_mapping.items():
                    score = r.get(score_key)
                    if score is not None:
                        score = float(score)
                        factor_performances[factor_name]['total'] += 1
                        factor_performances[factor_name]['score_sum'] += score
                        
                        # 如果因子得分与预测方向一致且预测命中，则认为该因子有效
                        if prediction == '上涨' and score > 0 and is_hit:
                            factor_performances[factor_name]['hit'] += 1
                        elif prediction == '下跌' and score < 0 and is_hit:
                            factor_performances[factor_name]['hit'] += 1
                
            except Exception as e:
                self.logger.debug(f"分析因子准确率失败: {str(e)}")
                continue
        
        # 计算各因子的准确率
        factor_accuracies = {}
        for factor_name, perf in factor_performances.items():
            if perf['total'] > 0:
                accuracy = perf['hit'] / perf['total']
                avg_score = perf['score_sum'] / perf['total']
                factor_accuracies[factor_name] = {
                    'accuracy': accuracy,
                    'avg_score': avg_score,
                    'hit_count': perf['hit'],
                    'total_count': perf['total']
                }
            else:
                factor_accuracies[factor_name] = {
                    'accuracy': 0.5,  # 默认准确率
                    'avg_score': 0.0,
                    'hit_count': 0,
                    'total_count': 0
                }
        
        return factor_accuracies
    
    def _calculate_optimal_weights(self, factor_accuracies: Dict) -> Dict:
        """
        基于因子准确率计算最优权重
        
        Args:
            factor_accuracies: 各因子的准确率字典
        
        Returns:
            最优权重配置
        """
        # 计算准确率权重（准确率越高，权重越大）
        accuracy_scores = {}
        total_accuracy_score = 0.0
        
        for factor_name, acc_info in factor_accuracies.items():
            # 使用准确率与基准准确率（0.5）的差值作为权重依据
            accuracy_diff = acc_info['accuracy'] - 0.5
            # 如果准确率 > 0.5，给予正权重；如果 < 0.5，给予负权重
            accuracy_scores[factor_name] = max(0.1, 0.5 + accuracy_diff * 2)  # 最小权重0.1
            total_accuracy_score += accuracy_scores[factor_name]
        
        # 归一化权重（总和为1）
        optimal_weights = {}
        if total_accuracy_score > 0:
            for factor_name, score in accuracy_scores.items():
                optimal_weights[factor_name] = score / total_accuracy_score
        else:
            # 如果所有因子准确率都很低，使用默认权重（对应config.py中的65%传统因子体系）
            default_weights = {
                'technical': 0.20,
                'news': 0.16,
                'capital_flow': 0.13,
                'market': 0.11,
                'history': 0.05,
            }
            return default_weights
        
        return optimal_weights
    
    def _generate_weight_suggestions(self, optimal_weights: Dict, factor_accuracies: Dict) -> List[Dict]:
        """
        生成权重调整建议
        
        Args:
            optimal_weights: 最优权重配置
            factor_accuracies: 因子准确率
        
        Returns:
            调整建议列表
        """
        suggestions = []
        
        # 当前默认权重（65%传统因子体系，与config.py一致）
        current_weights = {
            'technical': 0.20,
            'news': 0.16,
            'capital_flow': 0.13,
            'market': 0.11,
            'history': 0.05,
            # 【已优化移除】sector_rotation、valuation、us_sector 已从预测模型中移除
        }
        
        for factor_name, optimal_weight in optimal_weights.items():
            current_weight = current_weights.get(factor_name, 0.0)
            change = optimal_weight - current_weight
            change_pct = (change / current_weight * 100) if current_weight > 0 else 0
            
            accuracy_info = factor_accuracies.get(factor_name, {})
            accuracy = accuracy_info.get('accuracy', 0.5)
            
            if abs(change_pct) > 10:  # 变化超过10%才建议调整
                suggestions.append({
                    'factor': factor_name,
                    'current_weight': current_weight,
                    'suggested_weight': optimal_weight,
                    'change': change,
                    'change_pct': change_pct,
                    'accuracy': accuracy,
                    'reason': f'因子准确率{accuracy:.1%}，建议调整权重'
                })
        
        # 按变化幅度排序
        suggestions.sort(key=lambda x: abs(x['change_pct']), reverse=True)
        
        return suggestions
    
    def adjust_weights_by_stock_type(self, symbol: str, base_weights: Dict) -> Dict:
        """
        根据个股特性调整权重
        
        Args:
            symbol: 股票代码
            base_weights: 基础权重配置
        
        Returns:
            调整后的权重配置
        """
        try:
            # 尝试获取股票信息（如果表存在且有相关字段）
            market_cap = None
            stock_type = None
            
            # 尝试从历史数据中获取市值（stock_info表不存在，直接从stock_history_data获取）
            try:
                # 从最新历史数据中获取市值
                sql = """
                    SELECT total_market_cap, float_market_cap
                    FROM stock_history_data
                    WHERE symbol = %s
                    ORDER BY trade_date DESC
                    LIMIT 1
                """
                history_info = self.db.execute_query(sql, (symbol,))
                if history_info:
                    history_data = history_info[0]
                    market_cap = (history_data.get('total_market_cap') or 
                                history_data.get('float_market_cap') or 0)
                    if market_cap and market_cap > 0:
                        if market_cap > 10000:
                            market_cap = market_cap / 100000000  # 转换为亿元
            except Exception as e:
                self.logger.debug(f"从历史数据获取市值失败: {str(e)}")
                market_cap = None
            
            adjusted_weights = base_weights.copy()
            
            # 根据市值调整权重（如果市值信息可用）
            if market_cap and market_cap > 0:
                if market_cap > 500:  # 大盘股（市值>500亿）
                    # 大盘股：增加资金流向权重，降低技术指标权重
                    # 【已优化移除】valuation_weight已从预测模型中移除
                    adjusted_weights['capital_flow_weight'] = base_weights.get('capital_flow_weight', 0.20) * 1.3
                    adjusted_weights['technical_weight'] = base_weights.get('technical_weight', 0.22) * 0.9
                    self.logger.debug(f"股票{symbol}识别为大盘股（市值{market_cap:.1f}亿），调整权重")
                elif market_cap < 100:  # 小盘股（市值<100亿）
                    # 小盘股：增加技术指标和新闻权重
                    # 【已优化移除】valuation_weight已从预测模型中移除
                    adjusted_weights['technical_weight'] = base_weights.get('technical_weight', 0.22) * 1.2
                    adjusted_weights['news_weight'] = base_weights.get('news_weight', 0.28) * 1.15
                    self.logger.debug(f"股票{symbol}识别为小盘股（市值{market_cap:.1f}亿），调整权重")
            
            # 根据股票类型调整权重（如果类型信息可用）
            if stock_type:
                if stock_type in ['成长股', 'growth', 'g']:
                    # 成长股：增加新闻权重
                    # 【已优化移除】sector_rotation_weight已从预测模型中移除
                    adjusted_weights['news_weight'] = base_weights.get('news_weight', 0.28) * 1.2
                    self.logger.debug(f"股票{symbol}识别为成长股，调整权重")
                elif stock_type in ['价值股', 'value', 'v']:
                    # 价值股：增加历史权重
                    # 【已优化移除】valuation_weight已从预测模型中移除
                    adjusted_weights['history_weight'] = base_weights.get('history_weight', 0.11) * 1.3
                    self.logger.debug(f"股票{symbol}识别为价值股，调整权重")
            
            # 归一化权重（确保总和为1）
            total_weight = sum(adjusted_weights.values())
            if total_weight > 0:
                for key in adjusted_weights:
                    adjusted_weights[key] = adjusted_weights[key] / total_weight
            
            return adjusted_weights
            
        except Exception as e:
            self.logger.debug(f"根据个股特性调整权重失败: {str(e)}")
            return base_weights
    
    def adjust_weights_by_market_state(self, market_state: Dict, base_weights: Dict) -> Dict:
        """
        根据市场状态调整权重（使用MarketStateIdentifier的建议）
        
        Args:
            market_state: 市场状态字典
            base_weights: 基础权重配置
        
        Returns:
            调整后的权重配置
        """
        try:
            from utils.market_state_identifier import MarketStateIdentifier
            
            identifier = MarketStateIdentifier()
            multipliers = identifier.get_weight_adjustment(market_state)
            
            adjusted_weights = base_weights.copy()
            
            # 应用权重倍数
            if 'technical_weight_multiplier' in multipliers:
                adjusted_weights['technical_weight'] = (
                    base_weights.get('technical_weight', 0.20) * 
                    multipliers['technical_weight_multiplier']
                )
            
            if 'news_weight_multiplier' in multipliers:
                adjusted_weights['news_weight'] = (
                    base_weights.get('news_weight', 0.25) * 
                    multipliers['news_weight_multiplier']
                )
            
            if 'capital_flow_weight_multiplier' in multipliers:
                adjusted_weights['capital_flow_weight'] = (
                    base_weights.get('capital_flow_weight', 0.18) * 
                    multipliers['capital_flow_weight_multiplier']
                )
            
            if 'market_weight_multiplier' in multipliers:
                adjusted_weights['market_weight'] = (
                    base_weights.get('market_weight', 0.17) * 
                    multipliers['market_weight_multiplier']
                )
            
            # 归一化权重（确保总和为1）
            total_weight = sum(adjusted_weights.values())
            if total_weight > 0:
                for key in adjusted_weights:
                    adjusted_weights[key] = adjusted_weights[key] / total_weight
            
            return adjusted_weights
            
        except Exception as e:
            self.logger.debug(f"根据市场状态调整权重失败: {str(e)}")
            return base_weights
    
    def get_optimized_weights(self, symbol: Optional[str] = None, 
                             market_state: Optional[Dict] = None,
                             use_accuracy_optimization: bool = True) -> Dict:
        """
        获取优化后的权重配置（综合考虑历史准确率、市场状态、个股特性）
        
        Args:
            symbol: 股票代码（可选，用于个股特性调整）
            market_state: 市场状态（可选）
            use_accuracy_optimization: 是否使用基于准确率的优化
        
        Returns:
            优化后的权重配置
        """
        # 1. 获取基础权重（65%传统因子体系，与config.py一致）
        base_weights = {
            'technical_weight': 0.20,
            'news_weight': 0.16,
            'capital_flow_weight': 0.13,
            'market_weight': 0.11,
            'history_weight': 0.05,
            # 已移除：sector_rotation, valuation, us_sector
        }
        
        # 2. 如果使用基于准确率的优化，先优化基础权重
        if use_accuracy_optimization and self.use_database:
            try:
                opt_result = self.optimize_weights_by_accuracy(days=30, min_samples=50)
                if opt_result.get('success') and opt_result.get('optimal_weights'):
                    # 使用优化后的权重作为基础权重
                    optimal = opt_result['optimal_weights']
                    # 映射因子名到权重名
                    # 【已优化移除】以下三个因子已从预测模型中移除
                    weight_mapping = {
                        'technical': 'technical_weight',
                        'news': 'news_weight',
                        'capital_flow': 'capital_flow_weight',
                        'market': 'market_weight',
                        'history': 'history_weight'
                    }
                    for factor_name, weight_name in weight_mapping.items():
                        if factor_name in optimal:
                            base_weights[weight_name] = optimal[factor_name]
            except Exception as e:
                self.logger.debug(f"基于准确率的权重优化失败: {str(e)}")
        
        # 3. 根据市场状态调整权重
        if market_state:
            base_weights = self.adjust_weights_by_market_state(market_state, base_weights)
        
        # 4. 根据个股特性调整权重
        if symbol:
            base_weights = self.adjust_weights_by_stock_type(symbol, base_weights)
        
        return base_weights


# 全局权重优化器实例
_weight_optimizer = None
_weight_optimizer_lock = threading.Lock()


def get_weight_optimizer() -> WeightOptimizer:
    """获取全局权重优化器实例（单例模式）"""
    global _weight_optimizer
    
    if _weight_optimizer is None:
        with _weight_optimizer_lock:
            if _weight_optimizer is None:
                _weight_optimizer = WeightOptimizer()
    
    return _weight_optimizer
