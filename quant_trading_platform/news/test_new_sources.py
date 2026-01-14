"""
测试新增的新闻源
"""
import sys
import os

# 添加父目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from news.unified_news_source import UnifiedNewsSource
from utils.logger import get_logger

logger = get_logger(__name__)

def test_news_sources():
    """测试所有新闻源"""
    print("=" * 60)
    print("测试新增的新闻源")
    print("=" * 60)
    
    # 初始化统一新闻源
    try:
        unified_source = UnifiedNewsSource()
        print(f"\n已初始化 {len(unified_source.sources)} 个新闻源")
        for name, source in unified_source.sources:
            print(f"  - {name}")
    except Exception as e:
        print(f"初始化统一新闻源失败: {str(e)}")
        return
    
    # 测试获取股票新闻
    test_symbol = "000001"  # 平安银行
    print(f"\n测试获取股票 {test_symbol} 的新闻...")
    try:
        news_list = unified_source.get_stock_news(test_symbol, limit=5)
        print(f"获取到 {len(news_list)} 条新闻")
        for i, news in enumerate(news_list[:3], 1):
            print(f"\n{i}. {news.get('title', '无标题')}")
            print(f"   来源: {news.get('source', '未知')}")
            print(f"   时间: {news.get('time', '未知')}")
            print(f"   URL: {news.get('url', '未知')}")
    except Exception as e:
        print(f"获取股票新闻失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 测试获取市场新闻
    print(f"\n测试获取市场新闻...")
    try:
        market_news = unified_source.get_market_news(limit=5)
        print(f"获取到 {len(market_news)} 条市场新闻")
        for i, news in enumerate(market_news[:3], 1):
            print(f"\n{i}. {news.get('title', '无标题')}")
            print(f"   来源: {news.get('source', '未知')}")
            print(f"   时间: {news.get('time', '未知')}")
    except Exception as e:
        print(f"获取市场新闻失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_news_sources()



