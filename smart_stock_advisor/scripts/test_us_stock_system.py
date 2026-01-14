"""
测试美股数据系统
"""
import os
import sys
import io

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.logger import get_logger
from utils.us_stock_storage import USStockStorage
from data_source.us_stock_data_source import USStockDataSource
from utils.us_stock_collector import USStockCollector

logger = get_logger(__name__)


def test_table_exists():
    """测试表是否存在"""
    logger.info("=" * 60)
    logger.info("测试数据库表")
    logger.info("=" * 60)
    
    storage = USStockStorage()
    tables = [
        'us_sectors',
        'us_industries',
        'us_stock_info',
        'us_stock_history_data',
        'us_sector_stock_map',
        'us_industry_stock_map',
        'us_sector_index_history'
    ]
    
    all_exist = True
    for table in tables:
        try:
            sql = f"SELECT 1 FROM {table} LIMIT 1"
            storage.db.execute_query(sql)
            logger.info(f"[OK] 表 {table} 存在")
        except Exception as e:
            logger.error(f"[ERROR] 表 {table} 不存在: {str(e)}")
            all_exist = False
    
    return all_exist


def test_data_source():
    """测试数据源"""
    logger.info("=" * 60)
    logger.info("测试数据源")
    logger.info("=" * 60)
    
    data_source = USStockDataSource()
    
    # 测试获取股票数据
    logger.info("测试获取AAPL历史数据...")
    df = data_source.get_stock_data('AAPL', period='1mo')
    if not df.empty:
        logger.info(f"[OK] 成功获取AAPL数据，共 {len(df)} 条记录")
        logger.info(f"  列: {', '.join(df.columns.tolist())}")
    else:
        logger.error("[ERROR] 获取AAPL数据失败")
    
    # 测试获取股票信息
    logger.info("测试获取AAPL基本信息...")
    info = data_source.get_stock_info('AAPL')
    if info:
        logger.info(f"[OK] 成功获取AAPL基本信息")
        logger.info(f"  名称: {info.get('name_en')}")
        logger.info(f"  板块: {info.get('sector')}")
        logger.info(f"  行业: {info.get('industry')}")
        logger.info(f"  交易所: {info.get('exchange')}")
    else:
        logger.error("[ERROR] 获取AAPL基本信息失败")


def test_collector():
    """测试数据收集器"""
    logger.info("=" * 60)
    logger.info("测试数据收集器（收集AAPL最近1个月数据作为测试）")
    logger.info("=" * 60)
    
    collector = USStockCollector()
    
    # 初始化板块数据
    logger.info("初始化GICS板块数据...")
    collector.initialize_gics_sectors()
    
    # 测试收集单只股票数据（使用较短周期）
    from datetime import datetime, timedelta
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    logger.info(f"收集AAPL数据: {start_date} 至 {end_date}")
    result = collector.collect_stock_history(
        'AAPL',
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        update_existing=False
    )
    
    if result.get('success'):
        logger.info(f"[OK] 收集成功: {result.get('message')}")
        logger.info(f"  成功保存: {result.get('count')} 条记录")
        logger.info(f"  失败: {result.get('fail_count', 0)} 条记录")
    else:
        logger.error(f"[ERROR] 收集失败: {result.get('message')}")


def main():
    """主测试函数"""
    logger.info("\n" + "=" * 60)
    logger.info(" 美股数据系统测试")
    logger.info("=" * 60)
    
    # 1. 测试表是否存在
    if not test_table_exists():
        logger.error("数据库表不存在，请先运行: python scripts/create_us_stock_tables.py")
        return
    
    # 2. 测试数据源
    try:
        test_data_source()
    except Exception as e:
        logger.error(f"数据源测试失败: {str(e)}")
        logger.info("提示：请确保已安装 yfinance: pip install yfinance")
    
    # 3. 测试数据收集器
    try:
        test_collector()
    except Exception as e:
        logger.error(f"数据收集器测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("\n" + "=" * 60)
    logger.info(" 测试完成")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
