#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试增量更新性能，分析性能瓶颈

用法:
    python scripts/test_incremental_update_performance.py --symbols 000001 600519 --test-count 10
    python scripts/test_incremental_update_performance.py --all --test-count 20
"""
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List
import statistics

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage
from data_source.stock_data_source import StockDataSource

logger = get_logger(__name__)


class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.timings = {}
        self.api_call_times = []
        self.db_query_times = []
        self.data_processing_times = []
        self.save_times = []
        
    def start_timer(self, name: str):
        """开始计时"""
        self.timings[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        """结束计时并返回耗时（秒）"""
        if name in self.timings:
            elapsed = time.time() - self.timings[name]
            del self.timings[name]
            return elapsed
        return 0.0
    
    def record_api_call(self, duration: float):
        """记录API调用耗时"""
        self.api_call_times.append(duration)
    
    def record_db_query(self, duration: float):
        """记录数据库查询耗时"""
        self.db_query_times.append(duration)
    
    def record_data_processing(self, duration: float):
        """记录数据处理耗时"""
        self.data_processing_times.append(duration)
    
    def record_save(self, duration: float):
        """记录保存耗时"""
        self.save_times.append(duration)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {}
        
        if self.api_call_times:
            stats['api_calls'] = {
                'count': len(self.api_call_times),
                'total': sum(self.api_call_times),
                'avg': statistics.mean(self.api_call_times),
                'min': min(self.api_call_times),
                'max': max(self.api_call_times),
                'median': statistics.median(self.api_call_times)
            }
        
        if self.db_query_times:
            stats['db_queries'] = {
                'count': len(self.db_query_times),
                'total': sum(self.db_query_times),
                'avg': statistics.mean(self.db_query_times),
                'min': min(self.db_query_times),
                'max': max(self.db_query_times),
                'median': statistics.median(self.db_query_times)
            }
        
        if self.data_processing_times:
            stats['data_processing'] = {
                'count': len(self.data_processing_times),
                'total': sum(self.data_processing_times),
                'avg': statistics.mean(self.data_processing_times),
                'min': min(self.data_processing_times),
                'max': max(self.data_processing_times),
                'median': statistics.median(self.data_processing_times)
            }
        
        if self.save_times:
            stats['save_operations'] = {
                'count': len(self.save_times),
                'total': sum(self.save_times),
                'avg': statistics.mean(self.save_times),
                'min': min(self.save_times),
                'max': max(self.save_times),
                'median': statistics.median(self.save_times)
            }
        
        return stats


def test_single_stock_performance(symbol: str, date: str, fast_mode: bool = True) -> Dict:
    """测试单只股票的性能"""
    profiler = PerformanceProfiler()
    collector = StockHistoryCollector()
    
    print(f"\n{'='*60}")
    print(f"测试股票: {symbol}, 日期: {date}, 快速模式: {fast_mode}")
    print(f"{'='*60}")
    
    # 1. 测试数据采集
    profiler.start_timer('collect_data')
    try:
        data = collector.collect_stock_daily_data(symbol, date, fast_mode=fast_mode)
        collect_time = profiler.end_timer('collect_data')
        
        if data:
            print(f"[成功] 数据采集成功，耗时: {collect_time:.2f}秒")
        else:
            print(f"[失败] 数据采集失败，耗时: {collect_time:.2f}秒")
            return {
                'symbol': symbol,
                'success': False,
                'collect_time': collect_time,
                'total_time': collect_time
            }
    except Exception as e:
        collect_time = profiler.end_timer('collect_data')
        print(f"[异常] 数据采集异常: {str(e)}, 耗时: {collect_time:.2f}秒")
        return {
            'symbol': symbol,
            'success': False,
            'error': str(e),
            'collect_time': collect_time,
            'total_time': collect_time
        }
    
    # 2. 测试数据保存
    profiler.start_timer('save_data')
    try:
        storage = StockHistoryStorage()
        save_success = storage.save_stock_daily_data(symbol, date, data)
        save_time = profiler.end_timer('save_data')
        
        if save_success:
            print(f"[成功] 数据保存成功，耗时: {save_time:.2f}秒")
        else:
            print(f"[失败] 数据保存失败，耗时: {save_time:.2f}秒")
    except Exception as e:
        save_time = profiler.end_timer('save_data')
        print(f"[异常] 数据保存异常: {str(e)}, 耗时: {save_time:.2f}秒")
        save_success = False
    
    total_time = collect_time + save_time
    
    result = {
        'symbol': symbol,
        'success': save_success,
        'collect_time': collect_time,
        'save_time': save_time,
        'total_time': total_time
    }
    
    print(f"总耗时: {total_time:.2f}秒 (采集: {collect_time:.2f}秒, 保存: {save_time:.2f}秒)")
    
    return result


def test_api_performance(symbol: str, date: str):
    """测试各个API调用的性能"""
    print(f"\n{'='*60}")
    print(f"测试API性能: {symbol}")
    print(f"{'='*60}")
    
    data_source = StockDataSource()
    api_times = {}
    
    # 1. 测试获取股票信息
    try:
        start = time.time()
        stock_info = data_source.get_stock_info(symbol)
        api_times['get_stock_info'] = time.time() - start
        print(f"get_stock_info: {api_times['get_stock_info']:.2f}秒")
    except Exception as e:
        api_times['get_stock_info'] = -1
        print(f"get_stock_info: 失败 ({str(e)})")
    
    # 2. 测试获取K线数据（当日）
    try:
        start = time.time()
        kline_data = data_source.get_stock_data(symbol, start_date=date, end_date=date)
        api_times['get_stock_data_today'] = time.time() - start
        print(f"get_stock_data (当日): {api_times['get_stock_data_today']:.2f}秒")
    except Exception as e:
        api_times['get_stock_data_today'] = -1
        print(f"get_stock_data (当日): 失败 ({str(e)})")
    
    # 3. 测试获取K线数据（前后10天）
    try:
        from datetime import timedelta
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        start_date = (date_obj - timedelta(days=10)).strftime('%Y-%m-%d')
        end_date = (date_obj + timedelta(days=10)).strftime('%Y-%m-%d')
        start = time.time()
        kline_data = data_source.get_stock_data(symbol, start_date=start_date, end_date=end_date)
        api_times['get_stock_data_21days'] = time.time() - start
        print(f"get_stock_data (21天): {api_times['get_stock_data_21days']:.2f}秒")
    except Exception as e:
        api_times['get_stock_data_21days'] = -1
        print(f"get_stock_data (21天): 失败 ({str(e)})")
    
    # 4. 测试获取实时行情
    try:
        start = time.time()
        realtime_quote = data_source.get_realtime_quote(symbol)
        api_times['get_realtime_quote'] = time.time() - start
        print(f"get_realtime_quote: {api_times['get_realtime_quote']:.2f}秒")
    except Exception as e:
        api_times['get_realtime_quote'] = -1
        print(f"get_realtime_quote: 失败 ({str(e)})")
    
    # 5. 测试获取买卖盘数据
    try:
        start = time.time()
        bid_ask = data_source.get_bid_ask_data(symbol)
        api_times['get_bid_ask_data'] = time.time() - start
        print(f"get_bid_ask_data: {api_times['get_bid_ask_data']:.2f}秒")
    except Exception as e:
        api_times['get_bid_ask_data'] = -1
        print(f"get_bid_ask_data: 失败 ({str(e)})")
    
    # 6. 测试获取成本分布
    try:
        if hasattr(data_source, 'get_cost_distribution'):
            start = time.time()
            cost_dist = data_source.get_cost_distribution(symbol)
            api_times['get_cost_distribution'] = time.time() - start
            print(f"get_cost_distribution: {api_times['get_cost_distribution']:.2f}秒")
        else:
            api_times['get_cost_distribution'] = -1
            print(f"get_cost_distribution: 方法不存在")
    except Exception as e:
        api_times['get_cost_distribution'] = -1
        print(f"get_cost_distribution: 失败 ({str(e)})")
    
    # 7. 测试获取资金流向
    try:
        if hasattr(data_source, 'get_realtime_capital_flow'):
            start = time.time()
            capital_flow = data_source.get_realtime_capital_flow(symbol)
            api_times['get_realtime_capital_flow'] = time.time() - start
            print(f"get_realtime_capital_flow: {api_times['get_realtime_capital_flow']:.2f}秒")
        else:
            api_times['get_realtime_capital_flow'] = -1
            print(f"get_realtime_capital_flow: 方法不存在")
    except Exception as e:
        api_times['get_realtime_capital_flow'] = -1
        print(f"get_realtime_capital_flow: 失败 ({str(e)})")
    
    # 8. 测试获取融资融券数据
    try:
        if hasattr(data_source, 'get_margin_trading_data'):
            start = time.time()
            margin_data = data_source.get_margin_trading_data(symbol)
            api_times['get_margin_trading_data'] = time.time() - start
            print(f"get_margin_trading_data: {api_times['get_margin_trading_data']:.2f}秒")
        else:
            api_times['get_margin_trading_data'] = -1
            print(f"get_margin_trading_data: 方法不存在")
    except Exception as e:
        api_times['get_margin_trading_data'] = -1
        print(f"get_margin_trading_data: 失败 ({str(e)})")
    
    # 9. 测试数据库查询（获取历史数据）
    try:
        storage = StockHistoryStorage()
        from datetime import timedelta
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        history_start = (date_obj - timedelta(days=60)).strftime('%Y-%m-%d')
        history_end = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
        
        start = time.time()
        history_data = storage.get_stock_history_data(
            symbol=symbol,
            start_date=history_start,
            end_date=history_end,
            limit=None
        )
        api_times['db_get_history_data'] = time.time() - start
        print(f"db_get_history_data (60天): {api_times['db_get_history_data']:.2f}秒, 记录数: {len(history_data) if history_data else 0}")
    except Exception as e:
        api_times['db_get_history_data'] = -1
        print(f"db_get_history_data: 失败 ({str(e)})")
    
    return api_times


def test_batch_performance(symbols: List[str], fast_mode: bool = True, max_workers: int = 10):
    """测试批量更新的性能"""
    print(f"\n{'='*60}")
    print(f"测试批量更新性能")
    print(f"股票数量: {len(symbols)}, 快速模式: {fast_mode}, 线程数: {max_workers}")
    print(f"{'='*60}")
    
    collector = StockHistoryCollector()
    today = datetime.now().strftime('%Y-%m-%d')
    
    start_time = time.time()
    result = collector.incremental_update_today(
        symbols=symbols,
        max_workers=max_workers,
        batch_size=100
    )
    total_time = time.time() - start_time
    
    print(f"\n批量更新结果:")
    print(f"  总耗时: {total_time:.2f}秒 ({total_time/60:.2f}分钟)")
    print(f"  股票数量: {result.get('total_symbols', 0)}")
    print(f"  成功: {result.get('success_count', 0)}")
    print(f"  失败: {result.get('fail_count', 0)}")
    print(f"  跳过: {result.get('skip_count', 0)}")
    
    if result.get('success_count', 0) > 0:
        avg_time_per_stock = total_time / result.get('success_count', 1)
        print(f"  平均每只股票: {avg_time_per_stock:.2f}秒")
    
    return result


def main():
    parser = argparse.ArgumentParser(description='测试增量更新性能')
    parser.add_argument('--symbols', nargs='+', help='股票代码列表（例如: 000001 600519）')
    parser.add_argument('--all', action='store_true', help='测试所有股票（从数据库获取）')
    parser.add_argument('--test-count', type=int, default=10, help='测试股票数量（默认10）')
    parser.add_argument('--fast-mode', action='store_true', default=True, help='使用快速模式（默认True）')
    parser.add_argument('--no-fast-mode', dest='fast_mode', action='store_false', help='不使用快速模式')
    parser.add_argument('--api-test', action='store_true', help='测试各个API的性能')
    parser.add_argument('--batch-test', action='store_true', help='测试批量更新性能')
    parser.add_argument('--max-workers', type=int, default=10, help='最大线程数（默认10）')
    
    args = parser.parse_args()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print("增量更新性能测试")
    print("=" * 60)
    print(f"测试日期: {today}")
    print(f"快速模式: {args.fast_mode}")
    
    # 获取测试股票列表
    if args.all:
        # 从数据库获取所有股票
        storage = StockHistoryStorage()
        sql = "SELECT DISTINCT symbol FROM stock_history_data LIMIT %s"
        results = storage.db.execute_query(sql, (args.test_count,))
        symbols = [r['symbol'] for r in results]
        print(f"从数据库获取 {len(symbols)} 只股票")
    elif args.symbols:
        symbols = args.symbols
        print(f"使用指定的 {len(symbols)} 只股票: {symbols}")
    else:
        # 默认测试几只股票
        symbols = ['000001', '600519', '000002', '600036', '000858']
        print(f"使用默认的 {len(symbols)} 只股票: {symbols}")
    
    # 1. 测试各个API的性能
    if args.api_test or not args.batch_test:
        print("\n" + "=" * 60)
        print("1. 测试各个API的性能")
        print("=" * 60)
        
        api_results = []
        for symbol in symbols[:3]:  # 只测试前3只
            api_times = test_api_performance(symbol, today)
            api_results.append(api_times)
        
        # 汇总API性能
        if api_results:
            print("\n" + "=" * 60)
            print("API性能汇总:")
            print("=" * 60)
            
            api_names = set()
            for result in api_results:
                api_names.update(result.keys())
            
            for api_name in sorted(api_names):
                times = [r.get(api_name, -1) for r in api_results if r.get(api_name, -1) >= 0]
                if times:
                    avg_time = statistics.mean(times)
                    print(f"{api_name:30s}: 平均 {avg_time:.2f}秒 (共{len(times)}次成功)")
                else:
                    print(f"{api_name:30s}: 全部失败")
    
    # 2. 测试单只股票的性能
    if not args.batch_test:
        print("\n" + "=" * 60)
        print("2. 测试单只股票的性能")
        print("=" * 60)
        
        single_results = []
        for symbol in symbols[:args.test_count]:
            result = test_single_stock_performance(symbol, today, fast_mode=args.fast_mode)
            single_results.append(result)
            time.sleep(0.5)  # 避免请求过快
        
        # 汇总单只股票性能
        if single_results:
            print("\n" + "=" * 60)
            print("单只股票性能汇总:")
            print("=" * 60)
            
            successful = [r for r in single_results if r.get('success', False)]
            if successful:
                collect_times = [r['collect_time'] for r in successful]
                save_times = [r['save_time'] for r in successful]
                total_times = [r['total_time'] for r in successful]
                
                print(f"成功数量: {len(successful)}/{len(single_results)}")
                print(f"\n数据采集耗时:")
                print(f"  平均: {statistics.mean(collect_times):.2f}秒")
                print(f"  最小: {min(collect_times):.2f}秒")
                print(f"  最大: {max(collect_times):.2f}秒")
                print(f"  中位数: {statistics.median(collect_times):.2f}秒")
                
                print(f"\n数据保存耗时:")
                print(f"  平均: {statistics.mean(save_times):.2f}秒")
                print(f"  最小: {min(save_times):.2f}秒")
                print(f"  最大: {max(save_times):.2f}秒")
                print(f"  中位数: {statistics.median(save_times):.2f}秒")
                
                print(f"\n总耗时:")
                print(f"  平均: {statistics.mean(total_times):.2f}秒")
                print(f"  最小: {min(total_times):.2f}秒")
                print(f"  最大: {max(total_times):.2f}秒")
                print(f"  中位数: {statistics.median(total_times):.2f}秒")
                
                # 性能瓶颈分析
                print(f"\n性能瓶颈分析:")
                avg_collect = statistics.mean(collect_times)
                avg_save = statistics.mean(save_times)
                avg_total = statistics.mean(total_times)
                
                collect_pct = (avg_collect / avg_total) * 100
                save_pct = (avg_save / avg_total) * 100
                
                print(f"  数据采集占比: {collect_pct:.1f}%")
                print(f"  数据保存占比: {save_pct:.1f}%")
                
                if collect_pct > 80:
                    print(f"  [警告] 性能瓶颈: 数据采集（建议优化API调用）")
                elif save_pct > 50:
                    print(f"  [警告] 性能瓶颈: 数据保存（建议优化数据库操作）")
                else:
                    print(f"  [正常] 性能分布较均匀")
    
    # 3. 测试批量更新性能
    if args.batch_test:
        print("\n" + "=" * 60)
        print("3. 测试批量更新性能")
        print("=" * 60)
        
        test_symbols = symbols[:args.test_count]
        result = test_batch_performance(test_symbols, fast_mode=args.fast_mode, max_workers=args.max_workers)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
