"""
回测引擎
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from strategies.base_strategy import BaseStrategy
from utils.logger import get_logger

logger = get_logger(__name__)

class BacktestEngine:
    """回测引擎"""
    
    def __init__(
        self,
        initial_cash: float = 1000000,
        commission: float = 0.0003,
        slippage: float = 0.001
    ):
        """
        初始化回测引擎
        
        Args:
            initial_cash: 初始资金
            commission: 手续费率
            slippage: 滑点率
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.logger = logger
        
    def run(
        self,
        data: pd.DataFrame,
        strategy: BaseStrategy
    ) -> pd.DataFrame:
        """
        运行回测
        
        Args:
            data: 股票数据（包含OHLCV）
            strategy: 交易策略
            
        Returns:
            包含回测结果的DataFrame
        """
        self.logger.info(f"开始回测策略: {strategy.name}")
        
        # 生成交易信号
        signals = strategy.generate_signals(data)
        
        # 合并数据
        df = data.join(signals)
        df['signal'] = df['signal'].fillna(0)
        
        # 初始化回测变量
        cash = self.initial_cash
        position = 0  # 持仓数量
        portfolio_value = []  # 组合价值
        trades = []  # 交易记录
        
        # 回测循环
        for i in range(len(df)):
            date = df.index[i]
            close_price = df.loc[date, 'close']
            signal = df.loc[date, 'signal']
            
            # 计算当前持仓价值
            current_value = cash + position * close_price
            
            # 执行交易
            if signal > 0:  # 买入信号
                if position == 0 and cash > 0:  # 当前无持仓
                    # 计算可买入数量（考虑手续费和滑点）
                    price_with_slippage = close_price * (1 + self.slippage)
                    cost_per_share = price_with_slippage * (1 + self.commission)
                    
                    # 买入（100股为一手）
                    shares_to_buy = int(cash / cost_per_share / 100) * 100
                    
                    if shares_to_buy > 0:
                        cost = shares_to_buy * cost_per_share
                        position = shares_to_buy
                        cash -= cost
                        
                        trades.append({
                            'date': date,
                            'action': '买入',
                            'price': price_with_slippage,
                            'shares': shares_to_buy,
                            'cost': cost,
                            'cash': cash,
                            'position': position
                        })
                        self.logger.debug(f"{date}: 买入 {shares_to_buy} 股，价格 {price_with_slippage:.2f}")
                        
            elif signal < 0:  # 卖出信号
                if position > 0:  # 当前有持仓
                    # 计算卖出价格（考虑滑点）
                    price_with_slippage = close_price * (1 - self.slippage)
                    revenue_per_share = price_with_slippage * (1 - self.commission)
                    
                    # 卖出
                    revenue = position * revenue_per_share
                    cash += revenue
                    
                    trades.append({
                        'date': date,
                        'action': '卖出',
                        'price': price_with_slippage,
                        'shares': position,
                        'revenue': revenue,
                        'cash': cash,
                        'position': 0
                    })
                    self.logger.debug(f"{date}: 卖出 {position} 股，价格 {price_with_slippage:.2f}")
                    position = 0
            
            # 记录组合价值
            portfolio_value.append({
                'date': date,
                'cash': cash,
                'position': position,
                'stock_value': position * close_price,
                'total_value': cash + position * close_price,
                'close_price': close_price
            })
        
        # 生成回测结果
        results = pd.DataFrame(portfolio_value)
        results = results.set_index('date')
        results['trades'] = len(trades)
        
        # 计算收益
        results['returns'] = results['total_value'].pct_change()
        results['cumulative_returns'] = (1 + results['returns']).cumprod() - 1
        
        # 计算基准收益（买入持有策略）
        results['benchmark_returns'] = results['close_price'].pct_change()
        results['benchmark_cumulative_returns'] = (1 + results['benchmark_returns']).cumprod() - 1
        
        self.logger.info(f"回测完成，共执行 {len(trades)} 笔交易")
        self.logger.info(f"最终价值: {results['total_value'].iloc[-1]:.2f}")
        self.logger.info(f"总收益率: {results['cumulative_returns'].iloc[-1]*100:.2f}%")
        
        # 保存交易记录
        self.trades = pd.DataFrame(trades)
        if len(self.trades) > 0:
            self.trades = self.trades.set_index('date')
        
        return results
    
    def get_performance_metrics(self, results: pd.DataFrame) -> Dict:
        """
        计算性能指标
        
        Args:
            results: 回测结果DataFrame
            
        Returns:
            性能指标字典
        """
        total_return = results['cumulative_returns'].iloc[-1]
        benchmark_return = results['benchmark_cumulative_returns'].iloc[-1]
        
        # 年化收益率
        days = (results.index[-1] - results.index[0]).days
        years = days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 波动率（年化）
        returns = results['returns'].dropna()
        volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
        
        # 夏普比率（假设无风险利率为3%）
        risk_free_rate = 0.03
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 最大回撤
        cumulative = results['cumulative_returns']
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_drawdown = drawdown.min()
        
        # 胜率（如果有交易记录）
        win_rate = 0
        if hasattr(self, 'trades') and len(self.trades) > 0:
            if 'action' in self.trades.columns:
                buy_trades = self.trades[self.trades['action'] == '买入']
                sell_trades = self.trades[self.trades['action'] == '卖出']
                if len(buy_trades) > 0 and len(sell_trades) > 0:
                    # 简化计算：比较买入和卖出价格
                    pass  # 这里可以进一步实现详细的胜率计算
        
        metrics = {
            '总收益率': f"{total_return*100:.2f}%",
            '年化收益率': f"{annual_return*100:.2f}%",
            '基准收益率': f"{benchmark_return*100:.2f}%",
            '最大回撤': f"{max_drawdown*100:.2f}%",
            '波动率': f"{volatility*100:.2f}%",
            '夏普比率': f"{sharpe_ratio:.2f}",
            '交易次数': len(self.trades) if hasattr(self, 'trades') else 0
        }
        
        return metrics

