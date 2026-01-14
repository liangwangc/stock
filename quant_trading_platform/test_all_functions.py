"""
全功能测试脚本
测试平台所有核心功能
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import get_logger

logger = get_logger(__name__)

def test_data_source():
    """测试数据源功能"""
    logger.info("\n" + "="*60)
    logger.info("测试1: 数据源功能")
    logger.info("="*60)
    
    try:
        from data_source import AkshareDataSource
        
        data_source = AkshareDataSource()
        logger.info("[OK] 数据源初始化成功")
        
        # 测试获取股票数据
        test_symbol = "000001"
        logger.info(f"正在获取 {test_symbol} 的数据...")
        data = data_source.get_stock_data(test_symbol, "20240101", "20241231")
        
        if not data.empty:
            logger.info(f"[OK] 数据获取成功，共 {len(data)} 条记录")
            logger.info(f"   日期范围: {data.index[0]} 至 {data.index[-1]}")
            logger.info(f"   列: {', '.join(data.columns)}")
            return True
        else:
            logger.error("[X] 数据获取失败，返回空数据")
            return False
            
    except Exception as e:
        logger.error(f"[X] 数据源测试失败: {str(e)}")
        return False

def test_indicators():
    """测试技术指标功能"""
    logger.info("\n" + "="*60)
    logger.info("测试2: 技术指标功能")
    logger.info("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        from indicators import SMA, EMA, MACD, RSI, BollingerBands
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        test_data = pd.Series(prices, index=dates)
        
        # 测试SMA
        sma = SMA(test_data, 20)
        logger.info(f"[OK] SMA计算成功，最后值: {sma.iloc[-1]:.2f}")
        
        # 测试EMA
        ema = EMA(test_data, 20)
        logger.info(f"[OK] EMA计算成功，最后值: {ema.iloc[-1]:.2f}")
        
        # 测试MACD
        macd_data = MACD(test_data)
        logger.info(f"[OK] MACD计算成功")
        logger.info(f"   MACD值: {macd_data['macd'].iloc[-1]:.2f}")
        logger.info(f"   信号线: {macd_data['signal'].iloc[-1]:.2f}")
        
        # 测试RSI
        rsi = RSI(test_data)
        logger.info(f"[OK] RSI计算成功，最后值: {rsi.iloc[-1]:.2f}")
        
        # 测试布林带
        bb = BollingerBands(test_data)
        logger.info(f"[OK] 布林带计算成功")
        logger.info(f"   上轨: {bb['upper'].iloc[-1]:.2f}")
        logger.info(f"   中轨: {bb['middle'].iloc[-1]:.2f}")
        logger.info(f"   下轨: {bb['lower'].iloc[-1]:.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"[X] 技术指标测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_strategies():
    """测试策略功能"""
    logger.info("\n" + "="*60)
    logger.info("测试3: 策略功能")
    logger.info("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        from strategies import MovingAverageStrategy, MACDStrategy
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        base_price = 100
        prices = base_price + np.cumsum(np.random.randn(100) * 2)
        
        test_data = pd.DataFrame({
            'open': prices * (1 + np.random.randn(100) * 0.01),
            'high': prices * (1 + abs(np.random.randn(100)) * 0.02),
            'low': prices * (1 - abs(np.random.randn(100)) * 0.02),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 100)
        }, index=dates)
        
        # 测试移动平均策略
        ma_strategy = MovingAverageStrategy(short_period=5, long_period=20)
        ma_signals = ma_strategy.generate_signals(test_data)
        signal_count = (ma_signals['signal'] != 0).sum()
        logger.info(f"[OK] 移动平均策略测试成功")
        logger.info(f"   生成信号数量: {signal_count}")
        
        # 测试MACD策略
        macd_strategy = MACDStrategy()
        macd_signals = macd_strategy.generate_signals(test_data)
        signal_count = (macd_signals['signal'] != 0).sum()
        logger.info(f"[OK] MACD策略测试成功")
        logger.info(f"   生成信号数量: {signal_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"[X] 策略测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_backtest():
    """测试回测功能"""
    logger.info("\n" + "="*60)
    logger.info("测试4: 回测功能")
    logger.info("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        from backtest import BacktestEngine
        from strategies import MACDStrategy
        
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        base_price = 100
        prices = base_price + np.cumsum(np.random.randn(100) * 2)
        
        test_data = pd.DataFrame({
            'open': prices * (1 + np.random.randn(100) * 0.01),
            'high': prices * (1 + abs(np.random.randn(100)) * 0.02),
            'low': prices * (1 - abs(np.random.randn(100)) * 0.02),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 100)
        }, index=dates)
        
        # 初始化回测引擎
        engine = BacktestEngine(initial_cash=100000)
        strategy = MACDStrategy()
        
        # 运行回测
        results = engine.run(test_data, strategy)
        
        logger.info(f"[OK] 回测运行成功")
        logger.info(f"   回测天数: {len(results)}")
        logger.info(f"   最终价值: {results['total_value'].iloc[-1]:.2f}元")
        
        # 测试性能指标
        metrics = engine.get_performance_metrics(results)
        logger.info(f"[OK] 性能指标计算成功")
        for key, value in metrics.items():
            logger.info(f"   {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"[X] 回测测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_simulated_trading():
    """测试模拟交易功能"""
    logger.info("\n" + "="*60)
    logger.info("测试5: 模拟交易功能")
    logger.info("="*60)
    
    try:
        from trading.simulated_trader import SimulatedTrader
        from data_source import AkshareDataSource
        
        data_source = AkshareDataSource()
        trader = SimulatedTrader(
            initial_cash=100000,
            commission=0.0003,
            slippage=0.001,
            data_source=data_source
        )
        
        logger.info("[OK] 模拟交易接口初始化成功")
        
        # 测试账户查询
        balance = trader.get_balance()
        assert balance['cash'] == 100000
        logger.info("[OK] 账户查询功能正常")
        
        return True
        
    except Exception as e:
        logger.error(f"[X] 模拟交易测试失败: {str(e)}")
        return False

def main():
    """运行所有测试"""
    logger.info("="*60)
    logger.info("量化交易平台 - 全功能测试")
    logger.info("="*60)
    
    results = []
    
    # 运行各项测试
    results.append(("数据源功能", test_data_source()))
    results.append(("技术指标功能", test_indicators()))
    results.append(("策略功能", test_strategies()))
    results.append(("回测功能", test_backtest()))
    results.append(("模拟交易功能", test_simulated_trading()))
    
    # 输出测试结果
    logger.info("\n" + "="*60)
    logger.info("测试结果汇总")
    logger.info("="*60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "[OK]" if result else "[X]"
        logger.info(f"{status} {name}: {'通过' if result else '失败'}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info("="*60)
    logger.info(f"总计: {len(results)} 项测试")
    logger.info(f"通过: {passed} 项")
    logger.info(f"失败: {failed} 项")
    logger.info("="*60)
    
    if failed == 0:
        logger.info("\n[OK] 所有功能测试通过！平台运行正常。")
        return True
    else:
        logger.error(f"\n[X] 有 {failed} 项测试失败，请检查上述错误信息。")
        return False

if __name__ == "__main__":
    main()

