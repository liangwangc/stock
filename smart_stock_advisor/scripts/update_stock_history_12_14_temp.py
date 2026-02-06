#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
临时脚本：只获取1月12-14号的数据
"""
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage

logger = get_logger(__name__)


def update_stock_history_12_14(symbols: list = None, max_workers: int = 10, batch_size: int = 100):
    """
    临时脚本：只获取1月12-14号的数据
    
    Args:
        symbols: 股票代码列表（如果为None，则更新所有股票）
        max_workers: 最大并发线程数（默认10，设置为1则使用单线程模式）
        batch_size: 批量保存的批次大小（默认100）
    """
    try:
        logger.info("=" * 60)
        logger.info("临时脚本：开始获取1月12-14号的数据")
        logger.info("=" * 60)
        
        collector = StockHistoryCollector()
        
        # 指定要获取的日期（只获取12-14号，不获取今日）
        target_dates = ['2026-01-12', '2026-01-13', '2026-01-14']
        logger.info(f"目标日期: {target_dates}")
        
        # 初始化存储对象
        storage = StockHistoryStorage()
        
        # 如果未指定股票列表，从数据库获取所有已有数据的股票
        if symbols is None:
            sql = "SELECT DISTINCT symbol FROM stock_history_data"
            results = storage.db.execute_query(sql)
            symbols = [r['symbol'] for r in results]
            logger.info(f"从数据库获取到 {len(symbols)} 只股票")
        
        logger.info(f"需要更新 {len(symbols)} 只股票的数据")
        
        # 批量查询目标日期数据已存在的股票
        existing_data_map = {}
        if len(symbols) > 0:
            logger.info(f"批量查询目标日期数据已存在的股票...")
            try:
                query_batch_size = 1000
                for query_start in range(0, len(symbols), query_batch_size):
                    query_end = min(query_start + query_batch_size, len(symbols))
                    query_batch = symbols[query_start:query_end]
                    
                    # 构建IN条件查询（查询所有目标日期）
                    placeholders = ','.join(['%s'] * len(query_batch))
                    date_placeholders = ','.join(['%s'] * len(target_dates))
                    sql = f"""
                        SELECT DISTINCT symbol, trade_date
                        FROM stock_history_data 
                        WHERE symbol IN ({placeholders}) 
                          AND trade_date IN ({date_placeholders})
                          AND period_type = 'daily'
                    """
                    params = [str(s).zfill(6) for s in query_batch] + target_dates
                    results = storage.db.execute_query(sql, tuple(params))
                    
                    for result in results:
                        symbol = str(result.get('symbol', '')).strip()
                        date = str(result.get('trade_date', ''))
                        if symbol not in existing_data_map:
                            existing_data_map[symbol] = {}
                        existing_data_map[symbol][date] = True
                
                # 找出需要处理的股票和日期组合
                pending_tasks = []  # [(symbol, date), ...]
                skip_count = 0
                
                for symbol in symbols:
                    symbol_str = str(symbol).strip()
                    for date in target_dates:
                        if existing_data_map.get(symbol_str, {}).get(date, False):
                            skip_count += 1
                        else:
                            pending_tasks.append((symbol_str, date))
                
                logger.info(f"批量查询完成: 已存在 {skip_count} 条数据，待处理 {len(pending_tasks)} 条数据（{len(set(s[0] for s in pending_tasks))} 只股票）")
            except Exception as e:
                logger.warning(f"批量查询已存在数据失败: {str(e)}，将处理所有股票的所有日期")
                # 回退：为所有股票的所有日期创建任务
                pending_tasks = [(str(s).strip(), date) for s in symbols for date in target_dates]
                skip_count = 0
        else:
            pending_tasks = []
            skip_count = 0
        
        if not pending_tasks:
            logger.info(f"所有股票的目标日期数据已存在，无需处理")
            return {
                'dates': target_dates,
                'total_symbols': len(symbols),
                'success_count': 0,
                'fail_count': 0,
                'skip_count': skip_count
            }
        
        # 执行增量更新（传入additional_dates参数，方法会自动合并今日，但我们可以通过修改逻辑来排除今日）
        # 由于方法会合并今日，我们需要修改逻辑：传入空列表，然后在方法内部特殊处理
        # 或者直接调用底层方法
        
        # 方法1：直接调用底层方法（推荐）
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from threading import Lock
        import time
        
        start_time = datetime.now()
        success_count = 0
        fail_count = 0
        collected_data = []
        data_lock = Lock()
        success_lock = Lock()
        fail_lock = Lock()
        
        def process_task(task: tuple) -> dict:
            """处理单个任务的工作函数（symbol, date）"""
            symbol, date = task
            try:
                # 采集数据（使用快速模式，跳过不必要的API调用）
                data = collector.collect_stock_daily_data(symbol, date, fast_mode=True)
                
                if data:
                    # 添加到批量保存列表
                    with data_lock:
                        collected_data.append((symbol, date, data))
                    return {'success': True, 'symbol': symbol, 'date': date}
                else:
                    with fail_lock:
                        fail_count += 1
                    return {'success': False, 'symbol': symbol, 'date': date, 'message': '数据采集失败'}
                    
            except Exception as e:
                with fail_lock:
                    fail_count += 1
                logger.error(f"{symbol} {date} 更新异常: {str(e)}")
                return {'success': False, 'symbol': symbol, 'date': date, 'message': str(e)}
        
        # 使用线程池并行处理
        logger.info(f"开始多线程处理 {len(pending_tasks)} 个任务（{len(set(s[0] for s in pending_tasks))} 只股票，{len(target_dates)} 个日期）...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(process_task, task): task
                for task in pending_tasks
            }
            
            # 处理完成的任务
            completed = 0
            for future in as_completed(future_to_task):
                completed += 1
                task = future_to_task[future]
                try:
                    result = future.result()
                    if result.get('success', False):
                        with success_lock:
                            success_count += 1
                        if completed % 100 == 0 or completed == len(pending_tasks):
                            logger.info(f"进度: {completed}/{len(pending_tasks)} ({completed*100//len(pending_tasks)}%)")
                    else:
                        logger.debug(f"  [失败] {result.get('symbol')} {result.get('date')}: {result.get('message', '未知错误')}")
                except Exception as e:
                    with fail_lock:
                        fail_count += 1
                    logger.error(f"  [异常] {task[0]} {task[1]}: {str(e)}")
        
        # 批量保存数据
        if collected_data:
            logger.info(f"开始批量保存 {len(collected_data)} 条数据...")
            save_result = storage.save_stock_daily_data_batch(
                collected_data, 
                batch_size=batch_size,
                skip_existence_check=True  # 已经检查过了，跳过存在性检查
            )
            
            # 更新成功和失败计数
            actual_success = save_result.get('success_count', 0)
            actual_fail = save_result.get('fail_count', 0)
            
            # 如果批量保存有失败，调整计数
            if actual_success < len(collected_data):
                success_count = actual_success
                fail_count += (len(collected_data) - actual_success)
            
            logger.info(f"批量保存完成: 成功 {actual_success}, 失败 {actual_fail}")
        
        total_duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            'dates': target_dates,
            'total_symbols': len(symbols),
            'success_count': success_count,
            'fail_count': fail_count,
            'skip_count': skip_count,
            'total_duration_seconds': total_duration
        }
        
        logger.info("=" * 60)
        logger.info("临时脚本执行完成")
        logger.info(f"  日期: {result.get('dates', target_dates)}")
        logger.info(f"  股票数量: {result.get('total_symbols', 0)}")
        logger.info(f"  成功: {result.get('success_count', 0)}")
        logger.info(f"  失败: {result.get('fail_count', 0)}")
        logger.info(f"  跳过: {result.get('skip_count', 0)}")
        if result.get('total_duration_seconds'):
            logger.info(f"  总耗时: {result.get('total_duration_seconds', 0):.2f}秒")
        logger.info("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"临时脚本执行异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='临时脚本：只获取1月12-14号的数据')
    parser.add_argument('--symbols', type=str, nargs='+', help='股票代码列表（可选，如果不指定则更新所有股票）')
    parser.add_argument('--symbol', type=str, help='单个股票代码（可选）')
    parser.add_argument('--threads', type=int, default=10, help='最大并发线程数（默认10，设置为1则使用单线程模式）')
    parser.add_argument('--batch-size', type=int, default=100, help='批量保存的批次大小（默认100）')
    
    args = parser.parse_args()
    
    symbols = None
    if args.symbols:
        symbols = args.symbols
    elif args.symbol:
        symbols = [args.symbol]
    
    update_stock_history_12_14(symbols, max_workers=args.threads, batch_size=args.batch_size)
