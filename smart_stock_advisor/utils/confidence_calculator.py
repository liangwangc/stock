"""
增强的置信度计算模块

本模块提供增强的置信度计算功能，不仅考虑基础的多因子一致性，
还结合历史准确率反馈、预测一致性检查、数据时效性影响和置信度校准，
提供更准确和可靠的置信度评估。

主要功能：
- 历史准确率反馈：根据历史预测准确率调整置信度
- 预测一致性检查：检查最近N次预测的一致性，提高稳定性
- 数据时效性影响：考虑数据的新鲜度，过期数据降低置信度
- 置信度校准：根据历史表现校准置信度，使其更接近实际准确率

置信度调整因子：
- 历史准确率因子：基于历史准确率调整（0.8-1.2）
- 一致性因子：基于预测一致性调整（0.9-1.1）
- 时效性因子：基于数据时效性调整（0.7-1.0）
- 校准调整：基于历史校准曲线调整（-0.1到+0.1）

使用示例：
    ```python
    from utils.confidence_calculator import ConfidenceCalculator
    
    calculator = ConfidenceCalculator()
    
    # 计算增强的置信度
    result = calculator.calculate_enhanced_confidence(
        base_confidence=0.75,
        final_score=0.65,
        factor_scores={'technical': 0.7, 'news': 0.6},
        symbol='000001',
        market_state={'state': 'bull'},
        data_quality={'completeness': 0.9, 'timeliness': 0.8}
    )
    
    enhanced_confidence = result['confidence']
    ```

作者：Smart Stock Advisor Team
创建日期：2024
最后更新：2024
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import defaultdict

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection, USE_DATABASE
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfidenceCalculator:
    """
    增强的置信度计算器
    
    提供增强的置信度计算功能，综合考虑多个因素来评估预测的可靠性。
    
    置信度调整机制：
    1. 历史准确率反馈：根据该股票/市场状态的历史预测准确率调整
    2. 预测一致性检查：检查最近N次预测的一致性，一致性强则提高置信度
    3. 数据时效性影响：数据越新鲜，置信度越高；过期数据降低置信度
    4. 置信度校准：根据历史校准曲线调整，使置信度更接近实际准确率
    
    性能优化：
    - 历史准确率缓存：缓存1小时，避免重复查询数据库
    - 预测历史记录：维护最近N次预测记录，用于一致性检查
    
    应用场景：
    - 股票预测置信度计算
    - 交易信号置信度评估
    - 风险评分中的置信度因子
    """
    
    def __init__(self):
        """
        初始化增强的置信度计算器
        
        初始化数据库连接、日志记录器、缓存系统和预测历史记录。
        
        Attributes:
            db: 数据库连接对象（如果数据库启用）
            logger: 日志记录器
            _accuracy_cache: 历史准确率缓存字典
            _cache_ttl: 缓存有效期（默认1小时）
            _cache_timestamp: 缓存时间戳字典
            _prediction_history: 预测历史记录，格式：{symbol: [predictions]}
            _max_history_size: 每个股票保留的最大预测历史数量（默认10次）
        """
        self.db = DatabaseConnection() if USE_DATABASE else None
        self.logger = logger
        
        # 缓存历史准确率（避免重复查询）
        self._accuracy_cache = {}
        self._cache_ttl = timedelta(hours=1)  # 缓存1小时
        self._cache_timestamp = {}
        
        # 预测一致性窗口（最近N次预测）
        self._prediction_history = defaultdict(list)
        self._max_history_size = 10
        
    def calculate_enhanced_confidence(
        self,
        base_confidence: float,
        final_score: float,
        factor_scores: Dict,
        symbol: str,
        market_state: Optional[Dict] = None,
        data_quality: Optional[Dict] = None,
        prediction_time: Optional[datetime] = None
    ) -> Dict:
        """
        计算增强的置信度（考虑历史准确率、一致性、数据时效性、校准）
        
        Args:
            base_confidence: 基础置信度（0-1）
            final_score: 最终得分
            factor_scores: 各因子得分字典
            symbol: 股票代码
            market_state: 市场状态字典（可选）
            data_quality: 数据质量信息（可选）
            prediction_time: 预测时间（可选，默认当前时间）
        
        Returns:
            增强的置信度信息字典，包含：
            - confidence: 最终置信度（0-1）
            - historical_accuracy_factor: 历史准确率调整因子
            - consistency_factor: 一致性调整因子
            - timeliness_factor: 数据时效性调整因子
            - calibration_adjustment: 校准调整量
            - details: 详细信息
        """
        if prediction_time is None:
            prediction_time = datetime.now()
        
        # 1. 获取历史准确率反馈
        historical_accuracy_factor = self._get_historical_accuracy_factor(
            symbol, market_state
        )
        
        # 2. 预测一致性检查
        consistency_factor = self._check_prediction_consistency(
            symbol, final_score, factor_scores
        )
        
        # 3. 数据时效性影响
        timeliness_factor = self._calculate_timeliness_factor(
            data_quality, prediction_time
        )
        
        # 4. 置信度校准
        calibration_adjustment = self._calculate_calibration_adjustment(
            base_confidence
        )
        
        # 综合计算最终置信度
        # 基础置信度 * 历史准确率因子 * 一致性因子 * 时效性因子 + 校准调整
        adjusted_confidence = (
            base_confidence *
            historical_accuracy_factor *
            consistency_factor *
            timeliness_factor
        ) + calibration_adjustment
        
        # 记录当前预测到历史中
        self._record_prediction(symbol, final_score, adjusted_confidence)
        
        # 确保置信度在合理范围内
        final_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        return {
            'confidence': final_confidence,
            'historical_accuracy_factor': historical_accuracy_factor,
            'consistency_factor': consistency_factor,
            'timeliness_factor': timeliness_factor,
            'calibration_adjustment': calibration_adjustment,
            'details': {
                'base_confidence': base_confidence,
                'adjusted_confidence': adjusted_confidence,
                'symbol': symbol,
                'market_state': market_state.get('state') if market_state else None,
            }
        }
    
    def _get_historical_accuracy_factor(
        self,
        symbol: str,
        market_state: Optional[Dict] = None
    ) -> float:
        """
        获取历史准确率反馈因子（按股票、按市场状态）
        
        Args:
            symbol: 股票代码
            market_state: 市场状态字典
        
        Returns:
            调整因子（0.8-1.2），基于历史准确率
        """
        if not self.db:
            return 1.0
        
        try:
            # 检查缓存
            cache_key = f"{symbol}_{market_state.get('state') if market_state else 'all'}"
            if cache_key in self._accuracy_cache:
                cache_time = self._cache_timestamp.get(cache_key)
                if cache_time and datetime.now() - cache_time < self._cache_ttl:
                    return self._accuracy_cache[cache_key]
            
            # 查询历史准确率（最近90天）
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
            
            # 基础查询：该股票的历史准确率
            base_sql = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN prediction_hit = '命中' THEN 1 ELSE 0 END) as hit_count
                FROM stock_predictions
                WHERE symbol = %s
                  AND target_date >= %s
                  AND target_date <= %s
                  AND prediction_hit IS NOT NULL
            """
            params = [symbol, start_date, end_date]
            
            # 如果有市场状态，可以进一步筛选（需要从prediction_factors表关联）
            if market_state and market_state.get('state'):
                # 简化处理：先获取整体准确率
                # 未来可以扩展为按市场状态筛选
                pass
            
            result = self.db.execute_query(base_sql, params)
            
            if result and result[0]['total'] and result[0]['total'] > 0:
                total = result[0]['total']
                hit_count = result[0]['hit_count']
                accuracy = hit_count / total
                
                # 计算调整因子
                # 准确率 > 0.6: 因子 1.1-1.2（提高置信度）
                # 准确率 0.5-0.6: 因子 1.0（不变）
                # 准确率 < 0.5: 因子 0.8-0.9（降低置信度）
                if accuracy >= 0.65:
                    factor = 1.0 + (accuracy - 0.65) * 0.57  # 0.65->1.0, 0.8->1.1, 1.0->1.2
                elif accuracy >= 0.55:
                    factor = 0.95 + (accuracy - 0.55) * 0.5  # 0.55->0.95, 0.65->1.0
                else:
                    factor = 0.8 + (accuracy - 0.3) * 0.6  # 0.3->0.8, 0.55->0.95
                
                factor = max(0.7, min(1.3, factor))  # 限制在0.7-1.3之间
                
                # 更新缓存
                self._accuracy_cache[cache_key] = factor
                self._cache_timestamp[cache_key] = datetime.now()
                
                return factor
            else:
                # 没有历史数据，使用默认值
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"获取历史准确率失败: {str(e)}")
            return 1.0
    
    def _check_prediction_consistency(
        self,
        symbol: str,
        final_score: float,
        factor_scores: Dict
    ) -> float:
        """
        检查预测一致性（多次预测的一致性）
        
        Args:
            symbol: 股票代码
            final_score: 当前预测得分
            factor_scores: 当前各因子得分
        
        Returns:
            一致性因子（0.8-1.2）
        """
        # 获取该股票的历史预测
        history = self._prediction_history.get(symbol, [])
        
        if len(history) < 2:
            # 历史数据不足，返回默认值
            return 1.0
        
        # 检查最近几次预测的方向一致性
        recent_scores = [h['score'] for h in history[-5:]]  # 最近5次
        recent_scores.append(final_score)
        
        # 计算方向一致性
        directions = [1 if s > 0 else -1 if s < 0 else 0 for s in recent_scores]
        if not directions:
            return 1.0
        
        # 计算同方向的比例
        most_common_direction = max(set(directions), key=directions.count)
        consistent_count = directions.count(most_common_direction)
        consistency_ratio = consistent_count / len(directions)
        
        # 计算调整因子
        # 一致性高（>80%）：提高置信度（1.05-1.15）
        # 一致性中等（50-80%）：不变（1.0）
        # 一致性低（<50%）：降低置信度（0.85-0.95）
        if consistency_ratio >= 0.8:
            factor = 1.0 + (consistency_ratio - 0.8) * 0.75  # 0.8->1.0, 1.0->1.15
        elif consistency_ratio >= 0.5:
            factor = 0.95 + (consistency_ratio - 0.5) * 0.17  # 0.5->0.95, 0.8->1.0
        else:
            factor = 0.85 + (consistency_ratio - 0.3) * 0.5  # 0.3->0.85, 0.5->0.95
        
        factor = max(0.8, min(1.2, factor))
        
        return factor
    
    def _calculate_timeliness_factor(
        self,
        data_quality: Optional[Dict],
        prediction_time: datetime
    ) -> float:
        """
        计算数据时效性对置信度的影响
        
        Args:
            data_quality: 数据质量信息（可选）
            prediction_time: 预测时间
        
        Returns:
            时效性因子（0.9-1.0）
        """
        # 如果没有数据质量信息，使用默认值
        if not data_quality:
            return 1.0
        
        # 检查数据的时效性
        data_timestamps = data_quality.get('timestamps', {})
        if not data_timestamps:
            return 1.0
        
        # 计算各数据源的时间差（小时）
        max_hours_old = 0
        for source, timestamp in data_timestamps.items():
            if isinstance(timestamp, str):
                try:
                    ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    continue
            elif isinstance(timestamp, datetime):
                ts = timestamp
            else:
                continue
            
            hours_old = (prediction_time - ts.replace(tzinfo=None)).total_seconds() / 3600
            max_hours_old = max(max_hours_old, hours_old)
        
        # 根据数据时效性调整因子
        # 数据很新（<1小时）：1.0（不降低）
        # 数据较新（1-6小时）：0.98-1.0
        # 数据较旧（6-24小时）：0.95-0.98
        # 数据很旧（>24小时）：0.9-0.95
        if max_hours_old < 1:
            factor = 1.0
        elif max_hours_old < 6:
            factor = 1.0 - (max_hours_old - 1) * 0.004  # 1小时->1.0, 6小时->0.98
        elif max_hours_old < 24:
            factor = 0.98 - (max_hours_old - 6) * 0.0017  # 6小时->0.98, 24小时->0.95
        else:
            factor = max(0.9, 0.95 - (max_hours_old - 24) * 0.002)  # 24小时->0.95, 48小时->0.9
        
        factor = max(0.9, min(1.0, factor))
        
        return factor
    
    def _calculate_calibration_adjustment(self, base_confidence: float) -> float:
        """
        计算置信度校准调整量
        
        基于历史数据：高置信度预测应该真的更准确
        如果历史显示高置信度预测不够准确，则降低调整
        
        Args:
            base_confidence: 基础置信度
        
        Returns:
            校准调整量（-0.1到0.1）
        """
        if not self.db:
            return 0.0
        
        try:
            # 查询历史置信度校准数据（最近90天）
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=90)
            
            sql = """
                SELECT 
                    confidence,
                    CASE WHEN prediction_hit = '命中' THEN 1 ELSE 0 END as hit
                FROM stock_predictions
                WHERE target_date >= %s
                  AND target_date <= %s
                  AND prediction_hit IS NOT NULL
                  AND confidence IS NOT NULL
                ORDER BY target_date DESC
                LIMIT 500
            """
            
            result = self.db.execute_query(sql, (start_date, end_date))
            
            if not result or len(result) < 20:
                # 数据不足，不进行调整
                return 0.0
            
            # 按置信度分组，计算每组实际准确率
            buckets = {
                'high': [],      # >= 0.7
                'medium': [],    # 0.5-0.7
                'low': []        # < 0.5
            }
            
            for r in result:
                confidence = float(r.get('confidence', 0))
                hit = r.get('hit', 0)
                
                if confidence >= 0.7:
                    buckets['high'].append(hit)
                elif confidence >= 0.5:
                    buckets['medium'].append(hit)
                else:
                    buckets['low'].append(hit)
            
            # 计算校准调整
            adjustment = 0.0
            
            if base_confidence >= 0.7:
                # 高置信度预测
                if buckets['high']:
                    actual_accuracy = sum(buckets['high']) / len(buckets['high'])
                    expected_accuracy = 0.75  # 期望准确率75%（对应0.7-0.8置信度）
                    
                    # 如果实际准确率低于期望，降低调整
                    if actual_accuracy < expected_accuracy:
                        adjustment = (actual_accuracy - expected_accuracy) * 0.3
            elif base_confidence >= 0.5:
                # 中等置信度预测
                if buckets['medium']:
                    actual_accuracy = sum(buckets['medium']) / len(buckets['medium'])
                    expected_accuracy = 0.6  # 期望准确率60%
                    
                    if actual_accuracy < expected_accuracy:
                        adjustment = (actual_accuracy - expected_accuracy) * 0.2
            else:
                # 低置信度预测
                if buckets['low']:
                    actual_accuracy = sum(buckets['low']) / len(buckets['low'])
                    expected_accuracy = 0.45  # 期望准确率45%
                    
                    if actual_accuracy > expected_accuracy:
                        # 低置信度但准确率高，可以适当提高
                        adjustment = (actual_accuracy - expected_accuracy) * 0.1
            
            # 限制调整幅度
            adjustment = max(-0.1, min(0.1, adjustment))
            
            return adjustment
            
        except Exception as e:
            self.logger.warning(f"置信度校准计算失败: {str(e)}")
            return 0.0
    
    def _record_prediction(
        self,
        symbol: str,
        final_score: float,
        confidence: float
    ):
        """
        记录预测到历史中（用于一致性检查）
        
        Args:
            symbol: 股票代码
            final_score: 最终得分
            confidence: 置信度
        """
        history = self._prediction_history.get(symbol, [])
        history.append({
            'score': final_score,
            'confidence': confidence,
            'timestamp': datetime.now()
        })
        
        # 只保留最近N次预测
        if len(history) > self._max_history_size:
            history = history[-self._max_history_size:]
        
        self._prediction_history[symbol] = history
    
    def get_calibration_report(self, days: int = 90) -> Dict:
        """
        获取置信度校准报告
        
        Args:
            days: 评估天数
        
        Returns:
            校准报告字典
        """
        if not self.db:
            return {'success': False, 'message': '数据库不可用'}
        
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            sql = """
                SELECT 
                    confidence,
                    CASE WHEN prediction_hit = '命中' THEN 1 ELSE 0 END as hit
                FROM stock_predictions
                WHERE target_date >= %s
                  AND target_date <= %s
                  AND prediction_hit IS NOT NULL
                  AND confidence IS NOT NULL
            """
            
            result = self.db.execute_query(sql, (start_date, end_date))
            
            if not result:
                return {'success': False, 'message': '没有数据'}
            
            # 按置信度区间分组
            buckets = {
                'very_high': {'range': (0.8, 1.0), 'hits': [], 'total': []},
                'high': {'range': (0.7, 0.8), 'hits': [], 'total': []},
                'medium_high': {'range': (0.6, 0.7), 'hits': [], 'total': []},
                'medium': {'range': (0.5, 0.6), 'hits': [], 'total': []},
                'low': {'range': (0.0, 0.5), 'hits': [], 'total': []},
            }
            
            for r in result:
                confidence = float(r.get('confidence', 0))
                hit = r.get('hit', 0)
                
                for bucket_name, bucket_info in buckets.items():
                    low, high = bucket_info['range']
                    if low <= confidence < high:
                        bucket_info['total'].append(confidence)
                        bucket_info['hits'].append(hit)
                        break
            
            # 计算每个区间的校准指标
            calibration_report = {}
            for bucket_name, bucket_info in buckets.items():
                if bucket_info['total']:
                    expected_accuracy = np.mean(bucket_info['total'])  # 期望准确率 = 平均置信度
                    actual_accuracy = sum(bucket_info['hits']) / len(bucket_info['hits']) if bucket_info['hits'] else 0
                    calibration_error = actual_accuracy - expected_accuracy
                    
                    calibration_report[bucket_name] = {
                        'range': f"{bucket_info['range'][0]:.1f}-{bucket_info['range'][1]:.1f}",
                        'count': len(bucket_info['total']),
                        'expected_accuracy': round(expected_accuracy, 4),
                        'actual_accuracy': round(actual_accuracy, 4),
                        'calibration_error': round(calibration_error, 4),
                        'is_well_calibrated': abs(calibration_error) < 0.1  # 误差<10%认为校准良好
                    }
            
            return {
                'success': True,
                'period_days': days,
                'total_samples': len(result),
                'calibration_by_bucket': calibration_report,
                'overall_calibration': {
                    'mean_expected': round(np.mean([float(r.get('confidence', 0)) for r in result]), 4),
                    'mean_actual': round(sum(r.get('hit', 0) for r in result) / len(result), 4) if result else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"生成校准报告失败: {str(e)}")
            return {'success': False, 'message': str(e)}


# 全局实例
_calculator_instance = None

def get_confidence_calculator() -> ConfidenceCalculator:
    """获取置信度计算器单例"""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = ConfidenceCalculator()
    return _calculator_instance
