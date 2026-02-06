"""
TuShare新闻源
使用TuShare接口获取新闻
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from .news_source import BaseNewsSource
from utils.logger import get_logger

logger = get_logger(__name__)

class TuShareNewsSource(BaseNewsSource):
    """TuShare新闻源（通过接口获取）"""
    
    # 支持的新闻源配置：Tushare的src参数 -> 显示名称
    NEWS_SOURCES = {
        'yicai': '第一财经',
        'fenghuang': '凤凰财经',
        '10jqka': '同花顺',
        'jinrongjie': '金融界',
        'sina': '新浪财经',
        'yuncaijing': '云财经',
        'eastmoney': '东方财富',
        'cctv': '央视新闻'  # 保留cctv作为备用
    }
    
    def __init__(self, token: str = None):
        """
        初始化TuShare新闻源
        
        Args:
            token: TuShare API token（必需）
        """
        self.logger = logger
        self.token = token
        self.base_url = "https://tushare.pro"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._use_api = False
        self.pro = None
        
        # 尝试使用tushare库
        try:
            import tushare as ts
            if self.token:
                ts.set_token(self.token)
                self.ts = ts
                self.pro = ts.pro_api() if hasattr(ts, 'pro_api') else None
                self._use_api = self.pro is not None
                if self._use_api:
                    self.logger.info("TuShare API可用")
                else:
                    self.logger.warning("TuShare API初始化失败：无法创建pro_api")
            else:
                self.logger.warning("TuShare token未提供，无法使用API")
        except ImportError:
            self.logger.warning("tushare库未安装，请运行: pip install tushare")
        except Exception as e:
            self.logger.warning(f"TuShare API初始化失败: {str(e)}")
    
    def _fetch_news_from_source(self, src: str, source_name: str, limit: int = 20, 
                                 start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        从指定的新闻源获取新闻
        
        Args:
            src: Tushare新闻源代码（如'sina'、'yicai'等）
            source_name: 新闻源显示名称
            limit: 获取数量
            start_date: 开始日期（格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
            end_date: 结束日期（格式：YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS）
            
        Returns:
            新闻列表
        """
        news_list = []
        
        if not self._use_api or not self.pro:
            return news_list
        
        try:
            # 构建参数
            params = {'src': src}
            
            # 如果没有指定日期，默认获取最近1天的新闻
            if not start_date:
                start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            params['start_date'] = start_date
            params['end_date'] = end_date
            
            # 调用Tushare news接口
            df = self.pro.news(**params)
            
            if df is not None and not df.empty:
                # 按时间排序（最新的在前）
                # 根据实际测试，字段名是 'datetime'
                if 'datetime' in df.columns:
                    df = df.sort_values('datetime', ascending=False)
                elif 'publish_time' in df.columns:
                    df = df.sort_values('publish_time', ascending=False)
                elif 'time' in df.columns:
                    df = df.sort_values('time', ascending=False)
                
                # 限制数量
                df = df.head(limit)
                
                for _, row in df.iterrows():
                    try:
                        # 解析时间（根据实际测试，字段名是 'datetime'）
                        news_time = datetime.now()
                        time_field = None
                        for field in ['datetime', 'publish_time', 'time', 'date']:
                            if field in row and pd.notna(row[field]):
                                time_field = field
                                break
                        
                        if time_field:
                            try:
                                news_time = pd.to_datetime(row[time_field])
                            except:
                                pass
                        
                        # 提取标题（根据实际测试，字段名是 'title'）
                        title = ''
                        for field in ['title', 'headline', 'subject']:
                            if field in row and pd.notna(row[field]):
                                title = str(row[field]).strip()
                                break
                        
                        # 提取内容（根据实际测试，字段名是 'content'）
                        content = ''
                        for field in ['content', 'text', 'summary', 'abstract']:
                            if field in row and pd.notna(row[field]):
                                content = str(row[field]).strip()
                                break
                        
                        # 提取URL（Tushare news接口可能不返回URL）
                        url = ''
                        for field in ['url', 'link', 'href']:
                            if field in row and pd.notna(row[field]):
                                url = str(row[field]).strip()
                                break
                        
                        # 如果没有标题，设置为空字符串（根据用户要求）
                        if not title:
                            title = ''
                        
                        # 只添加有标题的新闻
                        if title:
                            news_list.append({
                                'title': title,
                                'content': content,
                                'time': news_time,
                                'url': url,
                                'source': source_name,
                                'type': 'market'
                            })
                    except Exception as e:
                        self.logger.debug(f"解析新闻项失败: {str(e)}")
                        continue
                        
        except AttributeError as e:
            # news接口可能不存在或没有权限
            self.logger.debug(f"TuShare news接口不可用（可能没有权限或接口已变更）: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            # 检查是否是频率限制错误
            if '每分钟最多访问' in error_msg or '访问该接口' in error_msg:
                self.logger.warning(f"从 {source_name} 获取新闻失败: API调用频率限制（每分钟最多1次）")
            else:
                self.logger.debug(f"从 {source_name} 获取新闻失败: {error_msg}")
        
        return news_list
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        获取股票相关新闻
        
        注意：Tushare的news接口可能不支持直接按股票代码筛选，
        这里通过获取市场新闻后筛选包含股票代码的新闻
        
        注意：由于API频率限制，只会从第一个新闻源获取数据
        """
        import time
        all_news = []
        
        # 由于API频率限制，只从第一个新闻源获取（避免等待时间过长）
        # 如果需要更多新闻，可以依次调用多个源，但会需要较长时间
        src, source_name = list(self.NEWS_SOURCES.items())[0]
        
        try:
            # 获取更多新闻用于筛选
            news_list = self._fetch_news_from_source(src, source_name, limit=limit * 5)
            
            # 筛选包含股票代码的新闻
            symbol_variants = [
                symbol,
                symbol[:6],  # 如果symbol包含后缀
                f"{symbol[:6]}.{symbol[6:]}" if len(symbol) > 6 else symbol,  # 带点号格式
            ]
            
            for news in news_list:
                title = news.get('title', '')
                content = news.get('content', '')
                text = f"{title} {content}".lower()
                
                # 检查是否包含股票代码
                for variant in symbol_variants:
                    if variant and variant in text:
                        all_news.append(news)
                        break
                
                # 如果已经获取足够的新闻，可以提前停止
                if len(all_news) >= limit:
                    break
                    
        except Exception as e:
            self.logger.debug(f"从 {source_name} 获取股票新闻失败: {str(e)}")
        
        # 去重（基于标题）
        seen_titles = set()
        unique_news = []
        for news in all_news:
            title = news.get('title', '').strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(news)
        
        # 按时间排序
        unique_news.sort(key=lambda x: x.get('time', datetime.min), reverse=True)
        
        # 限制数量
        result = unique_news[:limit]
        
        self.logger.info(f"从TuShare获取到 {len(result)} 条股票 {symbol} 相关新闻")
        return result
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """
        获取市场新闻（从所有配置的新闻源聚合）
        
        注意：Tushare API有频率限制（每分钟最多1次），所以会依次调用各个新闻源
        
        Args:
            limit: 获取数量
            
        Returns:
            新闻列表
        """
        import time
        all_news = []
        
        # 从所有配置的新闻源获取新闻
        for i, (src, source_name) in enumerate(self.NEWS_SOURCES.items()):
            try:
                # 每个源获取 limit 条新闻
                news_list = self._fetch_news_from_source(src, source_name, limit=limit)
                all_news.extend(news_list)
                
                # 如果不是最后一个源，等待一段时间以避免频率限制
                # Tushare限制每分钟最多1次，所以每次调用后等待至少60秒
                if i < len(self.NEWS_SOURCES) - 1:
                    self.logger.debug(f"等待60秒以避免API频率限制...")
                    time.sleep(60)  # 等待60秒
                
                # 如果已经获取足够的新闻，可以提前停止
                if len(all_news) >= limit * 2:  # 多获取一些用于去重
                    break
                    
            except Exception as e:
                self.logger.debug(f"从 {source_name} 获取市场新闻失败: {str(e)}")
                # 即使失败也等待，避免影响下一个请求
                if i < len(self.NEWS_SOURCES) - 1:
                    time.sleep(60)
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
        
        self.logger.info(f"从TuShare获取到 {len(result)} 条市场新闻（去重后，来自 {len(set(n.get('source') for n in result))} 个新闻源）")
        return result

