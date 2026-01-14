"""
模拟交易功能测试脚本
测试模拟交易接口的各项功能
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading.simulated_trader import SimulatedTrader
from data_source import AkshareDataSource
from utils.logger import get_logger

logger = get_logger(__name__)

def test_simulated_trading():
    """测试模拟交易功能"""
    logger.info("=" * 60)
    logger.info("模拟交易功能测试")
    logger.info("=" * 60)
    
    try:
        # 初始化数据源
        logger.info("\n1. 初始化数据源...")
        data_source = AkshareDataSource()
        logger.info("[OK] 数据源初始化成功")
        
        # 初始化模拟交易接口
        logger.info("\n2. 初始化模拟交易接口...")
        trader = SimulatedTrader(
            initial_cash=100000,  # 初始资金10万
            commission=0.0003,    # 手续费万三
            slippage=0.001,       # 滑点0.1%
            data_source=data_source
        )
        logger.info("[OK] 模拟交易接口初始化成功")
        
        # 测试查询账户余额
        logger.info("\n3. 测试查询账户余额...")
        balance = trader.get_balance()
        logger.info(f"[OK] 账户余额查询成功")
        logger.info(f"   可用资金: {balance['cash']:.2f}元")
        logger.info(f"   总资产: {balance['total_value']:.2f}元")
        assert balance['cash'] == 100000, "初始资金不正确"
        assert balance['total_value'] == 100000, "初始总资产不正确"
        
        # 测试获取价格
        logger.info("\n4. 测试获取股票价格...")
        test_symbol = "000001"  # 平安银行
        price = trader.get_current_price(test_symbol)
        if price:
            logger.info(f"[OK] 获取价格成功: {test_symbol} = {price:.2f}元")
        else:
            logger.warning("[WARN] 无法获取价格（可能需要网络连接）")
            # 使用模拟价格继续测试
            price = 10.0
            logger.info(f"[INFO] 使用模拟价格: {price:.2f}元继续测试")
        
        # 测试买入股票
        logger.info("\n5. 测试买入股票...")
        buy_amount = 50000  # 买入5万元
        result = trader.buy(test_symbol, buy_amount, price=price)
        if result.get('success'):
            logger.info(f"[OK] 买入成功")
            logger.info(f"   股票: {result['symbol']}")
            logger.info(f"   数量: {result['shares']}股")
            logger.info(f"   价格: {result['price']:.2f}元")
            logger.info(f"   金额: {result['amount']:.2f}元")
        else:
            logger.error(f"[X] 买入失败: {result.get('message')}")
            return False
        
        # 测试查询持仓
        logger.info("\n6. 测试查询持仓...")
        position = trader.get_position(test_symbol)
        logger.info(f"[OK] 持仓查询成功")
        logger.info(f"   股票: {position['symbol']}")
        logger.info(f"   持仓数量: {position['shares']}股")
        logger.info(f"   成本价: {position['cost']:.2f}元")
        assert position['shares'] > 0, "持仓数量应该大于0"
        
        # 测试查询账户余额（买入后）
        logger.info("\n7. 测试查询账户余额（买入后）...")
        balance_after_buy = trader.get_balance()
        logger.info(f"[OK] 账户余额查询成功")
        logger.info(f"   可用资金: {balance_after_buy['cash']:.2f}元")
        logger.info(f"   持仓市值: {balance_after_buy['positions_value']:.2f}元")
        logger.info(f"   总资产: {balance_after_buy['total_value']:.2f}元")
        assert balance_after_buy['cash'] < balance['cash'], "买入后可用资金应该减少"
        
        # 测试卖出股票
        logger.info("\n8. 测试卖出股票...")
        sell_shares = position['shares']  # 全部卖出
        result = trader.sell(test_symbol, sell_shares, price=price * 1.1)  # 以更高价格卖出
        if result.get('success'):
            logger.info(f"[OK] 卖出成功")
            logger.info(f"   股票: {result['symbol']}")
            logger.info(f"   数量: {result['shares']}股")
            logger.info(f"   价格: {result['price']:.2f}元")
            logger.info(f"   金额: {result['amount']:.2f}元")
        else:
            logger.error(f"[X] 卖出失败: {result.get('message')}")
            return False
        
        # 测试查询持仓（卖出后）
        logger.info("\n9. 测试查询持仓（卖出后）...")
        position_after_sell = trader.get_position(test_symbol)
        logger.info(f"[OK] 持仓查询成功")
        logger.info(f"   持仓数量: {position_after_sell['shares']}股")
        assert position_after_sell['shares'] == 0, "卖出后持仓应该为0"
        
        # 测试查询账户余额（卖出后）
        logger.info("\n10. 测试查询账户余额（卖出后）...")
        balance_final = trader.get_balance()
        logger.info(f"[OK] 账户余额查询成功")
        logger.info(f"   可用资金: {balance_final['cash']:.2f}元")
        logger.info(f"   持仓市值: {balance_final['positions_value']:.2f}元")
        logger.info(f"   总资产: {balance_final['total_value']:.2f}元")
        
        logger.info("\n" + "=" * 60)
        logger.info("[OK] 所有模拟交易功能测试通过！")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"[X] 测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_simulated_trading()

