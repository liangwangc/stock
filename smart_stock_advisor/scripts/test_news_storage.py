"""
测试新闻存储功能
验证新闻是否正确存储到数据库，情感分析是否正常
"""
import os
import sys
import io
from datetime import datetime

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

from utils.logger import get_logger
from utils.news_storage import NewsStorage
from utils.news_crawler import NewsCrawler
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)

# 尝试导入配置
try:
    from config import TUSHARE_TOKEN
except ImportError:
    TUSHARE_TOKEN = None


def test_news_storage():
    """测试新闻存储功能"""
    logger.info("=" * 80)
    logger.info("测试新闻存储功能")
    logger.info("=" * 80)
    
    # 1. 测试数据库连接
    logger.info("\n1. 测试数据库连接...")
    db = DatabaseConnection()
    try:
        # 检查news_articles表是否存在
        sql = """
            SELECT COUNT(*) as cnt FROM news_articles
        """
        results = db.execute_query(sql)
        if results:
            count = results[0]['cnt']
            logger.info(f"  ✓ 数据库连接成功，news_articles表中有 {count} 条新闻")
        else:
            logger.warning("  ⚠ 无法查询news_articles表")
    except Exception as e:
        logger.error(f"  ✗ 数据库连接失败: {str(e)}")
        return False
    
    # 2. 测试新闻抓取和存储
    logger.info("\n2. 测试新闻抓取和存储...")
    try:
        crawler = NewsCrawler()
        result = crawler.crawl_market_news(limit=10)
        
        logger.info(f"  抓取结果: 成功 {result['success']}, 重复 {result['duplicate']}, 失败 {result['failed']}")
        
        if result['success'] > 0:
            logger.info(f"  ✓ 成功存储 {result['success']} 条新闻")
        else:
            logger.warning(f"  ⚠ 未存储任何新闻")
    except Exception as e:
        logger.error(f"  ✗ 新闻抓取和存储失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # 3. 检查存储的新闻数据
    logger.info("\n3. 检查存储的新闻数据...")
    try:
        sql = """
            SELECT id, title, source, sentiment, sentiment_score, is_positive, is_negative,
                   symbol, sector, industry, news_type, publish_time, fetch_time
            FROM news_articles
            ORDER BY fetch_time DESC
            LIMIT 10
        """
        results = db.execute_query(sql)
        
        if results:
            logger.info(f"  最近10条新闻:")
            for i, news in enumerate(results, 1):
                logger.info(f"    {i}. [{news['source']}] {news['title'][:50]}...")
                logger.info(f"       情感: {news.get('sentiment', 'N/A')} "
                          f"(得分: {news.get('sentiment_score', 0):.2f}) "
                          f"[利好: {news.get('is_positive', 0)}, 利空: {news.get('is_negative', 0)}]")
                logger.info(f"       关联: 股票={news.get('symbol', 'N/A')}, "
                          f"板块={news.get('sector', 'N/A')}, 行业={news.get('industry', 'N/A')}")
                logger.info(f"       时间: 发布={news.get('publish_time', 'N/A')}, "
                          f"抓取={news.get('fetch_time', 'N/A')}")
                logger.info("")
            logger.info(f"  ✓ 成功查询到 {len(results)} 条新闻")
        else:
            logger.warning("  ⚠ 未查询到任何新闻")
    except Exception as e:
        logger.error(f"  ✗ 查询新闻失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # 4. 检查情感分析统计
    logger.info("\n4. 检查情感分析统计...")
    try:
        sql = """
            SELECT 
                sentiment,
                COUNT(*) as count,
                AVG(sentiment_score) as avg_score,
                SUM(is_positive) as positive_count,
                SUM(is_negative) as negative_count
            FROM news_articles
            WHERE sentiment IS NOT NULL
            GROUP BY sentiment
        """
        results = db.execute_query(sql)
        
        if results:
            logger.info(f"  情感分析统计:")
            total = 0
            for row in results:
                sentiment = row.get('sentiment', 'N/A')
                count = row.get('count', 0)
                avg_score = row.get('avg_score', 0)
                positive = row.get('positive_count', 0)
                negative = row.get('negative_count', 0)
                logger.info(f"    {sentiment}: {count} 条 "
                          f"(平均得分: {avg_score:.3f}, 利好: {positive}, 利空: {negative})")
                total += count
            logger.info(f"  总计: {total} 条新闻有情感分析结果")
        else:
            logger.warning("  ⚠ 未找到情感分析统计")
    except Exception as e:
        logger.error(f"  ✗ 查询情感分析统计失败: {str(e)}")
    
    # 5. 检查新闻与股票的关联
    logger.info("\n5. 检查新闻与股票的关联...")
    try:
        sql = """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT symbol) as stock_count,
                COUNT(DISTINCT sector) as sector_count,
                COUNT(DISTINCT industry) as industry_count
            FROM news_articles
            WHERE symbol IS NOT NULL OR sector IS NOT NULL OR industry IS NOT NULL
        """
        results = db.execute_query(sql)
        
        if results:
            row = results[0]
            total = row.get('total', 0)
            stock_count = row.get('stock_count', 0)
            sector_count = row.get('sector_count', 0)
            industry_count = row.get('industry_count', 0)
            logger.info(f"  关联统计:")
            logger.info(f"    有关联的新闻: {total} 条")
            logger.info(f"    关联股票数: {stock_count}")
            logger.info(f"    关联板块数: {sector_count}")
            logger.info(f"    关联行业数: {industry_count}")
            
            # 查看具体关联的股票
            sql2 = """
                SELECT symbol, COUNT(*) as count
                FROM news_articles
                WHERE symbol IS NOT NULL
                GROUP BY symbol
                ORDER BY count DESC
                LIMIT 10
            """
            results2 = db.execute_query(sql2)
            if results2:
                logger.info(f"    关联最多的股票:")
                for row2 in results2:
                    logger.info(f"      {row2['symbol']}: {row2['count']} 条新闻")
        else:
            logger.warning("  ⚠ 未找到关联统计")
    except Exception as e:
        logger.error(f"  ✗ 查询关联统计失败: {str(e)}")
    
    logger.info("\n" + "=" * 80)
    logger.info("测试完成")
    logger.info("=" * 80)
    
    return True


if __name__ == '__main__':
    try:
        test_news_storage()
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
