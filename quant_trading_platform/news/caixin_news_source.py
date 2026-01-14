"""
财新新闻源
财新网财经新闻
"""
import requests
from typing import List, Dict
from datetime import datetime
from bs4 import BeautifulSoup
from .news_source import BaseNewsSource
from utils.logger import get_logger

logger = get_logger(__name__)

class CaixinNewsSource(BaseNewsSource):
    """财新新闻源"""
    
    def __init__(self):
        self.base_url = "http://www.caixin.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.logger = logger
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取股票相关新闻"""
        news_list = []
        try:
            # 财新网股票新闻页面
            url = f"{self.base_url}/search"
            params = {
                'keyword': symbol,
                'page': 1
            }
            
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 解析新闻列表（需要根据实际HTML结构调整）
                    news_items = soup.find_all('div', class_='news-item')[:limit]
                    
                    for item in news_items:
                        title_elem = item.find('a', class_='title')
                        time_elem = item.find('span', class_='time')
                        summary_elem = item.find('div', class_='summary')
                        
                        if title_elem:
                            news_list.append({
                                'title': title_elem.text.strip(),
                                'content': summary_elem.text.strip() if summary_elem else '',
                                'time': self._parse_time(time_elem.text.strip() if time_elem else ''),
                                'url': self.base_url + title_elem.get('href', '') if title_elem.get('href', '').startswith('/') else title_elem.get('href', ''),
                                'source': '财新网',
                                'type': 'stock'
                            })
            except Exception as e:
                self.logger.warning(f"获取财新新闻失败: {str(e)}")
            
            self.logger.info(f"从财新获取到 {len(news_list)} 条新闻")
            return news_list
            
        except Exception as e:
            self.logger.error(f"获取财新新闻失败: {str(e)}")
            return news_list
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        news_list = []
        try:
            # 财新网财经频道
            url = f"{self.base_url}/finance"
            
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 解析新闻列表
                    news_items = soup.find_all('article', class_='news-item')[:limit]
                    
                    for item in news_items:
                        title_elem = item.find('h2')
                        time_elem = item.find('time')
                        summary_elem = item.find('p')
                        link_elem = item.find('a')
                        
                        if title_elem and link_elem:
                            news_list.append({
                                'title': title_elem.text.strip(),
                                'content': summary_elem.text.strip() if summary_elem else '',
                                'time': self._parse_time(time_elem.get('datetime', '') if time_elem else ''),
                                'url': link_elem.get('href', ''),
                                'source': '财新网',
                                'type': 'market'
                            })
            except Exception as e:
                self.logger.warning(f"获取财新市场新闻失败: {str(e)}")
            
            return news_list
            
        except Exception as e:
            self.logger.error(f"获取财新市场新闻失败: {str(e)}")
            return news_list
    
    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        try:
            # 尝试多种时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except:
                    continue
            
            return datetime.now()
        except:
            return datetime.now()

