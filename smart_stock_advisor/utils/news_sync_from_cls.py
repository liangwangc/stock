"""
从 news-analysis-system-main 同步新闻数据
支持从 cls_news_db 数据库同步新闻和分析结果到 smart_stock_advisor 数据库
"""
import os
import sys
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_connection import DatabaseConnection as DBConnection
from utils.logger import get_logger
from config_db import USE_DATABASE, DB_CONFIG

logger = get_logger(__name__)


class NewsSyncFromCls:
    """从财联社新闻系统同步数据"""
    
    def __init__(self, cls_db_config: Optional[Dict] = None):
        """
        初始化同步器
        
        Args:
            cls_db_config: 财联社数据库配置，格式：
                {
                    'host': 'localhost',
                    'user': 'root',
                    'password': 'password',
                    'database': 'cls_news_db',
                    'port': 3306
                }
                如果为None，则从环境变量或默认配置读取
        """
        self.logger = logger
        self.main_db = DBConnection() if USE_DATABASE else None
        
        # 财联社数据库配置
        if cls_db_config:
            self.cls_db_config = cls_db_config
        else:
            # 默认配置（可以从环境变量读取）
            self.cls_db_config = {
                'host': os.getenv('CLS_DB_HOST', 'localhost'),
                'user': os.getenv('CLS_DB_USER', 'root'),
                'password': os.getenv('CLS_DB_PASSWORD', 'qwer123123'),
                'database': os.getenv('CLS_DB_NAME', 'cls_news_db'),
                'port': int(os.getenv('CLS_DB_PORT', '3306'))
            }
        
        # 创建财联社数据库连接
        try:
            from sqlalchemy import create_engine
            self.cls_db_url = (
                f"mysql+pymysql://{self.cls_db_config['user']}:"
                f"{self.cls_db_config['password']}@{self.cls_db_config['host']}:"
                f"{self.cls_db_config['port']}/{self.cls_db_config['database']}"
            )
            self.cls_engine = create_engine(self.cls_db_url)
            self.logger.info(f"已连接到财联社数据库: {self.cls_db_config['database']}")
        except Exception as e:
            self.logger.error(f"连接财联社数据库失败: {str(e)}")
            self.cls_engine = None
    
    def generate_content_hash(self, title: str, content: str) -> str:
        """生成内容哈希"""
        combined = (title or '') + (content or '')
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def sync_news(self, limit: Optional[int] = None, since: Optional[datetime] = None) -> Dict[str, int]:
        """
        同步新闻数据
        
        Args:
            limit: 限制同步数量（None表示不限制）
            since: 只同步此时间之后的新闻（None表示同步所有未同步的）
            
        Returns:
            {'synced': 同步数量, 'skipped': 跳过数量, 'failed': 失败数量}
        """
        if not self.main_db or not self.cls_engine:
            self.logger.error("数据库连接不可用")
            return {'synced': 0, 'skipped': 0, 'failed': 0}
        
        try:
            import pandas as pd
            
            # 1. 查询财联社数据库中的新闻（包含股票关联信息）
            query = """
                SELECT id, title, content, publish_date, publish_time, content_hash, create_time,
                       symbol, sector, industry, concept, source
                FROM news
            """
            params = []
            
            if since:
                query += " WHERE create_time >= %s"
                params.append(since)
            
            query += " ORDER BY id ASC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            self.logger.info(f"查询财联社新闻，条件: since={since}, limit={limit}")
            cls_news_df = pd.read_sql(query, self.cls_engine, params=params if params else None)
            
            if cls_news_df.empty:
                self.logger.info("没有新新闻需要同步")
                return {'synced': 0, 'skipped': 0, 'failed': 0}
            
            self.logger.info(f"查询到 {len(cls_news_df)} 条新闻")
            
            # 2. 检查哪些新闻已经存在（通过 content_hash）
            existing_hashes = set()
            if not cls_news_df['content_hash'].isna().all():
                placeholders = ','.join(['%s'] * len(cls_news_df))
                check_sql = f"""
                    SELECT content_hash FROM news_articles 
                    WHERE content_hash IN ({placeholders})
                """
                existing_records = self.main_db.execute_query(
                    check_sql, 
                    tuple(cls_news_df['content_hash'].dropna().tolist())
                )
                existing_hashes = {str(r['content_hash']) for r in existing_records if r.get('content_hash')}
            
            # 3. 过滤出需要同步的新闻
            new_news_df = cls_news_df[~cls_news_df['content_hash'].isin(existing_hashes)]
            
            if new_news_df.empty:
                self.logger.info("所有新闻都已同步")
                return {'synced': 0, 'skipped': len(cls_news_df), 'failed': 0}
            
            self.logger.info(f"需要同步 {len(new_news_df)} 条新新闻")
            
            # 4. 准备插入数据
            synced_count = 0
            failed_count = 0
            
            for _, row in new_news_df.iterrows():
                try:
                    # 构建发布时间
                    publish_time = None
                    if pd.notna(row.get('publish_date')):
                        date_str = str(row['publish_date'])
                        time_str = str(row.get('publish_time', '00:00:00')) if pd.notna(row.get('publish_time')) else '00:00:00'
                        try:
                            publish_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                        except:
                            publish_time = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    # 确保 content_hash 存在
                    content_hash = row.get('content_hash')
                    if pd.isna(content_hash) or not content_hash:
                        content_hash = self.generate_content_hash(
                            str(row.get('title', '')),
                            str(row.get('content', ''))
                        )
                    
                    # 获取source字段（如果存在）
                    source = str(row.get('source', '财联社')) if pd.notna(row.get('source')) else '财联社'
                    
                    # 插入新闻（包含股票关联信息）
                    insert_sql = """
                        INSERT INTO news_articles 
                        (title, content, publish_time, fetch_time, source, content_hash, 
                         symbol, sector, industry, concept, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (
                        str(row.get('title', '')),
                        str(row.get('content', '')),
                        publish_time,
                        datetime.now(),
                        source,
                        content_hash,
                        str(row.get('symbol', '')) if pd.notna(row.get('symbol')) and str(row.get('symbol', '')) != 'None' else None,
                        str(row.get('sector', '')) if pd.notna(row.get('sector')) and str(row.get('sector', '')) != 'None' else None,
                        str(row.get('industry', '')) if pd.notna(row.get('industry')) and str(row.get('industry', '')) != 'None' else None,
                        str(row.get('concept', '')) if pd.notna(row.get('concept')) and str(row.get('concept', '')) != 'None' else None,
                        datetime.now()
                    )
                    
                    self.main_db.execute_update(insert_sql, params)
                    synced_count += 1
                    
                except Exception as e:
                    self.logger.error(f"同步新闻失败 (id={row.get('id')}): {str(e)}")
                    failed_count += 1
            
            skipped_count = len(cls_news_df) - len(new_news_df)
            
            self.logger.info(f"同步完成: 成功={synced_count}, 跳过={skipped_count}, 失败={failed_count}")
            
            return {
                'synced': synced_count,
                'skipped': skipped_count,
                'failed': failed_count
            }
            
        except Exception as e:
            self.logger.error(f"同步新闻异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'synced': 0, 'skipped': 0, 'failed': 0}
    
    def sync_analysis_results(self, limit: Optional[int] = None) -> Dict[str, int]:
        """
        同步LLM分析结果
        
        Args:
            limit: 限制同步数量（None表示不限制）
            
        Returns:
            {'synced': 同步数量, 'skipped': 跳过数量, 'failed': 失败数量}
        """
        if not self.main_db or not self.cls_engine:
            self.logger.error("数据库连接不可用")
            return {'synced': 0, 'skipped': 0, 'failed': 0}
        
        try:
            import pandas as pd
            
            # 1. 查询分析结果
            query = """
                SELECT ar.*, n.content_hash
                FROM analysis_results ar
                JOIN news n ON ar.news_index = n.id
                ORDER BY ar.id DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            self.logger.info(f"查询LLM分析结果，limit={limit}")
            analysis_df = pd.read_sql(query, self.cls_engine)
            
            if analysis_df.empty:
                self.logger.info("没有分析结果需要同步")
                return {'synced': 0, 'skipped': 0, 'failed': 0}
            
            self.logger.info(f"查询到 {len(analysis_df)} 条分析结果")
            
            # 2. 通过 content_hash 关联到 news_articles
            synced_count = 0
            skipped_count = 0
            failed_count = 0
            
            for _, row in analysis_df.iterrows():
                try:
                    content_hash = row.get('content_hash')
                    if pd.isna(content_hash) or not content_hash:
                        skipped_count += 1
                        continue
                    
                    # 查找对应的 news_articles 记录
                    find_sql = "SELECT id FROM news_articles WHERE content_hash = %s LIMIT 1"
                    news_record = self.main_db.execute_query(find_sql, (content_hash,))
                    
                    if not news_record:
                        skipped_count += 1
                        continue
                    
                    news_id = news_record[0]['id']
                    
                    # 检查是否已经同步过（通过 llm_analyzed_at 判断）
                    check_sql = "SELECT id FROM news_articles WHERE id = %s AND llm_analyzed_at IS NOT NULL"
                    existing = self.main_db.execute_query(check_sql, (news_id,))
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # 更新 LLM 分析字段
                    update_sql = """
                        UPDATE news_articles SET
                            llm_category = %s,
                            llm_subcategory = %s,
                            llm_keywords = %s,
                            llm_sentiment_score = %s,
                            llm_summary = %s,
                            llm_impact_markets = %s,
                            llm_is_market_relevant = %s,
                            llm_analyzed_at = %s
                        WHERE id = %s
                    """
                    
                    params = (
                        str(row.get('category', '')) if pd.notna(row.get('category')) else None,
                        str(row.get('subcategory', '')) if pd.notna(row.get('subcategory')) else None,
                        str(row.get('keywords', '')) if pd.notna(row.get('keywords')) else None,
                        float(row.get('sentiment')) if pd.notna(row.get('sentiment')) else None,
                        str(row.get('summary', '')) if pd.notna(row.get('summary')) else None,
                        str(row.get('impact_markets', '')) if pd.notna(row.get('impact_markets')) else None,
                        1 if pd.notna(row.get('is_market_relevant')) and row.get('is_market_relevant') else 0,
                        datetime.now(),
                        news_id
                    )
                    
                    self.main_db.execute_update(update_sql, params)
                    synced_count += 1
                    
                except Exception as e:
                    self.logger.error(f"同步分析结果失败 (news_index={row.get('news_index')}): {str(e)}")
                    failed_count += 1
            
            self.logger.info(f"分析结果同步完成: 成功={synced_count}, 跳过={skipped_count}, 失败={failed_count}")
            
            return {
                'synced': synced_count,
                'skipped': skipped_count,
                'failed': failed_count
            }
            
        except Exception as e:
            self.logger.error(f"同步分析结果异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'synced': 0, 'skipped': 0, 'failed': 0}
    
    def sync_all(self, news_limit: Optional[int] = None, analysis_limit: Optional[int] = None) -> Dict[str, any]:
        """
        同步所有数据（新闻 + 分析结果）
        
        Args:
            news_limit: 新闻同步限制
            analysis_limit: 分析结果同步限制
            
        Returns:
            同步结果统计
        """
        self.logger.info("开始同步所有数据...")
        
        # 1. 同步新闻
        news_result = self.sync_news(limit=news_limit)
        
        # 2. 同步分析结果
        analysis_result = self.sync_analysis_results(limit=analysis_limit)
        
        total_result = {
            'news': news_result,
            'analysis': analysis_result,
            'total_synced': news_result['synced'] + analysis_result['synced'],
            'total_skipped': news_result['skipped'] + analysis_result['skipped'],
            'total_failed': news_result['failed'] + analysis_result['failed']
        }
        
        self.logger.info(f"全部同步完成: {total_result}")
        
        return total_result


if __name__ == '__main__':
    # 测试同步功能
    sync = NewsSyncFromCls()
    
    # 同步最近1小时的新闻
    since = datetime.now() - timedelta(hours=1)
    result = sync.sync_all(news_limit=100, analysis_limit=100)
    
    print(f"同步结果: {result}")
