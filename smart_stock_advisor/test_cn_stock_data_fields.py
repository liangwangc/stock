"""
测试A股数据获取 - 逐个字段测试
测试各个字段是否能正确获取数据
"""
import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage
from utils.logger import get_logger

logger = get_logger(__name__)

def test_single_field_collection():
    """测试单只股票的数据获取，检查各个字段"""
    
    collector = StockHistoryCollector()
    storage = StockHistoryStorage()
    
    # 测试股票代码
    test_symbol = '000001'  # 平安银行
    test_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # 30天前的日期
    
    logger.info("=" * 60)
    logger.info(f"开始测试股票 {test_symbol} 在 {test_date} 的数据获取")
    logger.info("=" * 60)
    
    try:
        # 获取数据
        logger.info(f"\n步骤1: 调用 collect_stock_daily_data 获取数据...")
        data = collector.collect_stock_daily_data(test_symbol, test_date)
        
        if data is None:
            logger.error("❌ 数据获取失败，返回 None")
            return False
        
        logger.info("✅ 数据获取成功")
        logger.info(f"\n步骤2: 检查数据字段...")
        
        # 定义所有期望的字段
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
            'pre_close': '昨收价',
            'change_amount': '涨跌额',
            'change_pct': '涨跌幅',
            
            # 成交数据
            'volume': '成交量',
            'amount': '成交额',
            'turnover_rate': '换手率',
            'volume_ratio': '量比',
            
            # 盘口数据
            'outer_volume': '外盘',
            'inner_volume': '内盘',
            'bid_ask_ratio': '委比',
        }
        
        optional_fields = {
            # 五档买卖盘（JSON格式）
            'bid_levels': '五档买盘',
            'ask_levels': '五档卖盘',
            'bid_total_volume': '买盘总手数',
            'ask_total_volume': '卖盘总手数',
            
            # 成本分布（JSON格式）
            'cost_distribution': '成本分布',
            'cost_distribution_history': '历史成本分布',
            'cost_distribution_intraday': '当日成本分布',
            
            # 市值和估值
            'total_market_cap': '总市值',
            'float_market_cap': '流通市值',
            'pe_ratio': '市盈率',
            'pb_ratio': '市净率',
            
            # 涨跌停信息
            'limit_up': '涨停价',
            'limit_down': '跌停价',
            'limit_pct': '涨跌停幅度',
            'is_limit_up': '是否涨停',
            'is_limit_down': '是否跌停',
            
            # 振幅和波动
            'amplitude': '振幅',
            'price_range': '价格区间',
            
            # 技术指标
            'ma5': 'MA5均线',
            'ma10': 'MA10均线',
            'ma20': 'MA20均线',
            'ma60': 'MA60均线',
            'rsi': 'RSI指标',
            'macd': 'MACD',
            'macd_signal': 'MACD Signal',
            'macd_hist': 'MACD Histogram',
            
            # 资金流向
            'main_net_inflow': '主力净流入',
            'super_large_inflow': '超大单净流入',
            'large_inflow': '大单净流入',
            'medium_inflow': '中单净流入',
            'small_inflow': '小单净流入',
            
            # 融资融券
            'margin_balance': '融资余额',
            'short_balance': '融券余额',
            'margin_ratio': '融资融券余额占比',
            
            # 其他
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
                logger.info(f"  {status} {field:30s} ({desc:15s}): {value}")
                if value is None:
                    missing_optional.append(field)
            else:
                logger.warning(f"  ⚠️  {field:30s} ({desc:15s}): 字段缺失（可选）")
        
        # 测试数据保存
        logger.info("\n" + "-" * 60)
        logger.info("步骤3: 测试数据保存到数据库...")
        logger.info("-" * 60)
        try:
            success = storage.save_stock_daily_data(test_symbol, test_date, data)
            if success:
                logger.info("✅ 数据保存成功")
            else:
                logger.error("❌ 数据保存失败")
                return False
        except Exception as e:
            logger.error(f"❌ 数据保存异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
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
    print("A股数据获取字段测试")
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
