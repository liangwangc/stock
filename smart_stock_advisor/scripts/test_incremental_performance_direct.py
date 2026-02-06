#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试增量更新性能（不检查数据是否存在）
"""
import os
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage

logger = get_logger(__name__)


def test_batch_performance_direct(symbols, max_workers=10):
    """直接测试批量更新性能（不检查数据是否存在）"""
    print("=" * 60)
    print("直接测试批量更新性能")
    print(f"股票数量: {len(symbols)}, 线程数: {max_workers}")
    print("=" * 60)
    
    collector = StockHistoryCollector()
    storage = StockHistoryStorage()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 收集数据
    collected_data = []
    success_count = 0
    fail_count = 0
    
    def process_symbol(symbol):
        """处理单只股票"""
        try:
            start_time = time.time()
            # 使用快速模式采集数据
            data = collector.collect_stock_daily_data(symbol, today, fast_mode=True)
            collect_time = time.time() - start_time
            
            if data:
                return {
                    'symbol': symbol,
                    'success': True,
                    'data': data,
                    'collect_time': collect_time
                }
            else:
                return {
                    'symbol': symbol,
                    'success': False,
                    'collect_time': collect_time
                }
        except Exception as e:
            return {
                'symbol': symbol,
                'success': False,
                'error': str(e)
            }
    
    # 多线程采集数据
    start_time = time.time()
    print(f"\n开始多线程采集 {len(symbols)} 只股票的数据...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(process_symbol, symbol): symbol
            for symbol in symbols
        }
        
        completed = 0
        for future in as_completed(future_to_symbol):
            completed += 1
            result = future.result()
            
            if result.get('success', False):
                collected_data.append((result['symbol'], today, result['data']))
                success_count += 1
                if completed % 5 == 0 or completed == len(symbols):
                    print(f"进度: {completed}/{len(symbols)} ({completed*100//len(symbols)}%) - 成功: {success_count}, 失败: {fail_count}")
            else:
                fail_count += 1
                if completed <= 10:  # 只显示前10个失败
                    print(f"  [失败] {result['symbol']}: {result.get('error', '数据采集失败')}")
    
    collect_total_time = time.time() - start_time
    
    # 批量保存数据
    save_start_time = time.time()
    if collected_data:
        print(f"\n开始批量保存 {len(collected_data)} 条数据...")
        save_result = storage.save_stock_daily_data_batch(
            collected_data,
            batch_size=100,
            skip_existence_check=True
        )
        save_time = time.time() - save_start_time
        
        actual_success = save_result.get('success_count', 0)
        actual_fail = save_result.get('fail_count', 0)
        
        print(f"批量保存完成: 成功 {actual_success}, 失败 {actual_fail}, 耗时: {save_time:.2f}秒")
    else:
        save_time = 0
    
    total_time = time.time() - start_time
    
    # 输出结果
    print("\n" + "=" * 60)
    print("性能测试结果:")
    print("=" * 60)
    print(f"股票数量: {len(symbols)}")
    print(f"线程数: {max_workers}")
    print(f"成功采集: {success_count}")
    print(f"失败: {fail_count}")
    print(f"\n时间统计:")
    print(f"  数据采集总耗时: {collect_total_time:.2f}秒 ({collect_total_time/60:.2f}分钟)")
    print(f"  数据保存耗时: {save_time:.2f}秒")
    print(f"  总耗时: {total_time:.2f}秒 ({total_time/60:.2f}分钟)")
    
    if success_count > 0:
        avg_collect_time = collect_total_time / success_count
        avg_total_time = total_time / success_count
        print(f"\n平均每只股票:")
        print(f"  采集耗时: {avg_collect_time:.2f}秒")
        print(f"  总耗时: {avg_total_time:.2f}秒")
        
        # 性能估算
        print(f"\n性能估算（100只股票，{max_workers}线程）:")
        estimated_time = (total_time / success_count) * 100 / max_workers
        print(f"  预计耗时: {estimated_time:.2f}秒 ({estimated_time/60:.2f}分钟)")
    
    return {
        'total_symbols': len(symbols),
        'success_count': success_count,
        'fail_count': fail_count,
        'collect_time': collect_total_time,
        'save_time': save_time,
        'total_time': total_time
    }


if __name__ == '__main__':
    # 从数据库获取20只股票
    storage = StockHistoryStorage()
    sql = "SELECT DISTINCT symbol FROM stock_history_data LIMIT 20"
    results = storage.db.execute_query(sql)
    symbols = [r['symbol'] for r in results]
    
    print(f"测试股票: {symbols[:10]}... (共{len(symbols)}只)")
    
    # 测试批量更新性能
    result = test_batch_performance_direct(symbols, max_workers=10)
