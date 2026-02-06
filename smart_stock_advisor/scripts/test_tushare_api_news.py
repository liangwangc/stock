#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Tushare API新闻源（修复后）
"""
import os
import sys
import io

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
quant_trading_root = os.path.join(project_root, '..', 'quant_trading_platform')
sys.path.insert(0, project_root)
sys.path.insert(0, quant_trading_root)

# 添加quant_trading_platform的父目录到路径
sys.path.insert(0, os.path.dirname(quant_trading_root))

from utils.logger import get_logger

logger = get_logger(__name__)

def test_tushare_api_news():
    """测试Tushare API新闻源"""
    print("=" * 80)
    print("测试Tushare API新闻源（修复后）")
    print("=" * 80)
    
    try:
        # 导入配置
        TUSHARE_TOKEN = None
        try:
            # 尝试从config模块导入
            sys.path.insert(0, project_root)
            from config import TUSHARE_TOKEN
        except ImportError:
            try:
                # 尝试直接读取config.py文件
                import importlib.util
                config_path = os.path.join(project_root, 'config.py')
                if os.path.exists(config_path):
                    spec = importlib.util.spec_from_file_location("config", config_path)
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)
                    TUSHARE_TOKEN = getattr(config_module, 'TUSHARE_TOKEN', None)
            except Exception as e:
                print(f"\n[警告] 无法导入TUSHARE_TOKEN配置: {str(e)}")
        
        if not TUSHARE_TOKEN:
            print("\n[FAIL] TUSHARE_TOKEN未配置")
            print("请在 config.py 中配置 TUSHARE_TOKEN")
            return
        
        if not TUSHARE_TOKEN:
            print("\n[FAIL] TUSHARE_TOKEN未配置")
            return
        
        print(f"\n[OK] TUSHARE_TOKEN已配置（长度: {len(TUSHARE_TOKEN)}）")
        
        # 导入新闻源 - 直接使用文件路径导入
        tushare_news_file = os.path.join(quant_trading_root, 'news', 'tushare_news_source.py')
        if not os.path.exists(tushare_news_file):
            print(f"\n[FAIL] 找不到文件: {tushare_news_file}")
            return
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("tushare_news_source", tushare_news_file)
        tushare_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tushare_module)
        TuShareNewsSource = tushare_module.TuShareNewsSource
        
        print("\n1. 初始化新闻源...")
        source = TuShareNewsSource(token=TUSHARE_TOKEN)
        
        if not source._use_api:
            print("   [FAIL] TuShare API不可用")
            print("   可能原因：")
            print("   1. tushare库未安装（运行: pip install tushare）")
            print("   2. token无效或权限不足")
            return
        
        print("   [OK] TuShare API初始化成功")
        print(f"   支持的新闻源: {list(source.NEWS_SOURCES.values())}")
        
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
            print("   可能原因：")
            print("   1. news接口没有权限（需要足够的积分等级）")
            print("   2. 接口参数不正确")
            print("   3. 网络问题")
        
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
        print("请确保已安装 tushare: pip install tushare")
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_tushare_api_news()
