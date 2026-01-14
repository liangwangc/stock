#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试批量保存历史数据功能
"""

import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.stock_history_storage import StockHistoryStorage
from utils.logger import get_logger

logger = get_logger(__name__)


def test_batch_save():
    """测试批量保存功能"""
    try:
        logger.info("=" * 60)
        logger.info("开始测试批量保存历史数据功能")
        logger.info("=" * 60)
        
        storage = StockHistoryStorage()
        
        # 创建测试数据（历史数据格式，41个字段）
        test_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        test_data = [
            ('000001', test_date, {
                'name': '平安银行',
                'period_type': 'daily',
                'open_price': 10.50,
                'close_price': 10.60,
                'high_price': 10.70,
                'low_price': 10.40,
                'pre_close': 10.50,
                'change_amount': 0.10,
                'change_pct': 0.95,
                'volume': 1000000,
                'amount': 10600000,
                'volume_ratio': 1.2,
                'cost_distribution': {},
                'cost_distribution_history': {},
                'pe_ratio': 5.5,
                'pb_ratio': 0.8,
                'limit_up': 11.55,
                'limit_down': 9.45,
                'limit_pct': 10.0,
                'is_limit_up': False,
                'is_limit_down': False,
                'amplitude': 2.86,
                'price_range': 0.30,
                'ma5': 10.55,
                'ma10': 10.50,
                'ma20': 10.45,
                'ma60': 10.40,
                'rsi': 55.0,
                'x2': 0.5,
                'macd': 0.05,
                'macd_signal': 0.03,
                'macd_hist': 0.02,
                'margin_balance': 100000000,
                'short_balance': 50000000,
                'margin_ratio': 2.0,
                'extra_data': {},
                'data_source': 'akshare',
                'data_quality_score': 1.0,
                'is_valid': True
            })
        ]
        
        logger.info(f"\n测试数据: 股票000001，日期{test_date}")
        logger.info(f"数据字段数: {len(test_data[0][2])}")
        
        # 执行批量保存
        logger.info("\n执行批量保存...")
        result = storage.save_stock_daily_data_batch(test_data, batch_size=200)
        
        logger.info("\n" + "=" * 60)
        logger.info("测试结果:")
        logger.info("=" * 60)
        logger.info(f"成功数量: {result.get('success_count', 0)}")
        logger.info(f"失败数量: {result.get('fail_count', 0)}")
        logger.info(f"总数量: {result.get('total_count', 0)}")
        
        if result.get('success_count', 0) > 0:
            logger.info("\n✅ 测试成功！批量保存功能正常")
            return True
        else:
            logger.error("\n❌ 测试失败！批量保存未成功")
            return False
            
    except Exception as e:
        logger.error(f"\n❌ 测试异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = test_batch_save()
    sys.exit(0 if success else 1)
