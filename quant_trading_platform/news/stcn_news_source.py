"""
证券时报新闻源
证券时报是官方财经媒体，新闻质量高
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime, timedelta
from .news_source import BaseNewsSource
from utils.logger import get_logger
import re

logger = get_logger(__name__)

class STCNNewsSource(BaseNewsSource):
    """证券时报新闻源"""
    
    def __init__(self):
        self.logger = logger
        self.base_url = "http://www.stcn.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://www.stcn.com/'
        }
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取股票相关新闻"""
        news_list = []
        
        # 备用URL列表
        urls_to_try = [
            f"{self.base_url}/stock/{symbol}/",  # 主要URL
            f"{self.base_url}/stock/stockzt/{symbol}/",  # 备用URL 1
            f"{self.base_url}/stock/stocknews/{symbol}/",  # 备用URL 2
        ]
        
        for url in urls_to_try:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找新闻列表
                    news_items = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'news|item|list|article', re.I))
                    
                    for item in news_items[:limit * 2]:
                        try:
                            title_elem = item.find('a')
                            if not title_elem:
                                continue
                            
                            title = title_elem.get_text(strip=True)
                            if not title or len(title) < 5:
                                continue
                            
                            link = title_elem.get('href', '')
                            if not link.startswith('http'):
                                if link.startswith('/'):
                                    link = 'http://www.stcn.com' + link
                                else:
                                    link = self.base_url + '/' + link
                            
                            # 查找时间
                            time_elem = item.find(['span', 'time', 'em'], class_=re.compile(r'time|date', re.I))
                            news_time = datetime.now()
                            if time_elem:
                                time_text = time_elem.get_text(strip=True)
                                news_time = self._parse_time(time_text)
                            
                            news_list.append({
                                'title': title,
                                'content': '',
                                'time': news_time,
                                'url': link,
                                'source': '证券时报'
                            })
                            
                            if len(news_list) >= limit:
                                break
                        except Exception as e:
                            self.logger.debug(f"解析新闻项失败: {str(e)}")
                            continue
                    
                    # 如果成功获取到新闻，跳出循环
                    if news_list:
                        break
            except Exception as e:
                self.logger.debug(f"尝试URL {url} 失败: {str(e)}")
                continue
        
        self.logger.info(f"从证券时报获取到 {len(news_list)} 条新闻")
        return news_list[:limit]
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        news_list = []
        
        # 备用URL列表
        urls_to_try = [
            f"{self.base_url}/stock/",  # 主要URL
            f"{self.base_url}/stock/market/",  # 备用URL 1
            f"{self.base_url}/news/",  # 备用URL 2
            f"{self.base_url}/stock/stocknews/",  # 备用URL 3
        ]
        
        for url in urls_to_try:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找新闻列表
                    news_items = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'news|item|list|article', re.I))
                    
                    for item in news_items[:limit * 2]:
                        try:
                            title_elem = item.find('a')
                            if not title_elem:
                                continue
                            
                            title = title_elem.get_text(strip=True)
                            if not title or len(title) < 5:
                                continue
                            
                            link = title_elem.get('href', '')
                            if not link.startswith('http'):
                                if link.startswith('/'):
                                    link = 'http://www.stcn.com' + link
                                else:
                                    link = self.base_url + '/' + link
                            
                            # 查找时间
                            time_elem = item.find(['span', 'time', 'em'], class_=re.compile(r'time|date', re.I))
                            news_time = datetime.now()
                            if time_elem:
                                time_text = time_elem.get_text(strip=True)
                                news_time = self._parse_time(time_text)
                            
                            news_list.append({
                                'title': title,
                                'content': '',
                                'time': news_time,
                                'url': link,
                                'source': '证券时报'
                            })
                            
                            if len(news_list) >= limit:
                                break
                        except Exception as e:
                            self.logger.debug(f"解析新闻项失败: {str(e)}")
                            continue
                    
                    # 如果成功获取到新闻，跳出循环
                    if news_list:
                        break
            except Exception as e:
                self.logger.debug(f"尝试URL {url} 失败: {str(e)}")
                continue
        
        self.logger.info(f"从证券时报获取到 {len(news_list)} 条市场新闻")
        return news_list[:limit]
    
    def _parse_time(self, time_text: str) -> datetime:
        """解析时间文本"""
        try:
            time_text = time_text.strip()
            now = datetime.now()
            
            if '今天' in time_text or '今日' in time_text:
                return now
            elif '昨天' in time_text or '昨日' in time_text:
                return now - timedelta(days=1)
            elif '分钟前' in time_text:
                minutes = int(re.search(r'(\d+)', time_text).group(1))
                return now - timedelta(minutes=minutes)
            elif '小时前' in time_text:
                hours = int(re.search(r'(\d+)', time_text).group(1))
                return now - timedelta(hours=hours)
            else:
                # 尝试解析标准时间格式
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%m-%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d']:
                    try:
                        parsed_time = datetime.strptime(time_text, fmt)
                        # 如果没有年份，假设是今年
                        if '%Y' not in fmt and parsed_time.year == 1900:
                            parsed_time = parsed_time.replace(year=now.year)
                        return parsed_time
                    except:
                        continue
                return now
        except:
            return datetime.now()
