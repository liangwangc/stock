#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Tushare登录功能
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

def test_tushare_login():
    """测试Tushare登录"""
    print("=" * 80)
    print("测试Tushare登录功能")
    print("=" * 80)
    
    # 从用户输入获取账号密码
    print("\n请输入Tushare账号信息：")
    username = input("账号（手机或邮箱）: ").strip()
    password = input("密码: ").strip()
    
    if not username or not password:
        print("\n[FAIL] 账号或密码不能为空")
        return
    
    try:
        # 导入新闻源
        import importlib.util
        tushare_web_file = os.path.join(project_root, '..', 'quant_trading_platform', 'news', 'tushare_web_news_source.py')
        spec = importlib.util.spec_from_file_location("tushare_web_news_source", tushare_web_file)
        tushare_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tushare_module)
        TushareWebNewsSource = tushare_module.TushareWebNewsSource
        
        print("\n1. 初始化新闻源...")
        source = TushareWebNewsSource(username=username, password=password)
        
        if not source._logged_in:
            print("   [FAIL] 登录失败")
            print("   可能原因：")
            print("   1. 账号密码错误")
            print("   2. 验证码识别失败（需要手动输入验证码）")
            print("   3. 网络问题")
            return
        
        print("   [OK] 登录成功")
        
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
    test_tushare_login()
