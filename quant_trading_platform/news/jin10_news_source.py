"""
金十数据新闻源
金十数据提供财经新闻和实时数据
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
import time
from .news_source import BaseNewsSource
from utils.logger import get_logger

logger = get_logger(__name__)

class Jin10NewsSource(BaseNewsSource):
    """金十数据新闻源"""
    
    def __init__(self, api_key: str = ""):
        """
        初始化金十数据新闻源
        
        Args:
            api_key: 金十数据API密钥（可选，部分接口需要）
        """
        self.api_key = api_key
        self.base_url = "https://api.jin10.com"
        self.logger = logger
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.jin10.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        获取股票相关新闻
        
        Args:
            symbol: 股票代码
            limit: 获取数量
        """
        news_list = []
        
        # 尝试多个URL和方法
        # 注意：这些API端点不是从网页HTML直接解析的，而是通过分析网页的网络请求找到的
        # 网页 https://www.jin10.com/ 是动态加载的，内容通过JavaScript异步获取
        urls_to_try = [
            # 方法1: 金十数据快讯API（网页实际使用的API之一）
            {
                'url': 'https://flash-api.jin10.com/get_flash_list',
                'method': 'get',
                'params': {
                    'max_time': int(datetime.now().timestamp() * 1000),
                    'channel': '-8200'  # A股频道
                },
                'headers': self.headers
            },
            # 方法2: 金十数据快讯API（市场+股票）
            {
                'url': 'https://flash-api.jin10.com/get_flash_list',
                'method': 'get',
                'params': {
                    'max_time': int(datetime.now().timestamp() * 1000),
                    'channel': '-8200,-8201'  # A股+市场
                },
                'headers': self.headers
            },
            # 方法3: 金十数据日历API
            {
                'url': 'https://rili.jin10.com/dc/news/newsFlash',
                'method': 'get',
                'params': None,
                'headers': self.headers
            },
            # 方法4: 金十数据官方API（如果有API密钥）
            {
                'url': f"{self.base_url}/news/list",
                'method': 'get',
                'params': {
                    'category': 'stock',
                    'symbol': symbol if symbol != 'market' else None,
                    'limit': limit
                },
                'headers': self.headers
            } if self.api_key else None,
            # 方法5: 尝试从网页HTML中可能存在的API（备用）
            {
                'url': 'https://www.jin10.com/api/flash/list',
                'method': 'get',
                'params': {
                    'limit': limit
                },
                'headers': self.headers
            },
        ]
        
        # 过滤掉None
        urls_to_try = [u for u in urls_to_try if u is not None]
        
        for url_config in urls_to_try:
            if len(news_list) >= limit:
                break
            
            try:
                url = url_config['url']
                method = url_config.get('method', 'get')
                params = url_config.get('params')
                headers = url_config.get('headers', self.headers)
                
                # 如果有API密钥，添加到参数中
                if self.api_key and 'api_key' not in (params or {}):
                    if params is None:
                        params = {}
                    params['api_key'] = self.api_key
                
                self.logger.debug(f"尝试金十数据URL: {url}")
                
                if method.lower() == 'get':
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                else:
                    response = requests.post(url, json=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # 解析不同格式的响应
                        items = []
                        if isinstance(data, dict):
                            if 'data' in data:
                                items = data['data']
                            elif 'result' in data:
                                items = data['result']
                            elif 'list' in data:
                                items = data['list']
                        elif isinstance(data, list):
                            items = data
                        
                        if items:
                            self.logger.info(f"从金十数据URL {url} 获取到 {len(items)} 条原始数据")
                            
                            for item in items[:limit]:
                                try:
                                    # 解析时间
                                    news_time = datetime.now()
                                    if 'time' in item:
                                        time_val = item['time']
                                        if isinstance(time_val, (int, float)):
                                            # 时间戳（毫秒或秒）
                                            if time_val > 1e10:
                                                news_time = datetime.fromtimestamp(time_val / 1000)
                                            else:
                                                news_time = datetime.fromtimestamp(time_val)
                                        elif isinstance(time_val, str):
                                            try:
                                                news_time = datetime.strptime(time_val, '%Y-%m-%d %H:%M:%S')
                                            except:
                                                news_time = datetime.now()
                                    
                                    # 解析标题和内容
                                    title = item.get('title') or item.get('headline') or item.get('content', '')[:100]
                                    content = item.get('content') or item.get('summary') or item.get('text', '')
                                    
                                    if not title:
                                        continue
                                    
                                    news_item = {
                                        'title': title.strip(),
                                        'content': content.strip() if content else '',
                                        'time': news_time,
                                        'url': item.get('link') or item.get('url') or '',
                                        'source': '金十数据',
                                        'type': 'market'
                                    }
                                    
                                    news_list.append(news_item)
                                    
                                    if len(news_list) >= limit:
                                        break
                                        
                                except Exception as e:
                                    self.logger.debug(f"解析金十数据新闻项失败: {str(e)}")
                                    continue
                            
                            # 如果成功获取到新闻，跳出循环
                            if news_list:
                                break
                    except json.JSONDecodeError:
                        self.logger.debug(f"金十数据URL {url} 返回的不是JSON格式")
                        continue
                    except Exception as e:
                        self.logger.debug(f"解析金十数据响应失败: {str(e)}")
                        continue
                else:
                    self.logger.debug(f"金十数据URL {url} 返回状态码: {response.status_code}")
                    continue
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"金十数据URL {url_config['url']} 请求超时")
                continue
            except requests.exceptions.RequestException as e:
                self.logger.debug(f"金十数据URL {url_config['url']} 请求失败: {str(e)}")
                continue
            except Exception as e:
                self.logger.debug(f"金十数据URL {url_config['url']} 处理失败: {str(e)}")
                continue
        
        self.logger.info(f"从金十数据获取到 {len(news_list)} 条新闻")
        return news_list[:limit]
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        return self.get_stock_news("market", limit)

