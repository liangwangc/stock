#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交互式测试Tushare登录功能
支持手动输入验证码
"""
import os
import sys
import io
import requests
from bs4 import BeautifulSoup
import uuid

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

def interactive_login():
    """交互式登录"""
    print("=" * 80)
    print("Tushare交互式登录测试")
    print("=" * 80)
    
    # 获取账号密码
    print("\n请输入Tushare账号信息：")
    username = input("账号（手机或邮箱）: ").strip()
    password = input("密码: ").strip()
    
    if not username or not password:
        print("\n[FAIL] 账号或密码不能为空")
        return None
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://tushare.pro/'
    })
    
    base_url = "https://tushare.pro"
    
    # 1. 访问登录页面
    print("\n1. 访问登录页面...")
    login_url = f"{base_url}/login"
    response = session.get(login_url, timeout=10)
    
    if response.status_code != 200:
        print(f"   [FAIL] 访问登录页面失败，状态码: {response.status_code}")
        return None
    
    print("   [OK] 登录页面加载成功")
    
    # 2. 提取_xsrf token
    soup = BeautifulSoup(response.text, 'html.parser')
    xsrf_input = soup.find('input', {'name': '_xsrf'})
    if not xsrf_input:
        print("   [FAIL] 无法找到_xsrf token")
        return None
    
    xsrf_token = xsrf_input.get('value', '')
    print(f"   [OK] 获取到_xsrf token: {xsrf_token[:20]}...")
    
    # 3. 获取验证码
    print("\n2. 获取验证码...")
    unique_id = str(uuid.uuid4()).replace('-', '')
    captcha_url = f"{base_url}/captcha?action=login&unique_id={unique_id}"
    captcha_response = session.get(captcha_url, timeout=10)
    
    if captcha_response.status_code != 200:
        print(f"   [FAIL] 获取验证码失败，状态码: {captcha_response.status_code}")
        return None
    
    # 保存验证码图片
    captcha_path = os.path.join(project_root, 'captcha_temp.png')
    with open(captcha_path, 'wb') as f:
        f.write(captcha_response.content)
    
    print(f"   [OK] 验证码图片已保存到: {captcha_path}")
    print("   请打开图片查看验证码")
    
    # 4. 手动输入验证码
    print("\n3. 输入验证码...")
    captcha_code = input("请输入验证码（4位字符）: ").strip()
    
    if not captcha_code or len(captcha_code) != 4:
        print("   [FAIL] 验证码格式不正确")
        return None
    
    # 5. 提交登录
    print("\n4. 提交登录...")
    login_data = {
        '_xsrf': xsrf_token,
        'account': username,
        'password': password,
        'captcha': captcha_code
    }
    
    login_response = session.post(login_url, data=login_data, timeout=10, allow_redirects=False)
    
    # 6. 检查登录结果
    if login_response.status_code == 302:
        print("   [OK] 登录成功！")
        return session
    elif login_response.status_code == 200:
        # 检查是否还在登录页面
        soup = BeautifulSoup(login_response.text, 'html.parser')
        login_form = soup.find('form', id='login-form')
        
        if login_form:
            # 检查错误信息
            error_elem = soup.find('div', id='login-common-info')
            if error_elem:
                error_text = error_elem.get_text(strip=True)
                if error_text:
                    print(f"   [FAIL] 登录失败: {error_text}")
                else:
                    print("   [FAIL] 登录失败：可能是验证码错误或账号密码错误")
            else:
                print("   [FAIL] 登录失败：可能是验证码错误")
            return None
        else:
            print("   [OK] 登录成功！")
            return session
    else:
        print(f"   [FAIL] 登录请求失败，状态码: {login_response.status_code}")
        return None

def test_get_news(session):
    """测试获取新闻"""
    print("\n" + "=" * 80)
    print("测试获取新闻")
    print("=" * 80)
    
    base_url = "https://tushare.pro/news"
    
    news_sources = {
        'yicai': '第一财经',
        'fenghuang': '凤凰财经',
        '10jqka': '同花顺',
        'jinrongjie': '金融界',
        'sina': '新浪财经',
        'yuncaijing': '云财经',
        'eastmoney': '东方财富',
    }
    
    all_news = []
    
    for src, name in list(news_sources.items())[:3]:  # 只测试前3个
        print(f"\n测试: {name}")
        url = f"{base_url}/{src}"
        
        try:
            response = session.get(url, timeout=15)
            print(f"  状态码: {response.status_code}")
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 检查是否是登录页面
                login_form = soup.find('form', id='login-form')
                if login_form:
                    print(f"  [FAIL] 仍然是登录页面，登录可能已过期")
                    continue
                
                # 尝试提取新闻
                # 这里需要根据实际页面结构来解析
                # 由于我们不知道登录后的页面结构，先简单检查
                page_text = soup.get_text()
                if len(page_text) > 1000:  # 如果页面内容较多，可能包含新闻
                    print(f"  [OK] 页面内容长度: {len(page_text)} 字符")
                    print(f"  页面标题: {soup.find('title').get_text() if soup.find('title') else 'N/A'}")
                    # 这里可以添加具体的新闻解析逻辑
                else:
                    print(f"  [信息] 页面内容较少，可能没有新闻或页面结构不同")
            else:
                print(f"  [FAIL] HTTP状态码: {response.status_code}")
                
        except Exception as e:
            print(f"  [FAIL] 错误: {str(e)}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    print("\n注意：登录后的页面结构可能与预期不同，需要根据实际页面调整解析逻辑")

if __name__ == '__main__':
    session = interactive_login()
    if session:
        test_get_news(session)
