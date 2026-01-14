"""
TuShare新闻源
使用TuShare接口获取新闻
"""
import requests
from typing import List, Dict
from datetime import datetime
import pandas as pd
from .news_source import BaseNewsSource
from utils.logger import get_logger

logger = get_logger(__name__)

class TuShareNewsSource(BaseNewsSource):
    """TuShare新闻源（通过接口获取）"""
    
    def __init__(self, token: str = None):
        """
        初始化TuShare新闻源
        
        Args:
            token: TuShare API token（可选，如果需要）
        """
        self.logger = logger
        self.token = token
        self.base_url = "https://tushare.pro"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._use_api = False
        
        # 尝试使用tushare库
        try:
            import tushare as ts
            if self.token:
                ts.set_token(self.token)
            self.ts = ts
            self.pro = ts.pro_api() if hasattr(ts, 'pro_api') else None
            self._use_api = self.pro is not None
            self.logger.info("TuShare API可用")
        except ImportError:
            self.logger.warning("tushare库未安装，将使用网页爬虫方式")
        except Exception as e:
            self.logger.warning(f"TuShare API初始化失败: {str(e)}")
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """获取股票相关新闻"""
        news_list = []
        
        if self._use_api:
            try:
                # 使用TuShare API获取新闻（如果支持）
                # 注意：TuShare主要提供数据接口，新闻功能可能有限
                # 这里使用cctv_news或其他新闻接口
                df = self.pro.cctv_news(symbol=symbol, limit=limit)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        try:
                            news_list.append({
                                'title': str(row.get('title', '')),
                                'content': str(row.get('content', '')),
                                'time': pd.to_datetime(row.get('date', datetime.now())),
                                'url': str(row.get('url', '')),
                                'source': 'TuShare'
                            })
                        except:
                            continue
            except Exception as e:
                self.logger.debug(f"使用TuShare API获取新闻失败: {str(e)}")
        
        # 如果API不可用或失败，尝试网页爬虫
        if not news_list:
            try:
                # TuShare新闻页面（如果存在）
                url = f"{self.base_url}/news/{symbol}.html"
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # 根据实际页面结构解析
                    # 这里需要根据实际页面调整
                    pass
            except Exception as e:
                self.logger.debug(f"TuShare网页爬虫失败: {str(e)}")
        
        self.logger.info(f"从TuShare获取到 {len(news_list)} 条新闻")
        return news_list[:limit]
    
    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """获取市场新闻"""
        news_list = []
        
        if self._use_api:
            try:
                # 使用TuShare获取市场新闻
                df = self.pro.cctv_news(limit=limit)
                if df is not None and not df.empty:
                    import pandas as pd
                    for _, row in df.iterrows():
                        try:
                            news_list.append({
                                'title': str(row.get('title', '')),
                                'content': str(row.get('content', '')),
                                'time': pd.to_datetime(row.get('date', datetime.now())) if isinstance(row.get('date'), str) else datetime.now(),
                                'url': str(row.get('url', '')),
                                'source': 'TuShare'
                            })
                        except:
                            continue
            except Exception as e:
                self.logger.debug(f"使用TuShare API获取市场新闻失败: {str(e)}")
        
        self.logger.info(f"从TuShare获取到 {len(news_list)} 条市场新闻")
        return news_list[:limit]

