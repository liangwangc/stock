"""
新闻存储模块
负责将新闻文章保存到数据库，并进行情感分析标记
"""
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.logger import get_logger
from config_db import USE_DATABASE, DB_CONFIG

logger = get_logger(__name__)

# 尝试导入情感分析器
try:
    sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))
    from quant_trading_platform.news import NewsSentimentAnalyzer
    SENTIMENT_ANALYZER_AVAILABLE = True
except ImportError:
    try:
        from news import NewsSentimentAnalyzer
        SENTIMENT_ANALYZER_AVAILABLE = True
    except ImportError:
        SENTIMENT_ANALYZER_AVAILABLE = False
        logger.warning("新闻情感分析器不可用")

# 尝试导入新闻股票关联器
try:
    from utils.news_stock_mapper import NewsStockMapper
    NEWS_STOCK_MAPPER_AVAILABLE = True
except ImportError:
    NEWS_STOCK_MAPPER_AVAILABLE = False
    logger.warning("新闻股票关联器不可用")

# 尝试导入新闻推送通知器
try:
    from utils.news_notification import NewsNotification
    NEWS_NOTIFICATION_AVAILABLE = True
except ImportError:
    NEWS_NOTIFICATION_AVAILABLE = False
    logger.warning("新闻推送通知器不可用")

# 尝试导入新闻去重优化器
try:
    from utils.news_deduplication import NewsDeduplication
    NEWS_DEDUPLICATION_AVAILABLE = True
except ImportError:
    NEWS_DEDUPLICATION_AVAILABLE = False
    logger.warning("新闻去重优化器不可用")


class NewsStorage:
    """新闻存储管理器"""
    
    def __init__(self):
        self.logger = logger
        self.use_database = USE_DATABASE
        
        # 初始化情感分析器
        if SENTIMENT_ANALYZER_AVAILABLE:
            try:
                self.sentiment_analyzer = NewsSentimentAnalyzer()
            except Exception as e:
                self.logger.warning(f"初始化情感分析器失败: {str(e)}")
                self.sentiment_analyzer = None
        else:
            self.sentiment_analyzer = None
        
        # 初始化新闻股票关联器
        if NEWS_STOCK_MAPPER_AVAILABLE:
            try:
                self.stock_mapper = NewsStockMapper()
            except Exception as e:
                self.logger.warning(f"初始化新闻股票关联器失败: {str(e)}")
                self.stock_mapper = None
        else:
            self.stock_mapper = None
        
        # 初始化新闻去重优化器
        if NEWS_DEDUPLICATION_AVAILABLE:
            try:
                self.deduplication = NewsDeduplication()
            except Exception as e:
                self.logger.warning(f"初始化新闻去重优化器失败: {str(e)}")
                self.deduplication = None
        else:
            self.deduplication = None
        
        # 初始化新闻推送通知器
        if NEWS_NOTIFICATION_AVAILABLE:
            try:
                self.notification = NewsNotification()
            except Exception as e:
                self.logger.warning(f"初始化新闻推送通知器失败: {str(e)}")
                self.notification = None
        else:
            self.notification = None
    
    def save_news_article(self, news: Dict, symbol: Optional[str] = None, 
                          sector: Optional[str] = None, industry: Optional[str] = None,
                          concept: Optional[str] = None) -> Optional[int]:
        """
        保存单条新闻文章到数据库
        
        Args:
            news: 新闻字典，包含 title, content, time, url, source 等
            symbol: 关联股票代码
            sector: 关联板块
            industry: 关联行业
            concept: 关联概念
            
        Returns:
            新闻ID，如果保存失败返回None
        """
        if not self.use_database:
            self.logger.debug("数据库未启用，跳过保存新闻")
            return None
        
        try:
            # 提取新闻信息
            title = news.get('title', '').strip()
            content = news.get('content', '').strip()
            source = news.get('source', 'unknown')
            source_url = news.get('url', '')
            publish_time = news.get('time')
            
            if not title:
                self.logger.warning("新闻标题为空，跳过保存")
                return None
            
            # 转换发布时间
            if isinstance(publish_time, str):
                try:
                    publish_time = datetime.strptime(publish_time, '%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        publish_time = datetime.strptime(publish_time, '%Y-%m-%d')
                    except:
                        publish_time = datetime.now()
            elif not isinstance(publish_time, datetime):
                publish_time = datetime.now()
            
            # 判断新闻类型
            news_type = 'market'
            if symbol:
                news_type = 'stock'
            elif news.get('is_policy', False):
                news_type = 'policy'
            elif industry or sector:
                news_type = 'industry'
            
            # 判断相关性类型
            relevance_type = 'market'
            relevance_score = 0.5
            if symbol:
                relevance_type = 'direct'
                relevance_score = 1.0
            elif industry or sector:
                relevance_type = 'industry'
                relevance_score = 0.7
            
            # 情感分析
            sentiment_result = self._analyze_sentiment(news)
            sentiment = sentiment_result.get('sentiment', 'neutral')
            sentiment_score = sentiment_result.get('score', 0.0)
            sentiment_confidence = sentiment_result.get('confidence', 0.0)
            is_positive = 1 if sentiment == 'positive' and sentiment_score > 0.1 else 0
            is_negative = 1 if sentiment == 'negative' and sentiment_score < -0.1 else 0
            keywords = json.dumps(sentiment_result.get('keywords', []), ensure_ascii=False)
            
            # 检查是否已存在（优先使用内容相似度检测）
            existing_id = None
            
            # 1. 先检查精确匹配（基于标题和来源）
            existing_id = self._check_duplicate(title, source)
            
            # 2. 如果没有精确匹配，使用SimHash相似度检测
            if not existing_id and self.deduplication and content:
                try:
                    duplicate_id = self.deduplication.check_duplicate_by_content(title, content, source)
                    if duplicate_id:
                        existing_id = duplicate_id
                        self.logger.debug(f"通过SimHash检测到相似新闻: {title[:50]}... (相似ID: {duplicate_id})")
                except Exception as e:
                    self.logger.debug(f"SimHash检测失败: {str(e)}")
            
            if existing_id:
                self.logger.debug(f"新闻已存在或相似，跳过保存: {title[:50]}...")
                # 即使已存在，也尝试更新股票关联
                if not symbol and self.stock_mapper:
                    try:
                        mappings = self.stock_mapper.map_news_to_stocks(news)
                        if mappings:
                            self.stock_mapper.update_news_stock_mapping(existing_id, mappings)
                    except:
                        pass
                return existing_id
            
            # 如果没有传入symbol，尝试自动关联股票
            if not symbol and self.stock_mapper:
                try:
                    mappings = self.stock_mapper.map_news_to_stocks(news)
                    if mappings:
                        primary_mapping = mappings[0]
                        symbol = primary_mapping.get('symbol')
                        sector = primary_mapping.get('sector') or sector
                        industry = primary_mapping.get('industry') or industry
                        relevance_type = primary_mapping.get('match_type', 'market')
                        relevance_score = primary_mapping.get('relevance_score', 0.5)
                        
                        self.logger.debug(f"自动关联股票: {symbol} (相关性: {relevance_score:.2f}, 类型: {relevance_type})")
                except Exception as e:
                    self.logger.debug(f"自动关联股票失败: {str(e)}")
            
            # 计算SimHash（用于相似度检测）
            simhash = None
            simhash_available = True  # 标记simhash字段是否可用
            if self.deduplication:
                try:
                    full_text = f"{title} {content or ''}"
                    simhash = self.deduplication.calculate_simhash(full_text)
                except Exception as e:
                    self.logger.debug(f"计算SimHash失败: {str(e)}")
            
            # 保存到数据库
            # 先尝试包含simhash字段的SQL，如果失败则使用不包含simhash的SQL
            sql_with_simhash = """
                INSERT INTO news_articles 
                (title, content, summary, publish_time, fetch_time, source, source_url,
                 news_type, symbol, sector, industry, concept,
                 sentiment, sentiment_score, sentiment_confidence,
                 is_positive, is_negative, is_policy,
                 keywords, relevance_type, relevance_score, simhash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            sql_without_simhash = """
                INSERT INTO news_articles 
                (title, content, summary, publish_time, fetch_time, source, source_url,
                 news_type, symbol, sector, industry, concept,
                 sentiment, sentiment_score, sentiment_confidence,
                 is_positive, is_negative, is_policy,
                 keywords, relevance_type, relevance_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # 根据simhash字段是否可用选择SQL
            sql = sql_with_simhash if simhash_available else sql_without_simhash
            
            # 生成摘要（取内容前200字）
            summary = content[:200] if content else title
            
            # 根据SQL选择不同的参数
            if simhash_available:
                params = (
                    title, content, summary,
                    publish_time, datetime.now(), source, source_url,
                    news_type, symbol, sector, industry, concept,
                    sentiment, sentiment_score, sentiment_confidence,
                    is_positive, is_negative, int(news.get('is_policy', False)),
                    keywords, relevance_type, relevance_score, simhash
                )
            else:
                params = (
                    title, content, summary,
                    publish_time, datetime.now(), source, source_url,
                    news_type, symbol, sector, industry, concept,
                    sentiment, sentiment_score, sentiment_confidence,
                    is_positive, is_negative, int(news.get('is_policy', False)),
                    keywords, relevance_type, relevance_score
                )
            
            conn = DBConnection.get_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(sql, params)
                    if not DB_CONFIG.get('autocommit', True):
                        conn.commit()
                    news_id = cursor.lastrowid
                    cursor.close()
                except Exception as e:
                    # 如果是因为simhash字段不存在而失败，尝试使用不包含simhash的SQL
                    if ("Unknown column 'simhash'" in str(e) or "1054" in str(e)) and simhash_available:
                        self.logger.warning("simhash字段不存在，使用不包含simhash的SQL重试。请运行 database/add_simhash_field.sql 添加字段。")
                        sql = sql_without_simhash
                        params = (
                            title, content, summary,
                            publish_time, datetime.now(), source, source_url,
                            news_type, symbol, sector, industry, concept,
                            sentiment, sentiment_score, sentiment_confidence,
                            is_positive, is_negative, int(news.get('is_policy', False)),
                            keywords, relevance_type, relevance_score
                        )
                        cursor = conn.cursor()
                        cursor.execute(sql, params)
                        if not DB_CONFIG.get('autocommit', True):
                            conn.commit()
                        news_id = cursor.lastrowid
                        cursor.close()
                        simhash_available = False  # 标记为不可用，后续不再尝试
                    else:
                        if not DB_CONFIG.get('autocommit', True):
                            conn.rollback()
                        raise
            else:
                news_id = None
            
            # 获取刚插入的记录
            if news_id:
                sql2 = "SELECT id FROM news_articles WHERE id = %s"
                result = DBConnection.execute_query(sql2, (news_id,))
            
            self.logger.debug(f"保存新闻成功: {title[:50]}... (ID: {news_id})")
            
            # 如果有多个股票关联，需要更新关联表（如果需要支持多对多关系）
            # 目前先只保存主要关联，后续可以扩展
            
            return news_id
            
        except Exception as e:
            self.logger.error(f"保存新闻失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def save_news_batch(self, news_list: List[Dict], symbol: Optional[str] = None,
                       sector: Optional[str] = None, industry: Optional[str] = None,
                       concept: Optional[str] = None) -> Dict[str, int]:
        """
        批量保存新闻
        
        Returns:
            {'success': 成功数量, 'failed': 失败数量, 'duplicate': 重复数量}
        """
        result = {'success': 0, 'failed': 0, 'duplicate': 0}
        
        for news in news_list:
            news_id = self.save_news_article(news, symbol, sector, industry, concept)
            if news_id:
                result['success'] += 1
            elif news_id is None and self._check_duplicate(news.get('title', ''), news.get('source', '')):
                result['duplicate'] += 1
            else:
                result['failed'] += 1
        
        return result
    
    def _analyze_sentiment(self, news: Dict) -> Dict:
        """分析新闻情感"""
        if not self.sentiment_analyzer:
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'keywords': []
            }
        
        try:
            result = self.sentiment_analyzer.analyze(news)
            return {
                'sentiment': result.get('sentiment', 'neutral'),
                'score': result.get('score', 0.0),
                'confidence': result.get('confidence', 0.0),
                'keywords': result.get('keywords', [])
            }
        except Exception as e:
            self.logger.warning(f"情感分析失败: {str(e)}")
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'keywords': []
            }
    
    def _check_duplicate(self, title: str, source: str) -> Optional[int]:
        """检查新闻是否已存在"""
        if not self.use_database:
            return None
        
        try:
            sql = "SELECT id FROM news_articles WHERE title = %s AND source = %s LIMIT 1"
            result = DBConnection.execute_query(sql, (title[:200], source))
            if result:
                return result[0]['id']
            return None
        except Exception as e:
            self.logger.warning(f"检查重复新闻失败: {str(e)}")
            return None
    
    def get_news_by_symbol(self, symbol: str, limit: int = 20, 
                          sentiment: Optional[str] = None) -> List[Dict]:
        """获取股票相关新闻"""
        if not self.use_database:
            return []
        
        try:
            sql = """
                SELECT * FROM news_articles 
                WHERE symbol = %s
            """
            params = [symbol]
            
            if sentiment:
                sql += " AND sentiment = %s"
                params.append(sentiment)
            
            # 验证limit（防止SQL注入）
            try:
                limit_int = int(limit)
                if limit_int > 0 and limit_int <= 1000:  # 设置上限
                    sql += " ORDER BY publish_time DESC LIMIT %s"
                    params.append(limit_int)
                else:
                    self.logger.warning(f"limit值超出范围: {limit_int}，使用默认值100")
                    sql += " ORDER BY publish_time DESC LIMIT %s"
                    params.append(100)
            except (ValueError, TypeError):
                self.logger.warning(f"无效的limit值: {limit}，使用默认值100")
                sql += " ORDER BY publish_time DESC LIMIT %s"
                params.append(100)
            
            return DBConnection.execute_query(sql, tuple(params))
        except Exception as e:
            self.logger.error(f"获取股票新闻失败: {str(e)}")
            return []
    
    def get_today_news_by_symbol(self, symbol: str, limit: int = 20, 
                                 sentiment: Optional[str] = None) -> List[Dict]:
        """
        从数据库获取股票当天的新闻
        
        Args:
            symbol: 股票代码
            limit: 返回数量限制
            sentiment: 情感倾向过滤（可选）
        
        Returns:
            新闻列表（格式与UnifiedNewsSource返回的格式兼容）
        """
        if not self.use_database:
            return []
        
        try:
            today = datetime.now().date()
            today_str = today.strftime('%Y-%m-%d')
            
            sql = """
                SELECT * FROM news_articles 
                WHERE symbol = %s
                AND DATE(publish_time) = %s
            """
            params = [symbol, today_str]
            
            if sentiment:
                sql += " AND sentiment = %s"
                params.append(sentiment)
            
            # 验证limit（防止SQL注入）
            try:
                limit_int = int(limit)
                if limit_int > 0 and limit_int <= 1000:  # 设置上限
                    sql += " ORDER BY publish_time DESC LIMIT %s"
                    params.append(limit_int)
                else:
                    self.logger.warning(f"limit值超出范围: {limit_int}，使用默认值100")
                    sql += " ORDER BY publish_time DESC LIMIT %s"
                    params.append(100)
            except (ValueError, TypeError):
                self.logger.warning(f"无效的limit值: {limit}，使用默认值100")
                sql += " ORDER BY publish_time DESC LIMIT %s"
                params.append(100)
            
            results = DBConnection.execute_query(sql, tuple(params))
            
            # 转换为UnifiedNewsSource格式
            news_list = []
            for row in results:
                news = {
                    'title': row.get('title', ''),
                    'content': row.get('content', '') or row.get('summary', ''),
                    'time': row.get('publish_time'),
                    'url': row.get('source_url', ''),
                    'source': row.get('source', 'unknown'),
                    'sentiment': row.get('sentiment', 'neutral'),
                    'sentiment_score': float(row.get('sentiment_score', 0.0)) if row.get('sentiment_score') else 0.0,
                    'sentiment_confidence': float(row.get('sentiment_confidence', 0.0)) if row.get('sentiment_confidence') else 0.0,
                    'is_policy': bool(row.get('is_policy', False)),
                    'relevance_type': row.get('relevance_type', 'direct'),
                    'relevance_score': float(row.get('relevance_score', 1.0)) if row.get('relevance_score') else 1.0,
                }
                news_list.append(news)
            
            self.logger.info(f"从数据库获取到 {symbol} 当天 {len(news_list)} 条新闻")
            return news_list
            
        except Exception as e:
            self.logger.error(f"获取股票当天新闻失败: {str(e)}")
            return []
    
    def get_today_market_news(self, limit: int = 50, 
                              sentiment: Optional[str] = None) -> List[Dict]:
        """
        从数据库获取当天的市场新闻
        
        Args:
            limit: 返回数量限制
            sentiment: 情感倾向过滤（可选）
        
        Returns:
            新闻列表（格式与UnifiedNewsSource返回的格式兼容）
        """
        if not self.use_database:
            return []
        
        try:
            today = datetime.now().date()
            today_str = today.strftime('%Y-%m-%d')
            
            sql = """
                SELECT * FROM news_articles 
                WHERE (news_type = 'market' OR symbol IS NULL)
                AND DATE(publish_time) = %s
            """
            params = [today_str]
            
            if sentiment:
                sql += " AND sentiment = %s"
                params.append(sentiment)
            
            # 验证limit（防止SQL注入）
            try:
                limit_int = int(limit)
                if limit_int > 0 and limit_int <= 1000:  # 设置上限
                    sql += " ORDER BY publish_time DESC LIMIT %s"
                    params.append(limit_int)
                else:
                    self.logger.warning(f"limit值超出范围: {limit_int}，使用默认值100")
                    sql += " ORDER BY publish_time DESC LIMIT %s"
                    params.append(100)
            except (ValueError, TypeError):
                self.logger.warning(f"无效的limit值: {limit}，使用默认值100")
                sql += " ORDER BY publish_time DESC LIMIT %s"
                params.append(100)
            
            results = DBConnection.execute_query(sql, tuple(params))
            
            # 转换为UnifiedNewsSource格式
            news_list = []
            for row in results:
                news = {
                    'title': row.get('title', ''),
                    'content': row.get('content', '') or row.get('summary', ''),
                    'time': row.get('publish_time'),
                    'url': row.get('source_url', ''),
                    'source': row.get('source', 'unknown'),
                    'sentiment': row.get('sentiment', 'neutral'),
                    'sentiment_score': float(row.get('sentiment_score', 0.0)) if row.get('sentiment_score') else 0.0,
                    'sentiment_confidence': float(row.get('sentiment_confidence', 0.0)) if row.get('sentiment_confidence') else 0.0,
                    'is_policy': bool(row.get('is_policy', False)),
                    'relevance_type': row.get('relevance_type', 'market'),
                    'relevance_score': float(row.get('relevance_score', 0.5)) if row.get('relevance_score') else 0.5,
                }
                news_list.append(news)
            
            self.logger.info(f"从数据库获取到当天 {len(news_list)} 条市场新闻")
            return news_list
            
        except Exception as e:
            self.logger.error(f"获取当天市场新闻失败: {str(e)}")
            return []
    
    def get_news_statistics(self, symbol: Optional[str] = None, 
                           days: int = 7) -> Dict:
        """获取新闻统计信息"""
        if not self.use_database:
            return {}
        
        try:
            date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            sql = """
                SELECT 
                    COUNT(*) as total_count,
                    SUM(CASE WHEN is_positive = 1 THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN is_negative = 1 THEN 1 ELSE 0 END) as negative_count,
                    AVG(sentiment_score) as avg_sentiment_score
                FROM news_articles
                WHERE fetch_time >= %s
            """
            params = [date_from]
            
            if symbol:
                sql += " AND symbol = %s"
                params.append(symbol)
            
            result = DBConnection.execute_query(sql, tuple(params))
            if result:
                return result[0]
            return {}
        except Exception as e:
            self.logger.error(f"获取新闻统计失败: {str(e)}")
            return {}
