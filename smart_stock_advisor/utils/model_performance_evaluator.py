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
            
            # 查询有实际结果的预测记录
            sql = """
                SELECT 
                    symbol, name, prediction_date, target_date,
                    prediction, up_probability, down_probability, confidence,
                    actual_price, actual_change_pct, actual_direction, prediction_hit,
                    current_price
                FROM stock_predictions
                WHERE target_date >= %s 
                  AND target_date <= %s
                  AND actual_price IS NOT NULL
                  AND prediction_hit IS NOT NULL
                ORDER BY target_date DESC
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
            magnitude_errors = []
            for r in results:
                if r.get('actual_change_pct') is not None:
                    # 根据预测方向估算预测涨跌幅
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
