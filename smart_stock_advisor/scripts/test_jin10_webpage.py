#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试从金十数据网页获取新闻
检查网页实际使用的API
"""
import os
import sys
import io
import requests
from datetime import datetime
import json
import re
from bs4 import BeautifulSoup

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

from utils.logger import get_logger

logger = get_logger(__name__)


def test_jin10_webpage():
    """测试从金十数据网页获取数据"""
    print("\n" + "=" * 80)
    print("测试从金十数据网页获取数据")
    print("=" * 80)
    
    url = "https://www.jin10.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    print(f"\n1. 获取网页HTML内容")
    print(f"   URL: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   状态码: {response.status_code}")
        print(f"   响应长度: {len(response.text)} 字符")
        
        if response.status_code == 200:
            html = response.text
            print(f"   HTML前500字符: {html[:500]}")
            
            # 尝试解析HTML
            print(f"\n2. 解析HTML内容")
            try:
                soup = BeautifulSoup(html, 'html.parser')
                
                # 查找可能的新闻数据
                # 检查是否有内联的JSON数据
                scripts = soup.find_all('script')
                print(f"   找到 {len(scripts)} 个script标签")
                
                # 查找包含新闻数据的script标签
                news_data_found = False
                for i, script in enumerate(scripts):
                    script_content = script.string
                    if script_content:
                        # 查找可能的API URL
                        api_urls = re.findall(r'https?://[^\s"\'<>]+(?:api|flash|rili)[^\s"\'<>]*', script_content)
                        if api_urls:
                            print(f"   Script {i} 中找到API URL: {api_urls[:5]}")
                            news_data_found = True
                        
                        # 查找可能的JSON数据
                        json_matches = re.findall(r'\{[^{}]*"title"[^{}]*\}', script_content)
                        if json_matches:
                            print(f"   Script {i} 中找到可能的JSON数据: {len(json_matches)} 条")
                            news_data_found = True
                
                if not news_data_found:
                    print("   未在HTML中找到明显的新闻数据（可能是动态加载）")
                
            except Exception as e:
                print(f"   解析HTML失败: {str(e)}")
            
            # 检查响应头中的线索
            print(f"\n3. 检查响应头")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"   Server: {response.headers.get('Server', 'N/A')}")
            
    except Exception as e:
        print(f"   [FAIL] 请求失败: {str(e)}")
        import traceback
        print(traceback.format_exc())


def test_jin10_api_from_webpage():
    """测试网页可能使用的API"""
    print("\n" + "=" * 80)
    print("测试网页可能使用的API")
    print("=" * 80)
    
    # 根据网页分析，可能的API端点
    api_endpoints = [
        {
            'name': '快讯列表API',
            'url': 'https://flash-api.jin10.com/get_flash_list',
            'params': {
                'max_time': int(datetime.now().timestamp() * 1000),
                'channel': '-8200'  # A股
            }
        },
        {
            'name': '快讯列表API（市场）',
            'url': 'https://flash-api.jin10.com/get_flash_list',
            'params': {
                'max_time': int(datetime.now().timestamp() * 1000),
                'channel': '-8200,-8201'  # A股+市场
            }
        },
        {
            'name': '日历快讯API',
            'url': 'https://rili.jin10.com/dc/news/newsFlash',
            'params': None
        },
        {
            'name': '新闻列表API',
            'url': 'https://api.jin10.com/news/list',
            'params': {
                'limit': 20
            }
        },
        {
            'name': '快讯WebSocket端点（模拟）',
            'url': 'wss://flash-api.jin10.com/ws',
            'params': None,
            'is_websocket': True
        }
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.jin10.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Origin': 'https://www.jin10.com'
    }
    
    for endpoint in api_endpoints:
        if endpoint.get('is_websocket'):
            print(f"\n{endpoint['name']}: {endpoint['url']}")
            print("   [跳过] WebSocket需要特殊处理")
            continue
        
        print(f"\n{endpoint['name']}: {endpoint['url']}")
        try:
            response = requests.get(
                endpoint['url'],
                params=endpoint['params'],
                headers=headers,
                timeout=10
            )
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   响应类型: JSON")
                    
                    # 检查数据结构
                    if isinstance(data, dict):
                        keys = list(data.keys())[:10]
                        print(f"   数据键: {keys}")
                        
                        # 查找新闻数据
                        items = []
                        if 'data' in data:
                            items = data['data'] if isinstance(data['data'], list) else []
                        elif 'result' in data:
                            items = data['result'] if isinstance(data['result'], list) else []
                        elif 'list' in data:
                            items = data['list'] if isinstance(data['list'], list) else []
                        
                        if items:
                            print(f"   [OK] 找到 {len(items)} 条新闻数据")
                            if len(items) > 0:
                                print(f"   示例数据: {json.dumps(items[0], ensure_ascii=False, indent=2)[:300]}")
                        else:
                            print(f"   响应数据: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
                    elif isinstance(data, list):
                        print(f"   [OK] 找到 {len(data)} 条数据（列表格式）")
                        if len(data) > 0:
                            print(f"   示例数据: {json.dumps(data[0], ensure_ascii=False, indent=2)[:300]}")
                    else:
                        print(f"   响应数据: {str(data)[:500]}")
                        
                except json.JSONDecodeError:
                    print(f"   响应类型: 文本")
                    print(f"   响应内容: {response.text[:500]}")
            else:
                print(f"   响应内容: {response.text[:300]}")
                
        except requests.exceptions.Timeout:
            print(f"   [FAIL] 请求超时")
        except Exception as e:
            print(f"   [FAIL] 请求失败: {str(e)}")


if __name__ == '__main__':
    print("=" * 80)
    print("金十数据网页数据获取测试")
    print("=" * 80)
    
    # 测试网页HTML
    test_jin10_webpage()
    
    # 测试可能的API
    test_jin10_api_from_webpage()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
