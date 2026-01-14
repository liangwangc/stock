"""
数据质量验证工具
用于验证股票数据的完整性、合理性和时效性
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


class DataValidator:
    """数据质量验证器"""
    
    def __init__(self):
        self.logger = logger
        
        # 数据质量阈值配置
        self.config = {
            # 价格合理性
            'min_price': 0.01,  # 最低价格（元）
            'max_price': 10000,  # 最高价格（元）
            'max_price_change_pct': 20.0,  # 单日最大涨跌幅（%），正常股票为10%，ST为5%
            
            # 成交量合理性
            'min_volume': 0,  # 最低成交量
            'max_volume_ratio': 100,  # 成交量相对均值的最大倍数
            
            # 数据完整性
            'min_data_points': 30,  # 最少数据点数量
            'max_missing_ratio': 0.1,  # 最大缺失比例（10%）
            
            # 数据时效性
            'max_data_age_hours': 24,  # 数据最大年龄（小时）
            
            # 异常检测
            'outlier_z_score': 3.0,  # 异常值Z分数阈值
        }
    
    def validate_stock_data(self, data: pd.DataFrame, symbol: str = None) -> Tuple[bool, str, Dict]:
        """
        验证股票数据的质量
        
        Args:
            data: 股票数据DataFrame（包含open, high, low, close, volume等列）
            symbol: 股票代码（用于日志）
        
        Returns:
            (is_valid, message, quality_report)
            - is_valid: 数据是否有效
            - message: 验证结果消息
            - quality_report: 详细的质量报告
        """
        quality_report = {
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': [],
            'quality_score': 0.0,  # 质量得分 0-1
        }
        
        if data is None or data.empty:
            return False, "数据为空", quality_report
        
        # 1. 检查数据完整性
        completeness_result = self._check_completeness(data)
        quality_report.update(completeness_result)
        
        if not completeness_result.get('is_valid', False):
            return False, completeness_result.get('message', '数据不完整'), quality_report
        
        # 2. 检查价格合理性
        price_result = self._check_price_reasonableness(data)
        quality_report['checks_passed'] += price_result.get('checks_passed', 0)
        quality_report['checks_failed'] += price_result.get('checks_failed', 0)
        quality_report['warnings'].extend(price_result.get('warnings', []))
        quality_report['errors'].extend(price_result.get('errors', []))
        
        # 3. 检查成交量合理性
        volume_result = self._check_volume_reasonableness(data)
        quality_report['checks_passed'] += volume_result.get('checks_passed', 0)
        quality_report['checks_failed'] += volume_result.get('checks_failed', 0)
        quality_report['warnings'].extend(volume_result.get('warnings', []))
        quality_report['errors'].extend(volume_result.get('errors', []))
        
        # 4. 检查数据一致性
        consistency_result = self._check_consistency(data)
        quality_report['checks_passed'] += consistency_result.get('checks_passed', 0)
        quality_report['checks_failed'] += consistency_result.get('checks_failed', 0)
        quality_report['warnings'].extend(consistency_result.get('warnings', []))
        quality_report['errors'].extend(consistency_result.get('errors', []))
        
        # 5. 检查异常值
        outlier_result = self._check_outliers(data)
        quality_report['checks_passed'] += outlier_result.get('checks_passed', 0)
        quality_report['checks_failed'] += outlier_result.get('checks_failed', 0)
        quality_report['warnings'].extend(outlier_result.get('warnings', []))
        quality_report['errors'].extend(outlier_result.get('errors', []))
        
        # 计算质量得分
        total_checks = quality_report['checks_passed'] + quality_report['checks_failed']
        if total_checks > 0:
            quality_report['quality_score'] = quality_report['checks_passed'] / total_checks
        
        # 判断是否有效（有错误则无效，只有警告则有效但降低质量得分）
        is_valid = len(quality_report['errors']) == 0
        if is_valid:
            message = f"数据验证通过（质量得分: {quality_report['quality_score']:.2%}）"
            if quality_report['warnings']:
                message += f"，有 {len(quality_report['warnings'])} 个警告"
        else:
            message = f"数据验证失败：{quality_report['errors'][0]}"
        
        return is_valid, message, quality_report
    
    def _check_completeness(self, data: pd.DataFrame) -> Dict:
        """检查数据完整性"""
        result = {
            'is_valid': False,
            'message': '',
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': [],
        }
        
        # 检查数据点数量
        if len(data) < self.config['min_data_points']:
            result['checks_failed'] += 1
            result['errors'].append(f"数据点数量不足（{len(data)} < {self.config['min_data_points']}）")
            result['message'] = f"数据点数量不足（需要至少{self.config['min_data_points']}个）"
            return result
        
        result['checks_passed'] += 1
        
        # 检查必需列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            result['checks_failed'] += 1
            result['errors'].append(f"缺少必需列: {', '.join(missing_columns)}")
            result['message'] = f"缺少必需列: {', '.join(missing_columns)}"
            return result
        
        result['checks_passed'] += 1
        
        # 检查缺失值比例
        missing_ratio = data[required_columns].isna().sum().sum() / (len(data) * len(required_columns))
        if missing_ratio > self.config['max_missing_ratio']:
            result['checks_failed'] += 1
            result['warnings'].append(f"缺失值比例较高: {missing_ratio:.1%}（阈值: {self.config['max_missing_ratio']:.1%}）")
        else:
            result['checks_passed'] += 1
        
        result['is_valid'] = True
        result['message'] = "数据完整性检查通过"
        return result
    
    def _check_price_reasonableness(self, data: pd.DataFrame) -> Dict:
        """检查价格合理性"""
        result = {
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': [],
        }
        
        # 检查价格范围
        if 'close' in data.columns:
            prices = data['close'].dropna()
            if len(prices) > 0:
                min_price = prices.min()
                max_price = prices.max()
                
                if min_price < self.config['min_price']:
                    result['checks_failed'] += 1
                    result['errors'].append(f"价格异常低: {min_price:.2f}元（最低: {self.config['min_price']}元）")
                else:
                    result['checks_passed'] += 1
                
                if max_price > self.config['max_price']:
                    result['checks_failed'] += 1
                    result['warnings'].append(f"价格异常高: {max_price:.2f}元（最高: {self.config['max_price']}元）")
                else:
                    result['checks_passed'] += 1
                
                # 检查单日涨跌幅
                if len(prices) > 1:
                    price_changes = prices.pct_change().dropna() * 100
                    max_change = price_changes.abs().max()
                    
                    if max_change > self.config['max_price_change_pct']:
                        result['checks_failed'] += 1
                        result['warnings'].append(
                            f"单日涨跌幅异常: {max_change:.2f}%（阈值: {self.config['max_price_change_pct']}%）"
                        )
                    else:
                        result['checks_passed'] += 1
        
        return result
    
    def _check_volume_reasonableness(self, data: pd.DataFrame) -> Dict:
        """检查成交量合理性"""
        result = {
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': [],
        }
        
        if 'volume' in data.columns:
            volumes = data['volume'].dropna()
            if len(volumes) > 0:
                # 检查负成交量
                if (volumes < 0).any():
                    result['checks_failed'] += 1
                    result['errors'].append("存在负成交量")
                else:
                    result['checks_passed'] += 1
                
                # 检查成交量异常（相对于均值）
                if len(volumes) > 10:
                    mean_volume = volumes.mean()
                    if mean_volume > 0:
                        max_volume_ratio = volumes.max() / mean_volume
                        if max_volume_ratio > self.config['max_volume_ratio']:
                            result['checks_failed'] += 1
                            result['warnings'].append(
                                f"成交量异常放大: {max_volume_ratio:.1f}倍（阈值: {self.config['max_volume_ratio']}倍）"
                            )
                        else:
                            result['checks_passed'] += 1
        
        return result
    
    def _check_consistency(self, data: pd.DataFrame) -> Dict:
        """检查数据一致性（如 high >= low, high >= close 等）"""
        result = {
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': [],
        }
        
        required_cols = ['open', 'high', 'low', 'close']
        if all(col in data.columns for col in required_cols):
            # 检查 high >= low
            invalid_high_low = (data['high'] < data['low']).sum()
            if invalid_high_low > 0:
                result['checks_failed'] += 1
                result['errors'].append(f"存在 {invalid_high_low} 条记录的高价低于低价")
            else:
                result['checks_passed'] += 1
            
            # 检查 high >= close >= low
            invalid_close = ((data['close'] > data['high']) | (data['close'] < data['low'])).sum()
            if invalid_close > 0:
                result['checks_failed'] += 1
                result['errors'].append(f"存在 {invalid_close} 条记录的收盘价不在高低价范围内")
            else:
                result['checks_passed'] += 1
            
            # 检查 high >= open >= low
            invalid_open = ((data['open'] > data['high']) | (data['open'] < data['low'])).sum()
            if invalid_open > 0:
                result['checks_failed'] += 1
                result['warnings'].append(f"存在 {invalid_open} 条记录的开盘价不在高低价范围内")
            else:
                result['checks_passed'] += 1
        
        return result
    
    def _check_outliers(self, data: pd.DataFrame) -> Dict:
        """检查异常值（使用Z分数方法）"""
        result = {
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': [],
        }
        
        if 'close' in data.columns:
            prices = data['close'].dropna()
            if len(prices) > 10:
                # 计算Z分数
                mean_price = prices.mean()
                std_price = prices.std()
                
                if std_price > 0:
                    z_scores = np.abs((prices - mean_price) / std_price)
                    outliers = (z_scores > self.config['outlier_z_score']).sum()
                    
                    if outliers > 0:
                        result['checks_failed'] += 1
                        result['warnings'].append(
                            f"检测到 {outliers} 个价格异常值（Z分数 > {self.config['outlier_z_score']}）"
                        )
                    else:
                        result['checks_passed'] += 1
        
        return result
    
    def check_data_freshness(self, latest_date: datetime, max_age_hours: int = None) -> Tuple[bool, str]:
        """
        检查数据时效性
        
        Args:
            latest_date: 最新数据的日期时间
            max_age_hours: 最大年龄（小时），默认使用配置值
        
        Returns:
            (is_fresh, message)
        """
        if max_age_hours is None:
            max_age_hours = self.config['max_data_age_hours']
        
        if latest_date is None:
            return False, "数据日期为空"
        
        age_hours = (datetime.now() - latest_date).total_seconds() / 3600
        
        if age_hours > max_age_hours:
            return False, f"数据已过期 {age_hours:.1f} 小时（阈值: {max_age_hours} 小时）"
        else:
            return True, f"数据新鲜（年龄: {age_hours:.1f} 小时）"
    
    def validate_realtime_quote(self, quote: Dict) -> Tuple[bool, str, Dict]:
        """
        验证实时行情数据
        
        Args:
            quote: 实时行情字典
        
        Returns:
            (is_valid, message, quality_report)
        """
        quality_report = {
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': [],
            'errors': [],
        }
        
        if not quote:
            return False, "实时行情数据为空", quality_report
        
        # 检查必需字段
        required_fields = ['current_price', 'change_pct']
        missing_fields = [field for field in required_fields if field not in quote]
        if missing_fields:
            quality_report['errors'].append(f"缺少必需字段: {', '.join(missing_fields)}")
            return False, f"缺少必需字段: {', '.join(missing_fields)}", quality_report
        
        quality_report['checks_passed'] += 1
        
        # 检查价格合理性
        price = quote.get('current_price', 0)
        if price <= 0 or price > self.config['max_price']:
            quality_report['errors'].append(f"价格异常: {price}元")
            return False, f"价格异常: {price}元", quality_report
        
        quality_report['checks_passed'] += 1
        
        # 检查涨跌幅合理性
        change_pct = quote.get('change_pct', 0)
        if abs(change_pct) > self.config['max_price_change_pct']:
            quality_report['warnings'].append(f"涨跌幅异常: {change_pct:.2f}%")
        else:
            quality_report['checks_passed'] += 1
        
        total_checks = quality_report['checks_passed'] + quality_report['checks_failed']
        quality_report['quality_score'] = quality_report['checks_passed'] / total_checks if total_checks > 0 else 0.0
        
        is_valid = len(quality_report['errors']) == 0
        message = "实时行情数据验证通过" if is_valid else f"实时行情数据验证失败: {quality_report['errors'][0]}"
        
        return is_valid, message, quality_report
