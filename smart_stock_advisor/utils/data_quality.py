"""
数据质量保证模块

本模块提供数据质量检查和验证功能，用于检测和标识数据中的异常、不一致和错误。
主要应用于股票数据、新闻数据等业务数据的质量保证。

主要功能：
- 异常值检测：使用IQR、Z分数等方法检测离群值
- 数据完整性检查：检查必需字段是否存在、非空
- 数据合理性检查：检查数值范围、日期格式等是否符合预期
- 数据一致性检查：检查数据间的关系和约束是否满足
- 数据时效性检查：检查数据是否过期或过于陈旧

检测方法：
- IQR（四分位距）：基于统计学方法检测离群值
- Z分数：基于标准差的离群值检测
- 范围检查：检查数值是否在合理范围内
- 格式验证：检查日期、字符串等格式是否正确

使用示例：
    ```python
    from utils.data_quality import DataQualityChecker
    
    checker = DataQualityChecker()
    
    # 检测离群值
    outliers = checker.detect_outliers(prices, method='iqr')
    
    # 检查数据完整性
    issues = checker.check_completeness(data_dict, required_fields=['symbol', 'price'])
    
    # 检查数据合理性
    is_valid = checker.check_reasonableness(price, min_value=0, max_value=1000)
    ```

作者：Smart Stock Advisor Team
创建日期：2024
最后更新：2024
"""
import os
import sys
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)


class DataQualityChecker:
    """
    数据质量检查器
    
    提供各种数据质量检查和验证功能，用于确保数据的正确性、完整性和一致性。
    
    主要功能：
    - 异常值检测：使用统计方法检测数据中的离群值
    - 完整性检查：检查必需字段是否存在
    - 合理性检查：检查数据值是否在合理范围内
    - 一致性检查：检查数据间的关系是否一致
    - 时效性检查：检查数据是否及时更新
    
    应用场景：
    - 股票数据入库前的质量检查
    - 数据更新时的验证
    - 定期数据质量审计
    """
    
    def __init__(self):
        """
        初始化数据质量检查器
        
        初始化数据库连接和日志记录器。
        """
        self.logger = logger
        self.db = DBConnection()
        self.use_database = USE_DATABASE
    
    def detect_outliers(self, values: List[float], method: str = 'iqr') -> List[int]:
        """
        检测离群值（异常值）
        
        使用统计学方法检测数据序列中的离群值，返回离群值在原列表中的索引。
        
        Args:
            values: 数值列表，需要检测的数据序列
            method: 检测方法，可选值：
                - 'iqr': 四分位距方法（默认），基于Q1-1.5*IQR和Q3+1.5*IQR
                - 'zscore': Z分数方法，基于标准差，|Z| > 3视为离群值
                - 'isolation': 隔离森林方法（需要scikit-learn，暂未实现）
        
        Returns:
            List[int]: 离群值在原列表中的索引列表，如果数据不足或检测失败返回空列表
        
        Note:
            - 数据点少于3个时无法检测，返回空列表
            - IQR方法：离群值定义为 < Q1-1.5*IQR 或 > Q3+1.5*IQR 的值
            - Z分数方法：离群值定义为 |Z| > 3 的值
        """
        if not values or len(values) < 3:
            return []
        
        try:
            values_arr = np.array(values)
            outliers = []
            
            if method == 'iqr':
                # 使用四分位距方法
                Q1 = np.percentile(values_arr, 25)
                Q3 = np.percentile(values_arr, 75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = [i for i, v in enumerate(values) if v < lower_bound or v > upper_bound]
            
            elif method == 'zscore':
                # 使用Z分数方法
                mean = np.mean(values_arr)
                std = np.std(values_arr)
                if std > 0:
                    z_scores = np.abs((values_arr - mean) / std)
                    outliers = [i for i, z in enumerate(z_scores) if z > 3]  # Z分数 > 3
            
            return outliers
            
        except Exception as e:
            self.logger.error(f"检测离群值失败: {str(e)}")
            return []
    
    def check_data_completeness(self, data: Dict, required_fields: List[str]) -> Dict:
        """
        检查数据完整性
        
        Args:
            data: 数据字典
            required_fields: 必需字段列表
        
        Returns:
            完整性检查结果: {'complete': bool, 'missing_fields': List[str], 'completeness_rate': float}
        """
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                missing_fields.append(field)
        
        completeness_rate = (len(required_fields) - len(missing_fields)) / len(required_fields) if required_fields else 1.0
        
        return {
            'complete': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'completeness_rate': completeness_rate
        }
    
    def check_data_reasonableness(self, value: float, min_value: float = None, 
                                  max_value: float = None, expected_range: Tuple[float, float] = None) -> bool:
        """
        检查数据合理性
        
        Args:
            value: 数值
            min_value: 最小值
            max_value: 最大值
            expected_range: 预期范围 (min, max)
        
        Returns:
            是否合理
        """
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return False
        
        if expected_range:
            min_value, max_value = expected_range
        
        if min_value is not None and value < min_value:
            return False
        
        if max_value is not None and value > max_value:
            return False
        
        return True
    
    def check_data_consistency(self, data1: Dict, data2: Dict, key_fields: List[str]) -> Dict:
        """
        检查数据一致性
        
        Args:
            data1: 数据1
            data2: 数据2
            key_fields: 关键字段列表（用于比较）
        
        Returns:
            一致性检查结果: {'consistent': bool, 'inconsistent_fields': List[str], 'consistency_rate': float}
        """
        inconsistent_fields = []
        
        for field in key_fields:
            val1 = data1.get(field)
            val2 = data2.get(field)
            
            # 如果两者都为None，视为一致
            if val1 is None and val2 is None:
                continue
            
            # 如果只有一个为None，视为不一致
            if val1 is None or val2 is None:
                inconsistent_fields.append(field)
                continue
            
            # 数值比较（允许小的误差）
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                if abs(val1 - val2) > 0.01:  # 允许0.01的误差
                    inconsistent_fields.append(field)
            elif val1 != val2:
                inconsistent_fields.append(field)
        
        consistency_rate = (len(key_fields) - len(inconsistent_fields)) / len(key_fields) if key_fields else 1.0
        
        return {
            'consistent': len(inconsistent_fields) == 0,
            'inconsistent_fields': inconsistent_fields,
            'consistency_rate': consistency_rate
        }
    
    def check_data_timeliness(self, timestamp: datetime, max_age_hours: int = 24) -> bool:
        """
        检查数据时效性
        
        Args:
            timestamp: 时间戳
            max_age_hours: 最大年龄（小时）
        
        Returns:
            是否及时
        """
        if timestamp is None:
            return False
        
        age = (datetime.now() - timestamp).total_seconds() / 3600  # 转换为小时
        return age <= max_age_hours
    
    def generate_data_quality_report(self, table_name: str, date_field: str = 'created_at', 
                                    days: int = 7) -> Dict:
        """
        生成数据质量报告
        
        Args:
            table_name: 表名
            date_field: 日期字段名
            days: 查询天数
        
        Returns:
            数据质量报告
        """
        if not self.use_database:
            return {'success': False, 'message': '数据库未启用'}
        
        try:
            start_date = (datetime.now() - timedelta(days=days)).date()
            
            # 查询数据
            sql = f"""
                SELECT COUNT(*) as total_count,
                       COUNT(DISTINCT {date_field}) as date_count,
                       MIN({date_field}) as min_date,
                       MAX({date_field}) as max_date
                FROM {table_name}
                WHERE {date_field} >= %s
            """
            
            result = self.db.execute_query(sql, (start_date,))
            
            if not result:
                return {'success': False, 'message': '查询失败'}
            
            stats = result[0]
            total_count = stats.get('total_count', 0)
            date_count = stats.get('date_count', 0)
            
            # 计算数据质量指标
            quality_score = min(100, (date_count / days) * 100) if days > 0 else 0
            
            return {
                'success': True,
                'table_name': table_name,
                'time_period': f'{days} days',
                'total_count': total_count,
                'date_count': date_count,
                'min_date': stats.get('min_date'),
                'max_date': stats.get('max_date'),
                'quality_score': round(quality_score, 2),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"生成数据质量报告失败: {str(e)}")
            return {'success': False, 'message': str(e)}


# 全局数据质量检查器实例
_data_quality_checker = None
_quality_checker_lock = threading.Lock()


def get_data_quality_checker() -> DataQualityChecker:
    """获取全局数据质量检查器实例（单例模式）"""
    global _data_quality_checker
    
    if _data_quality_checker is None:
        with _quality_checker_lock:
            if _data_quality_checker is None:
                _data_quality_checker = DataQualityChecker()
    
    return _data_quality_checker
