"""
测试美股数据获取 - 逐个字段测试
测试各个字段是否能正确获取数据
"""
import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.us_stock_collector import USStockCollector
from utils.us_stock_storage import USStockStorage
from utils.logger import get_logger

logger = get_logger(__name__)

def test_single_field_collection():
    """测试单只股票的数据获取，检查各个字段"""
    
    collector = USStockCollector()
    storage = USStockStorage()
    
    # 测试股票代码
    test_symbol = 'AAPL'  # 苹果
    test_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # 30天前的日期
    
    logger.info("=" * 60)
    logger.info(f"开始测试股票 {test_symbol} 在 {test_date} 的数据获取")
    logger.info("=" * 60)
    
    try:
        # 获取数据
        logger.info(f"\n步骤1: 调用 collect_stock_history 获取数据...")
        # 美股收集器使用不同的方法，需要获取一段时间范围的数据
        # 先获取最近60天的数据，然后从中提取目标日期
        result = collector.collect_stock_history(
            symbol=test_symbol,
            period='60d'  # 获取最近60天
        )
        
        if not result.get('success', False):
            logger.error("❌ 数据获取失败")
            logger.error(f"错误信息: {result.get('message', '未知错误')}")
            return False
        
        # 从存储中获取指定日期的数据
        logger.info(f"\n步骤2: 从数据库获取 {test_date} 的数据...")
        data_list = storage.get_stock_history(test_symbol, start_date=test_date, end_date=test_date)
        
        if not data_list or len(data_list) == 0:
            logger.warning(f"⚠️ 未找到 {test_date} 的数据，尝试获取最近的数据...")
            # 如果找不到指定日期，获取最近的数据
            data_list = storage.get_stock_history(test_symbol, limit=1)
            if data_list:
                data = data_list[0]
                logger.info(f"使用最近的数据: {data.get('trade_date')}")
            else:
                logger.error("❌ 未能获取到任何数据")
                return False
        else:
            data = data_list[0]
            logger.info("✅ 数据获取成功")
        
        logger.info(f"\n步骤3: 检查数据字段...")
        
        # 定义所有期望的字段（基于us_stock_history_data表结构）
        required_fields = {
            # 基本信息
            'symbol': '股票代码',
            'name': '股票名称',
            'trade_date': '交易日期',
            'period_type': '周期类型',
            
            # 价格数据
            'open_price': '开盘价',
            'close_price': '收盘价',
            'high_price': '最高价',
            'low_price': '最低价',
            'adj_close_price': '调整后收盘价',
            'pre_close': '昨收价',
            'change_amount': '涨跌额',
            'change_pct': '涨跌幅',
            
            # 成交数据
            'volume': '成交量',
            'amount': '成交额',
        }
        
        optional_fields = {
            # 盘口数据
            'bid_price': '买一价',
            'ask_price': '卖一价',
            'bid_volume': '买一量',
            'ask_volume': '卖一量',
            'bid_levels': '买盘档位',
            'ask_levels': '卖盘档位',
            
            # 市值和估值
            'market_cap': '市值',
            'enterprise_value': '企业价值',
            'pe_ratio': '市盈率',
            'forward_pe': '预期市盈率',
            'pb_ratio': '市净率',
            'ps_ratio': '市销率',
            'ev_ebitda': 'EV/EBITDA',
            'dividend_yield': '股息率',
            
            # 技术指标
            'ma5': 'MA5均线',
            'ma10': 'MA10均线',
            'ma20': 'MA20均线',
            'ma50': 'MA50均线',
            'ma200': 'MA200均线',
            'rsi': 'RSI指标',
            'macd': 'MACD',
            'macd_signal': 'MACD Signal',
            'macd_hist': 'MACD Histogram',
            
            # 资金流向
            'net_inflow': '净流入',
            'institutional_flow': '机构资金流',
            'retail_flow': '散户资金流',
            
            # 期权数据
            'put_call_ratio': '看跌看涨比率',
            'implied_volatility': '隐含波动率',
            
            # 其他数据
            'amplitude': '振幅',
            'price_range': '价格区间',
            'volatility': '波动率',
            'extra_data': '扩展数据',
            'data_source': '数据来源',
            'data_quality_score': '数据质量得分',
            'is_valid': '是否有效',
        }
        
        # 检查必需字段
        logger.info("\n" + "-" * 60)
        logger.info("必需字段检查:")
        logger.info("-" * 60)
        missing_required = []
        for field, desc in required_fields.items():
            if field in data:
                value = data[field]
                status = "✅" if value is not None else "⚠️ (None)"
                logger.info(f"  {status} {field:30s} ({desc:15s}): {value}")
                if value is None:
                    missing_required.append(field)
            else:
                logger.warning(f"  ❌ {field:30s} ({desc:15s}): 字段缺失")
                missing_required.append(field)
        
        # 检查可选字段
        logger.info("\n" + "-" * 60)
        logger.info("可选字段检查:")
        logger.info("-" * 60)
        missing_optional = []
        for field, desc in optional_fields.items():
            if field in data:
                value = data[field]
                status = "✅" if value is not None else "⚠️ (None)"
                # 对于长内容，只显示类型和长度
                if isinstance(value, dict) and len(str(value)) > 100:
                    logger.info(f"  {status} {field:30s} ({desc:15s}): <dict with {len(value)} keys>")
                elif isinstance(value, list) and len(str(value)) > 100:
                    logger.info(f"  {status} {field:30s} ({desc:15s}): <list with {len(value)} items>")
                else:
                    logger.info(f"  {status} {field:30s} ({desc:15s}): {value}")
                if value is None:
                    missing_optional.append(field)
            else:
                logger.warning(f"  ⚠️  {field:30s} ({desc:15s}): 字段缺失（可选）")
        
        # 测试数据保存（如果数据是从API获取的，需要先保存）
        logger.info("\n" + "-" * 60)
        logger.info("步骤4: 验证数据保存功能...")
        logger.info("-" * 60)
        
        # 如果数据是从数据库获取的，说明保存功能正常
        # 这里我们测试一下保存功能是否可用
        try:
            # 尝试获取原始数据并保存（如果还没有保存的话）
            test_result = collector.collect_stock_history(
                symbol=test_symbol,
                period='1d'  # 获取最近1天的数据用于测试保存
            )
            if test_result.get('success', False):
                logger.info("✅ 数据收集和保存功能正常")
            else:
                logger.warning(f"⚠️ 数据收集返回失败: {test_result.get('message', '未知错误')}")
        except Exception as e:
            logger.warning(f"⚠️ 测试保存功能时出错: {str(e)}")
        
        # 总结
        logger.info("\n" + "=" * 60)
        logger.info("测试总结:")
        logger.info("=" * 60)
        logger.info(f"总字段数: {len(required_fields) + len(optional_fields)}")
        logger.info(f"必需字段: {len(required_fields)}")
        logger.info(f"可选字段: {len(optional_fields)}")
        logger.info(f"缺失的必需字段: {len(missing_required)}")
        if missing_required:
            logger.warning(f"  缺失字段列表: {', '.join(missing_required)}")
        logger.info(f"缺失的可选字段: {len(missing_optional)}")
        if missing_optional:
            logger.info(f"  缺失字段列表: {', '.join(missing_optional)} (这些字段可能在某些情况下不可用)")
        
        if missing_required:
            logger.error("\n❌ 测试失败：存在缺失的必需字段")
            return False
        else:
            logger.info("\n✅ 测试通过：所有必需字段都存在")
            return True
            
    except Exception as e:
        logger.error(f"❌ 测试过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("美股数据获取字段测试")
    print("=" * 60)
    print()
    
    success = test_single_field_collection()
    
    print()
    print("=" * 60)
    if success:
        print("✅ 测试完成：所有测试通过")
    else:
        print("❌ 测试完成：发现问题，请检查日志")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
