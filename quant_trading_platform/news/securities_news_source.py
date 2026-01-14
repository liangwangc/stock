"""
各大证券公司新闻源
包括：中信证券、海通证券、广发证券等
"""
import requests
from typing import List, Dict
from datetime import datetime
from bs4 import BeautifulSoup
from .news_source import BaseNewsSource
from utils.logger import get_logger

logger = get_logger(__name__)

class SecuritiesNewsSource(BaseNewsSource):
    """证券公司新闻源聚合"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.logger = logger
        
        # 各大证券公司网站
        self.sources = {
            'gf': {
                'name': '广发证券',
                'base_url': 'https://www.gf.com.cn',
                'news_url': '/research/news'
            },
            'citics': {
                'name': '中信证券',
                'base_url': 'https://www.citics.com',
                'news_url': '/research/news'
            },
            'htsec': {
                'name': '海通证券',
                'base_url': 'https://www.htsec.com',
                'news_url': '/news'
            }
        }
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取股票相关新闻"""
        all_news = []
        
        for source_key, source_info in self.sources.items():
            try:
                news = self._get_from_source(source_info, symbol, limit // len(self.sources))
                all_news.extend(news)
            except Exception as e:
                self.logger.warning(f"从{source_info['name']}获取新闻失败: {str(e)}")
        
        # 按时间排序，取最新的
        all_news.sort(key=lambda x: x.get('time', datetime.min), reverse=True)
        return all_news[:limit]
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        all_news = []
        
        for source_key, source_info in self.sources.items():
            try:
                news = self._get_market_from_source(source_info, limit // len(self.sources))
                all_news.extend(news)
            except Exception as e:
                self.logger.warning(f"从{source_info['name']}获取市场新闻失败: {str(e)}")
        
        all_news.sort(key=lambda x: x.get('time', datetime.min), reverse=True)
        return all_news[:limit]
    
    def _get_from_source(self, source_info: Dict, symbol: str, limit: int) -> List[Dict]:
        """从单个来源获取新闻"""
        news_list = []
        try:
            url = source_info['base_url'] + source_info['news_url']
            
            response = requests.get(url, headers=self.headers, timeout=10, params={'keyword': symbol})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 根据实际网页结构解析（需要根据每个网站调整）
                news_items = soup.find_all('div', class_='news-item')[:limit]
                
                for item in news_items:
                    title_elem = item.find('a')
                    time_elem = item.find('time') or item.find('span', class_='time')
                    
                    if title_elem:
                        news_list.append({
                            'title': title_elem.text.strip(),
                            'content': '',
                            'time': datetime.now(),
                            'url': title_elem.get('href', ''),
                            'source': source_info['name'],
                            'type': 'stock'
                        })
        except Exception as e:
            self.logger.warning(f"从{source_info['name']}获取新闻出错: {str(e)}")
        
        return news_list
    
    def _get_market_from_source(self, source_info: Dict, limit: int) -> List[Dict]:
        """从单个来源获取市场新闻"""
        return self._get_from_source(source_info, 'market', limit)

