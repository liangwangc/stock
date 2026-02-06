"""
模型性能评估模块
用于评估预测模型和实时交易策略的性能
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

logger = get_logger(__name__)


class ModelPerformanceEvaluator:
    """模型性能评估器"""
    
    def __init__(self):
        self.db = DatabaseConnection()
        self.logger = logger
    
    def evaluate_prediction_performance(self, days: int = 30) -> Dict:
        """
        评估预测模型性能
        
        Args:
            days: 评估时间范围（天数）
            
        Returns:
            性能评估结果字典
        """
        try:
            # 计算评估日期范围
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 查询有实际结果的预测记录（关联配置表，支持按配置版本分析）
            # 优化：添加偏差值字段到查询中
            # 注意：factor_weights字段可能不存在，从prediction_factors表获取权重信息
            sql = """
                SELECT 
                    sp.symbol, sp.name, sp.prediction_date, sp.target_date,
                    sp.prediction, sp.up_probability, sp.down_probability, sp.confidence,
                    sp.actual_price, sp.actual_change_pct, sp.actual_direction, sp.prediction_hit,
                    sp.current_price, sp.config_id,
                    sp.predicted_change_pct, sp.deviation_pct, sp.absolute_deviation_pct,
                    pc.config_name, pc.is_active as config_is_active
                FROM stock_predictions sp
                LEFT JOIN prediction_config pc ON sp.config_id = pc.id
                WHERE sp.target_date >= %s 
                  AND sp.target_date <= %s
                  AND sp.actual_price IS NOT NULL
                  AND sp.prediction_hit IS NOT NULL
                ORDER BY sp.target_date DESC
            """
            
            results = self.db.execute_query(sql, (start_date, end_date))
            
            if not results:
                self.logger.warning(f"没有找到 {days} 天内的预测记录")
                return {
                    'success': False,
                    'message': f'没有找到 {days} 天内的预测记录',
                    'sample_count': 0
                }
            
            # 计算性能指标
            total_count = len(results)
            hit_count = sum(1 for r in results if r.get('prediction_hit') == '命中')
            direction_accuracy = hit_count / total_count if total_count > 0 else 0.0
            
            # 计算幅度误差（MAE）
            # 优化：优先使用存储的偏差值，如果没有则计算
            magnitude_errors = []
            for r in results:
                if r.get('actual_change_pct') is not None:
                    # 优先使用存储的绝对偏差值
                    if r.get('absolute_deviation_pct') is not None:
                        error = float(r.get('absolute_deviation_pct', 0))
                        magnitude_errors.append(error)
                    # 其次使用存储的偏差值
                    elif r.get('deviation_pct') is not None:
                        error = abs(float(r.get('deviation_pct', 0)))
                        magnitude_errors.append(error)
                    # 如果都没有，使用实际的predicted_change_pct计算
                    elif r.get('predicted_change_pct') is not None:
                        predicted_change = float(r.get('predicted_change_pct', 0))
                        actual_change = float(r.get('actual_change_pct', 0))
                        error = abs(predicted_change - actual_change)
                        magnitude_errors.append(error)
                    # 最后才使用简化的估算方法（向后兼容）
                    else:
                        if r.get('prediction') == '上涨':
                            predicted_change = r.get('up_probability', 0.5) * 5.0  # 简化估算
                        elif r.get('prediction') == '下跌':
                            predicted_change = -r.get('down_probability', 0.5) * 5.0
                        else:
                            predicted_change = 0.0
                        
                        actual_change = float(r.get('actual_change_pct', 0))
                        error = abs(predicted_change - actual_change)
                        magnitude_errors.append(error)
            
            magnitude_mae = sum(magnitude_errors) / len(magnitude_errors) if magnitude_errors else 0.0
            
            # 计算置信度校准度
            # 将预测按置信度分组，计算每组的准确率
            confidence_buckets = {
                'high': [],      # >= 0.7
                'medium': [],    # 0.5-0.7
                'low': []        # < 0.5
            }
            
            for r in results:
                confidence = float(r.get('confidence', 0))
                is_hit = r.get('prediction_hit') == '命中'
                
                if confidence >= 0.7:
                    confidence_buckets['high'].append(is_hit)
                elif confidence >= 0.5:
                    confidence_buckets['medium'].append(is_hit)
                else:
                    confidence_buckets['low'].append(is_hit)
            
            calibration_scores = {}
            for bucket, hits in confidence_buckets.items():
                if hits:
                    calibration_scores[bucket] = sum(hits) / len(hits)
                else:
                    calibration_scores[bucket] = 0.0
            
            # 计算因子贡献度（从prediction_factors表）
            factor_contributions = self._calculate_factor_contributions(start_date, end_date, results)
            
            # 识别市场状态
            market_condition = self._identify_market_condition(start_date, end_date)
            
            performance_result = {
                'success': True,
                'evaluation_date': end_date.strftime('%Y-%m-%d'),
                'evaluation_type': 'prediction',
                'time_period': f'{days}d',
                'sample_count': total_count,
                'direction_accuracy': round(direction_accuracy, 4),
                'magnitude_mae': round(magnitude_mae, 4),
                'confidence_calibration': calibration_scores,
                'factor_contributions': factor_contributions,
                'market_condition': market_condition,
                'details': {
                    'hit_count': hit_count,
                    'miss_count': total_count - hit_count,
                    'confidence_buckets': {
                        'high': len(confidence_buckets['high']),
                        'medium': len(confidence_buckets['medium']),
                        'low': len(confidence_buckets['low'])
                    }
                }
            }
            
            # 保存到数据库
            self._save_performance_record(performance_result)
            
            return performance_result
            
        except Exception as e:
            self.logger.error(f"评估预测性能失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'评估失败: {str(e)}'
            }
    
    def evaluate_trading_performance(self, days: int = 30) -> Dict:
        """
        评估实时交易决策性能
        
        Args:
            days: 评估时间范围（天数）
            
        Returns:
            性能评估结果字典
        """
        try:
            # 计算评估日期范围
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 查询实时交易决策记录（需要结合后续价格表现）
            sql = """
                SELECT 
                    id, timestamp, date, symbol,
                    action, action_cn, strength, strength_cn,
                    current_price, change_pct, confidence,
                    signal_strength, reasons
                FROM realtime_trading_decisions
                WHERE date >= %s 
                  AND date <= %s
                  AND action IN ('BUY', 'SELL', 'ADD', 'REDUCE')
                ORDER BY date DESC, timestamp DESC
            """
            
            results = self.db.execute_query(sql, (start_date, end_date))
            
            if not results:
                self.logger.warning(f"没有找到 {days} 天内的交易决策记录")
                return {
                    'success': False,
                    'message': f'没有找到 {days} 天内的交易决策记录',
                    'sample_count': 0
                }
            
            # 计算交易收益（根据决策时间和后续价格计算实际收益）
            total_return = 0.0
            win_count = 0
            loss_count = 0
            returns = []
            evaluated_decisions = []
            
            # 设置评估周期（决策后N天评估收益）
            evaluation_days = 5  # 默认评估5天后的收益
            
            for decision in results:
                symbol = decision.get('symbol', '')
                decision_date = decision.get('date')
                action = decision.get('action', '')
                current_price = float(decision.get('current_price', 0))
                
                if not symbol or not decision_date or current_price <= 0:
                    continue
                
                # 计算评估日期
                from datetime import date as date_type
                evaluation_date = None
                if isinstance(decision_date, date_type):
                    evaluation_date = decision_date + timedelta(days=evaluation_days)
                if not evaluation_date:
                    try:
                        if isinstance(decision_date, str):
                            evaluation_date = (datetime.strptime(decision_date, '%Y-%m-%d').date() + timedelta(days=evaluation_days))
                        else:
                            continue
                    except:
                        continue
                
                # 获取评估日期的价格（从stock_history_data表）
                price_sql = """
                    SELECT close_price
                    FROM stock_history_data
                    WHERE symbol = %s
                      AND trade_date = %s
                    ORDER BY trade_date DESC
                    LIMIT 1
                """
                price_result = self.db.execute_query(price_sql, (symbol, evaluation_date))
                
                if not price_result:
                    # 如果评估日期没有数据，尝试获取最近的日期
                    price_sql = """
                        SELECT close_price, trade_date
                        FROM stock_history_data
                        WHERE symbol = %s
                          AND trade_date >= %s
                        ORDER BY trade_date ASC
                        LIMIT 1
                    """
                    price_result = self.db.execute_query(price_sql, (symbol, evaluation_date))
                
                if not price_result:
                    continue
                
                future_price = float(price_result[0].get('close_price', 0))
                if future_price <= 0:
                    continue
                
                # 计算收益率
                if action in ['BUY', 'ADD']:
                    # 买入决策：计算买入后的收益率
                    return_pct = (future_price - current_price) / current_price * 100
                    returns.append(return_pct)
                    total_return += return_pct
                    
                    evaluated_decisions.append({
                        'symbol': symbol,
                        'date': decision_date,
                        'action': action,
                        'entry_price': current_price,
                        'exit_price': future_price,
                        'return_pct': return_pct,
                        'days': evaluation_days
                    })
                    
                    if return_pct > 0:
                        win_count += 1
                    elif return_pct < 0:
                        loss_count += 1
                
                elif action in ['SELL', 'REDUCE']:
                    # 卖出决策：计算如果未卖出可能产生的亏损（反向评估）
                    # 假设如果未卖出，继续持有到评估日期
                    return_pct = (future_price - current_price) / current_price * 100
                    # 卖出决策如果后续价格下跌，说明决策正确（避免了亏损）
                    # 如果后续价格上涨，说明可能卖早了（错失了收益）
                    # 这里我们计算"避免了多少损失"或"错失了多少收益"
                    returns.append(-return_pct)  # 反向计算
                    total_return += (-return_pct)
                    
                    evaluated_decisions.append({
                        'symbol': symbol,
                        'date': decision_date,
                        'action': action,
                        'entry_price': current_price,
                        'exit_price': future_price,
                        'return_pct': -return_pct,  # 反向计算
                        'days': evaluation_days
                    })
                    
                    # 卖出决策：如果后续价格下跌，说明决策正确（避免了亏损，视为盈利）
                    if return_pct < 0:
                        win_count += 1
                    elif return_pct > 0:
                        loss_count += 1
            
            # 计算平均收益率
            avg_return = total_return / len(evaluated_decisions) if evaluated_decisions else 0.0
            
            # 计算胜率
            win_rate = win_count / (win_count + loss_count) if (win_count + loss_count) > 0 else 0.0
            
            performance_result = {
                'success': True,
                'evaluation_date': end_date.strftime('%Y-%m-%d'),
                'evaluation_type': 'trading',
                'time_period': f'{days}d',
                'sample_count': len(results),
                'evaluated_count': len(evaluated_decisions),
                'evaluation_days': evaluation_days,
                'total_return': round(total_return, 2),  # 总收益率（百分比）
                'avg_return': round(avg_return, 2),  # 平均收益率（百分比）
                'win_rate': round(win_rate, 4),
                'win_count': win_count,
                'loss_count': loss_count,
                'returns': [round(r, 2) for r in returns[:50]],  # 只返回前50个收益数据
                'details': {
                    'action_distribution': self._get_action_distribution(results),
                    'evaluated_decisions': evaluated_decisions[:20]  # 只返回前20个决策详情
                }
            }
            
            # 保存到数据库
            self._save_performance_record(performance_result)
            
            return performance_result
            
        except Exception as e:
            self.logger.error(f"评估交易性能失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'评估失败: {str(e)}'
            }
    
    def _calculate_factor_contributions(self, start_date, end_date, prediction_results) -> Dict:
        """计算因子贡献度"""
        try:
            # 从prediction_factors表获取因子数据
            sql = """
                SELECT 
                    symbol, date,
                    technical_score, news_score, capital_flow_score,
                    market_score, sector_rotation_score, history_score,
                    us_sector_score, valuation_score
                FROM prediction_factors
                WHERE date >= %s AND date <= %s
            """
            
            factor_results = self.db.execute_query(sql, (start_date, end_date))
            
            if not factor_results:
                return {}
            
            # 按预测结果分组，计算各因子的平均得分
            hit_predictions = {r['symbol']: r for r in prediction_results if r.get('prediction_hit') == '命中'}
            miss_predictions = {r['symbol']: r for r in prediction_results if r.get('prediction_hit') == '未命中'}
            
            hit_factors = []
            miss_factors = []
            
            for fr in factor_results:
                symbol = fr.get('symbol', '')
                if symbol in hit_predictions:
                    hit_factors.append(fr)
                elif symbol in miss_predictions:
                    miss_factors.append(fr)
            
            # 计算各因子的平均得分差异
            contributions = {}
            factor_names = ['technical', 'news', 'capital_flow', 'market', 
                          'sector_rotation', 'history', 'us_sector', 'valuation']
            
            for factor_name in factor_names:
                score_key = f'{factor_name}_score'
                
                hit_scores = [float(f.get(score_key, 0)) for f in hit_factors if f.get(score_key) is not None]
                miss_scores = [float(f.get(score_key, 0)) for f in miss_factors if f.get(score_key) is not None]
                
                if hit_scores and miss_scores:
                    hit_avg = sum(hit_scores) / len(hit_scores)
                    miss_avg = sum(miss_scores) / len(miss_scores)
                    diff = hit_avg - miss_avg
                    contributions[factor_name] = round(diff, 4)
            
            return contributions
            
        except Exception as e:
            self.logger.warning(f"计算因子贡献度失败: {str(e)}")
            return {}
    
    def _identify_market_condition(self, start_date, end_date) -> str:
        """识别市场状态"""
        try:
            # 从market_sentiment表获取市场情绪数据
            sql = """
                SELECT trend, score
                FROM market_sentiment
                WHERE date >= %s AND date <= %s
                ORDER BY date DESC
                LIMIT 30
            """
            
            results = self.db.execute_query(sql, (start_date, end_date))
            
            if not results:
                return 'unknown'
            
            # 简单判断：根据trend和score判断市场状态
            trends = [r.get('trend', 'neutral') for r in results]
            scores = [float(r.get('score', 0)) for r in results if r.get('score') is not None]
            
            if scores:
                avg_score = sum(scores) / len(scores)
                if avg_score > 0.6:
                    return 'bull'
                elif avg_score < 0.4:
                    return 'bear'
                else:
                    return 'sideways'
            
            return 'sideways'
            
        except Exception as e:
            self.logger.warning(f"识别市场状态失败: {str(e)}")
            return 'unknown'
    
    def _get_action_distribution(self, results: List[Dict]) -> Dict:
        """获取操作分布"""
        distribution = {}
        for r in results:
            action = r.get('action', 'UNKNOWN')
            distribution[action] = distribution.get(action, 0) + 1
        return distribution
    
    def _save_performance_record(self, performance_result: Dict):
        """保存性能记录到数据库"""
        try:
            sql = """
                INSERT INTO model_performance
                (evaluation_date, evaluation_type, time_period,
                 direction_accuracy, magnitude_mae, confidence_calibration,
                 total_return, sharpe_ratio, max_drawdown, win_rate, profit_loss_ratio,
                 factor_contributions, market_condition, sample_count, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # 处理JSON字段
            factor_contributions_json = json.dumps(performance_result.get('factor_contributions', {}), ensure_ascii=False)
            details_json = json.dumps(performance_result.get('details', {}), ensure_ascii=False)
            confidence_calibration = performance_result.get('confidence_calibration', {})
            if isinstance(confidence_calibration, dict):
                confidence_calibration_json = json.dumps(confidence_calibration, ensure_ascii=False)
            else:
                confidence_calibration_json = None
            
            params = (
                performance_result.get('evaluation_date'),
                performance_result.get('evaluation_type'),
                performance_result.get('time_period'),
                performance_result.get('direction_accuracy'),
                performance_result.get('magnitude_mae'),
                confidence_calibration_json,
                performance_result.get('total_return'),
                performance_result.get('sharpe_ratio'),
                performance_result.get('max_drawdown'),
                performance_result.get('win_rate'),
                performance_result.get('profit_loss_ratio'),
                factor_contributions_json,
                performance_result.get('market_condition'),
                performance_result.get('sample_count'),
                details_json
            )
            
            self.db.execute_update(sql, params)
            self.logger.info(f"性能记录已保存: {performance_result.get('evaluation_type')} - {performance_result.get('time_period')}")
            
        except Exception as e:
            self.logger.error(f"保存性能记录失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def evaluate_comprehensive_performance(self, days: int = 30) -> Dict:
        """
        多指标综合评估
        
        Args:
            days: 评估时间范围（天数）
            
        Returns:
            综合评估结果字典（包含多个指标的综合评分）
        """
        try:
            # 获取基础评估结果
            prediction_result = self.evaluate_prediction_performance(days=days)
            trading_result = self.evaluate_trading_performance(days=days)
            
            if not prediction_result.get('success'):
                return prediction_result
            
            # 提取各项指标
            direction_accuracy = prediction_result.get('direction_accuracy', 0)
            magnitude_mae = prediction_result.get('magnitude_mae', 0)
            confidence_calibration = prediction_result.get('confidence_calibration', {})
            
            # 计算置信度校准得分（期望高置信度对应高准确率）
            calibration_score = 0.0
            if confidence_calibration:
                high_conf_accuracy = confidence_calibration.get('high', 0)
                medium_conf_accuracy = confidence_calibration.get('medium', 0)
                low_conf_accuracy = confidence_calibration.get('low', 0)
                
                # 理想情况下：high > medium > low
                if high_conf_accuracy >= medium_conf_accuracy >= low_conf_accuracy:
                    calibration_score = 1.0
                elif high_conf_accuracy >= medium_conf_accuracy:
                    calibration_score = 0.7
                elif high_conf_accuracy >= low_conf_accuracy:
                    calibration_score = 0.5
                else:
                    calibration_score = 0.3
            
            # 计算幅度误差得分（误差越小得分越高）
            magnitude_score = max(0, 1 - magnitude_mae / 5.0)  # 假设最大误差为5%
            
            # 计算综合得分（加权平均）
            weights = {
                'direction': 0.4,  # 方向准确率权重40%
                'magnitude': 0.3,  # 幅度准确率权重30%
                'calibration': 0.3  # 置信度校准权重30%
            }
            
            comprehensive_score = (
                direction_accuracy * weights['direction'] +
                magnitude_score * weights['magnitude'] +
                calibration_score * weights['calibration']
            )
            
            # 计算交易性能得分（如果有交易数据）
            trading_score = 0.0
            if trading_result.get('success') and trading_result.get('evaluated_count', 0) > 0:
                win_rate = trading_result.get('win_rate', 0)
                avg_return = trading_result.get('avg_return', 0)
                
                # 交易得分 = 胜率 * 0.5 + 平均收益率得分 * 0.5
                return_score = min(1.0, max(0, (avg_return + 10) / 20))  # 将-10%到+10%映射到0-1
                trading_score = win_rate * 0.5 + return_score * 0.5
            
            return {
                'success': True,
                'evaluation_date': prediction_result.get('evaluation_date'),
                'time_period': f'{days}d',
                'comprehensive_score': round(comprehensive_score, 4),
                'trading_score': round(trading_score, 4) if trading_score > 0 else None,
                'metrics': {
                    'direction_accuracy': round(direction_accuracy, 4),
                    'magnitude_mae': round(magnitude_mae, 4),
                    'magnitude_score': round(magnitude_score, 4),
                    'calibration_score': round(calibration_score, 4),
                    'confidence_calibration': confidence_calibration
                },
                'weights': weights,
                'prediction_details': prediction_result,
                'trading_details': trading_result if trading_result.get('success') else None
            }
            
        except Exception as e:
            self.logger.error(f"综合评估失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'综合评估失败: {str(e)}'
            }
    
    def evaluate_by_market_state(self, days: int = 30) -> Dict:
        """
        分市场状态评估
        
        Args:
            days: 评估时间范围（天数）
            
        Returns:
            按市场状态分组的评估结果
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 查询预测记录，包含市场状态
            sql = """
                SELECT 
                    sp.symbol, sp.name, sp.prediction_date, sp.target_date,
                    sp.prediction, sp.up_probability, sp.down_probability, sp.confidence,
                    sp.actual_price, sp.actual_change_pct, sp.actual_direction, sp.prediction_hit,
                    sp.current_price, sp.predicted_close_price, sp.predicted_change_pct,
                    NULL as market_state
                FROM stock_predictions sp
                WHERE sp.target_date >= %s 
                  AND sp.target_date <= %s
                  AND sp.actual_price IS NOT NULL
                  AND sp.prediction_hit IS NOT NULL
                ORDER BY sp.target_date DESC
            """
            
            results = self.db.execute_query(sql, (start_date, end_date))
            
            if not results:
                return {
                    'success': False,
                    'message': f'没有找到 {days} 天内的预测记录'
                }
            
            # 按市场状态分组
            # 如果market_state字段不存在，所有记录都归为'unknown'
            market_states = {}
            for r in results:
                market_state = r.get('market_state') or 'unknown'
                if market_state not in market_states:
                    market_states[market_state] = []
                market_states[market_state].append(r)
            
            # 对每个市场状态进行评估
            evaluation_by_state = {}
            for state, state_results in market_states.items():
                total_count = len(state_results)
                hit_count = sum(1 for r in state_results if r.get('prediction_hit') == '命中')
                direction_accuracy = hit_count / total_count if total_count > 0 else 0.0
                
                # 计算幅度误差
                magnitude_errors = []
                for r in state_results:
                    if r.get('predicted_change_pct') is not None and r.get('actual_change_pct') is not None:
                        predicted_change = float(r.get('predicted_change_pct', 0))
                        actual_change = float(r.get('actual_change_pct', 0))
                        error = abs(predicted_change - actual_change)
                        magnitude_errors.append(error)
                
                magnitude_mae = sum(magnitude_errors) / len(magnitude_errors) if magnitude_errors else 0.0
                
                # 计算置信度分布
                confidences = [float(r.get('confidence', 0)) for r in state_results if r.get('confidence') is not None]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                evaluation_by_state[state] = {
                    'sample_count': total_count,
                    'direction_accuracy': round(direction_accuracy, 4),
                    'magnitude_mae': round(magnitude_mae, 4),
                    'avg_confidence': round(avg_confidence, 4),
                    'hit_count': hit_count,
                    'miss_count': total_count - hit_count
                }
            
            return {
                'success': True,
                'evaluation_date': end_date.strftime('%Y-%m-%d'),
                'time_period': f'{days}d',
                'evaluation_by_state': evaluation_by_state,
                'total_samples': len(results)
            }
            
        except Exception as e:
            self.logger.error(f"分市场状态评估失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'分市场状态评估失败: {str(e)}'
            }
    
    def evaluate_confidence_calibration(self, days: int = 30, bins: int = 10) -> Dict:
        """
        置信度校准评估（更详细的校准分析）
        
        Args:
            days: 评估时间范围（天数）
            bins: 置信度分箱数量
            
        Returns:
            置信度校准评估结果
        """
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 查询预测记录
            sql = """
                SELECT 
                    confidence, prediction_hit
                FROM stock_predictions
                WHERE target_date >= %s 
                  AND target_date <= %s
                  AND prediction_hit IS NOT NULL
                  AND confidence IS NOT NULL
                ORDER BY confidence DESC
            """
            
            results = self.db.execute_query(sql, (start_date, end_date))
            
            if not results:
                return {
                    'success': False,
                    'message': f'没有找到 {days} 天内的预测记录'
                }
            
            # 将置信度分箱
            confidences = [float(r.get('confidence', 0)) for r in results]
            min_conf = min(confidences) if confidences else 0
            max_conf = max(confidences) if confidences else 1
            
            bin_width = (max_conf - min_conf) / bins if max_conf > min_conf else 1.0 / bins
            
            bins_data = {}
            for i in range(bins):
                bin_start = min_conf + i * bin_width
                bin_end = min_conf + (i + 1) * bin_width
                bins_data[i] = {
                    'range': (bin_start, bin_end),
                    'predictions': [],
                    'hits': [],
                    'count': 0,
                    'hit_count': 0
                }
            
            # 分配预测到各个箱
            for r in results:
                confidence = float(r.get('confidence', 0))
                is_hit = (r.get('prediction_hit') == '命中')
                
                # 找到对应的箱
                bin_idx = min(int((confidence - min_conf) / bin_width), bins - 1)
                bins_data[bin_idx]['predictions'].append(confidence)
                bins_data[bin_idx]['hits'].append(is_hit)
                bins_data[bin_idx]['count'] += 1
                if is_hit:
                    bins_data[bin_idx]['hit_count'] += 1
            
            # 计算每个箱的校准度
            calibration_data = []
            for i in range(bins):
                bin_info = bins_data[i]
                if bin_info['count'] > 0:
                    avg_confidence = sum(bin_info['predictions']) / len(bin_info['predictions'])
                    actual_accuracy = bin_info['hit_count'] / bin_info['count']
                    calibration_error = abs(avg_confidence - actual_accuracy)
                    
                    calibration_data.append({
                        'bin': i,
                        'confidence_range': bin_info['range'],
                        'avg_confidence': round(avg_confidence, 4),
                        'actual_accuracy': round(actual_accuracy, 4),
                        'calibration_error': round(calibration_error, 4),
                        'sample_count': bin_info['count']
                    })
            
            # 计算总体校准误差（Expected Calibration Error, ECE）
            ece = 0.0
            total_samples = len(results)
            for bin_info in calibration_data:
                weight = bin_info['sample_count'] / total_samples if total_samples > 0 else 0
                ece += weight * bin_info['calibration_error']
            
            # 计算最大校准误差（Maximum Calibration Error, MCE）
            mce = max([bin_info['calibration_error'] for bin_info in calibration_data], default=0.0)
            
            return {
                'success': True,
                'evaluation_date': end_date.strftime('%Y-%m-%d'),
                'time_period': f'{days}d',
                'total_samples': total_samples,
                'bins': bins,
                'expected_calibration_error': round(ece, 4),
                'max_calibration_error': round(mce, 4),
                'calibration_bins': calibration_data,
                'calibration_quality': 'excellent' if ece < 0.05 else ('good' if ece < 0.1 else ('fair' if ece < 0.2 else 'poor'))
            }
            
        except Exception as e:
            self.logger.error(f"置信度校准评估失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'置信度校准评估失败: {str(e)}'
            }


if __name__ == '__main__':
    # 测试代码
    evaluator = ModelPerformanceEvaluator()
    
    print("=" * 60)
    print("测试预测性能评估")
    print("=" * 60)
    result = evaluator.evaluate_prediction_performance(days=30)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("测试交易性能评估")
    print("=" * 60)
    result2 = evaluator.evaluate_trading_performance(days=30)
    print(json.dumps(result2, indent=2, ensure_ascii=False))
