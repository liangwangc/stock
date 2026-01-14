"""
测试美股板块和行业信息存储
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
from utils.us_stock_collector import USStockCollector
from utils.us_stock_storage import USStockStorage
from data_source.us_stock_data_source import USStockDataSource

logger = get_logger(__name__)


def test_sector_industry_mapping():
    """测试板块和行业信息映射和存储"""
    logger.info("=" * 60)
    logger.info("测试板块和行业信息存储")
    logger.info("=" * 60)
    
    # 测试股票列表（不同板块和行业）
    test_stocks = [
        'AAPL',   # Technology / Consumer Electronics
        'JPM',    # Financial Services / Banks
        'XOM',    # Energy / Oil & Gas
        'JNJ',    # Healthcare / Drug Manufacturers
        'WMT'     # Consumer Defensive / Discount Stores
    ]
    
    collector = USStockCollector()
    storage = USStockStorage()
    data_source = USStockDataSource()
    
    for symbol in test_stocks:
        logger.info(f"\n处理股票: {symbol}")
        logger.info("-" * 60)
        
        # 1. 获取股票基本信息
        stock_info = data_source.get_stock_info(symbol)
        if not stock_info:
            logger.warning(f"无法获取 {symbol} 的基本信息")
            continue
        
        logger.info(f"  名称: {stock_info.get('name_en')}")
        logger.info(f"  板块: {stock_info.get('sector')} (代码: {stock_info.get('sector_code')})")
        logger.info(f"  行业: {stock_info.get('industry')} (代码: {stock_info.get('industry_code')})")
        
        # 2. 保存股票信息
        if storage.save_stock_info(stock_info):
            logger.info(f"  [OK] 股票信息已保存")
            
            # 3. 保存板块映射
            if stock_info.get('sector_code'):
                if storage.save_sector_stock_map(
                    symbol=symbol,
                    sector_code=stock_info['sector_code'],
                    sector_name=stock_info.get('sector')
                ):
                    logger.info(f"  [OK] 板块映射已保存: {symbol} -> {stock_info['sector_code']}")
            
            # 4. 保存行业映射
            industry_code = stock_info.get('industry_code')
            if not industry_code and stock_info.get('industry'):
                # 如果没有industry_code，创建或查找
                industry_code = storage.create_or_get_industry(
                    industry_name=stock_info['industry'],
                    sector_code=stock_info.get('sector_code')
                )
                if industry_code:
                    stock_info['industry_code'] = industry_code
                    storage.update_stock_industry_code(symbol, industry_code)
            
            if industry_code:
                if storage.save_industry_stock_map(
                    symbol=symbol,
                    industry_code=industry_code,
                    industry_name=stock_info.get('industry')
                ):
                    logger.info(f"  [OK] 行业映射已保存: {symbol} -> {industry_code}")
        
        # 5. 验证存储结果
        sectors = storage.get_stock_sectors(symbol)
        industries = storage.get_stock_industries(symbol)
        
        logger.info(f"\n  验证结果:")
        logger.info(f"    板块数量: {len(sectors)}")
        for s in sectors:
            logger.info(f"      - {s['sector_code']}: {s['sector_name_en']}")
        
        logger.info(f"    行业数量: {len(industries)}")
        for i in industries:
            logger.info(f"      - {i['industry_code']}: {i['industry_name_en']}")
    
    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)


def verify_database_content():
    """验证数据库中的板块和行业数据"""
    logger.info("\n" + "=" * 60)
    logger.info("验证数据库内容")
    logger.info("=" * 60)
    
    storage = USStockStorage()
    
    # 查看板块
    logger.info("\n1. 板块数据:")
    sectors = storage.db.execute_query("SELECT * FROM us_sectors ORDER BY sector_code")
    logger.info(f"  共 {len(sectors)} 个板块")
    for s in sectors:
        logger.info(f"    {s['sector_code']}: {s['sector_name_en']}")
    
    # 查看行业
    logger.info("\n2. 行业数据:")
    industries = storage.db.execute_query("SELECT * FROM us_industries ORDER BY sector_code, industry_code LIMIT 20")
    logger.info(f"  共显示前 {len(industries)} 个行业（总共可能有更多）")
    for i in industries:
        logger.info(f"    {i['industry_code']}: {i['industry_name_en']} (板块: {i.get('sector_code', 'N/A')})")
    
    # 查看股票信息
    logger.info("\n3. 股票基本信息（包含板块和行业）:")
    stocks = storage.db.execute_query("""
        SELECT symbol, name_en, sector_code, industry_code, exchange
        FROM us_stock_info
        ORDER BY symbol
        LIMIT 10
    """)
    logger.info(f"  共显示前 {len(stocks)} 只股票")
    for s in stocks:
        logger.info(f"    {s['symbol']}: {s['name_en']}")
        logger.info(f"      板块: {s.get('sector_code', 'N/A')}, 行业: {s.get('industry_code', 'N/A')}")
    
    # 查看板块映射
    logger.info("\n4. 板块股票映射:")
    sector_maps = storage.db.execute_query("""
        SELECT symbol, sector_code, COUNT(*) as cnt
        FROM us_sector_stock_map
        GROUP BY symbol, sector_code
        LIMIT 10
    """)
    for m in sector_maps:
        logger.info(f"    {m['symbol']} -> {m['sector_code']}")
    
    # 查看行业映射
    logger.info("\n5. 行业股票映射:")
    industry_maps = storage.db.execute_query("""
        SELECT symbol, industry_code, COUNT(*) as cnt
        FROM us_industry_stock_map
        GROUP BY symbol, industry_code
        LIMIT 10
    """)
    for m in industry_maps:
        logger.info(f"    {m['symbol']} -> {m['industry_code']}")


if __name__ == '__main__':
    try:
        # 测试板块和行业映射
        test_sector_industry_mapping()
        
        # 验证数据库内容
        verify_database_content()
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
