"""
测试所有新闻源的可用性
如果某个新闻源不可用，尝试备用方案
"""
import sys
import os
import traceback
from typing import Dict, List
from datetime import datetime

# 添加父目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger

logger = get_logger(__name__)

def test_single_source(source_name: str, source_class, symbol: str = "000001") -> Dict:
    """
    测试单个新闻源
    
    Returns:
        {
            'available': bool,
            'stock_news_count': int,
            'market_news_count': int,
            'error': str or None,
            'details': dict
        }
    """
    result = {
        'available': False,
        'stock_news_count': 0,
        'market_news_count': 0,
        'error': None,
        'details': {}
    }
    
    try:
        # 尝试初始化
        print(f"\n测试 {source_name}...")
        
        # 初始化新闻源
        if 'TuShare' in source_name:
            source = source_class(token=None)
        else:
            source = source_class()
        
        result['details']['init'] = '成功'
        
        # 测试获取股票新闻
        try:
            stock_news = source.get_stock_news(symbol, limit=5)
            result['stock_news_count'] = len(stock_news)
            result['details']['stock_news'] = f'成功获取{len(stock_news)}条'
            
            if stock_news:
                result['details']['sample_title'] = stock_news[0].get('title', '无标题')[:50]
        except Exception as e:
            result['details']['stock_news'] = f'失败: {str(e)[:100]}'
        
        # 测试获取市场新闻
        try:
            market_news = source.get_market_news(limit=5)
            result['market_news_count'] = len(market_news)
            result['details']['market_news'] = f'成功获取{len(market_news)}条'
            
            if market_news:
                result['details']['sample_market_title'] = market_news[0].get('title', '无标题')[:50]
        except Exception as e:
            result['details']['market_news'] = f'失败: {str(e)[:100]}'
        
        # 判断是否可用（至少有一个功能可用）
        if result['stock_news_count'] > 0 or result['market_news_count'] > 0:
            result['available'] = True
        else:
            result['error'] = '无法获取任何新闻'
        
    except ImportError as e:
        result['error'] = f'导入失败: {str(e)}'
        result['details']['init'] = '导入失败'
    except Exception as e:
        result['error'] = f'初始化失败: {str(e)}'
        result['details']['init'] = f'失败: {str(e)[:100]}'
        traceback.print_exc()
    
    return result

def test_all_sources():
    """测试所有新闻源"""
    print("=" * 80)
    print("测试所有新闻源的可用性")
    print("=" * 80)
    
    test_symbol = "000001"  # 平安银行
    
    # 要测试的新闻源列表
    sources_to_test = []
    
    # 基础新闻源
    try:
        from news.jin10_news_source import Jin10NewsSource
        sources_to_test.append(('金十数据', Jin10NewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入金十数据: {e}")
    
    try:
        from news.caixin_news_source import CaixinNewsSource
        sources_to_test.append(('财新', CaixinNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入财新: {e}")
    
    try:
        from news.securities_news_source import SecuritiesNewsSource
        sources_to_test.append(('证券公司', SecuritiesNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入证券公司: {e}")
    
    try:
        from news.tonghuashun_news_source import TonghuashunNewsSource
        sources_to_test.append(('同花顺', TonghuashunNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入同花顺: {e}")
    
    # 新增新闻源
    try:
        from news.eastmoney_news_source import EastMoneyNewsSource
        sources_to_test.append(('东方财富', EastMoneyNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入东方财富: {e}")
    
    try:
        from news.xueqiu_news_source import XueqiuNewsSource
        sources_to_test.append(('雪球', XueqiuNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入雪球: {e}")
    
    try:
        from news.tushare_news_source import TuShareNewsSource
        sources_to_test.append(('TuShare', TuShareNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入TuShare: {e}")
    
    try:
        from news.sina_news_source import SinaNewsSource
        sources_to_test.append(('新浪财经', SinaNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入新浪财经: {e}")
    
    try:
        from news.tencent_news_source import TencentNewsSource
        sources_to_test.append(('腾讯财经', TencentNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入腾讯财经: {e}")
    
    try:
        from news.netease_news_source import NetEaseNewsSource
        sources_to_test.append(('网易财经', NetEaseNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入网易财经: {e}")
    
    try:
        from news.sse_news_source import SSENewsSource
        sources_to_test.append(('上交所', SSENewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入上交所: {e}")
    
    try:
        from news.szse_news_source import SZSENewsSource
        sources_to_test.append(('深交所', SZSENewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入深交所: {e}")
    
    try:
        from news.cninfo_news_source import CninfoNewsSource
        sources_to_test.append(('巨潮资讯', CninfoNewsSource))
    except ImportError as e:
        print(f"⚠️  无法导入巨潮资讯: {e}")
    
    print(f"\n共找到 {len(sources_to_test)} 个新闻源需要测试\n")
    
    # 测试结果
    results = {}
    available_count = 0
    unavailable_count = 0
    
    for source_name, source_class in sources_to_test:
        result = test_single_source(source_name, source_class, test_symbol)
        results[source_name] = result
        
        if result['available']:
            available_count += 1
            status = "✅ 可用"
        else:
            unavailable_count += 1
            status = "❌ 不可用"
        
        print(f"\n{status} - {source_name}")
        print(f"  股票新闻: {result['stock_news_count']} 条")
        print(f"  市场新闻: {result['market_news_count']} 条")
        if result['error']:
            print(f"  错误: {result['error']}")
        if result.get('details', {}).get('sample_title'):
            print(f"  示例标题: {result['details']['sample_title']}")
    
    # 汇总报告
    print("\n" + "=" * 80)
    print("测试汇总")
    print("=" * 80)
    print(f"总计: {len(sources_to_test)} 个新闻源")
    print(f"✅ 可用: {available_count} 个")
    print(f"❌ 不可用: {unavailable_count} 个")
    
    print("\n可用的新闻源:")
    for name, result in results.items():
        if result['available']:
            print(f"  ✅ {name} (股票:{result['stock_news_count']}, 市场:{result['market_news_count']})")
    
    print("\n不可用的新闻源:")
    for name, result in results.items():
        if not result['available']:
            print(f"  ❌ {name}: {result['error'] or '无法获取新闻'}")
    
    # 测试统一新闻源
    print("\n" + "=" * 80)
    print("测试统一新闻源集成")
    print("=" * 80)
    try:
        from news.unified_news_source import UnifiedNewsSource
        unified = UnifiedNewsSource()
        print(f"✅ 统一新闻源初始化成功，包含 {len(unified.sources)} 个可用新闻源:")
        for name, source in unified.sources:
            print(f"  - {name}")
        
        # 测试获取新闻
        print(f"\n测试获取股票 {test_symbol} 的新闻...")
        news_list = unified.get_stock_news(test_symbol, limit=10)
        print(f"✅ 成功获取 {len(news_list)} 条新闻")
        
        if news_list:
            print("\n前3条新闻:")
            for i, news in enumerate(news_list[:3], 1):
                print(f"  {i}. [{news.get('source', '未知')}] {news.get('title', '无标题')[:60]}")
    except Exception as e:
        print(f"❌ 统一新闻源测试失败: {str(e)}")
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_all_sources()



