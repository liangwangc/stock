"""
测试A股字段计算和获取
测试已实现字段的计算方式和获取数据是否有问题
"""
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.stock_history_collector import StockHistoryCollector
from utils.stock_history_storage import StockHistoryStorage
from utils.logger import get_logger

logger = get_logger(__name__)


def test_technical_indicators(data, days_data):
    """测试技术指标计算"""
    logger.info("\n" + "-" * 60)
    logger.info("技术指标计算测试:")
    logger.info("-" * 60)
    
    errors = []
    
    # 测试MA计算
    if not days_data.empty and len(days_data) >= 60:
        closes = days_data['close']
        
        # MA5
        expected_ma5 = float(closes.tail(5).mean())
        actual_ma5 = data.get('ma5')
        if actual_ma5 is not None:
            diff = abs(actual_ma5 - expected_ma5)
            if diff > 0.01:
                errors.append(f"MA5计算错误: 期望={expected_ma5:.4f}, 实际={actual_ma5:.4f}, 差异={diff:.4f}")
                logger.error(f"  ❌ MA5计算错误: 期望={expected_ma5:.4f}, 实际={actual_ma5:.4f}")
            else:
                logger.info(f"  ✅ MA5: {actual_ma5:.4f}")
        else:
            logger.warning(f"  ⚠️  MA5: None (数据不足或计算失败)")
        
        # MA10
        expected_ma10 = float(closes.tail(10).mean())
        actual_ma10 = data.get('ma10')
        if actual_ma10 is not None:
            diff = abs(actual_ma10 - expected_ma10)
            if diff > 0.01:
                errors.append(f"MA10计算错误: 期望={expected_ma10:.4f}, 实际={actual_ma10:.4f}, 差异={diff:.4f}")
                logger.error(f"  ❌ MA10计算错误: 期望={expected_ma10:.4f}, 实际={actual_ma10:.4f}")
            else:
                logger.info(f"  ✅ MA10: {actual_ma10:.4f}")
        else:
            logger.warning(f"  ⚠️  MA10: None (数据不足或计算失败)")
        
        # MA20
        expected_ma20 = float(closes.tail(20).mean())
        actual_ma20 = data.get('ma20')
        if actual_ma20 is not None:
            diff = abs(actual_ma20 - expected_ma20)
            if diff > 0.01:
                errors.append(f"MA20计算错误: 期望={expected_ma20:.4f}, 实际={actual_ma20:.4f}, 差异={diff:.4f}")
                logger.error(f"  ❌ MA20计算错误: 期望={expected_ma20:.4f}, 实际={actual_ma20:.4f}")
            else:
                logger.info(f"  ✅ MA20: {actual_ma20:.4f}")
        else:
            logger.warning(f"  ⚠️  MA20: None (数据不足或计算失败)")
        
        # MA60
        expected_ma60 = float(closes.tail(60).mean())
        actual_ma60 = data.get('ma60')
        if actual_ma60 is not None:
            diff = abs(actual_ma60 - expected_ma60)
            if diff > 0.01:
                errors.append(f"MA60计算错误: 期望={expected_ma60:.4f}, 实际={actual_ma60:.4f}, 差异={diff:.4f}")
                logger.error(f"  ❌ MA60计算错误: 期望={expected_ma60:.4f}, 实际={actual_ma60:.4f}")
            else:
                logger.info(f"  ✅ MA60: {actual_ma60:.4f}")
        else:
            logger.warning(f"  ⚠️  MA60: None (数据不足或计算失败)")
        
        # RSI
        actual_rsi = data.get('rsi')
        if actual_rsi is not None:
            if 0 <= actual_rsi <= 100:
                logger.info(f"  ✅ RSI: {actual_rsi:.4f} (范围正确)")
            else:
                errors.append(f"RSI值超出范围: {actual_rsi:.4f} (应该在0-100之间)")
                logger.error(f"  ❌ RSI值超出范围: {actual_rsi:.4f}")
        else:
            logger.warning(f"  ⚠️  RSI: None (数据不足或计算失败)")
        
        # MACD
        actual_macd = data.get('macd')
        actual_macd_signal = data.get('macd_signal')
        actual_macd_hist = data.get('macd_hist')
        if actual_macd is not None:
            logger.info(f"  ✅ MACD: {actual_macd:.4f}")
        else:
            logger.warning(f"  ⚠️  MACD: None (数据不足或计算失败)")
        if actual_macd_signal is not None:
            logger.info(f"  ✅ MACD Signal: {actual_macd_signal:.4f}")
        else:
            logger.warning(f"  ⚠️  MACD Signal: None (数据不足或计算失败)")
        if actual_macd_hist is not None:
            logger.info(f"  ✅ MACD Hist: {actual_macd_hist:.4f}")
        else:
            logger.warning(f"  ⚠️  MACD Hist: None (数据不足或计算失败)")
        
        # X2
        actual_x2 = data.get('x2')
        if actual_x2 is not None:
            if 0 <= actual_x2 <= 100:
                logger.info(f"  ✅ X2: {actual_x2:.4f} (范围正确)")
            else:
                errors.append(f"X2值超出范围: {actual_x2:.4f} (应该在0-100之间)")
                logger.error(f"  ❌ X2值超出范围: {actual_x2:.4f}")
        else:
            logger.warning(f"  ⚠️  X2: None (数据不足或计算失败)")
    else:
        logger.warning("  ⚠️  数据不足，无法测试技术指标（需要至少60日数据）")
    
    return errors


def test_null_fields(data):
    """测试应该为None的字段（历史数据不可用）"""
    logger.info("\n" + "-" * 60)
    logger.info("历史数据不可用字段测试 (应该为None):")
    logger.info("-" * 60)
    
    # 这些字段在历史数据中应该为None
    null_fields = [
        'outer_volume',
        'inner_volume',
        'bid_levels',
        'ask_levels',
        'bid_total_volume',
        'ask_total_volume',
        'bid_ask_ratio',
        'main_net_inflow',
        'super_large_inflow',
        'large_inflow',
        'medium_inflow',
        'small_inflow',
    ]
    
    errors = []
    for field in null_fields:
        value = data.get(field)
        if value is None:
            logger.info(f"  ✅ {field}: None (正确)")
        else:
            errors.append(f"{field}应该为None，但实际值为: {value}")
            logger.warning(f"  ⚠️  {field}: {value} (历史数据应该为None，但获取到了值，可能是实时数据)")
    
    return errors


def test_margin_trading_fields(data):
    """测试融资融券字段"""
    logger.info("\n" + "-" * 60)
    logger.info("融资融券字段测试:")
    logger.info("-" * 60)
    
    fields = ['margin_balance', 'short_balance', 'margin_ratio']
    for field in fields:
        value = data.get(field)
        if value is not None:
            logger.info(f"  ✅ {field}: {value}")
        else:
            logger.info(f"  ⚠️  {field}: None (可能该股票不支持融资融券或数据不可用)")


def test_field_collection():
    """测试字段收集"""
    collector = StockHistoryCollector()
    storage = StockHistoryStorage()
    
    # 测试股票代码
    test_symbol = '000001'  # 平安银行
    test_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # 30天前的日期
    
    logger.info("=" * 60)
    logger.info(f"测试股票 {test_symbol} 在 {test_date} 的数据获取")
    logger.info("=" * 60)
    
    try:
        # 获取数据
        logger.info(f"\n步骤1: 调用 collect_stock_daily_data 获取数据...")
        data = collector.collect_stock_daily_data(test_symbol, test_date)
        
        if data is None:
            logger.error("❌ 数据获取失败，返回 None")
            return False
        
        logger.info("✅ 数据获取成功")
        
        # 获取多日数据用于验证技术指标计算
        logger.info(f"\n步骤2: 获取多日数据用于验证技术指标计算...")
        date_obj = datetime.strptime(test_date, '%Y-%m-%d')
        start_date = (date_obj - timedelta(days=70)).strftime('%Y-%m-%d')
        end_date = (date_obj + timedelta(days=10)).strftime('%Y-%m-%d')
        days_data = collector.data_source.get_stock_data(test_symbol, start_date=start_date, end_date=end_date)
        
        all_errors = []
        
        # 测试技术指标计算
        errors = test_technical_indicators(data, days_data)
        all_errors.extend(errors)
        
        # 测试应该为None的字段
        errors = test_null_fields(data)
        all_errors.extend(errors)
        
        # 测试融资融券字段
        test_margin_trading_fields(data)
        
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
                all_errors.append("数据保存失败")
        except Exception as e:
            logger.error(f"❌ 数据保存异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            all_errors.append(f"数据保存异常: {str(e)}")
        
        # 总结
        logger.info("\n" + "=" * 60)
        logger.info("测试总结:")
        logger.info("=" * 60)
        if all_errors:
            logger.error(f"❌ 发现 {len(all_errors)} 个错误:")
            for error in all_errors:
                logger.error(f"  - {error}")
            return False
        else:
            logger.info("✅ 所有测试通过，未发现错误")
            return True
            
    except Exception as e:
        logger.error(f"❌ 测试过程出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("A股字段计算和获取测试")
    print("=" * 60)
    print()
    
    success = test_field_collection()
    
    print()
    print("=" * 60)
    if success:
        print("✅ 测试完成：所有测试通过")
    else:
        print("❌ 测试完成：发现问题，请检查日志")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
