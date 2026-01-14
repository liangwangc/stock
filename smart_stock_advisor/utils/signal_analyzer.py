"""
信号分析和优化模块

本模块提供交易信号的分析和优化功能，通过统计历史信号准确率、
动态调整交易阈值、提供信号强度评分说明，帮助提高交易信号的质量。

主要功能：
- 信号准确率统计：统计不同信号类型、不同股票的历史准确率
- 动态阈值调整：根据历史表现动态调整买入/卖出阈值
- 信号强度评分：计算信号强度评分，并提供详细说明
- 信号历史记录：记录和查询历史信号及其表现

统计维度：
- 按信号类型：BUY、SELL、ADD、REDUCE、HOLD等
- 按股票：不同股票的信号准确率
- 按时间：不同时间段的信号表现
- 按市场状态：不同市场状态下的信号表现

使用示例：
    ```python
    from utils.signal_analyzer import SignalAnalyzer
    
    analyzer = SignalAnalyzer()
    
    # 获取信号准确率统计
    stats = analyzer.get_signal_accuracy_statistics(days=30)
    
    # 获取动态阈值
    thresholds = analyzer.get_dynamic_thresholds(symbol='000001')
    
    # 生成信号强度评分说明
    explanation = analyzer.generate_signal_explanation(
        symbol='000001',
        action='BUY',
        strength=0.75
    )
    ```

作者：Smart Stock Advisor Team
创建日期：2024
最后更新：2024
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection, USE_DATABASE
from utils.logger import get_logger

logger = get_logger(__name__)


class SignalAnalyzer:
    """
    信号分析器
    
    负责交易信号的分析、统计和优化，通过历史数据学习提高信号质量。
    
    主要功能：
    - 信号准确率统计：分析历史信号的准确率，识别表现好的信号类型
    - 动态阈值调整：根据历史表现自动调整交易阈值，提高信号质量
    - 信号强度评分：计算信号强度并生成详细说明，帮助理解信号来源
    
    性能优化：
    - 结果缓存：统计结果缓存2小时，避免重复计算
    - 增量更新：支持增量更新统计结果
    
    应用场景：
    - 交易信号质量评估
    - 交易阈值优化
    - 信号强度解释
    - 交易策略改进
    """
    
    def __init__(self):
        """
        初始化信号分析器
        
        初始化数据库连接、日志记录器和缓存系统。
        
        Attributes:
            db: 数据库连接对象（如果数据库启用）
            logger: 日志记录器
            _statistics_cache: 统计结果缓存字典
            _cache_ttl: 缓存有效期（默认2小时）
            _cache_timestamp: 缓存时间戳字典
        """
        self.db = DatabaseConnection() if USE_DATABASE else None
        self.logger = logger
        
        # 缓存统计结果（避免重复查询）
        self._statistics_cache = {}
        self._cache_ttl = timedelta(hours=2)  # 缓存2小时
        self._cache_timestamp = {}
    
    def get_signal_accuracy_statistics(
        self,
        days: int = 30,
        symbol: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> Dict:
        """
        获取信号准确率统计（按信号类型、按股票）
        
        Args:
            days: 统计天数（默认30天）
            symbol: 股票代码（可选，指定某只股票）
            action_type: 信号类型（可选，BUY/SELL/ADD/REDUCE/HOLD等）
        
        Returns:
            统计结果字典
        """
        if not self.db:
            return {
                'success': False,
                'message': '数据库不可用，无法统计信号准确率'
            }
        
        try:
            # 检查缓存
            cache_key = f"{days}_{symbol or 'all'}_{action_type or 'all'}"
            if cache_key in self._statistics_cache:
                cache_time = self._cache_timestamp.get(cache_key)
                if cache_time and datetime.now() - cache_time < self._cache_ttl:
                    self.logger.debug(f"使用缓存的信号统计结果: {cache_key}")
                    return self._statistics_cache[cache_key]
            
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 查询实时交易决策数据
            base_sql = """
                SELECT 
                    rtd.symbol,
                    rtd.action,
                    rtd.action_cn,
                    rtd.strength,
                    rtd.up_probability,
                    rtd.confidence,
                    rtd.signal_strength,
                    rtd.timestamp,
                    rtd.date,
                    sp.prediction_hit,
                    sp.actual_change_pct,
                    sp.actual_direction
                FROM realtime_trading_decisions rtd
                LEFT JOIN stock_predictions sp ON (
                    rtd.symbol = sp.symbol 
                    AND rtd.target_date = sp.target_date
                    AND sp.prediction_hit IS NOT NULL
                )
                WHERE rtd.date >= %s
                  AND rtd.date <= %s
            """
            
            params = [start_date, end_date]
            
            if symbol:
                base_sql += " AND rtd.symbol = %s"
                params.append(symbol)
            
            if action_type:
                base_sql += " AND rtd.action = %s"
                params.append(action_type)
            
            base_sql += " ORDER BY rtd.timestamp DESC"
            
            results = self.db.execute_query(base_sql, params)
            
            if not results:
                return {
                    'success': False,
                    'message': f'没有找到 {days} 天内的交易决策记录',
                    'total_count': 0
                }
            
            # 统计准确率
            statistics = self._calculate_accuracy_statistics(results)
            
            # 添加元数据
            statistics['success'] = True
            statistics['period_days'] = days
            statistics['total_decisions'] = len(results)
            statistics['symbol'] = symbol
            statistics['action_type'] = action_type
            statistics['start_date'] = start_date.strftime('%Y-%m-%d')
            statistics['end_date'] = end_date.strftime('%Y-%m-%d')
            
            # 更新缓存
            self._statistics_cache[cache_key] = statistics
            self._cache_timestamp[cache_key] = datetime.now()
            
            return statistics
            
        except Exception as e:
            self.logger.error(f"统计信号准确率失败: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def _calculate_accuracy_statistics(self, results: List[Dict]) -> Dict:
        """
        计算准确率统计
        
        Args:
            results: 查询结果列表
        
        Returns:
            统计结果字典
        """
        # 按信号类型统计
        by_action = defaultdict(lambda: {
            'total': 0,
            'hit': 0,
            'miss': 0,
            'unknown': 0,
            'accuracy': 0.0,
            'avg_profit_pct': 0.0,
            'avg_loss_pct': 0.0
        })
        
        # 按股票统计
        by_symbol = defaultdict(lambda: {
            'total': 0,
            'hit': 0,
            'miss': 0,
            'unknown': 0,
            'accuracy': 0.0,
            'actions': defaultdict(int)
        })
        
        # 按信号强度统计
        by_strength = defaultdict(lambda: {
            'total': 0,
            'hit': 0,
            'miss': 0,
            'unknown': 0,
            'accuracy': 0.0
        })
        
        profits = []
        losses = []
        
        for r in results:
            action = r.get('action', 'UNKNOWN')
            symbol = r.get('symbol', '')
            strength = r.get('strength', 'NEUTRAL')
            prediction_hit = r.get('prediction_hit')
            actual_change_pct = r.get('actual_change_pct')
            
            # 按信号类型统计
            by_action[action]['total'] += 1
            if prediction_hit == '命中':
                by_action[action]['hit'] += 1
                if actual_change_pct is not None:
                    if actual_change_pct > 0:
                        profits.append(actual_change_pct)
                    else:
                        losses.append(actual_change_pct)
            elif prediction_hit == '未命中':
                by_action[action]['miss'] += 1
            else:
                by_action[action]['unknown'] += 1
            
            # 按股票统计
            by_symbol[symbol]['total'] += 1
            by_symbol[symbol]['actions'][action] += 1
            if prediction_hit == '命中':
                by_symbol[symbol]['hit'] += 1
            elif prediction_hit == '未命中':
                by_symbol[symbol]['miss'] += 1
            else:
                by_symbol[symbol]['unknown'] += 1
            
            # 按信号强度统计
            by_strength[strength]['total'] += 1
            if prediction_hit == '命中':
                by_strength[strength]['hit'] += 1
            elif prediction_hit == '未命中':
                by_strength[strength]['miss'] += 1
            else:
                by_strength[strength]['unknown'] += 1
        
        # 计算准确率
        for action, stats in by_action.items():
            total_with_result = stats['hit'] + stats['miss']
            if total_with_result > 0:
                stats['accuracy'] = stats['hit'] / total_with_result
            if profits:
                stats['avg_profit_pct'] = sum(profits) / len(profits)
            if losses:
                stats['avg_loss_pct'] = sum(losses) / len(losses)
        
        for symbol, stats in by_symbol.items():
            total_with_result = stats['hit'] + stats['miss']
            if total_with_result > 0:
                stats['accuracy'] = stats['hit'] / total_with_result
            # 转换 defaultdict 为普通 dict
            stats['actions'] = dict(stats['actions'])
        
        for strength, stats in by_strength.items():
            total_with_result = stats['hit'] + stats['miss']
            if total_with_result > 0:
                stats['accuracy'] = stats['hit'] / total_with_result
        
        return {
            'by_action': dict(by_action),
            'by_symbol': dict(by_symbol),
            'by_strength': dict(by_strength),
            'overall': {
                'total': len(results),
                'with_result': sum(1 for r in results if r.get('prediction_hit')),
                'hit': sum(1 for r in results if r.get('prediction_hit') == '命中'),
                'miss': sum(1 for r in results if r.get('prediction_hit') == '未命中'),
                'accuracy': sum(1 for r in results if r.get('prediction_hit') == '命中') / 
                           max(1, sum(1 for r in results if r.get('prediction_hit')))
            }
        }
    
    def get_optimized_thresholds(
        self,
        base_thresholds: Dict,
        days: int = 30,
        min_samples: int = 20
    ) -> Dict:
        """
        根据历史表现动态调整信号阈值
        
        Args:
            base_thresholds: 基础阈值配置字典，包含：
                - buy_signal_threshold: 买入信号阈值
                - strong_buy_threshold: 强烈买入信号阈值
                - sell_signal_threshold: 卖出信号阈值
                - strong_sell_threshold: 强烈卖出信号阈值
            days: 统计天数（默认30天）
            min_samples: 最小样本数（默认20）
        
        Returns:
            优化后的阈值字典，包含：
                - optimized_thresholds: 优化后的阈值
                - adjustments: 调整信息
                - recommendations: 调整建议
        """
        try:
            # 获取信号准确率统计
            statistics = self.get_signal_accuracy_statistics(days=days)
            
            if not statistics.get('success', False):
                self.logger.warning("无法获取信号统计，使用基础阈值")
                return {
                    'success': False,
                    'optimized_thresholds': base_thresholds.copy(),
                    'message': '无法获取统计信息'
                }
            
            by_action = statistics.get('by_action', {})
            optimized = base_thresholds.copy()
            adjustments = {}
            recommendations = []
            
            # 优化买入阈值
            buy_stats = by_action.get('BUY', {})
            if buy_stats.get('total', 0) >= min_samples:
                buy_accuracy = buy_stats.get('accuracy', 0)
                if buy_accuracy < 0.55:  # 准确率低于55%，提高阈值
                    adjustment = min(0.05, (0.55 - buy_accuracy) * 0.2)
                    old_threshold = base_thresholds.get('buy_signal_threshold', 0.65)
                    new_threshold = min(0.85, old_threshold + adjustment)
                    optimized['buy_signal_threshold'] = new_threshold
                    adjustments['buy_signal_threshold'] = {
                        'old': old_threshold,
                        'new': new_threshold,
                        'change': new_threshold - old_threshold,
                        'reason': f"买入信号准确率{buy_accuracy:.1%}偏低，提高阈值以提高质量"
                    }
                    recommendations.append(f"建议买入阈值从{old_threshold:.2f}调整到{new_threshold:.2f}")
                elif buy_accuracy > 0.70:  # 准确率高于70%，可以适当降低阈值
                    adjustment = min(0.03, (buy_accuracy - 0.70) * 0.15)
                    old_threshold = base_thresholds.get('buy_signal_threshold', 0.65)
                    new_threshold = max(0.60, old_threshold - adjustment)
                    optimized['buy_signal_threshold'] = new_threshold
                    adjustments['buy_signal_threshold'] = {
                        'old': old_threshold,
                        'new': new_threshold,
                        'change': new_threshold - old_threshold,
                        'reason': f"买入信号准确率{buy_accuracy:.1%}较高，可适当降低阈值增加机会"
                    }
                    recommendations.append(f"建议买入阈值从{old_threshold:.2f}调整到{new_threshold:.2f}")
            
            # 优化强烈买入阈值
            strong_buy_stats = by_action.get('BUY', {})
            if strong_buy_stats.get('total', 0) >= min_samples // 2:  # 强烈买入样本可能较少
                strong_buy_accuracy = strong_buy_stats.get('accuracy', 0)
                old_threshold = base_thresholds.get('strong_buy_threshold', 0.75)
                
                # 基于买入信号的准确率调整强烈买入阈值
                if buy_stats.get('accuracy', 0) > 0.65:
                    # 如果买入信号准确率高，可以适当降低强烈买入阈值
                    if strong_buy_accuracy > 0.75:
                        new_threshold = max(0.70, old_threshold - 0.02)
                        optimized['strong_buy_threshold'] = new_threshold
                        adjustments['strong_buy_threshold'] = {
                            'old': old_threshold,
                            'new': new_threshold,
                            'change': new_threshold - old_threshold,
                            'reason': f"强烈买入信号表现良好，可适当降低阈值"
                        }
                elif buy_stats.get('accuracy', 0) < 0.55:
                    # 如果买入信号准确率低，提高强烈买入阈值
                    new_threshold = min(0.80, old_threshold + 0.02)
                    optimized['strong_buy_threshold'] = new_threshold
                    adjustments['strong_buy_threshold'] = {
                        'old': old_threshold,
                        'new': new_threshold,
                        'change': new_threshold - old_threshold,
                        'reason': f"买入信号准确率偏低，提高强烈买入阈值以确保质量"
                    }
            
            # 优化卖出阈值
            sell_stats = by_action.get('SELL', {})
            if sell_stats.get('total', 0) >= min_samples:
                sell_accuracy = sell_stats.get('accuracy', 0)
                if sell_accuracy < 0.55:
                    adjustment = min(0.05, (0.55 - sell_accuracy) * 0.2)
                    old_threshold = base_thresholds.get('sell_signal_threshold', 0.60)
                    new_threshold = min(0.80, old_threshold + adjustment)
                    optimized['sell_signal_threshold'] = new_threshold
                    adjustments['sell_signal_threshold'] = {
                        'old': old_threshold,
                        'new': new_threshold,
                        'change': new_threshold - old_threshold,
                        'reason': f"卖出信号准确率{sell_accuracy:.1%}偏低，提高阈值以提高质量"
                    }
                    recommendations.append(f"建议卖出阈值从{old_threshold:.2f}调整到{new_threshold:.2f}")
                elif sell_accuracy > 0.70:
                    adjustment = min(0.03, (sell_accuracy - 0.70) * 0.15)
                    old_threshold = base_thresholds.get('sell_signal_threshold', 0.60)
                    new_threshold = max(0.55, old_threshold - adjustment)
                    optimized['sell_signal_threshold'] = new_threshold
                    adjustments['sell_signal_threshold'] = {
                        'old': old_threshold,
                        'new': new_threshold,
                        'change': new_threshold - old_threshold,
                        'reason': f"卖出信号准确率{sell_accuracy:.1%}较高，可适当降低阈值"
                    }
            
            # 优化强烈卖出阈值
            strong_sell_stats = by_action.get('SELL', {})
            if strong_sell_stats.get('total', 0) >= min_samples // 2:
                strong_sell_accuracy = strong_sell_stats.get('accuracy', 0)
                old_threshold = base_thresholds.get('strong_sell_threshold', 0.70)
                
                if sell_stats.get('accuracy', 0) > 0.65:
                    if strong_sell_accuracy > 0.75:
                        new_threshold = max(0.65, old_threshold - 0.02)
                        optimized['strong_sell_threshold'] = new_threshold
                        adjustments['strong_sell_threshold'] = {
                            'old': old_threshold,
                            'new': new_threshold,
                            'change': new_threshold - old_threshold,
                            'reason': f"强烈卖出信号表现良好，可适当降低阈值"
                        }
                elif sell_stats.get('accuracy', 0) < 0.55:
                    new_threshold = min(0.75, old_threshold + 0.02)
                    optimized['strong_sell_threshold'] = new_threshold
                    adjustments['strong_sell_threshold'] = {
                        'old': old_threshold,
                        'new': new_threshold,
                        'change': new_threshold - old_threshold,
                        'reason': f"卖出信号准确率偏低，提高强烈卖出阈值"
                    }
            
            return {
                'success': True,
                'optimized_thresholds': optimized,
                'base_thresholds': base_thresholds.copy(),
                'adjustments': adjustments,
                'recommendations': recommendations,
                'statistics_summary': {
                    'by_action': {k: {'accuracy': v.get('accuracy', 0), 'total': v.get('total', 0)} 
                                 for k, v in by_action.items()},
                    'overall_accuracy': statistics.get('overall', {}).get('accuracy', 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"优化阈值失败: {str(e)}")
            return {
                'success': False,
                'optimized_thresholds': base_thresholds.copy(),
                'message': str(e)
            }
    
    def generate_signal_explanation(
        self,
        signal_strength: float,
        final_score: float,
        factor_scores: Dict,
        weights: Dict
    ) -> Dict:
        """
        生成信号强度评分说明（为什么是这个分数）
        
        Args:
            signal_strength: 信号强度（0-1）
            final_score: 最终综合得分
            factor_scores: 各因子得分字典，包含：
                - prediction: 预测得分
                - capital_flow: 资金流向得分
                - bid_ask: 买卖盘得分
                - intraday: 盘中调整得分
            weights: 权重配置字典
        
        Returns:
            评分说明字典
        """
        explanation_parts = []
        components = []
        
        # 解析各因子得分
        prediction_score = factor_scores.get('prediction', 0)
        capital_flow_score = factor_scores.get('capital_flow', 0)
        bid_ask_score = factor_scores.get('bid_ask', 0)
        intraday_score = factor_scores.get('intraday', 0)
        
        # 解析权重
        prediction_weight = weights.get('prediction_weight', 0.5)
        capital_flow_weight = weights.get('capital_flow_weight', 0.25)
        bid_ask_weight = weights.get('bid_ask_weight', 0.15)
        intraday_weight = weights.get('intraday_weight', 0.10)
        
        # 计算各部分的贡献
        prediction_contribution = prediction_score * prediction_weight
        capital_flow_contribution = capital_flow_score * capital_flow_weight
        bid_ask_contribution = bid_ask_score * bid_ask_weight
        intraday_contribution = intraday_score * intraday_weight
        
        # 构建组成部分详情
        components.append({
            'name': '预测得分',
            'score': prediction_score,
            'weight': prediction_weight,
            'contribution': prediction_contribution,
            'description': self._describe_prediction_score(prediction_score)
        })
        
        components.append({
            'name': '资金流向',
            'score': capital_flow_score,
            'weight': capital_flow_weight,
            'contribution': capital_flow_contribution,
            'description': self._describe_capital_flow_score(capital_flow_score)
        })
        
        components.append({
            'name': '买卖盘',
            'score': bid_ask_score,
            'weight': bid_ask_weight,
            'contribution': bid_ask_contribution,
            'description': self._describe_bid_ask_score(bid_ask_score)
        })
        
        components.append({
            'name': '盘中调整',
            'score': intraday_score,
            'weight': intraday_weight,
            'contribution': intraday_contribution,
            'description': self._describe_intraday_score(intraday_score)
        })
        
        # 生成文字说明
        explanation_parts.append(f"综合信号强度为 {signal_strength:.1%}，得分由以下因素构成：")
        explanation_parts.append("")
        
        # 按贡献度排序
        components_sorted = sorted(components, key=lambda x: abs(x['contribution']), reverse=True)
        
        for i, comp in enumerate(components_sorted, 1):
            sign = '+' if comp['contribution'] >= 0 else ''
            explanation_parts.append(
                f"{i}. {comp['name']}："
                f"得分 {comp['score']:.2f} × 权重 {comp['weight']:.1%} = "
                f"贡献 {sign}{comp['contribution']:.3f} ({comp['description']})"
            )
        
        explanation_parts.append("")
        explanation_parts.append(f"最终综合得分：{final_score:.3f}")
        explanation_parts.append(f"转换为信号强度：{signal_strength:.1%}")
        
        # 生成改进建议
        suggestions = []
        if signal_strength < 0.5:
            suggestions.append("信号强度较低（<50%），建议观望或等待更明确的信号")
        if abs(prediction_contribution) < 0.1:
            suggestions.append("预测得分贡献较小，建议关注更多预测因子")
        if abs(capital_flow_contribution) > 0.15:
            suggestions.append("资金流向影响较大，需密切关注资金面变化")
        if abs(intraday_contribution) > 0.05:
            suggestions.append("盘中调整幅度较大，可能存在短期波动风险")
        
        return {
            'signal_strength': signal_strength,
            'final_score': final_score,
            'components': components,
            'explanation': '\n'.join(explanation_parts),
            'suggestions': suggestions,
            'interpretation': self._interpret_signal_strength(signal_strength)
        }
    
    def _describe_prediction_score(self, score: float) -> str:
        """描述预测得分"""
        if score > 0.3:
            return "强烈看涨"
        elif score > 0.1:
            return "看涨"
        elif score > -0.1:
            return "中性"
        elif score > -0.3:
            return "看跌"
        else:
            return "强烈看跌"
    
    def _describe_capital_flow_score(self, score: float) -> str:
        """描述资金流向得分"""
        if score > 0.05:
            return "大幅净流入"
        elif score > 0:
            return "净流入"
        elif score > -0.05:
            return "净流出"
        else:
            return "大幅净流出"
    
    def _describe_bid_ask_score(self, score: float) -> str:
        """描述买卖盘得分"""
        if score > 0.5:
            return "买盘非常强势"
        elif score > 0.2:
            return "买盘较强"
        elif score > -0.2:
            return "买卖均衡"
        elif score > -0.5:
            return "卖盘较强"
        else:
            return "卖盘非常强势"
    
    def _describe_intraday_score(self, score: float) -> str:
        """描述盘中调整得分"""
        if score > 0:
            return "盘中回调提供买入机会"
        elif score < 0:
            return "盘中涨幅较大需谨慎"
        else:
            return "盘中走势正常"
    
    def _interpret_signal_strength(self, strength: float) -> str:
        """解释信号强度"""
        if strength >= 0.75:
            return "强烈信号，建议重点关注"
        elif strength >= 0.65:
            return "较强信号，可以积极关注"
        elif strength >= 0.55:
            return "中等信号，建议谨慎操作"
        elif strength >= 0.45:
            return "较弱信号，建议观望"
        else:
            return "信号很弱，不建议操作"


# 全局实例
_analyzer_instance = None

def get_signal_analyzer() -> SignalAnalyzer:
    """获取信号分析器单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = SignalAnalyzer()
    return _analyzer_instance
