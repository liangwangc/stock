"""
Tushare网页新闻源
从Tushare新闻聚合页面获取数据
支持账号密码登录
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
import os
import time
import io
from bs4 import BeautifulSoup
from .news_source import BaseNewsSource
from utils.logger import get_logger

# 可选导入PIL和pytesseract（用于OCR识别验证码）
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

logger = get_logger(__name__)

class TushareWebNewsSource(BaseNewsSource):
    """Tushare网页新闻源，从多个新闻聚合页面获取数据"""
    
    # 新闻源配置：URL路径 -> 源名称
    NEWS_SOURCES = {
        'yicai': '第一财经',
        'fenghuang': '凤凰财经',
        '10jqka': '同花顺',
        'jinrongjie': '金融界',
        'sina': '新浪财经',
        'yuncaijing': '云财经',
        'eastmoney': '东方财富'
    }
    
    def __init__(self, username: str = None, password: str = None):
        """
        初始化Tushare网页新闻源
        
        Args:
            username: Tushare账号（手机或邮箱）
            password: Tushare密码
        """
        self.logger = logger
        self.base_url = "https://tushare.pro"
        self.username = username
        self.password = password
        self.session = requests.Session()  # 使用Session维护登录状态
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://tushare.pro/'
        }
        self.session.headers.update(self.headers)
        self._logged_in = False
        
        # 如果提供了账号密码，尝试登录（静默模式，失败不报错）
        if self.username and self.password:
            try:
                self._login()
            except Exception as e:
                self.logger.debug(f"初始化时登录失败: {str(e)}")
                # 不抛出异常，允许后续手动登录
    
    def _get_captcha(self, unique_id: str = None) -> tuple:
        """
        获取验证码图片和unique_id
        
        Returns:
            (验证码图片数据, unique_id) 或 (None, None)
        """
        try:
            if not unique_id:
                # 生成一个unique_id（通常是一个时间戳或UUID）
                import uuid
                unique_id = str(uuid.uuid4()).replace('-', '')
            
            captcha_url = f"{self.base_url}/captcha?action=login&unique_id={unique_id}"
            response = self.session.get(captcha_url, timeout=10)
            
            if response.status_code == 200:
                return response.content, unique_id
            else:
                self.logger.debug(f"获取验证码失败，状态码: {response.status_code}")
                return None, None
        except Exception as e:
            self.logger.debug(f"获取验证码失败: {str(e)}")
            return None, None
    
    def _login(self, captcha_code: str = None, max_retries: int = 3) -> bool:
        """
        登录Tushare
        
        Args:
            captcha_code: 验证码（如果提供，则使用；否则尝试OCR识别）
            max_retries: 最大重试次数（验证码错误时）
            
        Returns:
            是否登录成功
        """
        if not self.username or not self.password:
            self.logger.warning("未提供账号或密码，无法登录")
            return False
        
        for attempt in range(max_retries):
            try:
                # 1. 访问登录页面，获取_xsrf token
                login_page_url = f"{self.base_url}/login"
                response = self.session.get(login_page_url, timeout=10)
                
                if response.status_code != 200:
                    self.logger.warning(f"访问登录页面失败，状态码: {response.status_code}")
                    return False
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取_xsrf token
                xsrf_input = soup.find('input', {'name': '_xsrf'})
                if not xsrf_input:
                    self.logger.warning("无法找到_xsrf token")
                    return False
                
                xsrf_token = xsrf_input.get('value', '')
                
                # 2. 获取验证码
                import uuid
                unique_id = str(uuid.uuid4()).replace('-', '')
                captcha_img, _ = self._get_captcha(unique_id)
                
                if not captcha_img:
                    self.logger.warning("无法获取验证码图片")
                    return False
                
                # 3. 处理验证码
                current_captcha = captcha_code
                
                if not current_captcha:
                    # 尝试OCR识别验证码
                    if PIL_AVAILABLE and PYTESSERACT_AVAILABLE:
                        try:
                            img = Image.open(io.BytesIO(captcha_img))
                            # 预处理图片以提高识别率
                            img = img.convert('L')  # 转为灰度
                            current_captcha = pytesseract.image_to_string(img, config='--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ').strip()
                            self.logger.debug(f"OCR识别验证码: {current_captcha}")
                            
                            # 清理识别结果
                            current_captcha = re.sub(r'[^0-9A-Za-z]', '', current_captcha)
                            
                            if len(current_captcha) != 4:
                                self.logger.warning(f"验证码识别结果长度不正确: {current_captcha}")
                                # 保存图片供调试
                                try:
                                    captcha_path = os.path.join(os.path.dirname(__file__), '..', '..', 'smart_stock_advisor', 'captcha_temp.png')
                                    os.makedirs(os.path.dirname(captcha_path), exist_ok=True)
                                    with open(captcha_path, 'wb') as f:
                                        f.write(captcha_img)
                                    self.logger.info(f"验证码图片已保存到: {captcha_path}")
                                except:
                                    pass
                                current_captcha = None  # 清除识别结果，需要手动输入
                        except Exception as e:
                            self.logger.debug(f"OCR识别验证码失败: {str(e)}")
                            current_captcha = None
                    else:
                        self.logger.debug("未安装pytesseract或PIL，无法自动识别验证码")
                        # 保存验证码图片供手动输入
                        try:
                            captcha_path = os.path.join(os.path.dirname(__file__), '..', '..', 'smart_stock_advisor', 'captcha_temp.png')
                            os.makedirs(os.path.dirname(captcha_path), exist_ok=True)
                            with open(captcha_path, 'wb') as f:
                                f.write(captcha_img)
                            self.logger.info(f"验证码图片已保存到: {captcha_path}，请手动查看并输入验证码")
                        except Exception as e:
                            self.logger.debug(f"保存验证码图片失败: {str(e)}")
                
                if not current_captcha:
                    self.logger.warning("无法获取验证码，请手动提供或安装pytesseract")
                    return False
                
                # 4. 提交登录表单
                login_url = f"{self.base_url}/login"
                login_data = {
                    '_xsrf': xsrf_token,
                    'account': self.username,
                    'password': self.password,
                    'captcha': current_captcha
                }
                
                response = self.session.post(login_url, data=login_data, timeout=10, allow_redirects=False)
                
                # 5. 检查登录结果
                if response.status_code == 302:
                    # 重定向通常表示登录成功
                    self._logged_in = True
                    self.logger.info("Tushare登录成功")
                    return True
                elif response.status_code == 200:
                    # 检查响应内容判断是否登录成功
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 检查是否还在登录页面
                    login_form = soup.find('form', id='login-form')
                    if not login_form:
                        # 没有登录表单，可能登录成功
                        self._logged_in = True
                        self.logger.info("Tushare登录成功")
                        return True
                    else:
                        # 还在登录页面，检查错误信息
                        error_elem = soup.find('div', id='login-common-info')
                        if error_elem and 'hidden' not in error_elem.get('class', []):
                            error_text = error_elem.get_text(strip=True)
                            if error_text:
                                self.logger.warning(f"登录失败（尝试 {attempt + 1}/{max_retries}）: {error_text}")
                            else:
                                self.logger.warning(f"登录失败（尝试 {attempt + 1}/{max_retries}）: 可能是验证码错误")
                        else:
                            self.logger.warning(f"登录失败（尝试 {attempt + 1}/{max_retries}）: 可能是验证码错误")
                        
                        # 如果是验证码错误，可以重试
                        if attempt < max_retries - 1:
                            time.sleep(2)  # 等待一下再重试
                            captcha_code = None  # 清除验证码，重新获取
                            continue
                        else:
                            return False
                else:
                    self.logger.warning(f"登录请求失败，状态码: {response.status_code}")
                    return False
                    
            except Exception as e:
                self.logger.warning(f"登录过程出错（尝试 {attempt + 1}/{max_retries}）: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    import traceback
                    self.logger.debug(traceback.format_exc())
                    return False
        
        return False
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """
        解析时间字符串
        
        Args:
            time_str: 时间字符串
            
        Returns:
            datetime对象或None
        """
        if not time_str or not isinstance(time_str, str):
            return None
        
        time_str = time_str.strip()
        if not time_str:
            return None
        
        # 尝试多种时间格式
        time_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y/%m/%d',
            '%m-%d %H:%M',
            '%m/%d %H:%M',
        ]
        
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str, fmt)
            except:
                continue
        
        # 尝试解析相对时间（如"1小时前"、"昨天"等）
        now = datetime.now()
        if '分钟前' in time_str or '小时前' in time_str or '天前' in time_str:
            # 提取数字
            match = re.search(r'(\d+)', time_str)
            if match:
                num = int(match.group(1))
                if '分钟前' in time_str:
                    return now - timedelta(minutes=num)
                elif '小时前' in time_str:
                    return now - timedelta(hours=num)
                elif '天前' in time_str:
                    return now - timedelta(days=num)
        
        if '昨天' in time_str or '昨日' in time_str:
            return now - timedelta(days=1)
        
        if '今天' in time_str or '今日' in time_str:
            return now
        
        # 如果无法解析，返回None
        return None
    
    def _extract_news_from_page(self, url: str, source_name: str) -> List[Dict]:
        """
        从单个页面提取新闻
        
        Args:
            url: 页面URL
            source_name: 新闻源名称
            
        Returns:
            新闻列表
        """
        news_list = []
        
        try:
            # 使用Session访问（如果已登录，会自动携带cookies）
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                self.logger.debug(f"访问 {url} 失败，状态码: {response.status_code}")
                return news_list
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查是否是登录页面
            page_title = soup.find('title')
            title_text = page_title.get_text() if page_title else ''
            login_form = soup.find('form', id='login-form') or soup.find('form', class_=re.compile(r'login', re.I))
            
            if ('登录' in title_text or 'login' in title_text.lower()) or login_form:
                if self._logged_in:
                    self.logger.warning(f"页面 {url} 仍然显示登录页面，可能登录已过期")
                else:
                    self.logger.debug(f"页面 {url} 需要登录才能访问")
                return news_list
            
            # 尝试多种常见的新闻列表结构
            # 1. 查找包含新闻的容器（常见的类名）
            news_containers = []
            
            # 尝试通过类名查找
            container_selectors = [
                'div.news-list',
                'div.news-item',
                'div.item',
                'li.news-item',
                'li.item',
                'div.list-item',
                'article',
                'div.article',
                'div.content-item',
            ]
            
            for selector in container_selectors:
                containers = soup.select(selector)
                if containers:
                    news_containers = containers
                    self.logger.debug(f"使用选择器 {selector} 找到 {len(containers)} 个新闻项")
                    break
            
            # 如果没有找到，尝试查找所有包含链接的div或li
            if not news_containers:
                # 查找所有可能包含新闻的元素
                all_divs = soup.find_all(['div', 'li', 'article'], class_=re.compile(r'news|item|article|list', re.I))
                if all_divs:
                    news_containers = all_divs[:50]  # 限制数量
                    self.logger.debug(f"找到 {len(news_containers)} 个可能的新闻项")
            
            # 如果没有找到，尝试查找所有包含时间信息的元素
            if not news_containers:
                # 查找包含时间模式的所有元素
                time_pattern = re.compile(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|今天|昨天|\d+[分钟小时天]前')
                all_elements = soup.find_all(text=time_pattern)
                if all_elements:
                    # 获取父元素
                    news_containers = [elem.parent for elem in all_elements[:30] if elem.parent]
                    self.logger.debug(f"通过时间模式找到 {len(news_containers)} 个可能的新闻项")
            
            # 从每个容器中提取新闻信息
            for container in news_containers:
                try:
                    news_item = {}
                    
                    # 提取标题
                    title_elem = None
                    # 尝试多种方式查找标题
                    title_selectors = ['a', 'h1', 'h2', 'h3', 'h4', '.title', '[class*="title"]']
                    for selector in title_selectors:
                        title_elem = container.select_one(selector)
                        if title_elem:
                            break
                    
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title:
                            news_item['title'] = title
                            
                            # 提取URL
                            if title_elem.name == 'a':
                                href = title_elem.get('href', '')
                            else:
                                link = container.find('a')
                                href = link.get('href', '') if link else ''
                            
                            # 处理相对URL
                            if href and not href.startswith('http'):
                                if href.startswith('/'):
                                    news_item['url'] = f"{self.base_url}{href}"
                                else:
                                    news_item['url'] = f"{self.base_url}/{href}"
                            elif href:
                                news_item['url'] = href
                            else:
                                news_item['url'] = ''
                    else:
                        # 如果没有找到标题，跳过这条新闻
                        continue
                    
                    # 提取内容/摘要
                    content_elem = None
                    content_selectors = ['.content', '.summary', '.desc', '.description', '[class*="content"]', '[class*="summary"]', 'p']
                    for selector in content_selectors:
                        content_elem = container.select_one(selector)
                        if content_elem:
                            break
                    
                    if content_elem:
                        content = content_elem.get_text(strip=True)
                        news_item['content'] = content
                    else:
                        news_item['content'] = ''
                    
                    # 提取时间
                    time_elem = None
                    time_selectors = ['.time', '.date', '[class*="time"]', '[class*="date"]', 'time']
                    for selector in time_selectors:
                        time_elem = container.select_one(selector)
                        if time_elem:
                            break
                    
                    if time_elem:
                        time_text = time_elem.get_text(strip=True)
                        # 如果是time标签，也尝试datetime属性
                        if not time_text and time_elem.get('datetime'):
                            time_text = time_elem.get('datetime')
                        
                        news_time = self._parse_time(time_text)
                        if news_time:
                            news_item['time'] = news_time
                        else:
                            news_item['time'] = datetime.now()
                    else:
                        # 尝试从文本中提取时间
                        container_text = container.get_text()
                        time_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:\s+\d{1,2}:\d{1,2}(?::\d{1,2})?)?|今天|昨天|\d+[分钟小时天]前)', container_text)
                        if time_match:
                            time_text = time_match.group(1)
                            news_time = self._parse_time(time_text)
                            if news_time:
                                news_item['time'] = news_time
                            else:
                                news_item['time'] = datetime.now()
                        else:
                            news_item['time'] = datetime.now()
                    
                    # 设置源名称
                    news_item['source'] = source_name
                    news_item['type'] = 'market'
                    
                    # 如果没有标题，设置为空字符串（根据用户要求）
                    if 'title' not in news_item or not news_item['title']:
                        news_item['title'] = ''
                    
                    # 只添加有标题的新闻
                    if news_item.get('title'):
                        news_list.append(news_item)
                        
                except Exception as e:
                    self.logger.debug(f"解析新闻项失败: {str(e)}")
                    continue
            
            if len(news_list) == 0:
                # 如果没有提取到新闻，记录更详细的信息
                page_text = soup.get_text()[:200]
                self.logger.debug(f"从 {source_name} ({url}) 未提取到新闻，页面内容预览: {page_text}")
            else:
                self.logger.info(f"从 {source_name} ({url}) 提取到 {len(news_list)} 条新闻")
            
        except requests.exceptions.Timeout:
            self.logger.warning(f"访问 {url} 超时")
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"访问 {url} 失败: {str(e)}")
        except Exception as e:
            self.logger.debug(f"解析 {url} 失败: {str(e)}")
        
        return news_list
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """
        获取市场新闻（从所有配置的新闻源聚合）
        
        Args:
            limit: 获取数量
            
        Returns:
            新闻列表
        """
        all_news = []
        
        # 从所有配置的新闻源获取新闻
        for source_key, source_name in self.NEWS_SOURCES.items():
            try:
                url = f"{self.base_url}/news/{source_key}"
                news_list = self._extract_news_from_page(url, source_name)
                all_news.extend(news_list)
                
                # 如果已经获取足够的新闻，可以提前停止
                if len(all_news) >= limit * 2:  # 多获取一些用于去重
                    break
                    
            except Exception as e:
                self.logger.warning(f"从 {source_name} 获取新闻失败: {str(e)}")
                continue
        
        # 去重（基于标题）
        seen_titles = set()
        unique_news = []
        for news in all_news:
            title = news.get('title', '').strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(news)
        
        # 按时间排序（最新的在前）
        unique_news.sort(key=lambda x: x.get('time', datetime.min), reverse=True)
        
        # 限制数量
        result = unique_news[:limit]
        
        self.logger.info(f"从Tushare网页聚合获取到 {len(result)} 条市场新闻（去重后）")
        return result
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        获取股票相关新闻
        
        注意：Tushare网页新闻源主要提供市场新闻，股票相关新闻通过关键词筛选
        
        Args:
            symbol: 股票代码
            limit: 获取数量
            
        Returns:
            新闻列表
        """
        # 获取市场新闻
        market_news = self.get_market_news(limit * 3)  # 获取更多用于筛选
        
        # 筛选包含股票代码的新闻
        stock_news = []
        symbol_variants = [
            symbol,
            symbol[:6],  # 如果symbol包含后缀
            f"{symbol[:6]}.{symbol[6:]}" if len(symbol) > 6 else symbol,  # 带点号格式
        ]
        
        for news in market_news:
            title = news.get('title', '')
            content = news.get('content', '')
            text = f"{title} {content}".lower()
            
            # 检查是否包含股票代码
            for variant in symbol_variants:
                if variant and variant in text:
                    stock_news.append(news)
                    break
        
        # 限制数量
        result = stock_news[:limit]
        
        self.logger.info(f"从Tushare网页筛选出 {len(result)} 条股票 {symbol} 相关新闻")
        return result
