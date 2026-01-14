"""
采集股票历史数据（近10年）
用于初始数据采集或补充历史数据
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


def collect_stock_history(symbols: list = None, years: int = 10, 
                         limit: int = None, sort_by_turnover: bool = False):
    """
    采集股票历史数据（近N年）
    
    Args:
        symbols: 股票代码列表（如果为None，则获取所有股票）
        years: 采集多少年的数据（默认10年）
        limit: 限制股票数量（如果指定）
        sort_by_turnover: 是否按成交量排序
    """
    try:
        logger.info("=" * 60)
        logger.info(f"开始采集股票历史数据（近{years}年）")
        logger.info("=" * 60)
        
        collector = StockHistoryCollector()
        
        # 如果未指定股票列表，获取所有股票
        if symbols is None:
            try:
                data_source = StockDataSource()
                stock_list = data_source.get_all_stock_list(
                    limit=limit, 
                    sort_by_turnover=sort_by_turnover
                )
                symbols = [s['symbol'] for s in stock_list]
                logger.info(f"获取到 {len(symbols)} 只股票")
            except Exception as e:
                logger.error(f"获取股票列表失败: {str(e)}")
                return
        
        # 批量采集
        result = collector.batch_collect_stocks_history(symbols, years=years)
        
        logger.info("=" * 60)
        logger.info("历史数据采集完成")
        logger.info(f"  股票数量: {result.get('total_symbols', 0)}")
        logger.info(f"  总数据条数: {result.get('total_dates', 0)}")
        logger.info(f"  成功: {result.get('total_success', 0)}")
        logger.info(f"  失败: {result.get('total_fail', 0)}")
        logger.info(f"  成功率: {result.get('success_rate', 0):.1%}")
        logger.info("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"采集股票历史数据异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='采集股票历史数据（近10年）')
    parser.add_argument('--symbols', type=str, nargs='+', help='股票代码列表（可选）')
    parser.add_argument('--symbol', type=str, help='单个股票代码（可选）')
    parser.add_argument('--years', type=int, default=10, help='采集多少年的数据（默认10年）')
    parser.add_argument('--limit', type=int, help='限制股票数量')
    parser.add_argument('--sort-by-turnover', action='store_true', help='按成交量排序')
    
    args = parser.parse_args()
    
    symbols = None
    if args.symbols:
        symbols = args.symbols
    elif args.symbol:
        symbols = [args.symbol]
    
    collect_stock_history(
        symbols=symbols,
        years=args.years,
        limit=args.limit,
        sort_by_turnover=args.sort_by_turnover
    )
