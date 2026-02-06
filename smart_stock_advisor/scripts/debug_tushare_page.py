#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试Tushare页面结构
"""
import os
import sys
import io
import requests
from bs4 import BeautifulSoup

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def debug_page(url, source_name):
    """调试单个页面"""
    print(f"\n{'='*80}")
    print(f"调试页面: {source_name}")
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
            print(f"请求失败，状态码: {response.status_code}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查看页面标题
        title = soup.find('title')
        if title:
            print(f"\n页面标题: {title.get_text()[:100]}")
        
        # 查找所有可能的新闻容器
        print("\n查找可能的新闻容器...")
        
        # 查找包含"news"、"item"、"list"等关键词的类名
        all_divs = soup.find_all(['div', 'li', 'article', 'ul', 'ol'])
        news_like_elements = []
        for elem in all_divs:
            class_attr = elem.get('class', [])
            if isinstance(class_attr, list):
                class_str = ' '.join(class_attr).lower()
            else:
                class_str = str(class_attr).lower()
            
            id_attr = elem.get('id', '').lower()
            
            if any(keyword in class_str or keyword in id_attr for keyword in ['news', 'item', 'list', 'article', 'content']):
                news_like_elements.append((elem.name, class_str, id_attr, len(elem.get_text())))
        
        if news_like_elements:
            print(f"\n找到 {len(news_like_elements)} 个可能的新闻容器:")
            for i, (tag, cls, id_, text_len) in enumerate(news_like_elements[:20], 1):
                print(f"  {i}. <{tag}> class='{cls[:50]}' id='{id_[:30]}' 文本长度={text_len}")
        
        # 查找所有链接
        links = soup.find_all('a', href=True)
        print(f"\n找到 {len(links)} 个链接")
        if links:
            print("前10个链接:")
            for i, link in enumerate(links[:10], 1):
                href = link.get('href', '')
                text = link.get_text(strip=True)[:50]
                print(f"  {i}. {text} -> {href[:80]}")
        
        # 查找包含时间信息的元素
        import re
        time_pattern = re.compile(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|今天|昨天|\d+[分钟小时天]前')
        time_elements = []
        for elem in soup.find_all(text=time_pattern):
            parent = elem.parent
            if parent:
                time_elements.append((parent.name, parent.get('class', []), elem.strip()[:50]))
        
        if time_elements:
            print(f"\n找到 {len(time_elements)} 个包含时间信息的元素:")
            for i, (tag, cls, time_text) in enumerate(time_elements[:10], 1):
                print(f"  {i}. <{tag}> class='{cls}' 时间: {time_text}")
        
        # 保存HTML到文件用于分析
        html_file = f"debug_{source_name.replace(' ', '_')}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\nHTML已保存到: {html_file}")
        
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # 测试第一个页面
    debug_page('https://tushare.pro/news/yicai', '第一财经')
