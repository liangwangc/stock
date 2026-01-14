"""
数据质量检查器测试
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
from utils.data_quality import DataQualityChecker, get_data_quality_checker


class TestDataQualityChecker:
    """DataQualityChecker测试类"""
    
    def test_init(self):
        """测试初始化"""
        checker = DataQualityChecker()
        assert checker.use_database is not None
    
    def test_detect_outliers_iqr(self):
        """测试检测离群值（IQR方法）"""
        checker = DataQualityChecker()
        
        # 正常数据
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        outliers = checker.detect_outliers(values, method='iqr')
        assert len(outliers) == 0
        
        # 包含离群值的数据
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]  # 100是离群值
        outliers = checker.detect_outliers(values, method='iqr')
        assert len(outliers) > 0
        assert 9 in outliers  # 100的索引
    
    def test_detect_outliers_zscore(self):
        """测试检测离群值（Z分数方法）"""
        checker = DataQualityChecker()
        
        # 正常数据
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        outliers = checker.detect_outliers(values, method='zscore')
        assert len(outliers) == 0
        
        # 包含离群值的数据
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]  # 100是离群值
        outliers = checker.detect_outliers(values, method='zscore')
        assert len(outliers) > 0
    
    def test_check_data_completeness(self):
        """测试检查数据完整性"""
        checker = DataQualityChecker()
        
        # 完整数据
        data = {'field1': 'value1', 'field2': 'value2', 'field3': 'value3'}
        required_fields = ['field1', 'field2', 'field3']
        result = checker.check_data_completeness(data, required_fields)
        assert result['complete'] is True
        assert len(result['missing_fields']) == 0
        assert result['completeness_rate'] == 1.0
        
        # 不完整数据
        data = {'field1': 'value1', 'field2': None}
        result = checker.check_data_completeness(data, required_fields)
        assert result['complete'] is False
        assert 'field3' in result['missing_fields']
        assert result['completeness_rate'] < 1.0
    
    def test_check_data_reasonableness(self):
        """测试检查数据合理性"""
        checker = DataQualityChecker()
        
        # 合理数据
        assert checker.check_data_reasonableness(50, min_value=0, max_value=100) is True
        assert checker.check_data_reasonableness(50, expected_range=(0, 100)) is True
        
        # 不合理数据
        assert checker.check_data_reasonableness(150, min_value=0, max_value=100) is False
        assert checker.check_data_reasonableness(-10, min_value=0, max_value=100) is False
        
        # None值
        assert checker.check_data_reasonableness(None) is False
    
    def test_check_data_consistency(self):
        """测试检查数据一致性"""
        checker = DataQualityChecker()
        
        # 一致数据
        data1 = {'field1': 10.0, 'field2': 'value', 'field3': 100}
        data2 = {'field1': 10.0, 'field2': 'value', 'field3': 100}
        result = checker.check_data_consistency(data1, data2, ['field1', 'field2', 'field3'])
        assert result['consistent'] is True
        assert len(result['inconsistent_fields']) == 0
        assert result['consistency_rate'] == 1.0
        
        # 不一致数据
        data1 = {'field1': 10.0, 'field2': 'value1'}
        data2 = {'field1': 20.0, 'field2': 'value2'}
        result = checker.check_data_consistency(data1, data2, ['field1', 'field2'])
        assert result['consistent'] is False
        assert len(result['inconsistent_fields']) == 2
        assert result['consistency_rate'] == 0.0
    
    def test_check_data_timeliness(self):
        """测试检查数据时效性"""
        checker = DataQualityChecker()
        
        # 及时数据
        recent_timestamp = datetime.now() - timedelta(hours=12)
        assert checker.check_data_timeliness(recent_timestamp, max_age_hours=24) is True
        
        # 过期数据
        old_timestamp = datetime.now() - timedelta(hours=25)
        assert checker.check_data_timeliness(old_timestamp, max_age_hours=24) is False
        
        # None值
        assert checker.check_data_timeliness(None) is False
    
    def test_singleton(self):
        """测试单例模式"""
        checker1 = get_data_quality_checker()
        checker2 = get_data_quality_checker()
        assert checker1 is checker2
