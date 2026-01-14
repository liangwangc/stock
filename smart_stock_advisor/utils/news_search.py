"""
新闻搜索模块
实现全文搜索功能，支持关键词、时间、情感等多种筛选条件
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)


class NewsSearch:
    """新闻搜索器"""
    
    def __init__(self):
        self.logger = logger
        self.db = DBConnection()
        self.use_database = USE_DATABASE
    
    def search(self, keyword: str = None, symbol: str = None, sentiment: str = None,
               date_from: str = None, date_to: str = None, sector: str = None,
               industry: str = None, news_type: str = None, is_positive: bool = None,
               is_negative: bool = None, is_policy: bool = None,
               page: int = 1, page_size: int = 20, sort_by: str = 'publish_time',
               sort_order: str = 'DESC') -> Dict:
        """
        搜索新闻
        
        Args:
            keyword: 关键词（搜索标题和内容）
            symbol: 股票代码
            sentiment: 情感倾向（positive/negative/neutral）
            date_from: 开始日期（YYYY-MM-DD）
            date_to: 结束日期（YYYY-MM-DD）
            sector: 板块
            industry: 行业
            news_type: 新闻类型（stock/market/policy/industry）
            is_positive: 是否利好
            is_negative: 是否利空
            is_policy: 是否政策新闻
            page: 页码（默认1）
            page_size: 每页数量（默认20）
            sort_by: 排序字段（publish_time/relevance_score/sentiment_score）
            sort_order: 排序顺序（ASC/DESC）
        
        Returns:
            搜索结果字典: {'data': [...], 'total': 总数, 'page': 页码, 'page_size': 每页数量, 'total_pages': 总页数}
        """
        if not self.use_database:
            return {'data': [], 'total': 0, 'page': page, 'page_size': page_size, 'total_pages': 0}
        
        try:
            # 构建WHERE条件
            where_conditions = []
            params = []
            
            # 关键词搜索（使用MySQL FULLTEXT或LIKE）
            if keyword:
                keyword_clean = keyword.strip()
                if keyword_clean:
                    # 使用LIKE搜索（如果FULLTEXT不可用）
                    where_conditions.append("(title LIKE %s OR content LIKE %s)")
                    keyword_pattern = f"%{keyword_clean}%"
                    params.extend([keyword_pattern, keyword_pattern])
            
            # 股票代码
            if symbol:
                where_conditions.append("symbol = %s")
                params.append(symbol)
            
            # 情感倾向
            if sentiment:
                where_conditions.append("sentiment = %s")
                params.append(sentiment)
            
            # 日期范围
            if date_from:
                where_conditions.append("publish_time >= %s")
                params.append(f"{date_from} 00:00:00")
            
            if date_to:
                where_conditions.append("publish_time <= %s")
                params.append(f"{date_to} 23:59:59")
            
            # 板块
            if sector:
                where_conditions.append("sector = %s")
                params.append(sector)
            
            # 行业
            if industry:
                where_conditions.append("industry = %s")
                params.append(industry)
            
            # 新闻类型
            if news_type:
                where_conditions.append("news_type = %s")
                params.append(news_type)
            
            # 是否利好
            if is_positive is not None:
                where_conditions.append("is_positive = %s")
                params.append(1 if is_positive else 0)
            
            # 是否利空
            if is_negative is not None:
                where_conditions.append("is_negative = %s")
                params.append(1 if is_negative else 0)
            
            # 是否政策新闻
            if is_policy is not None:
                where_conditions.append("is_policy = %s")
                params.append(1 if is_policy else 0)
            
            # 构建SQL
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # 排序字段验证
            valid_sort_fields = ['publish_time', 'fetch_time', 'relevance_score', 'sentiment_score', 'sentiment_confidence']
            if sort_by not in valid_sort_fields:
                sort_by = 'publish_time'
            
            if sort_order.upper() not in ['ASC', 'DESC']:
                sort_order = 'DESC'
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) as cnt FROM news_articles WHERE {where_clause}"
            count_results = self.db.execute_query(count_sql, tuple(params))
            total = count_results[0]['cnt'] if count_results else 0
            
            # 分页查询
            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT * FROM news_articles
                WHERE {where_clause}
                ORDER BY {sort_by} {sort_order}
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])
            
            results = self.db.execute_query(query_sql, tuple(params))
            
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            return {
                'data': results or [],
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }
            
        except Exception as e:
            self.logger.error(f"搜索新闻失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {'data': [], 'total': 0, 'page': page, 'page_size': page_size, 'total_pages': 0}
    
    def search_by_keyword_fulltext(self, keyword: str, page: int = 1, page_size: int = 20) -> Dict:
        """
        使用MySQL FULLTEXT索引进行全文搜索（需要FULLTEXT索引支持）
        
        Args:
            keyword: 关键词
            page: 页码
            page_size: 每页数量
        
        Returns:
            搜索结果
        """
        if not self.use_database or not keyword:
            return {'data': [], 'total': 0, 'page': page, 'page_size': page_size, 'total_pages': 0}
        
        try:
            # 检查是否支持FULLTEXT
            # 这里使用LIKE作为备用方案
            return self.search(keyword=keyword, page=page, page_size=page_size)
            
        except Exception as e:
            self.logger.error(f"全文搜索失败: {str(e)}")
            return {'data': [], 'total': 0, 'page': page, 'page_size': page_size, 'total_pages': 0}
    
    def get_search_suggestions(self, keyword: str, limit: int = 10) -> List[str]:
        """
        获取搜索建议（自动补全）
        
        Args:
            keyword: 关键词前缀
            limit: 返回数量限制
        
        Returns:
            建议列表
        """
        if not self.use_database or not keyword:
            return []
        
        try:
            keyword_pattern = f"{keyword}%"
            sql = """
                SELECT DISTINCT title
                FROM news_articles
                WHERE title LIKE %s
                ORDER BY publish_time DESC
                LIMIT %s
            """
            results = self.db.execute_query(sql, (keyword_pattern, limit))
            
            suggestions = [r['title'][:50] for r in results if r.get('title')]
            return suggestions
            
        except Exception as e:
            self.logger.error(f"获取搜索建议失败: {str(e)}")
            return []
