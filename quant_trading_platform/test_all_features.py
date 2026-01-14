"""
完整功能测试脚本
测试平台的所有核心功能
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger
from data_source import AkshareDataSource
from strategies import MovingAverageStrategy, MACDStrategy
from backtest import BacktestEngine
from config import DEFAULT_STOCKS, DEFAULT_CASH, DEFAULT_COMMISSION, DEFAULT_SLIPPAGE, START_DATE, END_DATE
from trading.simulated_trader import SimulatedTrader

logger = get_logger(__name__)

def test_data_source():
    """测试数据源功能"""
    logger.info("=" * 60)
    logger.info("测试1: 数据源功能")
    logger.info("=" * 60)
    
    try:
        data_source = AkshareDataSource()
        symbol = DEFAULT_STOCKS[0]
        
        logger.info(f"正在获取 {symbol} 的数据...")
        data = data_source.get_stock_data(symbol, START_DATE, END_DATE)
        
        if data.empty:
            logger.error(f"[FAIL] 数据获取失败")
            return False
        
        logger.info(f"[PASS] 数据获取成功，共 {len(data)} 条记录")
        logger.info(f"   数据列: {list(data.columns)}")
        logger.info(f"   日期范围: {data.index[0]} 至 {data.index[-1]}")
        logger.info(f"   最新收盘价: {data['close'].iloc[-1]:.2f}元")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据源测试失败: {str(e)}")
        return False

def test_strategies():
    """测试策略功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 策略功能")
    logger.info("=" * 60)
    
    try:
        # 获取测试数据
        data_source = AkshareDataSource()
        symbol = DEFAULT_STOCKS[0]
        data = data_source.get_stock_data(symbol, START_DATE, END_DATE)
        
        if data.empty:
            logger.error("❌ 无法获取测试数据")
            return False
        
        # 测试移动平均策略
        logger.info("\n测试移动平均策略...")
        ma_strategy = MovingAverageStrategy(short_period=5, long_period=20)
        signals_ma = ma_strategy.generate_signals(data)
        logger.info(f"[PASS] 移动平均策略: 生成 {len(signals_ma[signals_ma['signal'] != 0])} 个交易信号")
        
        # 测试MACD策略
        logger.info("\n测试MACD策略...")
        macd_strategy = MACDStrategy()
        signals_macd = macd_strategy.generate_signals(data)
        logger.info(f"[PASS] MACD策略: 生成 {len(signals_macd[signals_macd['signal'] != 0])} 个交易信号")
        
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] 策略测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_backtest():
    """测试回测功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: 回测功能")
    logger.info("=" * 60)
    
    try:
        # 获取测试数据
        data_source = AkshareDataSource()
        symbol = DEFAULT_STOCKS[0]
        data = data_source.get_stock_data(symbol, START_DATE, END_DATE)
        
        if data.empty:
            logger.error("❌ 无法获取测试数据")
            return False
        
        # 使用MACD策略回测
        strategy = MACDStrategy()
        backtest_engine = BacktestEngine(
            initial_cash=DEFAULT_CASH,
            commission=DEFAULT_COMMISSION,
            slippage=DEFAULT_SLIPPAGE
        )
        
        logger.info("正在运行回测...")
        results = backtest_engine.run(data, strategy)
        
        if results.empty:
            logger.error("❌ 回测结果为空")
            return False
        
        # 计算性能指标
        metrics = backtest_engine.get_performance_metrics(results)
        
        logger.info("[PASS] 回测完成")
        logger.info(f"   总收益率: {metrics.get('总收益率', 'N/A')}")
        logger.info(f"   年化收益率: {metrics.get('年化收益率', 'N/A')}")
        logger.info(f"   最大回撤: {metrics.get('最大回撤', 'N/A')}")
        logger.info(f"   交易次数: {metrics.get('交易次数', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] 回测测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_simulated_trading():
    """测试模拟交易功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: 模拟交易功能")
    logger.info("=" * 60)
    
    try:
        data_source = AkshareDataSource()
        
        # 创建模拟交易接口
        trader = SimulatedTrader(
            initial_cash=100000,
            commission=DEFAULT_COMMISSION,
            slippage=DEFAULT_SLIPPAGE,
            data_source=data_source
        )
        
        symbol = DEFAULT_STOCKS[0]
        
        # 测试查询余额
        logger.info("\n测试查询账户余额...")
        balance = trader.get_balance()
        logger.info(f"[PASS] 初始余额: {balance['cash']:.2f}元")
        
        # 测试买入
        logger.info(f"\n测试买入 {symbol}...")
        buy_result = trader.buy(symbol, amount=10000)
        if buy_result.get('success'):
            logger.info(f"[PASS] 买入成功: {buy_result['shares']}股 @ {buy_result['price']:.2f}元")
        else:
            logger.warning(f"[WARN] 买入失败: {buy_result.get('message')}")
        
        # 测试查询持仓
        logger.info(f"\n测试查询持仓...")
        position = trader.get_position(symbol)
        logger.info(f"[PASS] 持仓: {position['shares']}股, 成本价: {position['cost']:.2f}元")
        
        # 测试卖出
        if position['shares'] > 0:
            logger.info(f"\n测试卖出 {symbol}...")
            sell_result = trader.sell(symbol, shares=100)  # 卖出100股
            if sell_result.get('success'):
                logger.info(f"[PASS] 卖出成功: {sell_result['shares']}股 @ {sell_result['price']:.2f}元")
            else:
                logger.warning(f"[WARN] 卖出失败: {sell_result.get('message')}")
        
        # 查询最终余额
        final_balance = trader.get_balance()
        logger.info(f"\n[PASS] 最终余额: 现金 {final_balance['cash']:.2f}元, 总资产 {final_balance['total_value']:.2f}元")
        
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] 模拟交易测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_indicators():
    """测试技术指标"""
    logger.info("\n" + "=" * 60)
    logger.info("测试5: 技术指标计算")
    logger.info("=" * 60)
    
    try:
        from indicators import SMA, EMA, MACD, RSI, BollingerBands
        import pandas as pd
        import numpy as np
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        test_data = pd.Series(prices, index=dates)
        
        # 测试SMA
        logger.info("\n测试SMA（简单移动平均）...")
        sma = SMA(test_data, 20)
        logger.info(f"[PASS] SMA计算成功，最新值: {sma.iloc[-1]:.2f}")
        
        # 测试EMA
        logger.info("\n测试EMA（指数移动平均）...")
        ema = EMA(test_data, 20)
        logger.info(f"[PASS] EMA计算成功，最新值: {ema.iloc[-1]:.2f}")
        
        # 测试MACD
        logger.info("\n测试MACD...")
        macd = MACD(test_data)
        logger.info(f"[PASS] MACD计算成功")
        logger.info(f"   MACD值: {macd['macd'].iloc[-1]:.4f}")
        logger.info(f"   信号线: {macd['signal'].iloc[-1]:.4f}")
        
        # 测试RSI
        logger.info("\n测试RSI（相对强弱指标）...")
        rsi = RSI(test_data)
        logger.info(f"[PASS] RSI计算成功，最新值: {rsi.iloc[-1]:.2f}")
        
        # 测试布林带
        logger.info("\n测试布林带...")
        bb = BollingerBands(test_data)
        logger.info(f"[PASS] 布林带计算成功")
        logger.info(f"   上轨: {bb['upper'].iloc[-1]:.2f}")
        logger.info(f"   中轨: {bb['middle'].iloc[-1]:.2f}")
        logger.info(f"   下轨: {bb['lower'].iloc[-1]:.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] 技术指标测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主测试函数"""
    logger.info("\n" + "=" * 60)
    logger.info("量化交易平台 - 完整功能测试")
    logger.info("=" * 60)
    
    results = []
    
    # 测试1: 数据源
    results.append(("数据源功能", test_data_source()))
    
    # 测试2: 策略
    results.append(("策略功能", test_strategies()))
    
    # 测试3: 回测
    results.append(("回测功能", test_backtest()))
    
    # 测试4: 模拟交易
    results.append(("模拟交易功能", test_simulated_trading()))
    
    # 测试5: 技术指标
    results.append(("技术指标", test_indicators()))
    
    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "[PASS] 通过" if result else "[FAIL] 失败"
        logger.info(f"{name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info("-" * 60)
    logger.info(f"总计: {len(results)} 项测试")
    logger.info(f"通过: {passed} 项")
    logger.info(f"失败: {failed} 项")
    logger.info("=" * 60)
    
    if failed == 0:
        logger.info("\n[SUCCESS] 所有测试通过！平台功能正常")
    else:
        logger.warning(f"\n[WARNING] 有 {failed} 项测试失败，请检查上述错误信息")

if __name__ == "__main__":
    main()

