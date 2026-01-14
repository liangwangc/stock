"""
雪球新闻源
"""
import requests
from typing import List, Dict
from datetime import datetime
from .news_source import BaseNewsSource
from utils.logger import get_logger
import json

logger = get_logger(__name__)

class XueqiuNewsSource(BaseNewsSource):
    """雪球新闻源"""
    
    def __init__(self):
        self.logger = logger
        self.base_url = "https://xueqiu.com"
        self.api_url = "https://xueqiu.com/v4/statuses/search.json"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://xueqiu.com/'
        }
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取股票相关新闻"""
        news_list = []
        try:
            # 雪球API需要股票代码转换（如000001 -> SZ000001）
            if symbol.startswith('0') or symbol.startswith('3'):
                xueqiu_symbol = f"SZ{symbol}"
            elif symbol.startswith('6'):
                xueqiu_symbol = f"SH{symbol}"
            else:
                xueqiu_symbol = symbol
            
            # 使用雪球搜索API
            params = {
                'symbol': xueqiu_symbol,
                'count': limit,
                'comment': '0',
                'hl': '0',
                'source': 'all',
                'sort': 'time'
            }
            
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'list' in data:
                    for item in data['list'][:limit]:
                        try:
                            title = item.get('title', item.get('text', ''))[:100]
                            if title:
                                news_list.append({
                                    'title': title,
                                    'content': item.get('text', ''),
                                    'time': datetime.fromtimestamp(item.get('created_at', 0) / 1000) if item.get('created_at') else datetime.now(),
                                    'url': f"{self.base_url}/S/{xueqiu_symbol}/{item.get('id', '')}",
                                    'source': '雪球'
                                })
                        except:
                            continue
            
            self.logger.info(f"从雪球获取到 {len(news_list)} 条新闻")
            return news_list[:limit]
            
        except Exception as e:
            self.logger.warning(f"从雪球获取新闻失败: {str(e)}")
            return news_list
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        news_list = []
        try:
            # 获取热门话题/市场新闻
            params = {
                'count': limit,
                'comment': '0',
                'hl': '0',
                'source': 'all',
                'sort': 'time'
            }
            
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'list' in data:
                    for item in data['list'][:limit]:
                        try:
                            title = item.get('title', item.get('text', ''))[:100]
                            if title:
                                news_list.append({
                                    'title': title,
                                    'content': item.get('text', ''),
                                    'time': datetime.fromtimestamp(item.get('created_at', 0) / 1000) if item.get('created_at') else datetime.now(),
                                    'url': f"{self.base_url}/statuses/{item.get('id', '')}",
                                    'source': '雪球'
                                })
                        except:
                            continue
            
            self.logger.info(f"从雪球获取到 {len(news_list)} 条市场新闻")
            return news_list[:limit]
            
        except Exception as e:
            self.logger.warning(f"从雪球获取市场新闻失败: {str(e)}")
            return news_list

