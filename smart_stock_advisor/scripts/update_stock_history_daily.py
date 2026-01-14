"""
每日收盘后增量更新股票历史数据
该脚本应在每天收盘后自动执行（通过定时任务）
"""
import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.stock_history_collector import StockHistoryCollector
from data_source.stock_data_source import StockDataSource

logger = get_logger(__name__)


def update_stock_history_daily(symbols: list = None):
    """
    每日收盘后增量更新股票历史数据
    
    Args:
        symbols: 股票代码列表（如果为None，则更新所有股票）
    """
    try:
        logger.info("=" * 60)
        logger.info("开始每日增量更新股票历史数据")
        logger.info("=" * 60)
        
        collector = StockHistoryCollector()
        
        # 如果未指定股票列表，获取所有股票
        if symbols is None:
            try:
                data_source = StockDataSource()
                stock_list = data_source.get_all_stock_list(limit=None, sort_by_turnover=False)
                symbols = [s['symbol'] for s in stock_list]
                logger.info(f"获取到 {len(symbols)} 只股票，将更新所有股票的数据")
            except Exception as e:
                logger.error(f"获取股票列表失败: {str(e)}")
                # 如果获取股票列表失败，使用数据库中已有的股票
                from utils.stock_history_storage import StockHistoryStorage
                storage = StockHistoryStorage()
                sql = "SELECT DISTINCT symbol FROM stock_history_data"
                results = storage.db.execute_query(sql)
                symbols = [r['symbol'] for r in results]
                logger.info(f"从数据库获取到 {len(symbols)} 只股票")
        
        # 执行增量更新
        result = collector.incremental_update_today(symbols)
        
        logger.info("=" * 60)
        logger.info("每日增量更新完成")
        logger.info(f"  日期: {result.get('date', 'N/A')}")
        logger.info(f"  股票数量: {result.get('total_symbols', 0)}")
        logger.info(f"  成功: {result.get('success_count', 0)}")
        logger.info(f"  失败: {result.get('fail_count', 0)}")
        logger.info(f"  跳过: {result.get('skip_count', 0)}")
        logger.info("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"每日增量更新异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='每日增量更新股票历史数据')
    parser.add_argument('--symbols', type=str, nargs='+', help='股票代码列表（可选，如果不指定则更新所有股票）')
    parser.add_argument('--symbol', type=str, help='单个股票代码（可选）')
    
    args = parser.parse_args()
    
    symbols = None
    if args.symbols:
        symbols = args.symbols
    elif args.symbol:
        symbols = [args.symbol]
    
    update_stock_history_daily(symbols)
