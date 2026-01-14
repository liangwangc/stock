"""
批量收集美股历史数据脚本（10年数据）
"""
import os
import sys
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.us_stock_collector import USStockCollector

logger = get_logger(__name__)


def collect_sp500_data():
    """收集S&P 500成分股的历史数据"""
    logger.info("=" * 60)
    logger.info("收集S&P 500成分股历史数据（10年）")
    logger.info("=" * 60)
    
    collector = USStockCollector()
    
    # 获取S&P 500成分股列表
    from data_source.us_stock_data_source import USStockDataSource
    data_source = USStockDataSource()
    
    symbols = data_source.get_sp500_stocks()
    
    if not symbols:
        logger.warning("无法获取S&P 500成分股列表，使用示例股票列表")
        # 使用一些知名股票作为示例
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ']
    
    logger.info(f"共 {len(symbols)} 只股票需要收集数据")
    
    # 批量收集
    result = collector.collect_batch_stocks(
        symbols=symbols,
        period="10y",
        delay=0.5  # 每只股票延迟0.5秒
    )
    
    logger.info("=" * 60)
    logger.info("批量收集完成")
    logger.info(f"总计: {result['total']}")
    logger.info(f"成功: {result['success_count']}")
    logger.info(f"失败: {result['fail_count']}")
    logger.info("=" * 60)
    
    if result['fail_list']:
        logger.warning(f"失败的股票: {', '.join(result['fail_list'])}")
    
    return result


def collect_custom_stocks(symbols: list):
    """收集指定股票的历史数据"""
    logger.info("=" * 60)
    logger.info(f"收集指定股票历史数据（共 {len(symbols)} 只）")
    logger.info("=" * 60)
    
    collector = USStockCollector()
    
    result = collector.collect_batch_stocks(
        symbols=symbols,
        period="10y",
        delay=0.5
    )
    
    logger.info("=" * 60)
    logger.info("收集完成")
    logger.info(f"总计: {result['total']}")
    logger.info(f"成功: {result['success_count']}")
    logger.info(f"失败: {result['fail_count']}")
    logger.info("=" * 60)
    
    return result


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='收集美股历史数据（10年）')
    parser.add_argument('--sp500', action='store_true', help='收集S&P 500成分股数据')
    parser.add_argument('--symbols', nargs='+', help='指定要收集的股票代码列表，如：--symbols AAPL MSFT GOOGL')
    parser.add_argument('--init-sectors', action='store_true', help='初始化GICS板块数据')
    
    args = parser.parse_args()
    
    collector = USStockCollector()
    
    # 初始化板块数据
    if args.init_sectors:
        logger.info("初始化GICS板块数据...")
        collector.initialize_gics_sectors()
    
    # 收集数据
    if args.sp500:
        collect_sp500_data()
    elif args.symbols:
        collect_custom_stocks(args.symbols)
    else:
        logger.info("请指定要收集的数据类型：")
        logger.info("  --sp500 : 收集S&P 500成分股数据")
        logger.info("  --symbols AAPL MSFT : 收集指定股票数据")
        logger.info("  --init-sectors : 初始化板块数据")
        logger.info("\n示例：")
        logger.info("  python scripts/collect_us_stock_data.py --init-sectors")
        logger.info("  python scripts/collect_us_stock_data.py --symbols AAPL MSFT GOOGL")
        logger.info("  python scripts/collect_us_stock_data.py --sp500")


if __name__ == '__main__':
    main()
