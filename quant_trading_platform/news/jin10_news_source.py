"""
金十数据新闻源
金十数据提供财经新闻和实时数据
"""
import requests
from typing import List, Dict
from datetime import datetime
import json
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
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        获取股票相关新闻
        
        Args:
            symbol: 股票代码
            limit: 获取数量
        """
        news_list = []
        try:
            # 金十数据可能需要转换为特定格式
            # 这里提供一个基础实现框架
            
            # 方法1: 使用金十数据API（如果有）
            if self.api_key:
                url = f"{self.base_url}/news/list"
                params = {
                    'category': 'stock',
                    'symbol': symbol,
                    'limit': limit,
                    'api_key': self.api_key
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # 解析返回的数据
                    # news_list = self._parse_jin10_data(data)
            
            # 方法2: 使用金十数据RSS或公开接口
            # 金十数据可能有RSS订阅或公开的新闻接口
            
            # 示例：获取A股新闻
            url = f"https://rili.jin10.com/dc/news/newsFlash"
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        items = data['data'][:limit]
                        for item in items:
                            news_list.append({
                                'title': item.get('title', ''),
                                'content': item.get('content', item.get('summary', '')),
                                'time': datetime.fromtimestamp(item.get('time', 0) / 1000) if item.get('time') else datetime.now(),
                                'url': item.get('link', ''),
                                'source': '金十数据',
                                'type': 'market'
                            })
            except Exception as e:
                self.logger.warning(f"获取金十数据失败: {str(e)}")
            
            self.logger.info(f"从金十数据获取到 {len(news_list)} 条新闻")
            return news_list
            
        except Exception as e:
            self.logger.error(f"获取金十数据新闻失败: {str(e)}")
            return news_list
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        return self.get_stock_news("market", limit)

