#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Tushare登录功能（支持手动输入验证码）
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

def test_tushare_login_with_captcha():
    """测试Tushare登录（支持手动输入验证码）"""
    print("=" * 80)
    print("测试Tushare登录功能（支持手动输入验证码）")
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
            print("   [信息] 自动登录失败，可能需要手动输入验证码")
            
            # 尝试手动登录
            print("\n2. 尝试手动登录...")
            print("   正在获取验证码...")
            
            # 访问登录页面获取验证码
            import requests
            from bs4 import BeautifulSoup
            import uuid
            
            session = requests.Session()
            login_url = "https://tushare.pro/login"
            response = session.get(login_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                xsrf_input = soup.find('input', {'name': '_xsrf'})
                xsrf_token = xsrf_input.get('value', '') if xsrf_input else ''
                
                # 获取验证码
                unique_id = str(uuid.uuid4()).replace('-', '')
                captcha_url = f"https://tushare.pro/captcha?action=login&unique_id={unique_id}"
                captcha_response = session.get(captcha_url, timeout=10)
                
                if captcha_response.status_code == 200:
                    # 保存验证码图片
                    captcha_path = os.path.join(project_root, 'captcha_temp.png')
                    with open(captcha_path, 'wb') as f:
                        f.write(captcha_response.content)
                    print(f"   验证码图片已保存到: {captcha_path}")
                    print("   请打开图片查看验证码")
                    
                    # 手动输入验证码
                    captcha_code = input("\n请输入验证码（4位字符）: ").strip()
                    
                    if captcha_code:
                        # 尝试登录
                        login_data = {
                            '_xsrf': xsrf_token,
                            'account': username,
                            'password': password,
                            'captcha': captcha_code
                        }
                        
                        login_response = session.post(login_url, data=login_data, timeout=10, allow_redirects=False)
                        
                        if login_response.status_code == 302:
                            print("   [OK] 登录成功！")
                            # 使用登录后的session更新source的session
                            source.session = session
                            source._logged_in = True
                        else:
                            print("   [FAIL] 登录失败，可能是验证码错误或账号密码错误")
                            return
                    else:
                        print("   [FAIL] 未输入验证码")
                        return
                else:
                    print("   [FAIL] 无法获取验证码图片")
                    return
            else:
                print("   [FAIL] 无法访问登录页面")
                return
        
        print("\n3. 测试获取市场新闻...")
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
            print("   1. 登录状态已过期")
            print("   2. 页面结构发生变化")
            print("   3. 该时间段内没有新闻")
        
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
    test_tushare_login_with_captcha()
