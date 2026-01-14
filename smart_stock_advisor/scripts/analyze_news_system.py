"""
新闻系统综合分析脚本
1. 测试新闻源抓取
2. 验证数据库存储
3. 检查情感分析标签
4. 验证新闻与股票关联
5. 批量处理未关联的新闻
"""
import os
import sys
import io
from datetime import datetime, timedelta

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, '..', 'quant_trading_platform'))

from utils.logger import get_logger
from utils.news_crawler import NewsCrawler
from utils.news_storage import NewsStorage
from utils.news_stock_mapper import NewsStockMapper
from utils.db_connection import DatabaseConnection

logger = get_logger(__name__)

# 尝试导入配置
try:
    from config import TUSHARE_TOKEN
except ImportError:
    TUSHARE_TOKEN = None


def test_news_sources():
    """1. 测试新闻源抓取"""
    logger.info("=" * 80)
    logger.info("1. 测试新闻源抓取")
    logger.info("=" * 80)
    
    try:
        crawler = NewsCrawler()
        result = crawler.crawl_market_news(limit=20)
        
        logger.info(f"抓取结果: 成功 {result['success']}, 重复 {result['duplicate']}, 失败 {result['failed']}")
        return result['success'] > 0
    except Exception as e:
        logger.error(f"测试新闻源抓取失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_database_storage():
    """2. 验证数据库存储"""
    logger.info("\n" + "=" * 80)
    logger.info("2. 验证数据库存储")
    logger.info("=" * 80)
    
    try:
        db = DatabaseConnection()
        
        # 检查新闻总数
        sql = "SELECT COUNT(*) as cnt FROM news_articles"
        results = db.execute_query(sql)
        total_count = results[0]['cnt'] if results else 0
        logger.info(f"数据库中共有 {total_count} 条新闻")
        
        # 检查最近的新闻
        sql = """
            SELECT id, title, source, sentiment, is_positive, is_negative, symbol, sector, industry
            FROM news_articles
            ORDER BY fetch_time DESC
            LIMIT 5
        """
        results = db.execute_query(sql)
        
        if results:
            logger.info(f"\n最近5条新闻:")
            for i, news in enumerate(results, 1):
                logger.info(f"  {i}. [{news['source']}] {news['title'][:60]}...")
                logger.info(f"     情感: {news.get('sentiment', 'N/A')} "
                          f"[利好: {news.get('is_positive', 0)}, 利空: {news.get('is_negative', 0)}]")
                logger.info(f"     关联: 股票={news.get('symbol', 'N/A')}, "
                          f"板块={news.get('sector', 'N/A')}, 行业={news.get('industry', 'N/A')}")
        
        return True
    except Exception as e:
        logger.error(f"验证数据库存储失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_sentiment_analysis():
    """3. 检查情感分析标签"""
    logger.info("\n" + "=" * 80)
    logger.info("3. 检查情感分析标签")
    logger.info("=" * 80)
    
    try:
        db = DatabaseConnection()
        
        # 统计情感分析结果
        sql = """
            SELECT 
                sentiment,
                COUNT(*) as count,
                AVG(sentiment_score) as avg_score,
                SUM(is_positive) as positive_count,
                SUM(is_negative) as negative_count,
                AVG(sentiment_confidence) as avg_confidence
            FROM news_articles
            WHERE sentiment IS NOT NULL
            GROUP BY sentiment
            ORDER BY count DESC
        """
        results = db.execute_query(sql)
        
        if results:
            logger.info(f"情感分析统计:")
            total = 0
            for row in results:
                sentiment = row.get('sentiment', 'N/A')
                count = row.get('count', 0)
                avg_score = row.get('avg_score', 0)
                avg_conf = row.get('avg_confidence', 0)
                positive = row.get('positive_count', 0)
                negative = row.get('negative_count', 0)
                logger.info(f"  {sentiment}: {count} 条 "
                          f"(得分: {avg_score:.3f}, 置信度: {avg_conf:.3f}, "
                          f"利好: {positive}, 利空: {negative})")
                total += count
            logger.info(f"  总计: {total} 条新闻有情感分析结果")
        
        # 检查未分析的新闻
        sql = "SELECT COUNT(*) as cnt FROM news_articles WHERE sentiment IS NULL"
        results = db.execute_query(sql)
        unanalyzed = results[0]['cnt'] if results else 0
        if unanalyzed > 0:
            logger.warning(f"  有 {unanalyzed} 条新闻未进行情感分析")
        
        return True
    except Exception as e:
        logger.error(f"检查情感分析标签失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_news_stock_mapping():
    """4. 验证新闻与股票关联"""
    logger.info("\n" + "=" * 80)
    logger.info("4. 验证新闻与股票关联")
    logger.info("=" * 80)
    
    try:
        db = DatabaseConnection()
        mapper = NewsStockMapper()
        
        # 统计关联情况
        sql = """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT symbol) as stock_count,
                COUNT(DISTINCT sector) as sector_count,
                COUNT(DISTINCT industry) as industry_count,
                SUM(CASE WHEN symbol IS NOT NULL THEN 1 ELSE 0 END) as with_symbol,
                SUM(CASE WHEN sector IS NOT NULL THEN 1 ELSE 0 END) as with_sector,
                SUM(CASE WHEN industry IS NOT NULL THEN 1 ELSE 0 END) as with_industry
            FROM news_articles
        """
        results = db.execute_query(sql)
        
        if results:
            row = results[0]
            total = row.get('total', 0)
            with_symbol = row.get('with_symbol', 0)
            with_sector = row.get('with_sector', 0)
            with_industry = row.get('with_industry', 0)
            stock_count = row.get('stock_count', 0)
            
            logger.info(f"关联统计:")
            logger.info(f"  总新闻数: {total}")
            logger.info(f"  关联股票的新闻: {with_symbol} 条 ({with_symbol/total*100:.1f}%)")
            logger.info(f"  关联板块的新闻: {with_sector} 条 ({with_sector/total*100:.1f}%)")
            logger.info(f"  关联行业的新闻: {with_industry} 条 ({with_industry/total*100:.1f}%)")
            logger.info(f"  关联的股票数: {stock_count}")
        
        # 查看关联最多的股票
        sql = """
            SELECT symbol, COUNT(*) as count
            FROM news_articles
            WHERE symbol IS NOT NULL
            GROUP BY symbol
            ORDER BY count DESC
            LIMIT 10
        """
        results = db.execute_query(sql)
        
        if results:
            logger.info(f"\n关联最多的股票:")
            for row in results:
                logger.info(f"  {row['symbol']}: {row['count']} 条新闻")
        
        # 检查未关联的新闻
        sql = """
            SELECT COUNT(*) as cnt
            FROM news_articles
            WHERE symbol IS NULL AND sector IS NULL AND industry IS NULL
        """
        results = db.execute_query(sql)
        unlinked = results[0]['cnt'] if results else 0
        if unlinked > 0:
            logger.warning(f"\n  有 {unlinked} 条新闻未关联任何股票/板块/行业")
            return False
        
        return True
    except Exception as e:
        logger.error(f"验证新闻与股票关联失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def process_unlinked_news():
    """5. 批量处理未关联的新闻"""
    logger.info("\n" + "=" * 80)
    logger.info("5. 批量处理未关联的新闻")
    logger.info("=" * 80)
    
    try:
        mapper = NewsStockMapper()
        result = mapper.process_news_batch(limit=100)
        
        logger.info(f"批量处理结果: 处理 {result['processed']}, 关联 {result['mapped']}, 失败 {result['failed']}")
        
        if result['mapped'] > 0:
            logger.info(f"✓ 成功关联 {result['mapped']} 条新闻")
            return True
        else:
            logger.info(f"没有需要关联的新闻或关联失败")
            return False
    except Exception as e:
        logger.error(f"批量处理未关联新闻失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("新闻系统综合分析")
    logger.info("=" * 80)
    
    results = {}
    
    # 1. 测试新闻源抓取
    results['news_sources'] = test_news_sources()
    
    # 2. 验证数据库存储
    results['database_storage'] = test_database_storage()
    
    # 3. 检查情感分析标签
    results['sentiment_analysis'] = test_sentiment_analysis()
    
    # 4. 验证新闻与股票关联
    results['stock_mapping'] = test_news_stock_mapping()
    
    # 5. 批量处理未关联的新闻
    if not results['stock_mapping']:
        results['process_unlinked'] = process_unlinked_news()
    else:
        results['process_unlinked'] = True
        logger.info("\n所有新闻都已关联，无需批量处理")
    
    # 总结
    logger.info("\n" + "=" * 80)
    logger.info("综合分析总结")
    logger.info("=" * 80)
    
    logger.info(f"\n测试结果:")
    logger.info(f"  新闻源抓取: {'✓ 通过' if results.get('news_sources') else '✗ 失败'}")
    logger.info(f"  数据库存储: {'✓ 通过' if results.get('database_storage') else '✗ 失败'}")
    logger.info(f"  情感分析: {'✓ 通过' if results.get('sentiment_analysis') else '✗ 失败'}")
    logger.info(f"  股票关联: {'✓ 通过' if results.get('stock_mapping') else '✗ 失败'}")
    logger.info(f"  批量处理: {'✓ 完成' if results.get('process_unlinked') else '✗ 失败'}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✓ 所有测试通过！")
    else:
        logger.warning("\n⚠ 部分测试未通过，请检查相关功能")
    
    logger.info("=" * 80)
    
    return all_passed


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"分析失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
