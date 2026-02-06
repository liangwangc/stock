#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Tushare网页链接是否能获取新闻数据
"""
import os
import sys
import io
import requests
from bs4 import BeautifulSoup
import time

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_tushare_web_link(url, source_name):
    """测试单个Tushare网页链接"""
    print(f"\n{'='*80}")
    print(f"测试: {source_name}")
    print(f"URL: {url}")
    print(f"{'='*80}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://tushare.pro/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"状态码: {response.status_code}")
        print(f"响应长度: {len(response.text)} 字符")
        
        if response.status_code != 200:
            print(f"[FAIL] HTTP状态码: {response.status_code}")
            return False
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 检查是否是登录页面
        page_title = soup.find('title')
        title_text = page_title.get_text() if page_title else ''
        
        login_form = soup.find('form', id='login-form') or soup.find('form', class_=lambda x: x and 'login' in str(x).lower())
        
        if '登录' in title_text or 'login' in title_text.lower() or login_form:
            print(f"[FAIL] 这是登录页面，需要登录才能访问")
            print(f"页面标题: {title_text}")
            return False
        
        # 尝试查找新闻内容
        print(f"\n页面标题: {title_text}")
        
        # 查找可能的新闻列表
        news_containers = []
        
        # 尝试多种选择器
        selectors = [
            'div.news-list', 'div.news-item', 'div.item', 'li.news-item',
            'li.item', 'div.list-item', 'article', 'div.article', 'div.content-item'
        ]
        
        for selector in selectors:
            containers = soup.select(selector)
            if containers:
                news_containers = containers
                print(f"[OK] 使用选择器 '{selector}' 找到 {len(containers)} 个可能的新闻项")
                break
        
        if not news_containers:
            # 查找包含链接的元素
            all_links = soup.find_all('a', href=True)
            print(f"\n找到 {len(all_links)} 个链接")
            
            # 查找可能包含新闻的链接
            news_links = []
            for link in all_links[:20]:  # 只检查前20个
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if text and len(text) > 10 and ('news' in href.lower() or 'article' in href.lower() or len(text) > 20):
                    news_links.append((text[:50], href[:80]))
            
            if news_links:
                print(f"\n找到 {len(news_links)} 个可能的新闻链接:")
                for i, (text, href) in enumerate(news_links[:5], 1):
                    print(f"  {i}. {text} -> {href}")
            else:
                print(f"\n[FAIL] 未找到明显的新闻内容")
                print(f"页面内容预览: {soup.get_text()[:300]}")
                return False
        
        # 尝试提取新闻
        news_count = 0
        for container in news_containers[:10]:
            title_elem = container.find(['a', 'h1', 'h2', 'h3', 'h4', '.title'])
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 5:
                    news_count += 1
                    if news_count <= 3:
                        print(f"  新闻 {news_count}: {title[:60]}")
        
        if news_count > 0:
            print(f"\n[OK] 找到 {news_count} 条可能的新闻")
            return True
        else:
            print(f"\n[FAIL] 未找到新闻内容")
            return False
            
    except requests.exceptions.Timeout:
        print(f"[FAIL] 请求超时")
        return False
    except Exception as e:
        print(f"[FAIL] 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """测试所有Tushare网页链接"""
    print("=" * 80)
    print("测试Tushare网页链接是否能获取新闻数据")
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
    
    results = {}
    
    for src, name in news_sources.items():
        url = f"{base_url}/{src}"
        success = test_tushare_web_link(url, name)
        results[name] = success
        
        # 等待一下，避免请求过快
        if src != list(news_sources.keys())[-1]:  # 不是最后一个
            time.sleep(2)
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("测试汇总")
    print("=" * 80)
    
    success_count = sum(1 for v in results.values() if v)
    fail_count = len(results) - success_count
    
    print(f"总计: {len(results)} 个链接")
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")
    
    print("\n成功获取数据的链接:")
    for name, success in results.items():
        if success:
            print(f"  ✅ {name}")
    
    print("\n无法获取数据的链接:")
    for name, success in results.items():
        if not success:
            print(f"  ❌ {name}")
    
    print("\n" + "=" * 80)
    print("结论:")
    if fail_count == len(results):
        print("所有网页链接都无法获取新闻数据（需要登录）")
        print("建议：禁用 TushareWebNewsSource，只使用 TuShareNewsSource（API方式）")
    elif success_count > 0:
        print(f"部分链接可以获取数据，但大部分需要登录")
    print("=" * 80)

if __name__ == '__main__':
    main()
