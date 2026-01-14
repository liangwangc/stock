"""
市场状态识别模块
用于识别当前市场状态（牛市/熊市/震荡市），并根据市场状态调整策略
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

logger = get_logger(__name__)


class MarketStateIdentifier:
    """市场状态识别器"""
    
    def __init__(self):
        self.logger = logger
        
        # 市场状态识别阈值配置
        self.config = {
            # 趋势判断
            'trend_period': 20,           # 趋势判断周期（天）
            'bull_trend_threshold': 0.02, # 牛市趋势阈值（20日均线涨幅>2%）
            'bear_trend_threshold': -0.02, # 熊市趋势阈值（20日均线跌幅<-2%）
            
            # 成交量判断
            'volume_ratio_threshold': 1.2, # 成交量放大倍数（>1.2表示放量）
            
            # 波动率判断
            'volatility_period': 20,      # 波动率计算周期
            'high_volatility_threshold': 0.03, # 高波动率阈值（日波动率>3%）
            'low_volatility_threshold': 0.015, # 低波动率阈值（日波动率<1.5%）
            
            # 涨跌天数比例
            'bull_up_days_ratio': 0.6,   # 牛市上涨天数比例（>60%）
            'bear_down_days_ratio': 0.6, # 熊市下跌天数比例（>60%）
        }
    
    def identify_market_state(self, index_data: pd.DataFrame, 
                             market_index_name: str = '上证指数') -> Dict:
        """
        识别市场状态
        
        Args:
            index_data: 大盘指数数据（包含close, volume等列）
            market_index_name: 指数名称
        
        Returns:
            市场状态字典：
            {
                'state': 'bull_market'/'bear_market'/'sideways',
                'confidence': 0.0-1.0,
                'trend': 'up'/'down'/'neutral',
                'volatility': 'high'/'medium'/'low',
                'volume_trend': 'increasing'/'decreasing'/'stable',
                'indicators': {...},
                'description': '市场状态描述'
            }
        """
        if index_data is None or index_data.empty or len(index_data) < self.config['trend_period']:
            return {
                'state': 'unknown',
                'confidence': 0.0,
                'trend': 'neutral',
                'volatility': 'medium',
                'volume_trend': 'stable',
                'indicators': {},
                'description': '数据不足，无法识别市场状态'
            }
        
        # 1. 计算趋势
        trend_info = self._calculate_trend(index_data)
        
        # 2. 计算波动率
        volatility_info = self._calculate_volatility(index_data)
        
        # 3. 计算成交量趋势
        volume_info = self._calculate_volume_trend(index_data)
        
        # 4. 计算涨跌天数比例
        up_down_ratio = self._calculate_up_down_ratio(index_data)
        
        # 5. 综合判断市场状态
        market_state = self._judge_market_state(
            trend_info, volatility_info, volume_info, up_down_ratio
        )
        
        # 6. 计算置信度
        confidence = self._calculate_state_confidence(
            trend_info, volatility_info, volume_info, up_down_ratio
        )
        
        # 7. 生成描述
        description = self._generate_state_description(
            market_state, trend_info, volatility_info, volume_info
        )
        
        return {
            'state': market_state,
            'confidence': confidence,
            'trend': trend_info['trend'],
            'volatility': volatility_info['level'],
            'volume_trend': volume_info['trend'],
            'indicators': {
                'trend_score': trend_info['score'],
                'volatility_score': volatility_info['score'],
                'volume_ratio': volume_info['ratio'],
                'up_days_ratio': up_down_ratio['up_ratio']
            },
            'description': description
        }
    
    def _calculate_trend(self, data: pd.DataFrame) -> Dict:
        """计算趋势"""
        if 'close' not in data.columns:
            return {'trend': 'neutral', 'score': 0.0}
        
        period = self.config['trend_period']
        recent_data = data.tail(period)
        
        # 计算20日均线
        ma20 = recent_data['close'].rolling(window=period).mean()
        
        # 计算趋势（当前价格相对于20日均线的涨幅）
        current_price = recent_data['close'].iloc[-1]
        ma20_value = ma20.iloc[-1]
        
        if pd.isna(ma20_value) or ma20_value == 0:
            return {'trend': 'neutral', 'score': 0.0}
        
        trend_pct = (current_price - ma20_value) / ma20_value
        
        # 判断趋势方向
        if trend_pct > self.config['bull_trend_threshold']:
            trend = 'up'
            score = min(1.0, (trend_pct - self.config['bull_trend_threshold']) * 10)
        elif trend_pct < self.config['bear_trend_threshold']:
            trend = 'down'
            score = max(-1.0, (trend_pct - self.config['bear_trend_threshold']) * 10)
        else:
            trend = 'neutral'
            score = 0.0
        
        return {
            'trend': trend,
            'score': score,
            'trend_pct': trend_pct
        }
    
    def _calculate_volatility(self, data: pd.DataFrame) -> Dict:
        """计算波动率"""
        if 'close' not in data.columns:
            return {'level': 'medium', 'score': 0.0}
        
        period = self.config['volatility_period']
        recent_data = data.tail(period)
        
        # 计算日收益率
        returns = recent_data['close'].pct_change().dropna()
        
        if len(returns) == 0:
            return {'level': 'medium', 'score': 0.0}
        
        # 计算波动率（标准差）
        volatility = returns.std()
        
        # 判断波动率水平
        if volatility > self.config['high_volatility_threshold']:
            level = 'high'
            score = min(1.0, (volatility - self.config['high_volatility_threshold']) * 20)
        elif volatility < self.config['low_volatility_threshold']:
            level = 'low'
            score = max(-1.0, (volatility - self.config['low_volatility_threshold']) * 20)
        else:
            level = 'medium'
            score = 0.0
        
        return {
            'level': level,
            'score': score,
            'volatility': volatility
        }
    
    def _calculate_volume_trend(self, data: pd.DataFrame) -> Dict:
        """计算成交量趋势"""
        if 'volume' not in data.columns:
            return {'trend': 'stable', 'ratio': 1.0}
        
        period = self.config['trend_period']
        recent_data = data.tail(period)
        
        # 计算平均成交量
        avg_volume = recent_data['volume'].mean()
        
        # 最近5天的平均成交量
        recent_volume = recent_data['volume'].tail(5).mean()
        
        if avg_volume == 0:
            return {'trend': 'stable', 'ratio': 1.0}
        
        # 成交量比率
        volume_ratio = recent_volume / avg_volume
        
        # 判断成交量趋势
        if volume_ratio > self.config['volume_ratio_threshold']:
            trend = 'increasing'
        elif volume_ratio < 1.0 / self.config['volume_ratio_threshold']:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'ratio': volume_ratio
        }
    
    def _calculate_up_down_ratio(self, data: pd.DataFrame) -> Dict:
        """计算涨跌天数比例"""
        if 'close' not in data.columns:
            return {'up_ratio': 0.5, 'down_ratio': 0.5}
        
        period = self.config['trend_period']
        recent_data = data.tail(period)
        
        # 计算涨跌天数
        price_changes = recent_data['close'].diff()
        up_days = (price_changes > 0).sum()
        down_days = (price_changes < 0).sum()
        total_days = up_days + down_days
        
        if total_days == 0:
            return {'up_ratio': 0.5, 'down_ratio': 0.5}
        
        up_ratio = up_days / total_days
        down_ratio = down_days / total_days
        
        return {
            'up_ratio': up_ratio,
            'down_ratio': down_ratio
        }
    
    def _judge_market_state(self, trend_info: Dict, volatility_info: Dict,
                           volume_info: Dict, up_down_ratio: Dict) -> str:
        """综合判断市场状态"""
        trend = trend_info['trend']
        volatility = volatility_info['level']
        volume_trend = volume_info['trend']
        up_ratio = up_down_ratio['up_ratio']
        down_ratio = up_down_ratio['down_ratio']
        
        # 牛市判断条件
        bull_conditions = [
            trend == 'up',
            volatility in ['low', 'medium'],
            volume_trend in ['increasing', 'stable'],
            up_ratio >= self.config['bull_up_days_ratio']
        ]
        
        # 熊市判断条件
        bear_conditions = [
            trend == 'down',
            volatility == 'high',
            volume_trend in ['increasing', 'stable'],
            down_ratio >= self.config['bear_down_days_ratio']
        ]
        
        # 牛市：趋势向上 + 低波动 + 放量/稳定 + 上涨天数多
        if sum(bull_conditions) >= 3:
            return 'bull_market'
        
        # 熊市：趋势向下 + 高波动 + 放量/稳定 + 下跌天数多
        elif sum(bear_conditions) >= 3:
            return 'bear_market'
        
        # 震荡市：其他情况
        else:
            return 'sideways'
    
    def _calculate_state_confidence(self, trend_info: Dict, volatility_info: Dict,
                                   volume_info: Dict, up_down_ratio: Dict) -> float:
        """计算市场状态判断的置信度"""
        confidence_factors = []
        
        # 趋势强度（绝对值越大，置信度越高）
        trend_confidence = min(abs(trend_info['score']), 1.0)
        confidence_factors.append(trend_confidence * 0.4)
        
        # 波动率一致性（波动率水平与状态一致时置信度高）
        volatility_score = abs(volatility_info['score'])
        confidence_factors.append(volatility_score * 0.2)
        
        # 成交量趋势一致性
        volume_confidence = abs(volume_info['ratio'] - 1.0) * 2  # 成交量变化越大，置信度越高
        volume_confidence = min(volume_confidence, 1.0)
        confidence_factors.append(volume_confidence * 0.2)
        
        # 涨跌天数比例一致性
        up_ratio = up_down_ratio['up_ratio']
        down_ratio = up_down_ratio['down_ratio']
        ratio_confidence = max(abs(up_ratio - 0.5), abs(down_ratio - 0.5)) * 2
        ratio_confidence = min(ratio_confidence, 1.0)
        confidence_factors.append(ratio_confidence * 0.2)
        
        # 综合置信度
        confidence = sum(confidence_factors)
        return max(0.0, min(1.0, confidence))
    
    def _generate_state_description(self, state: str, trend_info: Dict,
                                   volatility_info: Dict, volume_info: Dict) -> str:
        """生成市场状态描述"""
        trend = trend_info['trend']
        volatility = volatility_info['level']
        volume_trend = volume_info['trend']
        
        state_names = {
            'bull_market': '牛市',
            'bear_market': '熊市',
            'sideways': '震荡市',
            'unknown': '未知'
        }
        
        state_name = state_names.get(state, '未知')
        
        descriptions = {
            'bull_market': f"{state_name}：趋势向上，波动率{volatility}，成交量{volume_info['trend']}",
            'bear_market': f"{state_name}：趋势向下，波动率高，成交量{volume_info['trend']}",
            'sideways': f"{state_name}：趋势{trend}，波动率{volatility}，成交量{volume_info['trend']}",
            'unknown': "数据不足，无法判断市场状态"
        }
        
        return descriptions.get(state, "无法判断市场状态")
    
    def get_weight_adjustment(self, market_state: Dict) -> Dict:
        """
        根据市场状态获取权重调整建议
        
        Args:
            market_state: 市场状态字典
        
        Returns:
            权重调整字典，例如：
            {
                'technical_weight_multiplier': 1.2,
                'news_weight_multiplier': 0.8,
                ...
            }
        """
        state = market_state.get('state', 'sideways')
        confidence = market_state.get('confidence', 0.5)
        
        # 默认权重倍数（不调整）
        multipliers = {
            'technical_weight_multiplier': 1.0,
            'news_weight_multiplier': 1.0,
            'capital_flow_weight_multiplier': 1.0,
            'market_weight_multiplier': 1.0,
        }
        
        if state == 'bull_market':
            # 牛市：增加技术指标权重（技术分析在牛市中更有效）
            # 降低新闻权重（情绪主导，新闻影响相对较小）
            multipliers['technical_weight_multiplier'] = 1.2
            multipliers['news_weight_multiplier'] = 0.8
            multipliers['capital_flow_weight_multiplier'] = 1.1
        elif state == 'bear_market':
            # 熊市：增加新闻和政策权重（政策面影响大）
            # 降低技术指标权重（技术分析在熊市中失效更快）
            multipliers['technical_weight_multiplier'] = 0.8
            multipliers['news_weight_multiplier'] = 1.3
            multipliers['capital_flow_weight_multiplier'] = 1.2
            multipliers['market_weight_multiplier'] = 1.1
        else:
            # 震荡市：平衡各因素权重
            multipliers['technical_weight_multiplier'] = 1.0
            multipliers['news_weight_multiplier'] = 1.0
            multipliers['capital_flow_weight_multiplier'] = 1.0
        
        # 根据置信度调整调整幅度（置信度低时调整幅度小）
        for key in multipliers:
            if multipliers[key] != 1.0:
                adjustment = multipliers[key] - 1.0
                multipliers[key] = 1.0 + adjustment * confidence
        
        return multipliers
