"""
测试不同股票数据获取接口的性能
对比各种akshare接口的速度和效率
"""
import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

logger = get_logger(__name__)


def test_api_performance(api_func, api_name, symbol, start_date, end_date, **kwargs):
    """
    测试API接口的性能
    
    Args:
        api_func: API函数
        api_name: API名称
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        **kwargs: 其他参数
    
    Returns:
        (success, duration, record_count, error_msg)
    """
    try:
        start_time = time.time()
        df = api_func(symbol=symbol, start_date=start_date, end_date=end_date, **kwargs)
        duration = time.time() - start_time
        
        if df is None or df.empty:
            return False, duration, 0, "返回空数据"
        
        record_count = len(df)
        return True, duration, record_count, None
        
    except Exception as e:
        duration = time.time() - start_time if 'start_time' in locals() else 0
        return False, duration, 0, str(e)


def test_batch_api_performance(api_func, api_name, symbols, start_date, end_date, **kwargs):
    """
    测试批量API接口的性能
    
    Args:
        api_func: API函数
        api_name: API名称
        symbols: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        **kwargs: 其他参数
    
    Returns:
        (success_count, total_duration, avg_duration, total_records, errors)
    """
    success_count = 0
    total_duration = 0
    total_records = 0
    errors = []
    
    for symbol in symbols:
        success, duration, record_count, error = test_api_performance(
            api_func, api_name, symbol, start_date, end_date, **kwargs
        )
        
        total_duration += duration
        if success:
            success_count += 1
            total_records += record_count
        else:
            errors.append(f"{symbol}: {error}")
        
        # 避免请求过快
        time.sleep(0.1)
    
    avg_duration = total_duration / len(symbols) if symbols else 0
    return success_count, total_duration, avg_duration, total_records, errors


def main():
    """主测试函数"""
    print("=" * 80)
    print("股票数据获取接口性能测试")
    print("=" * 80)
    
    # 测试参数
    test_symbols = ['000001', '000002', '600000', '600519', '000858']  # 5只股票
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')  # 1年数据
    
    print(f"\n测试参数:")
    print(f"  股票代码: {test_symbols}")
    print(f"  日期范围: {start_date} 至 {end_date}")
    print(f"  数据量: 约1年历史数据")
    print()
    
    results = []
    
    # 测试1: stock_zh_a_hist (当前使用的接口)
    print("测试1: ak.stock_zh_a_hist (当前使用的接口)")
    print("-" * 80)
    try:
        success_count, total_duration, avg_duration, total_records, errors = test_batch_api_performance(
            ak.stock_zh_a_hist,
            "stock_zh_a_hist",
            test_symbols,
            start_date,
            end_date,
            period="daily",
            adjust="qfq"
        )
        
        results.append({
            'api_name': 'stock_zh_a_hist',
            'description': '股票历史行情数据（当前使用）',
            'success_count': success_count,
            'total_duration': total_duration,
            'avg_duration': avg_duration,
            'total_records': total_records,
            'errors': errors,
            'speed': total_records / total_duration if total_duration > 0 else 0
        })
        
        print(f"  成功: {success_count}/{len(test_symbols)}")
        print(f"  总耗时: {total_duration:.2f}秒")
        print(f"  平均耗时: {avg_duration:.2f}秒/股票")
        print(f"  总记录数: {total_records}")
        print(f"  速度: {results[-1]['speed']:.2f} 条记录/秒")
        if errors:
            print(f"  错误: {errors}")
    except Exception as e:
        print(f"  测试失败: {str(e)}")
        results.append({
            'api_name': 'stock_zh_a_hist',
            'description': '股票历史行情数据（当前使用）',
            'success_count': 0,
            'total_duration': 0,
            'avg_duration': 0,
            'total_records': 0,
            'errors': [str(e)],
            'speed': 0
        })
    
    print()
    
    # 测试2: stock_zh_a_hist_min_em (分钟级数据，可能更快)
    print("测试2: ak.stock_zh_a_hist_min_em (分钟级数据接口)")
    print("-" * 80)
    try:
        # 注意：这个接口可能需要不同的参数
        # 先测试单个股票
        test_symbol = test_symbols[0]
        start_time = time.time()
        try:
            df = ak.stock_zh_a_hist_min_em(symbol=test_symbol, period="1", adjust="qfq")
            duration = time.time() - start_time
            if df is not None and not df.empty:
                print(f"  单股票测试成功: {test_symbol}, 耗时: {duration:.2f}秒, 记录数: {len(df)}")
                print(f"  注意: 这是分钟级数据接口，不适合批量获取历史数据")
            else:
                print(f"  单股票测试: 返回空数据")
        except Exception as e:
            print(f"  单股票测试失败: {str(e)}")
            print(f"  注意: 此接口可能不支持或需要不同参数")
    except Exception as e:
        print(f"  接口不存在或不可用: {str(e)}")
    
    print()
    
    # 测试3: stock_zh_a_hist_pre_min_em (盘前数据)
    print("测试3: ak.stock_zh_a_hist_pre_min_em (盘前数据接口)")
    print("-" * 80)
    try:
        test_symbol = test_symbols[0]
        start_time = time.time()
        try:
            df = ak.stock_zh_a_hist_pre_min_em(symbol=test_symbol)
            duration = time.time() - start_time
            if df is not None and not df.empty:
                print(f"  单股票测试成功: {test_symbol}, 耗时: {duration:.2f}秒, 记录数: {len(df)}")
                print(f"  注意: 这是盘前数据接口，不适合批量获取历史数据")
            else:
                print(f"  单股票测试: 返回空数据")
        except Exception as e:
            print(f"  单股票测试失败: {str(e)}")
            print(f"  注意: 此接口可能不支持或需要不同参数")
    except Exception as e:
        print(f"  接口不存在或不可用: {str(e)}")
    
    print()
    
    # 测试4: 尝试使用不同的adjust参数
    print("测试4: stock_zh_a_hist 不同adjust参数对比")
    print("-" * 80)
    adjust_options = ['qfq', 'hfq', '']
    for adjust in adjust_options:
        try:
            test_symbol = test_symbols[0]
            start_time = time.time()
            df = ak.stock_zh_a_hist(
                symbol=test_symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            duration = time.time() - start_time
            if df is not None and not df.empty:
                print(f"  adjust='{adjust}': 耗时 {duration:.2f}秒, 记录数 {len(df)}")
            else:
                print(f"  adjust='{adjust}': 返回空数据")
            time.sleep(0.5)
        except Exception as e:
            print(f"  adjust='{adjust}': 失败 - {str(e)}")
    
    print()
    
    # 测试5: 尝试批量获取接口（如果存在）
    print("测试5: 查找批量获取接口")
    print("-" * 80)
    batch_apis = [
        'stock_zh_a_hist_min_em',
        'stock_zh_a_hist_pre_min_em',
        'stock_zh_a_spot_em',  # 实时行情（批量）
    ]
    
    for api_name in batch_apis:
        try:
            api_func = getattr(ak, api_name)
            print(f"  找到接口: {api_name}")
            
            # 测试接口是否可用
            try:
                if api_name == 'stock_zh_a_spot_em':
                    # 实时行情接口不需要symbol参数
                    start_time = time.time()
                    df = api_func()
                    duration = time.time() - start_time
                    if df is not None and not df.empty:
                        print(f"    测试成功: 耗时 {duration:.2f}秒, 记录数 {len(df)}")
                        print(f"    注意: 这是实时行情接口，可以批量获取所有股票")
                else:
                    test_symbol = test_symbols[0]
                    start_time = time.time()
                    df = api_func(symbol=test_symbol)
                    duration = time.time() - start_time
                    if df is not None and not df.empty:
                        print(f"    测试成功: 耗时 {duration:.2f}秒, 记录数 {len(df)}")
            except Exception as e:
                print(f"    测试失败: {str(e)}")
        except AttributeError:
            print(f"  接口不存在: {api_name}")
    
    print()
    
    # 测试6: 测试实时行情接口的批量获取能力
    print("测试6: stock_zh_a_spot_em 批量获取能力")
    print("-" * 80)
    try:
        start_time = time.time()
        df = ak.stock_zh_a_spot_em()
        duration = time.time() - start_time
        
        if df is not None and not df.empty:
            print(f"  成功获取所有A股实时行情")
            print(f"  耗时: {duration:.2f}秒")
            print(f"  股票数量: {len(df)}")
            print(f"  速度: {len(df) / duration:.2f} 只股票/秒")
            print(f"  列名: {list(df.columns)[:10]}...")  # 显示前10个列名
            
            # 检查是否包含历史数据字段
            has_history_fields = any(col in df.columns for col in ['日期', 'date', '开盘', 'open', '收盘', 'close'])
            if has_history_fields:
                print(f"  ⚠️  注意: 此接口包含历史数据字段，可能可以用于批量获取")
            else:
                print(f"  ✓ 这是实时行情接口，不包含历史数据")
        else:
            print(f"  返回空数据")
    except Exception as e:
        print(f"  测试失败: {str(e)}")
    
    print()
    
    # 总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    
    if results:
        print("\n接口性能对比:")
        print(f"{'接口名称':<30} {'成功率':<10} {'平均耗时(秒)':<15} {'速度(条/秒)':<15}")
        print("-" * 80)
        
        for result in results:
            success_rate = f"{result['success_count']}/{len(test_symbols)}"
            avg_duration = f"{result['avg_duration']:.2f}"
            speed = f"{result['speed']:.2f}"
            print(f"{result['api_name']:<30} {success_rate:<10} {avg_duration:<15} {speed:<15}")
    
    print("\n建议:")
    print("1. stock_zh_a_hist 是当前使用的接口，适合获取历史数据")
    print("2. stock_zh_a_spot_em 可以批量获取所有股票的实时行情，速度快")
    print("3. 如果只需要实时数据，可以考虑使用 stock_zh_a_spot_em 批量获取")
    print("4. 历史数据获取建议继续使用 stock_zh_a_hist，但可以考虑:")
    print("   - 增加缓存机制")
    print("   - 批量获取时减少API调用次数")
    print("   - 使用数据库缓存已获取的数据")
    
    print("\n优化建议:")
    print("1. 优先从数据库获取历史数据（已实现）")
    print("2. 使用 stock_zh_a_spot_em 批量获取实时行情，然后更新数据库")
    print("3. 对于历史数据收集，继续使用 stock_zh_a_hist，但优化批量处理逻辑")
    print("4. 考虑使用多线程并发获取，但要注意API限流")


if __name__ == '__main__':
    main()
