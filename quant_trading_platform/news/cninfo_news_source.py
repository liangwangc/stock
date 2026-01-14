"""
巨潮资讯网新闻源
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime
from .news_source import BaseNewsSource
from utils.logger import get_logger
import re
from datetime import timedelta

logger = get_logger(__name__)

class CninfoNewsSource(BaseNewsSource):
    """巨潮资讯网新闻源"""
    
    def __init__(self):
        self.logger = logger
        self.base_url = "http://www.cninfo.com.cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://www.cninfo.com.cn/'
        }
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取股票相关新闻"""
        news_list = []
        try:
            # 巨潮资讯公告查询URL
            url = f"{self.base_url}/new/disclosure/detail?stock={symbol}&announcementId="
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找公告列表
                news_items = soup.find_all(['div', 'li'], class_=re.compile(r'announcement|notice|news', re.I))
                
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
                                link = 'http://www.cninfo.com.cn' + link
                            else:
                                link = self.base_url + '/' + link
                        
                        # 查找时间
                        time_elem = item.find(['span', 'time'], class_=re.compile(r'time|date', re.I))
                        news_time = datetime.now()
                        if time_elem:
                            time_text = time_elem.get_text(strip=True)
                            news_time = self._parse_time(time_text)
                        
                        news_list.append({
                            'title': title,
                            'content': '',
                            'time': news_time,
                            'url': link,
                            'source': '巨潮资讯'
                        })
                        
                        if len(news_list) >= limit:
                            break
                    except Exception as e:
                        self.logger.debug(f"解析公告项失败: {str(e)}")
                        continue
            
            self.logger.info(f"从巨潮资讯获取到 {len(news_list)} 条新闻")
            return news_list[:limit]
            
        except Exception as e:
            self.logger.warning(f"从巨潮资讯获取新闻失败: {str(e)}")
            return news_list
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        news_list = []
        try:
            # 巨潮资讯市场新闻URL
            url = f"{self.base_url}/new/information/topNews"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                news_items = soup.find_all(['div', 'li'], class_=re.compile(r'news|notice', re.I))
                
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
                                link = 'http://www.cninfo.com.cn' + link
                            else:
                                link = self.base_url + '/' + link
                        
                        time_elem = item.find(['span', 'time'], class_=re.compile(r'time|date', re.I))
                        news_time = datetime.now()
                        if time_elem:
                            time_text = time_elem.get_text(strip=True)
                            news_time = self._parse_time(time_text)
                        
                        news_list.append({
                            'title': title,
                            'content': '',
                            'time': news_time,
                            'url': link,
                            'source': '巨潮资讯'
                        })
                        
                        if len(news_list) >= limit:
                            break
                    except:
                        continue
            
            self.logger.info(f"从巨潮资讯获取到 {len(news_list)} 条市场新闻")
            return news_list[:limit]
            
        except Exception as e:
            self.logger.warning(f"从巨潮资讯获取市场新闻失败: {str(e)}")
            return news_list
    
    def _parse_time(self, time_text: str) -> datetime:
        """解析时间文本"""
        try:
            time_text = time_text.strip()
            now = datetime.now()
            
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d']:
                try:
                    return datetime.strptime(time_text, fmt)
                except:
                    continue
            return now
        except:
            return datetime.now()



