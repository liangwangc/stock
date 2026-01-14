"""
测试新闻源抓取功能
检查10个新闻源是否正常抓取，是否有数据
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

logger = get_logger(__name__)

# 尝试导入配置
try:
    from config import TUSHARE_TOKEN
except ImportError:
    TUSHARE_TOKEN = None

# 尝试导入UnifiedNewsSource
try:
    from quant_trading_platform.news import UnifiedNewsSource
    NEWS_SOURCE_AVAILABLE = True
except ImportError:
    try:
        from news import UnifiedNewsSource
        NEWS_SOURCE_AVAILABLE = True
    except ImportError:
        NEWS_SOURCE_AVAILABLE = False
        logger.error("无法导入UnifiedNewsSource")


def test_news_sources():
    """测试所有新闻源的抓取功能"""
    if not NEWS_SOURCE_AVAILABLE:
        logger.error("新闻源不可用，无法测试")
        return
    
    logger.info("=" * 80)
    logger.info("开始测试新闻源抓取功能")
    logger.info("=" * 80)
    
    try:
        # 初始化统一新闻源
        logger.info("\n初始化统一新闻源...")
        news_source = UnifiedNewsSource(tushare_token=TUSHARE_TOKEN)
        
        # 获取所有新闻源信息
        sources_info = []
        for source_name, source in news_source.sources:
            sources_info.append({
                'name': source_name,
                'source': source
            })
            logger.info(f"  ✓ {source_name}")
        
        logger.info(f"\n共初始化 {len(sources_info)} 个新闻源\n")
        
        # 测试每个新闻源
        results = {}
        total_news = 0
        total_success = 0
        total_failed = 0
        
        for source_info in sources_info:
            source_name = source_info['name']
            source = source_info['source']
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"测试新闻源: {source_name}")
            logger.info(f"{'=' * 80}")
            
            try:
                # 测试市场新闻抓取
                logger.info(f"\n1. 测试市场新闻抓取（限制5条）...")
                start_time = datetime.now()
                
                market_news = source.get_market_news(limit=5)
                
                elapsed = (datetime.now() - start_time).total_seconds()
                
                if market_news:
                    logger.info(f"  ✓ 成功获取 {len(market_news)} 条市场新闻 (耗时: {elapsed:.2f}秒)")
                    
                    # 显示前几条新闻的标题
                    for i, news in enumerate(market_news[:3], 1):
                        title = news.get('title', 'N/A')
                        source_news = news.get('source', 'unknown')
                        time = news.get('time', 'N/A')
                        logger.info(f"    {i}. [{source_news}] {title[:60]}... ({time})")
                    
                    results[source_name] = {
                        'status': 'success',
                        'market_news_count': len(market_news),
                        'elapsed_time': elapsed,
                        'sample_news': market_news[:3]
                    }
                    total_news += len(market_news)
                    total_success += 1
                else:
                    logger.warning(f"  ✗ 未获取到市场新闻")
                    results[source_name] = {
                        'status': 'no_data',
                        'market_news_count': 0,
                        'elapsed_time': elapsed
                    }
                    total_failed += 1
                
                # 测试股票新闻抓取（如果有该功能）
                if hasattr(source, 'get_stock_news'):
                    logger.info(f"\n2. 测试股票新闻抓取（测试股票: 600519，限制3条）...")
                    try:
                        stock_news = source.get_stock_news('600519', limit=3)
                        
                        if stock_news:
                            logger.info(f"  ✓ 成功获取 {len(stock_news)} 条股票新闻")
                            results[source_name]['stock_news_count'] = len(stock_news)
                            
                            # 显示前几条新闻的标题
                            for i, news in enumerate(stock_news[:2], 1):
                                title = news.get('title', 'N/A')
                                logger.info(f"    {i}. {title[:60]}...")
                        else:
                            logger.warning(f"  ✗ 未获取到股票新闻")
                            results[source_name]['stock_news_count'] = 0
                    except Exception as e:
                        logger.warning(f"  ✗ 股票新闻抓取失败: {str(e)}")
                        results[source_name]['stock_news_count'] = 0
                        results[source_name]['stock_error'] = str(e)
                
            except Exception as e:
                logger.error(f"  ✗ 测试失败: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                results[source_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                total_failed += 1
        
        # 测试统一新闻源
        logger.info(f"\n{'=' * 80}")
        logger.info("测试统一新闻源聚合功能")
        logger.info(f"{'=' * 80}")
        
        try:
            logger.info("\n测试 get_market_news() (限制20条)...")
            start_time = datetime.now()
            all_market_news = news_source.get_market_news(limit=20)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if all_market_news:
                logger.info(f"  ✓ 统一新闻源成功获取 {len(all_market_news)} 条市场新闻 (耗时: {elapsed:.2f}秒)")
                logger.info(f"  去重后新闻数量: {len(all_market_news)}")
                
                # 统计各新闻源贡献
                source_count = {}
                for news in all_market_news:
                    source = news.get('source', 'unknown')
                    source_count[source] = source_count.get(source, 0) + 1
                
                logger.info(f"\n  各新闻源贡献:")
                for source, count in sorted(source_count.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"    {source}: {count} 条")
                
                results['unified_source'] = {
                    'status': 'success',
                    'total_news': len(all_market_news),
                    'elapsed_time': elapsed,
                    'source_distribution': source_count
                }
            else:
                logger.warning(f"  ✗ 统一新闻源未获取到新闻")
                results['unified_source'] = {
                    'status': 'no_data',
                    'total_news': 0
                }
        except Exception as e:
            logger.error(f"  ✗ 统一新闻源测试失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            results['unified_source'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # 总结
        logger.info(f"\n{'=' * 80}")
        logger.info("测试总结")
        logger.info(f"{'=' * 80}")
        logger.info(f"\n新闻源统计:")
        logger.info(f"  总新闻源数: {len(sources_info)}")
        logger.info(f"  成功抓取: {total_success}")
        logger.info(f"  失败/无数据: {total_failed}")
        logger.info(f"  总抓取新闻数: {total_news}")
        
        logger.info(f"\n各新闻源详情:")
        for source_name, result in results.items():
            if source_name == 'unified_source':
                continue
            status = result.get('status', 'unknown')
            news_count = result.get('market_news_count', 0)
            elapsed = result.get('elapsed_time', 0)
            if status == 'success':
                logger.info(f"  ✓ {source_name}: {news_count} 条新闻 ({elapsed:.2f}秒)")
            elif status == 'no_data':
                logger.info(f"  ⚠ {source_name}: 无数据")
            else:
                error = result.get('error', 'unknown')
                logger.info(f"  ✗ {source_name}: 错误 - {error}")
        
        if 'unified_source' in results:
            unified = results['unified_source']
            if unified.get('status') == 'success':
                logger.info(f"\n  ✓ 统一新闻源: {unified['total_news']} 条新闻 ({unified.get('elapsed_time', 0):.2f}秒)")
        
        return results
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == '__main__':
    results = test_news_sources()
    if results:
        logger.info("\n测试完成！")
    else:
        logger.error("\n测试失败！")
