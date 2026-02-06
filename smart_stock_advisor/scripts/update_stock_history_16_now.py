#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票数据获取脚本：从2026-01-16号到现在（优化版）

优化说明：
- 使用 StockHistoryCollector.collect_stock_history_data() 方法
- 自动检查缺失的日期，只获取缺失的数据
- 使用批量模式减少API调用，避免API限制
- 支持多线程并发处理
"""
import os
import sys
from datetime import datetime, timedelta
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage

logger = get_logger(__name__)


def update_stock_history_16_now(symbols: list = None, max_workers: int = 10, delay: float = 1.0,
                                 start_date: str = '2026-01-16', end_date: str = None):
    """
    获取从2026-01-16号到现在的股票数据（优化版）
    
    使用 StockHistoryCollector.collect_stock_history_data() 方法：
    - 自动检查缺失的日期，只获取缺失的数据
    - 使用批量模式减少API调用，避免API限制
    - 支持多线程并发处理
    
    Args:
        symbols: 股票代码列表（如果为None，则从数据库获取所有已有数据的股票）
        max_workers: 最大并发线程数（默认10，设置为1则使用单线程模式）
        delay: 每只股票之间的延迟（秒，默认1.0，用于避免API限制）
        start_date: 开始日期（格式：YYYY-MM-DD），默认 '2026-01-16'
        end_date: 结束日期（格式：YYYY-MM-DD），如果为None则使用今天
    """
    try:
        logger.info("=" * 60)
        logger.info("股票数据获取脚本：从2026-01-16号到现在（优化版）")
        logger.info("=" * 60)
        
        # 计算日期范围
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        days_diff = (end_date_obj - start_date_obj).days
        years = days_diff / 365.0  # 转换为年数
        
        logger.info(f"目标日期范围: {start_date} 到 {end_date}")
        logger.info(f"时间跨度: {days_diff} 天（约 {years:.2f} 年）")
        
        # 初始化收集器和存储对象
        collector = StockHistoryCollector()
        storage = StockHistoryStorage()
        
        # 如果未指定股票列表，从数据库获取所有已有数据的股票
        if symbols is None:
            sql = "SELECT DISTINCT symbol FROM stock_history_data"
            results = storage.db.execute_query(sql)
            symbols = [r['symbol'] for r in results]
            logger.info(f"从数据库获取到 {len(symbols)} 只股票")
        
        logger.info(f"需要更新 {len(symbols)} 只股票的数据")
        logger.info(f"使用 {max_workers} 个线程并发处理，每只股票延迟 {delay} 秒")
        logger.info("=" * 60)
        
        # 使用 StockHistoryCollector.collect_stock_history_data() 方法
        # 该方法会自动检查缺失的日期，并使用批量模式减少API调用
        start_time = datetime.now()
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        # 多线程处理函数
        def collect_single_stock(symbol: str) -> dict:
            """收集单只股票的数据"""
            try:
                # 每个线程创建自己的收集器实例（避免线程安全问题）
                thread_collector = StockHistoryCollector()
                
                # 使用 collect_stock_history_data 方法
                # 该方法会自动检查缺失的日期，只获取缺失的数据
                result = thread_collector.collect_stock_history_data(
                    symbol=symbol,
                    years=years,  # 转换为年数
                    force_refresh=False,  # 不强制刷新，只收集缺失的数据
                    use_batch_mode=True  # 使用批量模式提升效率，减少API调用
                )
                
                success_records = result.get('success_count', 0)
                fail_records = result.get('fail_count', 0)
                
                if success_records > 0:
                    logger.info(f"  ✓ {symbol}: 成功采集 {success_records} 条记录，失败 {fail_records} 条")
                    return {
                        'success': True,
                        'symbol': symbol,
                        'success_count': success_records,
                        'fail_count': fail_records
                    }
                elif result.get('message') == '数据已完整':
                    logger.debug(f"  - {symbol}: 数据已完整，无需采集")
                    return {
                        'success': True,
                        'symbol': symbol,
                        'success_count': 0,
                        'fail_count': 0,
                        'skipped': True
                    }
                else:
                    logger.warning(f"  ✗ {symbol}: {result.get('message', '未知错误')}")
                    return {
                        'success': False,
                        'symbol': symbol,
                        'success_count': 0,
                        'fail_count': fail_records,
                        'message': result.get('message', '未知错误')
                    }
            except Exception as e:
                logger.error(f"  ✗ {symbol}: 处理异常: {str(e)}")
                return {
                    'success': False,
                    'symbol': symbol,
                    'success_count': 0,
                    'fail_count': 0,
                    'message': str(e)
                }
        
        # 使用线程池并行处理
        logger.info(f"开始多线程处理 {len(symbols)} 只股票...")
        success_lock = Lock()
        fail_lock = Lock()
        skip_lock = Lock()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_symbol = {
                executor.submit(collect_single_stock, symbol): symbol
                for symbol in symbols
            }
            
            # 处理完成的任务
            completed = 0
            for future in as_completed(future_to_symbol):
                completed += 1
                symbol = future_to_symbol[future]
                
                try:
                    result = future.result()
                    
                    if result.get('skipped', False):
                        with skip_lock:
                            skip_count += 1
                    elif result.get('success', False):
                        with success_lock:
                            success_count += result.get('success_count', 0)
                        with fail_lock:
                            fail_count += result.get('fail_count', 0)
                    else:
                        with fail_lock:
                            fail_count += 1
                    
                    # 每50只股票或最后一只打印进度
                    if completed % 50 == 0 or completed == len(symbols):
                        logger.info(f"进度: {completed}/{len(symbols)} ({completed*100//len(symbols)}%) - 成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}")
                    
                    # 延迟，避免API限制（只在多线程模式下）
                    if max_workers > 1 and completed < len(symbols):
                        time.sleep(delay)
                        
                except Exception as e:
                    with fail_lock:
                        fail_count += 1
                    logger.error(f"  [异常] {symbol}: {str(e)}")
        
        total_duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            'start_date': start_date,
            'end_date': end_date,
            'years': years,
            'total_symbols': len(symbols),
            'success_count': success_count,
            'fail_count': fail_count,
            'skip_count': skip_count,
            'total_duration_seconds': total_duration
        }
        
        logger.info("=" * 60)
        logger.info("股票数据获取脚本执行完成")
        logger.info(f"  开始日期: {start_date}")
        logger.info(f"  结束日期: {end_date}")
        logger.info(f"  时间跨度: {years:.2f} 年")
        logger.info(f"  股票数量: {len(symbols)}")
        logger.info(f"  成功: {success_count} 条记录")
        logger.info(f"  失败: {fail_count} 条记录")
        logger.info(f"  跳过: {skip_count} 只股票（数据已完整）")
        logger.info(f"  总耗时: {total_duration:.2f}秒 ({total_duration/60:.2f}分钟)")
        logger.info("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"脚本执行失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='股票数据获取脚本：从2026-01-16号到现在（优化版）')
    parser.add_argument('--symbols', type=str, nargs='+', help='股票代码列表（可选，如果不指定则更新所有股票）')
    parser.add_argument('--symbol', type=str, help='单个股票代码（可选）')
    parser.add_argument('--threads', type=int, default=10, help='最大并发线程数（默认10，设置为1则使用单线程模式）')
    parser.add_argument('--delay', type=float, default=1.0, help='每只股票之间的延迟（秒，默认1.0，用于避免API限制）')
    parser.add_argument('--start-date', type=str, default='2026-01-16', help='开始日期（格式：YYYY-MM-DD，默认2026-01-16）')
    parser.add_argument('--end-date', type=str, default=None, help='结束日期（格式：YYYY-MM-DD，如果不指定则使用今天）')
    
    args = parser.parse_args()
    
    symbols = None
    if args.symbols:
        symbols = args.symbols
    elif args.symbol:
        symbols = [args.symbol]
    
    update_stock_history_16_now(
        symbols=symbols, 
        max_workers=args.threads, 
        delay=args.delay,
        start_date=args.start_date,
        end_date=args.end_date
    )
