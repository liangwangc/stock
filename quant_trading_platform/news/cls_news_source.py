"""
财联社新闻源
财联社是专业财经媒体，新闻及时
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime, timedelta
from .news_source import BaseNewsSource
from utils.logger import get_logger
import re
import json

logger = get_logger(__name__)

class CLSNewsSource(BaseNewsSource):
    """财联社新闻源"""
    
    def __init__(self):
        self.logger = logger
        self.base_url = "https://www.cls.cn"
        self.api_url = "https://www.cls.cn/api/sw"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.cls.cn/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取股票相关新闻"""
        news_list = []
        
        # 方法1: 尝试使用API接口
        try:
            # 财联社可能有API接口，这里提供一个基础框架
            api_params = {
                'app': 'CailianpressWeb',
                'os': 'web',
                'sv': '7.7.5',
                'sign': '',
                'token': '',
                'keyword': symbol,
                'page': 1,
                'rn': limit
            }
            
            response = requests.get(self.api_url, params=api_params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'data' in data and 'list' in data['data']:
                        for item in data['data']['list'][:limit]:
                            news_list.append({
                                'title': item.get('title', ''),
                                'content': item.get('brief', ''),
                                'time': self._parse_api_time(item.get('ctime', '')),
                                'url': item.get('shareurl', '') or f"{self.base_url}/detail/{item.get('id', '')}",
                                'source': '财联社'
                            })
                except:
                    pass
        except Exception as e:
            self.logger.debug(f"财联社API获取失败: {str(e)}")
        
        # 方法2: 如果API失败，使用网页爬虫
        if not news_list:
            urls_to_try = [
                f"{self.base_url}/search?keyword={symbol}",  # 搜索URL
                f"{self.base_url}/stock/{symbol}/",  # 股票页面
            ]
            
            for url in urls_to_try:
                try:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 查找新闻列表
                        news_items = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'news|item|list|article|card', re.I))
                        
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
                                        link = 'https://www.cls.cn' + link
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
                                    'source': '财联社'
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
        
        self.logger.info(f"从财联社获取到 {len(news_list)} 条新闻")
        return news_list[:limit]
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        news_list = []
        
        # 方法1: 尝试使用API接口
        try:
            api_params = {
                'app': 'CailianpressWeb',
                'os': 'web',
                'sv': '7.7.5',
                'sign': '',
                'token': '',
                'page': 1,
                'rn': limit
            }
            
            response = requests.get(self.api_url, params=api_params, headers=self.headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'data' in data and 'list' in data['data']:
                        for item in data['data']['list'][:limit]:
                            news_list.append({
                                'title': item.get('title', ''),
                                'content': item.get('brief', ''),
                                'time': self._parse_api_time(item.get('ctime', '')),
                                'url': item.get('shareurl', '') or f"{self.base_url}/detail/{item.get('id', '')}",
                                'source': '财联社'
                            })
                except:
                    pass
        except Exception as e:
            self.logger.debug(f"财联社API获取失败: {str(e)}")
        
        # 方法2: 如果API失败，使用网页爬虫
        if not news_list:
            urls_to_try = [
                f"{self.base_url}/",  # 首页
                f"{self.base_url}/telegraph",  # 电报页面
                f"{self.base_url}/news",  # 新闻页面
            ]
            
            for url in urls_to_try:
                try:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 查找新闻列表
                        news_items = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'news|item|list|article|card|telegraph', re.I))
                        
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
                                        link = 'https://www.cls.cn' + link
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
                                    'source': '财联社'
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
        
        self.logger.info(f"从财联社获取到 {len(news_list)} 条市场新闻")
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
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d', '%m-%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d', '%H:%M']:
                    try:
                        parsed_time = datetime.strptime(time_text, fmt)
                        # 如果没有年份，假设是今年
                        if '%Y' not in fmt and parsed_time.year == 1900:
                            parsed_time = parsed_time.replace(year=now.year)
                        # 如果只有时间，假设是今天
                        if '%Y' not in fmt and '%m' not in fmt and '%d' not in fmt:
                            parsed_time = now.replace(hour=parsed_time.hour, minute=parsed_time.minute)
                        return parsed_time
                    except:
                        continue
                return now
        except:
            return datetime.now()
    
    def _parse_api_time(self, timestamp: str) -> datetime:
        """解析API返回的时间戳"""
        try:
            if isinstance(timestamp, (int, float)):
                # 如果是时间戳（秒）
                if timestamp < 1e10:
                    return datetime.fromtimestamp(timestamp)
                # 如果是毫秒时间戳
                else:
                    return datetime.fromtimestamp(timestamp / 1000)
            elif isinstance(timestamp, str):
                # 尝试解析为时间戳
                try:
                    ts = float(timestamp)
                    if ts < 1e10:
                        return datetime.fromtimestamp(ts)
                    else:
                        return datetime.fromtimestamp(ts / 1000)
                except:
                    # 尝试解析为日期字符串
                    return self._parse_time(timestamp)
            return datetime.now()
        except:
            return datetime.now()
