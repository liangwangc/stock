#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断新闻源获取情况
重点检查金十数据为什么获取不到新闻
"""
import os
import sys
import io
import requests
from datetime import datetime
import json

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

from utils.logger import get_logger

logger = get_logger(__name__)


def test_jin10_directly():
    """直接测试金十数据API"""
    print("\n" + "=" * 80)
    print("直接测试金十数据API")
    print("=" * 80)
    
    # 测试URL 1: 原代码中的URL
    url1 = "https://rili.jin10.com/dc/news/newsFlash"
    print(f"\n测试URL 1: {url1}")
    try:
        response = requests.get(url1, timeout=10)
        print(f"  状态码: {response.status_code}")
        print(f"  响应头: {dict(response.headers)}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  响应类型: JSON")
                print(f"  响应数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
                if 'data' in data:
                    print(f"  数据条数: {len(data.get('data', []))}")
            except:
                print(f"  响应类型: 文本")
                print(f"  响应内容前500字符: {response.text[:500]}")
        else:
            print(f"  响应内容: {response.text[:500]}")
    except Exception as e:
        print(f"  ✗ 请求失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
    
    # 测试URL 2: 金十数据官网的API
    url2 = "https://api.jin10.com/news/list"
    print(f"\n测试URL 2: {url2}")
    try:
        response = requests.get(url2, timeout=10)
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  响应类型: JSON")
                print(f"  响应数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            except:
                print(f"  响应类型: 文本")
                print(f"  响应内容前500字符: {response.text[:500]}")
        else:
            print(f"  响应内容: {response.text[:500]}")
    except Exception as e:
        print(f"  ✗ 请求失败: {str(e)}")
    
    # 测试URL 3: 金十数据快讯接口（可能需要特定参数）
    url3 = "https://flash-api.jin10.com/get_flash_list"
    print(f"\n测试URL 3: {url3}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.jin10.com/'
        }
        params = {
            'max_time': int(datetime.now().timestamp() * 1000),
            'channel': '-8200'
        }
        response = requests.get(url3, headers=headers, params=params, timeout=10)
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  响应类型: JSON")
                print(f"  响应数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
                if 'data' in data:
                    print(f"  数据条数: {len(data.get('data', []))}")
            except:
                print(f"  响应类型: 文本")
                print(f"  响应内容前500字符: {response.text[:500]}")
        else:
            print(f"  响应内容: {response.text[:500]}")
    except Exception as e:
        print(f"  ✗ 请求失败: {str(e)}")
        import traceback
        print(traceback.format_exc())


def test_jin10_via_class():
    """通过类测试金十数据"""
    print("\n" + "=" * 80)
    print("通过Jin10NewsSource类测试")
    print("=" * 80)
    
    try:
        from quant_trading_platform.news.jin10_news_source import Jin10NewsSource
        from news.jin10_news_source import Jin10NewsSource as Jin10NewsSource2
        jin10 = Jin10NewsSource()
    except ImportError:
        try:
            from news.jin10_news_source import Jin10NewsSource
            jin10 = Jin10NewsSource()
        except ImportError as e:
            print(f"  ✗ 无法导入Jin10NewsSource: {str(e)}")
            return
    
    print("\n测试get_market_news方法...")
    try:
        news_list = jin10.get_market_news(limit=5)
        print(f"  返回新闻数量: {len(news_list)}")
        if news_list:
            print("  前3条新闻:")
            for i, news in enumerate(news_list[:3], 1):
                print(f"    {i}. {news.get('title', 'N/A')[:60]}...")
                print(f"       来源: {news.get('source', 'N/A')}")
                print(f"       时间: {news.get('time', 'N/A')}")
        else:
            print("  ✗ 未获取到新闻")
    except Exception as e:
        print(f"  ✗ 获取失败: {str(e)}")
        import traceback
        print(traceback.format_exc())


def test_single_source(source_name: str, source, timeout: int = 15):
    """
    测试单个新闻源（独立测试，不会影响其他新闻源）
    
    Args:
        source_name: 新闻源名称
        source: 新闻源实例
        timeout: 超时时间（秒）
    """
    import signal
    
    result = {
        'name': source_name,
        'success': False,
        'count': 0,
        'error': None,
        'time': 0
    }
    
    print(f"\n{'=' * 60}")
    print(f"测试: {source_name}")
    print(f"{'=' * 60}")
    
    start_time = datetime.now()
    
    try:
        # 设置超时（使用线程方式，避免signal在Windows上的问题）
        import threading
        news_result = [None]
        exception_result = [None]
        
        def fetch_news():
            try:
                news_result[0] = source.get_market_news(limit=3)
            except Exception as e:
                exception_result[0] = e
        
        thread = threading.Thread(target=fetch_news, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            print(f"  ⚠ 超时（>{timeout}秒），跳过")
            result['error'] = f'超时（>{timeout}秒）'
            return result
        
        elapsed = (datetime.now() - start_time).total_seconds()
        result['time'] = elapsed
        
        if exception_result[0]:
            raise exception_result[0]
        
        news = news_result[0]
        
        if news and len(news) > 0:
            print(f"  ✓ 成功获取 {len(news)} 条新闻 (耗时: {elapsed:.2f}秒)")
            for i, n in enumerate(news[:2], 1):
                title = n.get('title', 'N/A')
                print(f"    {i}. {title[:60]}...")
                print(f"       来源: {n.get('source', 'N/A')}, 时间: {n.get('time', 'N/A')}")
            result['success'] = True
            result['count'] = len(news)
        else:
            print(f"  ✗ 未获取到新闻 (耗时: {elapsed:.2f}秒)")
            result['error'] = '未获取到数据'
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        result['time'] = elapsed
        error_msg = str(e)
        print(f"  ✗ 获取失败 (耗时: {elapsed:.2f}秒): {error_msg}")
        result['error'] = error_msg
        # 不打印完整traceback，避免输出过多
    
    return result


def test_single_source_comprehensive(source_name: str, source, timeout: int = 15):
    """
    对单个新闻源进行多方位测试
    
    Args:
        source_name: 新闻源名称
        source: 新闻源实例
        timeout: 超时时间（秒）
    """
    print("\n" + "=" * 80)
    print(f"多方位测试: {source_name}")
    print("=" * 80)
    
    results = {
        'name': source_name,
        'market_news': None,
        'stock_news': None,
        'error': None
    }
    
    # 测试1: 获取市场新闻
    print(f"\n[测试1] 获取市场新闻（限制3条）...")
    try:
        import threading
        news_result = [None]
        exception_result = [None]
        
        def fetch_market_news():
            try:
                news_result[0] = source.get_market_news(limit=3)
            except Exception as e:
                exception_result[0] = e
        
        thread = threading.Thread(target=fetch_market_news, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            print(f"  ⚠ 超时（>{timeout}秒）")
            results['market_news'] = {'success': False, 'error': f'超时（>{timeout}秒）'}
        elif exception_result[0]:
            print(f"  ✗ 失败: {str(exception_result[0])}")
            results['market_news'] = {'success': False, 'error': str(exception_result[0])}
        elif news_result[0] and len(news_result[0]) > 0:
            print(f"  ✓ 成功获取 {len(news_result[0])} 条新闻")
            for i, n in enumerate(news_result[0][:2], 1):
                print(f"    {i}. {n.get('title', 'N/A')[:60]}...")
            results['market_news'] = {'success': True, 'count': len(news_result[0])}
        else:
            print(f"  ✗ 未获取到新闻")
            results['market_news'] = {'success': False, 'error': '未获取到数据'}
    except Exception as e:
        print(f"  ✗ 测试异常: {str(e)}")
        results['market_news'] = {'success': False, 'error': str(e)}
    
    # 测试2: 获取股票新闻（如果支持）
    print(f"\n[测试2] 获取股票新闻（测试股票：000001，限制3条）...")
    try:
        import threading
        news_result = [None]
        exception_result = [None]
        
        def fetch_stock_news():
            try:
                news_result[0] = source.get_stock_news('000001', limit=3)
            except Exception as e:
                exception_result[0] = e
        
        thread = threading.Thread(target=fetch_stock_news, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            print(f"  ⚠ 超时（>{timeout}秒）")
            results['stock_news'] = {'success': False, 'error': f'超时（>{timeout}秒）'}
        elif exception_result[0]:
            print(f"  ✗ 失败: {str(exception_result[0])}")
            results['stock_news'] = {'success': False, 'error': str(exception_result[0])}
        elif news_result[0] and len(news_result[0]) > 0:
            print(f"  ✓ 成功获取 {len(news_result[0])} 条新闻")
            for i, n in enumerate(news_result[0][:2], 1):
                print(f"    {i}. {n.get('title', 'N/A')[:60]}...")
            results['stock_news'] = {'success': True, 'count': len(news_result[0])}
        else:
            print(f"  ✗ 未获取到新闻")
            results['stock_news'] = {'success': False, 'error': '未获取到数据'}
    except Exception as e:
        print(f"  ✗ 测试异常: {str(e)}")
        results['stock_news'] = {'success': False, 'error': str(e)}
    
    # 总结
    print(f"\n[总结] {source_name} 测试结果:")
    if results['market_news'] and results['market_news'].get('success'):
        print(f"  ✓ 市场新闻: 成功 ({results['market_news'].get('count', 0)} 条)")
    else:
        error = results['market_news'].get('error', '未知错误') if results['market_news'] else '未测试'
        print(f"  ✗ 市场新闻: {error}")
    
    if results['stock_news']:
        if results['stock_news'].get('success'):
            print(f"  ✓ 股票新闻: 成功 ({results['stock_news'].get('count', 0)} 条)")
        else:
            error = results['stock_news'].get('error', '未知错误')
            print(f"  ✗ 股票新闻: {error}")
    
    return results


def list_all_sources():
    """列出所有可用的新闻源"""
    print("\n" + "=" * 80)
    print("列出所有新闻源")
    print("=" * 80)
    
    try:
        from quant_trading_platform.news import UnifiedNewsSource
    except ImportError:
        try:
            from news import UnifiedNewsSource
        except ImportError:
            print("  ✗ 无法导入UnifiedNewsSource")
            return []
    
    try:
        from config import TUSHARE_TOKEN
    except ImportError:
        TUSHARE_TOKEN = None
    
    try:
        news_source = UnifiedNewsSource(tushare_token=TUSHARE_TOKEN)
        sources = []
        print(f"\n共找到 {len(news_source.sources)} 个新闻源:")
        for i, (source_name, source) in enumerate(news_source.sources, 1):
            print(f"  {i}. {source_name}")
            sources.append((source_name, source))
        return sources
    except Exception as e:
        print(f"  ✗ 初始化失败: {str(e)}")
        return []


if __name__ == '__main__':
    print("=" * 80)
    print("新闻源诊断工具（逐个测试，避免中断）")
    print("=" * 80)
    
    import sys
    
    # 获取所有新闻源列表
    sources = list_all_sources()
    
    if not sources:
        print("\n未找到任何新闻源，退出")
        sys.exit(1)
    
    # 根据命令行参数决定测试内容
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == 'jin10':
            # 只测试金十数据（多方位）
            print("\n" + "=" * 80)
            print("金十数据专项测试")
            print("=" * 80)
            
            # 1. 直接测试API
            print("\n[步骤1] 直接测试金十数据API")
            try:
                test_jin10_directly()
            except Exception as e:
                print(f"  ⚠ 直接测试失败: {str(e)}")
            
            # 2. 通过类测试
            print("\n[步骤2] 通过类测试金十数据")
            try:
                test_jin10_via_class()
            except Exception as e:
                print(f"  ⚠ 类测试失败: {str(e)}")
            
            # 3. 通过统一新闻源测试
            print("\n[步骤3] 通过统一新闻源测试金十数据")
            jin10_source = next((s for name, s in sources if name == '金十数据'), None)
            if jin10_source:
                try:
                    test_single_source_comprehensive('金十数据', jin10_source, timeout=15)
                except Exception as e:
                    print(f"  ⚠ 统一测试失败: {str(e)}")
            else:
                print("  ✗ 未找到金十数据新闻源")
        
        elif test_type == 'list':
            # 只列出新闻源，不测试
            print("\n已列出所有新闻源")
        
        elif test_type.startswith('test:'):
            # 测试指定新闻源，格式: test:新闻源名称
            source_name = test_type.split(':', 1)[1]
            source_obj = next((s for name, s in sources if name == source_name), None)
            if source_obj:
                try:
                    test_single_source_comprehensive(source_name, source_obj, timeout=15)
                except Exception as e:
                    print(f"  ⚠ 测试失败: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
            else:
                print(f"  ✗ 未找到新闻源: {source_name}")
                print(f"  可用新闻源: {', '.join([name for name, _ in sources])}")
        
        else:
            print(f"\n未知测试类型: {test_type}")
            print("\n用法:")
            print("  python diagnose_news_sources.py              # 列出所有新闻源")
            print("  python diagnose_news_sources.py list         # 列出所有新闻源")
            print("  python diagnose_news_sources.py jin10        # 测试金十数据（多方位）")
            print("  python diagnose_news_sources.py test:新闻源名  # 测试指定新闻源")
            print(f"\n可用新闻源: {', '.join([name for name, _ in sources])}")
    else:
        # 默认：只列出新闻源，不测试（避免一次性测试太多导致中断）
        print("\n" + "=" * 80)
        print("提示：使用以下命令进行测试")
        print("=" * 80)
        print("\n1. 测试金十数据（多方位测试）:")
        print("   python diagnose_news_sources.py jin10")
        print("\n2. 测试指定新闻源:")
        for name, _ in sources:
            print(f"   python diagnose_news_sources.py test:{name}")
        print("\n注意：一次只测试一个新闻源，避免任务中断")
    
    print("\n" + "=" * 80)
    print("诊断工具就绪")
    print("=" * 80)
