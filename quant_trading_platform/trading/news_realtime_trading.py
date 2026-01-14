"""
基于新闻的实时交易系统
根据市场新闻快速买入/卖出
"""
import sys
import os
import time
import schedule
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.simulated_trader import SimulatedTrader
from trading.base_trader import BaseTrader
from strategies.news_strategy import NewsRealtimeStrategy
from data_source import AkshareDataSource
from utils.logger import get_logger
from config import DEFAULT_STOCKS, DEFAULT_CASH, DEFAULT_COMMISSION, DEFAULT_SLIPPAGE

logger = get_logger(__name__)

class NewsRealtimeTrading:
    """基于新闻的实时交易系统"""
    
    def __init__(
        self,
        trader: BaseTrader,
        strategy: NewsRealtimeStrategy,
        check_interval: int = 300,  # 检查间隔（秒），默认5分钟
        fast_trade: bool = True,  # 快速交易模式
        max_position_ratio: float = 0.8  # 最大持仓比例
    ):
        """
        初始化新闻实时交易系统
        
        Args:
            trader: 交易接口
            strategy: 新闻策略
            check_interval: 检查新闻的时间间隔（秒）
            fast_trade: 快速交易模式
            max_position_ratio: 最大持仓比例（相对于总资产）
        """
        self.trader = trader
        self.strategy = strategy
        self.check_interval = check_interval
        self.fast_trade = fast_trade
        self.max_position_ratio = max_position_ratio
        self.data_source = AkshareDataSource()
        self.logger = logger
        self.running = False
    
    def check_and_trade(self):
        """检查新闻并执行交易"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("检查新闻并生成交易信号...")
            
            # 获取新闻信号
            signal_result = self.strategy.check_news_and_generate_signal()
            
            signal = signal_result.get('signal', 0)
            sentiment = signal_result.get('sentiment', 'neutral')
            score = signal_result.get('score', 0.0)
            confidence = signal_result.get('confidence', 0.0)
            news_count = signal_result.get('news_count', 0)
            
            self.logger.info(f"信号结果: signal={signal}, sentiment={sentiment}, "
                           f"score={score:.2f}, confidence={confidence:.2f}, news={news_count}")
            
            if signal == 0:
                self.logger.info("无交易信号，继续监控")
                return
            
            # 获取账户信息
            balance = self.trader.get_balance()
            position = self.trader.get_position(self.strategy.symbol)
            
            available_cash = balance.get('cash', balance.get('available_cash', 0))
            total_value = balance.get('total_value', balance.get('total_asset', 0))
            
            # 快速买入（利好新闻）
            if signal > 0:
                if position['shares'] == 0:  # 当前无持仓
                    # 计算买入金额（使用可用资金的一定比例）
                    if self.fast_trade:
                        # 快速交易模式：使用更高比例
                        buy_ratio = 0.9
                    else:
                        buy_ratio = 0.7
                    
                    buy_amount = min(
                        available_cash * buy_ratio,
                        total_value * self.max_position_ratio
                    )
                    
                    if buy_amount > 1000:  # 至少1000元才买入
                        self.logger.info(f"🚀 快速买入: {self.strategy.symbol}, 金额: {buy_amount:.2f}元")
                        result = self.trader.buy(self.strategy.symbol, buy_amount)
                        
                        if result.get('success'):
                            self.logger.info(f"✅ 买入成功: {result['shares']}股 @ {result['price']:.2f}元")
                            self.logger.info(f"   触发原因: 利好新闻 (情感分数: {score:.2f}, 置信度: {confidence:.2f})")
                        else:
                            self.logger.warning(f"❌ 买入失败: {result.get('message')}")
                    else:
                        self.logger.warning("可用资金不足，无法买入")
                else:
                    self.logger.info(f"已有持仓 {position['shares']}股，不重复买入")
            
            # 快速卖出（利空新闻）
            elif signal < 0:
                if position['shares'] > 0:  # 当前有持仓
                    self.logger.info(f"🚨 快速卖出: {self.strategy.symbol}, 持仓: {position['shares']}股")
                    result = self.trader.sell(self.strategy.symbol, position['shares'])
                    
                    if result.get('success'):
                        self.logger.info(f"✅ 卖出成功: {result['shares']}股 @ {result['price']:.2f}元")
                        self.logger.info(f"   触发原因: 利空新闻 (情感分数: {score:.2f}, 置信度: {confidence:.2f})")
                    else:
                        self.logger.warning(f"❌ 卖出失败: {result.get('message')}")
                else:
                    self.logger.info("无持仓，无需卖出")
            
            # 显示账户状态
            balance = self.trader.get_balance()
            cash = balance.get('cash', balance.get('available_cash', 0))
            positions_value = balance.get('positions_value', balance.get('market_value', 0))
            total_value = balance.get('total_value', balance.get('total_asset', cash + positions_value))
            
            self.logger.info(f"账户状态 - 现金: {cash:.2f}元, "
                           f"持仓市值: {positions_value:.2f}元, "
                           f"总资产: {total_value:.2f}元")
            
        except Exception as e:
            self.logger.error(f"检查交易时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def start(self):
        """启动新闻实时交易系统"""
        self.logger.info("=" * 60)
        self.logger.info("启动基于新闻的实时交易系统")
        self.logger.info(f"股票: {self.strategy.symbol}")
        self.logger.info(f"检查间隔: {self.check_interval}秒 ({self.check_interval/60:.1f}分钟)")
        self.logger.info(f"快速交易模式: {'开启' if self.fast_trade else '关闭'}")
        self.logger.info("=" * 60)
        
        self.running = True
        
        # 立即执行一次检查
        self.check_and_trade()
        
        # 设置定时任务
        schedule.every(self.check_interval).seconds.do(self.check_and_trade)
        
        self.logger.info(f"系统已启动，每 {self.check_interval} 秒检查一次新闻")
        self.logger.info("按 Ctrl+C 停止交易")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在关闭交易系统...")
            self.stop()
    
    def stop(self):
        """停止交易系统"""
        self.running = False
        self.logger.info("交易系统已停止")

def main():
    """新闻实时交易主函数"""
    logger.info("=" * 60)
    logger.info("基于新闻的实时交易系统（模拟模式）")
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
    
    # 选择股票
    symbol = DEFAULT_STOCKS[0]
    
    # 创建新闻策略
    strategy = NewsRealtimeStrategy(
        symbol=symbol,
        sentiment_threshold=0.3,  # 情感阈值
        confidence_threshold=0.5,  # 置信度阈值
        news_count=5,  # 分析5条最新新闻
        fast_trade=True  # 快速交易模式
    )
    
    # 创建新闻实时交易系统
    news_trading = NewsRealtimeTrading(
        trader=trader,
        strategy=strategy,
        check_interval=300,  # 每5分钟检查一次
        fast_trade=True,  # 快速交易
        max_position_ratio=0.8  # 最大持仓80%
    )
    
    # 启动交易
    news_trading.start()

if __name__ == "__main__":
    main()






