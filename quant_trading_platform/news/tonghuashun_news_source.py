"""
同花顺新闻源
"""
import requests
from typing import List, Dict
from datetime import datetime
from bs4 import BeautifulSoup
from .news_source import BaseNewsSource
from utils.logger import get_logger

logger = get_logger(__name__)

class TonghuashunNewsSource(BaseNewsSource):
    """同花顺新闻源"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.logger = logger
        self.base_url = 'https://www.10jqka.com.cn'
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取股票相关新闻"""
        news_list = []
        try:
            # 同花顺股票新闻接口
            url = f'{self.base_url}/stock/{symbol}/news/'
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 解析新闻列表（根据实际网页结构调整）
                news_items = soup.find_all('div', class_='news-item')[:limit]
                if not news_items:
                    # 尝试其他可能的类名
                    news_items = soup.find_all('li', class_='news-item')[:limit]
                
                for item in news_items[:limit]:
                    title_elem = item.find('a') or item.find('h3')
                    time_elem = item.find('time') or item.find('span', class_='time')
                    
                    if title_elem:
                        title = title_elem.text.strip()
                        url_link = title_elem.get('href', '')
                        if url_link and not url_link.startswith('http'):
                            url_link = self.base_url + url_link
                        
                        # 解析时间
                        time_str = time_elem.text.strip() if time_elem else ''
                        news_time = self._parse_time(time_str)
                        
                        news_list.append({
                            'title': title,
                            'content': '',
                            'time': news_time,
                            'url': url_link,
                            'source': '同花顺',
                            'type': 'stock'
                        })
        except Exception as e:
            self.logger.warning(f"从同花顺获取新闻失败: {str(e)}")
        
        return news_list[:limit]
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        news_list = []
        try:
            url = f'{self.base_url}/news/'
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                news_items = soup.find_all('div', class_='news-item')[:limit]
                if not news_items:
                    news_items = soup.find_all('li', class_='news-item')[:limit]
                
                for item in news_items[:limit]:
                    title_elem = item.find('a') or item.find('h3')
                    time_elem = item.find('time') or item.find('span', class_='time')
                    
                    if title_elem:
                        title = title_elem.text.strip()
                        url_link = title_elem.get('href', '')
                        if url_link and not url_link.startswith('http'):
                            url_link = self.base_url + url_link
                        
                        time_str = time_elem.text.strip() if time_elem else ''
                        news_time = self._parse_time(time_str)
                        
                        news_list.append({
                            'title': title,
                            'content': '',
                            'time': news_time,
                            'url': url_link,
                            'source': '同花顺',
                            'type': 'market'
                        })
        except Exception as e:
            self.logger.warning(f"从同花顺获取市场新闻失败: {str(e)}")
        
        return news_list[:limit]
    
    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        try:
            # 尝试多种时间格式
            if '今天' in time_str or '今日' in time_str:
                return datetime.now()
            elif '昨天' in time_str or '昨日' in time_str:
                from datetime import timedelta
                return datetime.now() - timedelta(days=1)
            elif '小时前' in time_str:
                hours = int(time_str.split('小时前')[0])
                from datetime import timedelta
                return datetime.now() - timedelta(hours=hours)
            elif '分钟前' in time_str:
                minutes = int(time_str.split('分钟前')[0])
                from datetime import timedelta
                return datetime.now() - timedelta(minutes=minutes)
            else:
                # 尝试标准格式
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d']:
                    try:
                        return datetime.strptime(time_str, fmt)
                    except:
                        continue
        except:
            pass
        
        return datetime.now()


