"""
实时交易主程序
注意：这是基础框架，真实交易需要接入券商API
"""

import time
import schedule
from datetime import datetime
from typing import Optional
from strategies.base_strategy import BaseStrategy
from data_source import AkshareDataSource
from trading.simulated_trader import SimulatedTrader
from trading.base_trader import BaseTrader
from utils.logger import get_logger
from config import DEFAULT_STOCKS, DEFAULT_CASH, DEFAULT_COMMISSION, DEFAULT_SLIPPAGE

logger = get_logger(__name__)

class RealtimeTrader:
    """实时交易管理器"""
    
    def __init__(
        self,
        trader: BaseTrader,
        strategy: BaseStrategy,
        symbol: str,
        check_interval: int = 60  # 检查间隔（秒）
    ):
        """
        初始化实时交易管理器
        
        Args:
            trader: 交易接口
            strategy: 交易策略
            symbol: 交易股票代码
            check_interval: 检查信号的时间间隔（秒）
        """
        self.trader = trader
        self.strategy = strategy
        self.symbol = symbol
        self.check_interval = check_interval
        self.data_source = AkshareDataSource()
        self.historical_data = None
        self.logger = logger
        self.running = False
        
    def load_historical_data(self, days: int = 100):
        """加载历史数据用于计算指标"""
        try:
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            self.logger.info(f"正在加载 {self.symbol} 的历史数据...")
            self.historical_data = self.data_source.get_stock_data(self.symbol, start_date, end_date)
            
            if self.historical_data.empty:
                self.logger.error(f"无法获取 {self.symbol} 的历史数据")
                return False
            
            self.logger.info(f"成功加载 {len(self.historical_data)} 条历史数据")
            return True
            
        except Exception as e:
            self.logger.error(f"加载历史数据失败: {str(e)}")
            return False
    
    def update_data(self):
        """更新最新数据"""
        try:
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=100)).strftime('%Y%m%d')
            
            new_data = self.data_source.get_stock_data(self.symbol, start_date, end_date)
            if not new_data.empty:
                self.historical_data = new_data
                return True
            return False
        except Exception as e:
            self.logger.error(f"更新数据失败: {str(e)}")
            return False
    
    def check_and_trade(self):
        """检查信号并执行交易"""
        try:
            # 更新数据
            if not self.update_data():
                self.logger.warning("数据更新失败，跳过本次检查")
                return
            
            if self.historical_data is None or len(self.historical_data) < 50:
                self.logger.warning("历史数据不足，跳过本次检查")
                return
            
            # 生成交易信号
            signals = self.strategy.generate_signals(self.historical_data)
            
            if signals.empty:
                return
            
            # 获取最新信号
            latest_signal = signals['signal'].iloc[-1]
            latest_date = signals.index[-1]
            
            self.logger.info(f"[{latest_date}] {self.symbol} 信号: {latest_signal}")
            
            # 获取当前持仓
            position = self.trader.get_position(self.symbol)
            balance = self.trader.get_balance()
            
            # 执行交易逻辑
            if latest_signal > 0:  # 买入信号
                if position['shares'] == 0:  # 当前无持仓
                    # 使用可用资金的80%买入
                    available_cash = balance.get('cash', balance.get('available_cash', 0))
                    buy_amount = available_cash * 0.8
                    if buy_amount > 1000:  # 至少1000元才买入
                        result = self.trader.buy(self.symbol, buy_amount)
                        if result.get('success'):
                            self.logger.info(f"✅ 买入成功: {result['shares']}股 @ {result['price']:.2f}元")
                        else:
                            self.logger.warning(f"❌ 买入失败: {result.get('message')}")
            
            elif latest_signal < 0:  # 卖出信号
                if position['shares'] > 0:  # 当前有持仓
                    result = self.trader.sell(self.symbol, position['shares'])
                    if result.get('success'):
                        self.logger.info(f"✅ 卖出成功: {result['shares']}股 @ {result['price']:.2f}元")
                    else:
                        self.logger.warning(f"❌ 卖出失败: {result.get('message')}")
            
            # 打印账户状态
            balance = self.trader.get_balance()
            cash = balance.get('cash', balance.get('available_cash', 0))
            positions_value = balance.get('positions_value', balance.get('market_value', 0))
            total_value = balance.get('total_value', balance.get('total_asset', cash + positions_value))
            self.logger.info(f"账户状态 - 现金: {cash:.2f}元, "
                           f"持仓市值: {positions_value:.2f}元, "
                           f"总资产: {total_value:.2f}元")
            
        except Exception as e:
            self.logger.error(f"检查交易信号时出错: {str(e)}")
    
    def start(self):
        """启动实时交易"""
        self.logger.info("=" * 60)
        self.logger.info(f"启动实时交易 - 股票: {self.symbol}, 策略: {self.strategy.name}")
        self.logger.info("=" * 60)
        
        # 加载历史数据
        if not self.load_historical_data():
            self.logger.error("历史数据加载失败，无法启动交易")
            return
        
        self.running = True
        
        # 立即执行一次检查
        self.check_and_trade()
        
        # 设置定时任务
        schedule.every(self.check_interval).seconds.do(self.check_and_trade)
        
        self.logger.info(f"交易系统已启动，每 {self.check_interval} 秒检查一次信号")
        self.logger.info("按 Ctrl+C 停止交易")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在关闭交易系统...")
            self.stop()
    
    def stop(self):
        """停止实时交易"""
        self.running = False
        self.logger.info("交易系统已停止")


def main_realtime_trading():
    """实时交易主函数（使用模拟交易接口）"""
    logger.info("=" * 60)
    logger.info("实时交易系统（模拟模式）")
    logger.info("⚠️  警告：当前使用模拟交易接口，不涉及真实资金")
    logger.info("=" * 60)
    
    # 初始化数据源
    data_source = AkshareDataSource()
    
    # 初始化交易接口（模拟）
    trader = SimulatedTrader(
        initial_cash=DEFAULT_CASH,
        commission=DEFAULT_COMMISSION,
        slippage=DEFAULT_SLIPPAGE,
        data_source=data_source
    )
    
    # 选择策略
    from strategies import MACDStrategy
    strategy = MACDStrategy()
    
    # 选择股票
    symbol = DEFAULT_STOCKS[0]
    
    # 创建实时交易管理器
    realtime_trader = RealtimeTrader(
        trader=trader,
        strategy=strategy,
        symbol=symbol,
        check_interval=300  # 每5分钟检查一次（实际交易建议更频繁）
    )
    
    # 启动交易
    realtime_trader.start()


if __name__ == "__main__":
    main_realtime_trading()

