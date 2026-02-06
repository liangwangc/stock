"""
统一新闻源
聚合多个新闻源，提供统一的接口
"""
from typing import List, Dict
from datetime import datetime
from .news_source import BaseNewsSource
from .jin10_news_source import Jin10NewsSource
from .caixin_news_source import CaixinNewsSource
from .securities_news_source import SecuritiesNewsSource
from .tonghuashun_news_source import TonghuashunNewsSource
from utils.logger import get_logger

# 尝试导入新的新闻源
try:
    from .eastmoney_news_source import EastMoneyNewsSource
    EASTMONEY_AVAILABLE = True
except ImportError:
    EASTMONEY_AVAILABLE = False

# 尝试导入新增的新闻源
try:
    from .tushare_news_source import TuShareNewsSource
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False

try:
    from .sina_news_source import SinaNewsSource
    SINA_AVAILABLE = True
except ImportError:
    SINA_AVAILABLE = False

try:
    from .tencent_news_source import TencentNewsSource
    TENCENT_AVAILABLE = True
except ImportError:
    TENCENT_AVAILABLE = False

try:
    from .netease_news_source import NetEaseNewsSource
    NETEASE_AVAILABLE = True
except ImportError:
    NETEASE_AVAILABLE = False

try:
    from .sse_news_source import SSENewsSource
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False

try:
    from .szse_news_source import SZSENewsSource
    SZSE_AVAILABLE = True
except ImportError:
    SZSE_AVAILABLE = False

try:
    from .cninfo_news_source import CninfoNewsSource
    CNINFO_AVAILABLE = True
except ImportError:
    CNINFO_AVAILABLE = False

try:
    from .stcn_news_source import STCNNewsSource
    STCN_AVAILABLE = True
except ImportError:
    STCN_AVAILABLE = False

try:
    from .cs_news_source import CSNewsSource
    CS_AVAILABLE = True
except ImportError:
    CS_AVAILABLE = False

try:
    from .cls_news_source import CLSNewsSource
    CLS_AVAILABLE = True
except ImportError:
    CLS_AVAILABLE = False

try:
    from .tushare_web_news_source import TushareWebNewsSource
    TUSHARE_WEB_AVAILABLE = True
except ImportError:
    TUSHARE_WEB_AVAILABLE = False

logger = get_logger(__name__)

class UnifiedNewsSource(BaseNewsSource):
    """统一新闻源，聚合多个新闻源"""
    
    def __init__(self, jin10_api_key: str = "", tushare_token: str = None, 
                 tushare_username: str = None, tushare_password: str = None):
        """
        初始化统一新闻源
        
        Args:
            jin10_api_key: 金十数据API密钥（可选）
            tushare_token: TuShare API token（可选）
            tushare_username: Tushare账号（可选，用于网页登录）
            tushare_password: Tushare密码（可选，用于网页登录）
        """
        self.logger = logger
        
        # 初始化各个新闻源
        self.sources = []
        
        # 金十数据
        try:
            self.jin10 = Jin10NewsSource(api_key=jin10_api_key)
            self.sources.append(('金十数据', self.jin10))
        except Exception as e:
            self.logger.warning(f"初始化金十数据源失败: {str(e)}")
        
        # 财新
        try:
            self.caixin = CaixinNewsSource()
            self.sources.append(('财新', self.caixin))
        except Exception as e:
            self.logger.warning(f"初始化财新数据源失败: {str(e)}")
        
        # 证券公司（包括广发证券等）
        try:
            self.securities = SecuritiesNewsSource()
            self.sources.append(('证券公司', self.securities))
        except Exception as e:
            self.logger.warning(f"初始化证券公司数据源失败: {str(e)}")
        
        # 同花顺
        try:
            self.tonghuashun = TonghuashunNewsSource()
            self.sources.append(('同花顺', self.tonghuashun))
        except Exception as e:
            self.logger.warning(f"初始化同花顺数据源失败: {str(e)}")
        
        # 东方财富
        if EASTMONEY_AVAILABLE:
            try:
                self.eastmoney = EastMoneyNewsSource()
                self.sources.append(('东方财富', self.eastmoney))
            except Exception as e:
                self.logger.warning(f"初始化东方财富数据源失败: {str(e)}")
        
        # TuShare
        if TUSHARE_AVAILABLE:
            try:
                self.tushare = TuShareNewsSource(token=tushare_token)
                self.sources.append(('TuShare', self.tushare))
            except Exception as e:
                self.logger.warning(f"初始化TuShare数据源失败: {str(e)}")
        
        # 新浪财经
        if SINA_AVAILABLE:
            try:
                self.sina = SinaNewsSource()
                self.sources.append(('新浪财经', self.sina))
            except Exception as e:
                self.logger.warning(f"初始化新浪财经数据源失败: {str(e)}")
        
        # 腾讯财经
        if TENCENT_AVAILABLE:
            try:
                self.tencent = TencentNewsSource()
                self.sources.append(('腾讯财经', self.tencent))
            except Exception as e:
                self.logger.warning(f"初始化腾讯财经数据源失败: {str(e)}")
        
        # 网易财经
        if NETEASE_AVAILABLE:
            try:
                self.netease = NetEaseNewsSource()
                self.sources.append(('网易财经', self.netease))
            except Exception as e:
                self.logger.warning(f"初始化网易财经数据源失败: {str(e)}")
        
        # 上交所
        if SSE_AVAILABLE:
            try:
                self.sse = SSENewsSource()
                self.sources.append(('上交所', self.sse))
            except Exception as e:
                self.logger.warning(f"初始化上交所数据源失败: {str(e)}")
        
        # 深交所
        if SZSE_AVAILABLE:
            try:
                self.szse = SZSENewsSource()
                self.sources.append(('深交所', self.szse))
            except Exception as e:
                self.logger.warning(f"初始化深交所数据源失败: {str(e)}")
        
        # 巨潮资讯
        if CNINFO_AVAILABLE:
            try:
                self.cninfo = CninfoNewsSource()
                self.sources.append(('巨潮资讯', self.cninfo))
            except Exception as e:
                self.logger.warning(f"初始化巨潮资讯数据源失败: {str(e)}")
        
        # 证券时报
        if STCN_AVAILABLE:
            try:
                self.stcn = STCNNewsSource()
                self.sources.append(('证券时报', self.stcn))
            except Exception as e:
                self.logger.warning(f"初始化证券时报数据源失败: {str(e)}")
        
        # 中国证券报
        if CS_AVAILABLE:
            try:
                self.cs = CSNewsSource()
                self.sources.append(('中国证券报', self.cs))
            except Exception as e:
                self.logger.warning(f"初始化中国证券报数据源失败: {str(e)}")
        
        # 财联社
        if CLS_AVAILABLE:
            try:
                self.cls = CLSNewsSource()
                self.sources.append(('财联社', self.cls))
            except Exception as e:
                self.logger.warning(f"初始化财联社数据源失败: {str(e)}")
        
        # Tushare网页新闻源（聚合多个新闻源）
        # 如果提供了账号密码，可以启用网页登录方式
        if TUSHARE_WEB_AVAILABLE and tushare_username and tushare_password:
            try:
                self.tushare_web = TushareWebNewsSource(username=tushare_username, password=tushare_password)
                if self.tushare_web._logged_in:
                    self.sources.append(('Tushare网页聚合', self.tushare_web))
                    self.logger.info("Tushare网页新闻源已启用（已登录）")
                else:
                    self.logger.warning("Tushare网页新闻源登录失败，已禁用")
            except Exception as e:
                self.logger.warning(f"初始化Tushare网页新闻源失败: {str(e)}")
        
        self.logger.info(f"已初始化 {len(self.sources)} 个新闻源")
    
    def get_stock_news(self, symbol: str, limit: int = 10, industry_keywords: List[str] = None, only_today: bool = True) -> List[Dict]:
        """
        获取股票相关新闻（从所有新闻源聚合）
        包括直接提到股票的新闻和行业/概念相关的新闻
        
        Args:
            symbol: 股票代码
            limit: 获取数量
            industry_keywords: 行业/概念关键词列表，用于筛选相关新闻
            only_today: 是否只获取当天的新闻（默认True）
            
        Returns:
            新闻列表，已去重和排序
        """
        all_news = []
        today = datetime.now().date()
        
        # 1. 获取直接提到股票的新闻
        for source_name, source in self.sources:
            try:
                self.logger.debug(f"从 {source_name} 获取 {symbol} 的新闻...")
                
                # 使用超时控制，避免单个新闻源阻塞整个流程
                import threading
                news_result = [None]
                exception_result = [None]
                
                def fetch_news():
                    try:
                        news_result[0] = source.get_stock_news(symbol, limit // len(self.sources) + 1)
                    except Exception as e:
                        exception_result[0] = e
                
                thread = threading.Thread(target=fetch_news, daemon=True)
                thread.start()
                thread.join(timeout=30)  # 30秒超时
                
                if thread.is_alive():
                    self.logger.warning(f"从 {source_name} 获取股票新闻超时（>30秒），跳过")
                    continue
                
                if exception_result[0]:
                    raise exception_result[0]
                
                news = news_result[0]
                
                if news:
                    for n in news:
                        n['relevance'] = 'direct'  # 直接相关
                    all_news.extend(news)
                    self.logger.debug(f"从 {source_name} 获取到 {len(news)} 条新闻")
                else:
                    self.logger.debug(f"从 {source_name} 未获取到新闻")
            except Exception as e:
                self.logger.warning(f"从 {source_name} 获取新闻失败: {str(e)}")
                continue  # 继续下一个新闻源，不中断
        
        # 2. 如果提供了行业关键词，获取行业相关新闻
        if industry_keywords:
            market_news = self.get_market_news(limit * 2, only_today=only_today)  # 获取更多市场新闻用于筛选
            
            # 筛选包含行业关键词的新闻
            for news in market_news:
                title = news.get('title', '').lower()
                content = news.get('content', '').lower()
                text = title + ' ' + content
                
                # 检查是否包含行业关键词
                for keyword in industry_keywords:
                    if keyword and keyword.lower() in text:
                        news['relevance'] = 'industry'  # 行业相关
                        all_news.append(news)
                        break
        
        # 去重和过滤当天新闻
        seen_titles = set()
        unique_news = []
        for news in all_news:
            title = news.get('title', '')
            if not title or title in seen_titles:
                continue
            
            # 如果只获取当天新闻，过滤掉非当天的新闻
            # 优化：如果没有获取到新闻时间，则不需要存储，避免干扰
            news_time = news.get('time') or news.get('publish_time') or news.get('pub_time')
            if not news_time:
                # 没有时间信息，跳过，不进行存储
                continue
            
            if only_today:
                # 处理datetime对象
                if isinstance(news_time, datetime):
                    news_date = news_time.date()
                elif isinstance(news_time, str):
                    try:
                        # 尝试多种日期格式
                        if len(news_time) >= 10:
                            news_date = datetime.strptime(news_time[:10], '%Y-%m-%d').date()
                        else:
                            # 如果字符串太短，默认保留（可能是"今天"、"1小时前"等）
                            news_date = today
                    except:
                        # 如果无法解析日期，默认保留（可能是"今天"、"1小时前"等）
                        news_date = today
                else:
                    # 其他类型，默认保留
                    news_date = today
                
                # 只保留当天的新闻
                if news_date != today:
                    continue
            
            seen_titles.add(title)
            unique_news.append(news)
        
        # 按相关性和时间排序（直接相关的优先）
        def sort_key(news):
            relevance = news.get('relevance', 'other')
            time_val = news.get('time', datetime.min)
            if relevance == 'direct':
                return (0, time_val)
            elif relevance == 'industry':
                return (1, time_val)
            else:
                return (2, time_val)
        
        unique_news.sort(key=sort_key, reverse=True)
        
        # 取最新的
        result = unique_news[:limit]
        
        direct_count = sum(1 for n in result if n.get('relevance') == 'direct')
        industry_count = sum(1 for n in result if n.get('relevance') == 'industry')
        today_count = sum(1 for n in result if isinstance(n.get('time'), datetime) and n.get('time').date() == today)
        self.logger.info(f"聚合获取到 {len(result)} 条新闻（去重后），其中直接相关 {direct_count} 条，行业相关 {industry_count} 条，当天新闻 {today_count} 条")
        return result
    
    def get_market_news(self, limit: int = 20, only_today: bool = True) -> List[Dict]:
        """
        获取市场新闻（从所有新闻源聚合）
        
        Args:
            limit: 获取数量
            only_today: 是否只获取当天的新闻（默认True）
            
        Returns:
            新闻列表，已去重和排序
        """
        all_news = []
        today = datetime.now().date()
        
        # 优化：增大每个新闻源的获取数量，确保有足够的新闻
        # 原逻辑：limit // len(self.sources) + 1，对于limit=30，6个源，每个只获取6条
        # 优化后：每个新闻源获取 limit 条，然后去重和限制总数
        source_limit = max(limit, limit * 2 // max(len(self.sources), 1))  # 至少每个源获取 limit 条，或者 limit*2/源数量
        
        for source_name, source in self.sources:
            try:
                self.logger.debug(f"从 {source_name} 获取市场新闻（限制: {source_limit}条）...")
                
                # 使用超时控制，避免单个新闻源阻塞整个流程
                import threading
                news_result = [None]
                exception_result = [None]
                
                def fetch_news():
                    try:
                        news_result[0] = source.get_market_news(source_limit)
                    except Exception as e:
                        exception_result[0] = e
                
                thread = threading.Thread(target=fetch_news, daemon=True)
                thread.start()
                thread.join(timeout=30)  # 30秒超时
                
                if thread.is_alive():
                    self.logger.warning(f"从 {source_name} 获取新闻超时（>30秒），跳过")
                    continue
                
                if exception_result[0]:
                    raise exception_result[0]
                
                news = news_result[0]
                
                if news:
                    all_news.extend(news)
                    self.logger.debug(f"从 {source_name} 获取到 {len(news)} 条新闻")
                else:
                    self.logger.debug(f"从 {source_name} 未获取到新闻")
            except Exception as e:
                self.logger.warning(f"从 {source_name} 获取市场新闻失败: {str(e)}")
                # 不打印完整traceback，避免日志过多
                continue  # 继续下一个新闻源，不中断
        
        # 去重和过滤当天新闻
        seen_titles = set()
        unique_news = []
        for news in all_news:
            title = news.get('title', '')
            if not title or title in seen_titles:
                continue
            
            # 如果只获取当天新闻，过滤掉非当天的新闻
            # 优化：如果没有获取到新闻时间，则不需要存储，避免干扰
            news_time = news.get('time') or news.get('publish_time') or news.get('pub_time')
            if not news_time:
                # 没有时间信息，跳过，不进行存储
                continue
            
            if only_today:
                # 处理datetime对象
                if isinstance(news_time, datetime):
                    news_date = news_time.date()
                elif isinstance(news_time, str):
                    try:
                        # 尝试多种日期格式
                        if len(news_time) >= 10:
                            news_date = datetime.strptime(news_time[:10], '%Y-%m-%d').date()
                        else:
                            # 如果字符串太短，默认保留（可能是"今天"、"1小时前"等）
                            news_date = today
                    except:
                        # 如果无法解析日期，默认保留（可能是"今天"、"1小时前"等）
                        news_date = today
                else:
                    # 其他类型，默认保留
                    news_date = today
                
                # 只保留当天的新闻
                if news_date != today:
                    continue
            
            seen_titles.add(title)
            unique_news.append(news)
        
        # 按时间排序
        unique_news.sort(key=lambda x: x.get('time', datetime.min), reverse=True)
        
        result = unique_news[:limit]
        
        today_count = sum(1 for n in result if isinstance(n.get('time'), datetime) and n.get('time').date() == today)
        self.logger.info(f"聚合获取到 {len(result)} 条市场新闻（去重后），其中当天新闻 {today_count} 条")
        return result

