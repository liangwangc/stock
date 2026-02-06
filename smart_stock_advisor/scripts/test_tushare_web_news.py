#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Tushare网页新闻源
"""
import os
import sys
import io

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

from utils.logger import get_logger

logger = get_logger(__name__)

def test_tushare_web_news():
    """测试Tushare网页新闻源"""
    print("=" * 80)
    print("测试Tushare网页新闻源")
    print("=" * 80)
    
    try:
        # 尝试不同的导入路径
        try:
            from news.tushare_web_news_source import TushareWebNewsSource
        except ImportError:
            from quant_trading_platform.news.tushare_web_news_source import TushareWebNewsSource
        
        print("\n1. 初始化新闻源...")
        source = TushareWebNewsSource()
        print("   [OK] 初始化成功")
        
        print("\n2. 测试获取市场新闻...")
        market_news = source.get_market_news(limit=10)
        print(f"   [OK] 获取到 {len(market_news)} 条市场新闻")
        
        if market_news:
            print("\n   前5条新闻:")
            for i, news in enumerate(market_news[:5], 1):
                title = news.get('title', '无标题')
                source_name = news.get('source', '未知')
                time_str = str(news.get('time', '未知时间'))[:19] if news.get('time') else '未知时间'
                print(f"   {i}. [{source_name}] {title[:60]}")
                print(f"      时间: {time_str}")
                if news.get('url'):
                    print(f"      URL: {news.get('url')[:80]}")
                print()
        else:
            print("   [警告] 未获取到新闻")
        
        print("\n3. 测试获取股票新闻...")
        stock_news = source.get_stock_news("000001", limit=5)
        print(f"   [OK] 获取到 {len(stock_news)} 条股票新闻")
        
        if stock_news:
            print("\n   前3条新闻:")
            for i, news in enumerate(stock_news[:3], 1):
                title = news.get('title', '无标题')
                source_name = news.get('source', '未知')
                print(f"   {i}. [{source_name}] {title[:60]}")
        else:
            print("   [信息] 未获取到相关股票新闻（可能没有包含股票代码的新闻）")
        
        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)
        
    except ImportError as e:
        print(f"\n[FAIL] 导入失败: {str(e)}")
        print("请确保已安装 beautifulsoup4: pip install beautifulsoup4")
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_tushare_web_news()
