"""
新闻推送通知模块（增强版）
实现重要新闻的自动推送功能
支持浏览器通知、推送规则配置、推送历史、去重
"""
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import json
import hashlib

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.logger import get_logger
from config_db import USE_DATABASE

logger = get_logger(__name__)


class NewsNotification:
    """新闻推送通知管理器（增强版）"""
    
    def __init__(self):
        self.logger = logger
        self.db = DBConnection()
        self.use_database = USE_DATABASE
        
        # 推送去重缓存（内存中，用于快速去重）
        # 格式: {news_hash: notification_id}
        self._notification_cache: Dict[str, int] = {}
        self._cache_max_size = 1000  # 最大缓存数量
        
        # 默认推送规则
        self.default_rules = {
            'min_sentiment_confidence': 0.7,  # 最低置信度
            'min_sentiment_score': 0.5,  # 最低情感得分
            'min_importance_score': 0.5,  # 最低重要性评分
            'require_direct_relevance': False,  # 是否要求直接关联
            'include_policy_news': True,  # 是否包含政策新闻
            'deduplication_hours': 24,  # 去重时间窗口（小时）
        }
    
    def should_notify(self, news: Dict, user_rules: Optional[Dict] = None) -> bool:
        """
        判断新闻是否需要推送（支持自定义规则）
        
        Args:
            news: 新闻字典
            user_rules: 用户自定义推送规则（如果为None，使用默认规则）
        
        Returns:
            True表示需要推送，False表示不需要
        """
        try:
            # 合并用户规则和默认规则
            rules = {**self.default_rules, **(user_rules or {})}
            
            # 检查是否已推送过（去重）
            if self._is_duplicate_notification(news, rules.get('deduplication_hours', 24)):
                return False
            
            relevance_type = news.get('relevance_type', '')
            sentiment_confidence = float(news.get('sentiment_confidence', 0) or 0)
            sentiment_score = float(news.get('sentiment_score', 0) or 0)
            importance_score = float(news.get('importance_score', 0) or 0)
            is_positive = news.get('is_positive', 0) == 1
            is_negative = news.get('is_negative', 0) == 1
            is_policy = news.get('is_policy', 0) == 1
            
            # 条件1：直接关联的利好/利空新闻（如果要求直接关联）
            if rules.get('require_direct_relevance', False):
                if relevance_type == 'direct' and (is_positive or is_negative):
                    return True
                return False
            
            # 条件2：直接关联的利好/利空新闻（默认允许）
            if relevance_type == 'direct' and (is_positive or is_negative):
                return True
            
            # 条件3：高置信度 + 高强度情感
            min_confidence = rules.get('min_sentiment_confidence', 0.7)
            min_score = rules.get('min_sentiment_score', 0.5)
            if sentiment_confidence >= min_confidence and abs(sentiment_score) >= min_score:
                return True
            
            # 条件4：高重要性评分
            min_importance = rules.get('min_importance_score', 0.5)
            if importance_score >= min_importance:
                return True
            
            # 条件5：政策新闻（如果启用）
            if rules.get('include_policy_news', True) and is_policy and abs(sentiment_score) >= 0.3:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"判断是否需要推送失败: {str(e)}")
            return False
    
    def _is_duplicate_notification(self, news: Dict, deduplication_hours: int = 24) -> bool:
        """
        检查是否已推送过该新闻（去重）
        
        Args:
            news: 新闻字典
            deduplication_hours: 去重时间窗口（小时）
        
        Returns:
            True表示已推送过，False表示未推送过
        """
        try:
            # 生成新闻唯一标识（基于标题和发布时间）
            news_id = news.get('id')
            title = news.get('title', '')
            publish_time = news.get('publish_time')
            
            if not news_id and not title:
                return False
            
            # 方法1：检查内存缓存
            news_hash = self._get_news_hash(news)
            if news_hash in self._notification_cache:
                return True
            
            # 方法2：检查数据库（最近N小时内是否推送过）
            if self.use_database and news_id:
                cutoff_time = datetime.now() - timedelta(hours=deduplication_hours)
                
                sql = """
                    SELECT id FROM news_notifications 
                    WHERE news_id = %s AND is_sent = 1 AND sent_at >= %s
                    LIMIT 1
                """
                result = self.db.execute_query(sql, (news_id, cutoff_time))
                
                if result:
                    # 添加到缓存
                    if len(self._notification_cache) < self._cache_max_size:
                        self._notification_cache[news_hash] = result[0]['id']
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"检查推送去重失败: {str(e)}")
            return False
    
    def _get_news_hash(self, news: Dict) -> str:
        """生成新闻唯一标识"""
        try:
            title = news.get('title', '')
            publish_time = news.get('publish_time')
            source = news.get('source', '')
            
            # 使用标题+发布时间+来源生成hash
            hash_str = f"{title}|{publish_time}|{source}"
            return hashlib.md5(hash_str.encode('utf-8')).hexdigest()
        except:
            return str(news.get('id', ''))
    
    def create_notification(self, news_id: int, news: Dict, notification_type: str = 'important', 
                           user_rules: Optional[Dict] = None) -> Optional[int]:
        """
        创建通知记录（支持去重和自定义规则）
        
        Args:
            news_id: 新闻ID
            news: 新闻字典
            notification_type: 通知类型（important/positive/negative/policy）
            user_rules: 用户自定义推送规则
        
        Returns:
            通知ID，如果创建失败或已推送过返回None
        """
        if not self.use_database:
            return None
        
        try:
            # 检查是否需要推送（使用用户规则）
            if not self.should_notify(news, user_rules):
                return None
            
            # 检查是否已通知过（再次检查，确保不会重复创建）
            news_hash = self._get_news_hash(news)
            if news_hash in self._notification_cache:
                notification_id = self._notification_cache[news_hash]
                self.logger.debug(f"新闻已推送过（缓存），跳过: news_id={news_id}, notification_id={notification_id}")
                return None
            
            sql = "SELECT id FROM news_notifications WHERE news_id = %s LIMIT 1"
            existing = self.db.execute_query(sql, (news_id,))
            if existing:
                notification_id = existing[0]['id']
                # 添加到缓存
                if len(self._notification_cache) < self._cache_max_size:
                    self._notification_cache[news_hash] = notification_id
                return None  # 已存在，不重复创建
            
            # 确定通知类型
            if not notification_type:
                if news.get('is_positive'):
                    notification_type = 'positive'
                elif news.get('is_negative'):
                    notification_type = 'negative'
                elif news.get('is_policy'):
                    notification_type = 'policy'
                else:
                    notification_type = 'important'
            
            # 创建通知记录
            sql = """
                INSERT INTO news_notifications
                (news_id, notification_type, title, symbol, sentiment, 
                 is_sent, sent_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            title = news.get('title', '')[:200]
            symbol = news.get('symbol')
            sentiment = news.get('sentiment', 'neutral')
            
            params = (
                news_id, notification_type, title, symbol, sentiment,
                0, None, datetime.now()  # 默认未发送
            )
            
            self.db.execute_update(sql, params)
            
            # 获取通知ID
            sql2 = "SELECT LAST_INSERT_ID() as id"
            result = self.db.execute_query(sql2)
            if result:
                notification_id = result[0].get('id')
                # 添加到缓存
                if len(self._notification_cache) < self._cache_max_size:
                    self._notification_cache[news_hash] = notification_id
                self.logger.info(f"创建通知记录成功: 新闻ID={news_id}, 通知ID={notification_id}")
                return notification_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"创建通知记录失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def get_pending_notifications(self, limit: int = 50) -> List[Dict]:
        """
        获取待发送的通知
        
        Args:
            limit: 返回数量限制
        
        Returns:
            通知列表
        """
        if not self.use_database:
            return []
        
        try:
            sql = """
                SELECT n.*, na.content, na.source_url, na.publish_time
                FROM news_notifications n
                JOIN news_articles na ON n.news_id = na.id
                WHERE n.is_sent = 0
                ORDER BY n.created_at DESC
                LIMIT %s
            """
            results = self.db.execute_query(sql, (limit,))
            return results or []
            
        except Exception as e:
            self.logger.error(f"获取待发送通知失败: {str(e)}")
            return []
    
    def mark_as_sent(self, notification_id: int) -> bool:
        """
        标记通知为已发送
        
        Args:
            notification_id: 通知ID
        
        Returns:
            是否成功
        """
        if not self.use_database:
            return False
        
        try:
            sql = """
                UPDATE news_notifications
                SET is_sent = 1, sent_at = %s
                WHERE id = %s
            """
            self.db.execute_update(sql, (datetime.now(), notification_id))
            return True
            
        except Exception as e:
            self.logger.error(f"标记通知为已发送失败: {str(e)}")
            return False
    
    def get_user_notifications(self, user_id: int, limit: int = 20, unread_only: bool = False) -> List[Dict]:
        """
        获取用户的通知列表（推送历史）
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            unread_only: 是否只返回未读通知
        
        Returns:
            通知列表
        """
        if not self.use_database:
            return []
        
        try:
            # 动态检查importance_score字段是否存在
            try:
                check_sql = "SHOW COLUMNS FROM news_articles LIKE 'importance_score'"
                has_importance_score = len(self.db.execute_query(check_sql)) > 0
            except:
                has_importance_score = False
            
            if has_importance_score:
                sql = """
                    SELECT n.*, na.content, na.source_url, na.publish_time, na.sentiment, 
                           na.sentiment_score, na.importance_score, na.importance_level
                    FROM news_notifications n
                    JOIN news_articles na ON n.news_id = na.id
                    WHERE n.is_sent = 1
                """
            else:
                sql = """
                    SELECT n.*, na.content, na.source_url, na.publish_time, na.sentiment, 
                           na.sentiment_score, NULL as importance_score, NULL as importance_level
                    FROM news_notifications n
                    JOIN news_articles na ON n.news_id = na.id
                    WHERE n.is_sent = 1
                """
            params = []
            
            if unread_only:
                sql += " AND n.is_read = 0"
            
            # 验证limit（防止SQL注入）
            try:
                limit_int = int(limit)
                if limit_int > 0 and limit_int <= 1000:  # 设置上限
                    sql += " ORDER BY n.sent_at DESC LIMIT %s"
                    params.append(limit_int)
                else:
                    self.logger.warning(f"limit值超出范围: {limit_int}，使用默认值100")
                    sql += " ORDER BY n.sent_at DESC LIMIT %s"
                    params.append(100)
            except (ValueError, TypeError):
                self.logger.warning(f"无效的limit值: {limit}，使用默认值100")
                sql += " ORDER BY n.sent_at DESC LIMIT %s"
                params.append(100)
            
            results = self.db.execute_query(sql, tuple(params))
            return results or []
            
        except Exception as e:
            error_msg = str(e)
            # 如果表不存在，记录警告并返回空列表
            if "doesn't exist" in error_msg or "1146" in error_msg:
                self.logger.warning(f"news_notifications表不存在，请运行 database/create_news_notifications_table.py 创建表。错误: {error_msg}")
            else:
                self.logger.error(f"获取用户通知失败: {error_msg}")
            return []
    
    def get_notification_history(self, user_id: Optional[int] = None, limit: int = 50, 
                                 days: int = 7) -> List[Dict]:
        """
        获取推送历史记录
        
        Args:
            user_id: 用户ID（如果为None，返回所有用户的历史）
            limit: 返回数量限制
            days: 查询最近N天的记录
        
        Returns:
            推送历史列表
        """
        if not self.use_database:
            return []
        
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # 动态检查importance_score字段是否存在
            try:
                check_sql = "SHOW COLUMNS FROM news_articles LIKE 'importance_score'"
                has_importance_score = len(self.db.execute_query(check_sql)) > 0
            except:
                has_importance_score = False
            
            if has_importance_score:
                sql = """
                    SELECT n.*, na.content, na.source_url, na.publish_time, na.sentiment,
                           na.sentiment_score, na.importance_score, na.importance_level
                    FROM news_notifications n
                    JOIN news_articles na ON n.news_id = na.id
                    WHERE n.is_sent = 1 AND n.sent_at >= %s
                """
            else:
                sql = """
                    SELECT n.*, na.content, na.source_url, na.publish_time, na.sentiment,
                           na.sentiment_score, NULL as importance_score, NULL as importance_level
                    FROM news_notifications n
                    JOIN news_articles na ON n.news_id = na.id
                    WHERE n.is_sent = 1 AND n.sent_at >= %s
                """
            params = [cutoff_time]
            
            # 如果指定了用户ID，可以添加用户过滤（如果表中有user_id字段）
            # 目前news_notifications表中没有user_id，所以暂时返回所有历史
            
            # 验证limit（防止SQL注入）
            try:
                limit_int = int(limit)
                if limit_int > 0 and limit_int <= 1000:  # 设置上限
                    sql += " ORDER BY n.sent_at DESC LIMIT %s"
                    params.append(limit_int)
                else:
                    self.logger.warning(f"limit值超出范围: {limit_int}，使用默认值100")
                    sql += " ORDER BY n.sent_at DESC LIMIT %s"
                    params.append(100)
            except (ValueError, TypeError):
                self.logger.warning(f"无效的limit值: {limit}，使用默认值100")
                sql += " ORDER BY n.sent_at DESC LIMIT %s"
                params.append(100)
            
            results = self.db.execute_query(sql, tuple(params))
            return results or []
            
        except Exception as e:
            error_msg = str(e)
            # 如果表不存在，记录警告并返回空列表
            if "doesn't exist" in error_msg or "1146" in error_msg:
                self.logger.warning(f"news_notifications表不存在，请运行 database/create_news_notifications_table.py 创建表。错误: {error_msg}")
            else:
                self.logger.error(f"获取推送历史失败: {error_msg}")
            return []
    
    def get_user_notification_rules(self, user_id: int) -> Dict:
        """
        获取用户的推送规则配置
        
        Args:
            user_id: 用户ID
        
        Returns:
            推送规则字典
        """
        # TODO: 如果将来需要支持用户自定义规则，可以从数据库读取
        # 目前返回默认规则
        return self.default_rules.copy()
    
    def update_user_notification_rules(self, user_id: int, rules: Dict) -> bool:
        """
        更新用户的推送规则配置
        
        Args:
            user_id: 用户ID
            rules: 推送规则字典
        
        Returns:
            是否成功
        """
        # TODO: 如果将来需要支持用户自定义规则，可以保存到数据库
        # 目前只更新内存中的默认规则（临时）
        self.default_rules.update(rules)
        return True