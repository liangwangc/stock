"""
测试所有新闻源的获取能力
逐个测试每个新闻源，检查是否能获取到数据
"""
import sys
import os
from datetime import datetime, date

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

print("测试所有新闻源的获取能力")
print("="*80)
print(f"当前日期: {date.today()}")
print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# 测试统一新闻源
try:
    from quant_trading_platform.news.unified_news_source import UnifiedNewsSource
    
    news_source = UnifiedNewsSource()
    print(f"\n已初始化的新闻源: {len(news_source.sources)} 个")
    
    # 测试每个新闻源的get_market_news
    print("\n" + "="*80)
    print("测试市场新闻获取（only_today=True）")
    print("="*80)
    
    for source_name, source_obj in news_source.sources:
        print(f"\n[{source_name}]")
        try:
            if hasattr(source_obj, 'get_market_news'):
                # 测试only_today=True
                news_list = source_obj.get_market_news(limit=5)
                print(f"  获取到 {len(news_list)} 条新闻")
                
                if news_list:
                    # 检查日期
                    today = date.today()
                    today_count = 0
                    dates = []
                    for news in news_list:
                        pub_time = news.get('time') or news.get('publish_time')
                        if pub_time:
                            if isinstance(pub_time, datetime):
                                news_date = pub_time.date()
                            elif isinstance(pub_time, str):
                                try:
                                    news_date = datetime.strptime(pub_time[:10], '%Y-%m-%d').date()
                                except:
                                    news_date = None
                            else:
                                news_date = None
                            
                            if news_date:
                                dates.append(str(news_date))
                                if news_date == today:
                                    today_count += 1
                    
                    print(f"  当天新闻: {today_count}/{len(news_list)}")
                    if dates:
                        print(f"  日期范围: {min(dates)} 到 {max(dates)}")
                    
                    # 显示前3条新闻的标题
                    print(f"  前3条新闻标题:")
                    for i, news in enumerate(news_list[:3], 1):
                        title = news.get('title', '')[:50]
                        pub_time = news.get('time') or news.get('publish_time')
                        print(f"    {i}. {title} ({pub_time})")
                else:
                    print(f"  未获取到数据")
            else:
                print(f"  不支持get_market_news方法")
        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            print(f"  错误: {error_msg}")
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)
    
except Exception as e:
    print(f"初始化失败: {str(e)}")
    import traceback
    traceback.print_exc()
