"""
测试各个新闻源的only_today功能
检查为什么很多网站获取不到当天的数据
"""
import sys
import os
from datetime import datetime, date

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

from quant_trading_platform.news.unified_news_source import UnifiedNewsSource

print("测试各个新闻源的only_today功能")
print("="*80)
print(f"当前日期: {date.today()}")
print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# 初始化统一新闻源
try:
    news_source = UnifiedNewsSource()
    print(f"\n已初始化的新闻源数量: {len(news_source.sources)}")
    print(f"新闻源列表: {[name for name, _ in news_source.sources]}")
except Exception as e:
    print(f"初始化失败: {str(e)}")
    sys.exit(1)

# 测试每个新闻源
print("\n" + "="*80)
print("测试市场新闻（only_today=True）")
print("="*80)

for source_name, source_obj in news_source.sources:
    print(f"\n[{source_name}]")
    try:
        # 测试only_today=True
        if hasattr(source_obj, 'get_market_news'):
            news_list_today = source_obj.get_market_news(limit=10, only_today=True)
            print(f"  only_today=True: 获取到 {len(news_list_today)} 条新闻")
            if news_list_today:
                # 检查日期
                dates = []
                for news in news_list_today[:5]:
                    pub_time = news.get('publish_time')
                    if pub_time:
                        dates.append(pub_time)
                print(f"  前5条新闻的发布时间: {dates}")
            else:
                print(f"  未获取到数据")
        else:
            print(f"  不支持get_market_news方法")
    except Exception as e:
        print(f"  错误: {str(e)[:200]}")

print("\n" + "="*80)
print("测试市场新闻（only_today=False，获取全部）")
print("="*80)

for source_name, source_obj in news_source.sources:
    print(f"\n[{source_name}]")
    try:
        # 测试only_today=False
        if hasattr(source_obj, 'get_market_news'):
            news_list_all = source_obj.get_market_news(limit=10, only_today=False)
            print(f"  only_today=False: 获取到 {len(news_list_all)} 条新闻")
            if news_list_all:
                # 检查日期
                dates = []
                for news in news_list_all[:5]:
                    pub_time = news.get('publish_time')
                    if pub_time:
                        dates.append(pub_time)
                print(f"  前5条新闻的发布时间: {dates}")
            else:
                print(f"  未获取到数据")
        else:
            print(f"  不支持get_market_news方法")
    except Exception as e:
        print(f"  错误: {str(e)[:200]}")

print("\n" + "="*80)
print("测试完成")
print("="*80)
