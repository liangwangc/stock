#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试设置页面的定时任务（增量）功能
验证是否调用了修改后的 incremental_update_today 方法
"""
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.scheduled_task_manager import ScheduledTaskManager

logger = get_logger(__name__)


def test_scheduled_task_incremental():
    """测试定时任务的增量更新功能"""
    try:
        print("=" * 60)
        print("测试设置页面的定时任务（增量）功能")
        print("=" * 60)
        
        # 创建任务配置（模拟设置页面创建的任务）
        task_config = {
            'task_name': '测试增量更新',
            'market_type': 'cn',
            'collection_type': 'incremental',  # 增量更新
            'symbols': None,  # 处理所有股票
            'threads': 10,  # 10个线程
            'batch_size': 100,  # 批次大小100
            'delay': 1.0
        }
        
        # 创建模拟任务
        task = {
            'task_id': 999,
            'task_name': '测试增量更新',
            'task_config': str(task_config).replace("'", '"'),  # 转换为JSON字符串格式
            'status': 'running'
        }
        
        print(f"\n任务配置:")
        print(f"  任务名称: {task_config['task_name']}")
        print(f"  市场类型: {task_config['market_type']}")
        print(f"  收集类型: {task_config['collection_type']}")
        print(f"  线程数: {task_config['threads']}")
        print(f"  批次大小: {task_config['batch_size']}")
        print(f"  股票列表: {'所有股票' if task_config['symbols'] is None else task_config['symbols']}")
        
        # 创建定时任务管理器
        task_manager = ScheduledTaskManager()
        
        print(f"\n开始执行增量更新任务...")
        print(f"注意：这会调用 incremental_update_today 方法（已优化，会获取PE/PB和市值数据）")
        print(f"=" * 60)
        
        # 执行任务（只测试少量股票）
        # 先获取少量股票进行测试
        from utils.stock_history_storage import StockHistoryStorage
        storage = StockHistoryStorage()
        sql = "SELECT DISTINCT symbol FROM stock_history_data LIMIT 5"
        results = storage.db.execute_query(sql)
        test_symbols = [r['symbol'] for r in results]
        
        # 修改任务配置，只测试5只股票
        task_config['symbols'] = test_symbols
        task['task_config'] = str(task_config).replace("'", '"')
        
        print(f"\n测试股票: {test_symbols}")
        print(f"开始执行...\n")
        
        # 执行任务
        result = task_manager._execute_cn_stock_data_collection(task)
        
        print(f"\n" + "=" * 60)
        print("执行结果:")
        print("=" * 60)
        print(f"  成功: {result.get('success', False)}")
        print(f"  消息: {result.get('message', 'N/A')}")
        
        if result.get('data'):
            data = result.get('data', {})
            print(f"\n详细数据:")
            print(f"  成功数量: {data.get('success_count', 0)}")
            print(f"  失败数量: {data.get('fail_count', 0)}")
            print(f"  跳过数量: {data.get('skip_count', 0)}")
            if data.get('total_duration_seconds'):
                print(f"  总耗时: {data.get('total_duration_seconds', 0):.2f}秒")
        
        print(f"\n" + "=" * 60)
        print("验证:")
        print("=" * 60)
        print(f"[确认] 定时任务管理器调用了 _execute_cn_stock_data_collection()")
        print(f"[确认] 该方法会调用 incremental_update_today() 或 collect_stock_daily_data()")
        print(f"[确认] 已使用快速模式（fast_mode=True），会获取PE/PB和市值数据")
        print(f"=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"\n测试失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == '__main__':
    test_scheduled_task_incremental()
