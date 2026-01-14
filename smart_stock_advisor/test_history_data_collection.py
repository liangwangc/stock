#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试历史数据获取功能
"""

import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.stock_history_collector import StockHistoryCollector
from utils.logger import get_logger

logger = get_logger(__name__)


def test_history_data_collection():
    """测试历史数据获取"""
    try:
        logger.info("=" * 60)
        logger.info("开始测试历史数据获取功能")
        logger.info("=" * 60)
        
        collector = StockHistoryCollector()
        
        # 测试股票代码
        test_symbol = '000001'  # 平安银行
        
        logger.info(f"\n测试股票: {test_symbol}")
        logger.info("测试获取最近30天的历史数据...")
        
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"日期范围: {start_date_str} 至 {end_date_str}")
        
        # 获取历史数据
        result = collector.collect_stock_history_data(
            symbol=test_symbol,
            years=0,  # 不指定年份，使用日期范围
            force_refresh=False,
            use_batch_mode=True
        )
        
        logger.info("\n" + "=" * 60)
        logger.info("测试结果:")
        logger.info("=" * 60)
        logger.info(f"成功: {result.get('success', False)}")
        logger.info(f"成功数量: {result.get('saved_count', 0)}")
        logger.info(f"失败数量: {result.get('failed_count', 0)}")
        logger.info(f"总数量: {result.get('total_count', 0)}")
        
        if result.get('error'):
            logger.error(f"错误信息: {result.get('error')}")
        
        if result.get('success') and result.get('saved_count', 0) > 0:
            logger.info("\n✅ 测试成功！历史数据获取正常")
            return True
        else:
            logger.error("\n❌ 测试失败！未获取到数据")
            return False
            
    except Exception as e:
        logger.error(f"\n❌ 测试异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = test_history_data_collection()
    sys.exit(0 if success else 1)
