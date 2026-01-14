"""
模拟交易接口（用于测试，不涉及真实资金）
"""
import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from .base_trader import BaseTrader
from utils.logger import get_logger

logger = get_logger(__name__)

class SimulatedTrader(BaseTrader):
    """模拟交易接口，用于测试交易逻辑，不涉及真实资金"""
    
    def __init__(
        self,
        initial_cash: float = 1000000,
        commission: float = 0.0003,
        slippage: float = 0.001,
        data_source=None
    ):
        """
        初始化模拟交易接口
        
        Args:
            initial_cash: 初始资金
            commission: 手续费率
            slippage: 滑点率
            data_source: 数据源，用于获取实时价格
        """
        self.cash = initial_cash
        self.commission = commission
        self.slippage = slippage
        self.data_source = data_source
        self.positions = {}  # {symbol: {'shares': int, 'cost': float}}
        self.trades = []  # 交易记录
        self.logger = logger
        
    def buy(self, symbol: str, amount: float, price: Optional[float] = None) -> Dict:
        """买入股票（模拟）"""
        try:
            # 获取当前价格
            if price is None:
                current_price = self.get_current_price(symbol)
            else:
                current_price = price
            
            if current_price is None or current_price <= 0:
                return {'success': False, 'message': f'无法获取 {symbol} 的价格'}
            
            # 计算买入价格（考虑滑点）
            buy_price = current_price * (1 + self.slippage)
            cost_per_share = buy_price * (1 + self.commission)
            
            # 计算可买入数量（A股以100股为单位）
            shares = int(amount / cost_per_share / 100) * 100
            
            if shares <= 0:
                return {'success': False, 'message': '资金不足，无法买入'}
            
            # 计算总成本
            total_cost = shares * cost_per_share
            
            if total_cost > self.cash:
                return {'success': False, 'message': '资金不足'}
            
            # 执行买入
            self.cash -= total_cost
            
            # 更新持仓
            if symbol in self.positions:
                old_shares = self.positions[symbol]['shares']
                old_cost = self.positions[symbol]['cost']
                total_shares = old_shares + shares
                total_cost_basis = old_cost * old_shares + total_cost
                self.positions[symbol] = {
                    'shares': total_shares,
                    'cost': total_cost_basis / total_shares
                }
            else:
                self.positions[symbol] = {
                    'shares': shares,
                    'cost': cost_per_share
                }
            
            # 记录交易
            trade = {
                'date': datetime.now(),
                'symbol': symbol,
                'action': '买入',
                'price': buy_price,
                'shares': shares,
                'amount': total_cost,
                'cash_after': self.cash
            }
            self.trades.append(trade)
            
            self.logger.info(f"模拟买入: {symbol} {shares}股 @ {buy_price:.2f}元, 总成本: {total_cost:.2f}元")
            
            return {
                'success': True,
                'symbol': symbol,
                'shares': shares,
                'price': buy_price,
                'amount': total_cost,
                'order_id': f"SIM_{len(self.trades)}"
            }
            
        except Exception as e:
            self.logger.error(f"买入失败: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def sell(self, symbol: str, shares: int, price: Optional[float] = None) -> Dict:
        """卖出股票（模拟）"""
        try:
            # 检查持仓
            if symbol not in self.positions or self.positions[symbol]['shares'] <= 0:
                return {'success': False, 'message': f'没有 {symbol} 的持仓'}
            
            position_shares = self.positions[symbol]['shares']
            if shares > position_shares:
                shares = position_shares  # 全部卖出
            
            # 获取当前价格
            if price is None:
                current_price = self.get_current_price(symbol)
            else:
                current_price = price
            
            if current_price is None or current_price <= 0:
                return {'success': False, 'message': f'无法获取 {symbol} 的价格'}
            
            # 计算卖出价格（考虑滑点）
            sell_price = current_price * (1 - self.slippage)
            revenue_per_share = sell_price * (1 - self.commission)
            
            # 计算总收入
            total_revenue = shares * revenue_per_share
            
            # 执行卖出
            self.cash += total_revenue
            
            # 更新持仓
            self.positions[symbol]['shares'] -= shares
            if self.positions[symbol]['shares'] <= 0:
                del self.positions[symbol]
            
            # 记录交易
            trade = {
                'date': datetime.now(),
                'symbol': symbol,
                'action': '卖出',
                'price': sell_price,
                'shares': shares,
                'amount': total_revenue,
                'cash_after': self.cash
            }
            self.trades.append(trade)
            
            self.logger.info(f"模拟卖出: {symbol} {shares}股 @ {sell_price:.2f}元, 总收入: {total_revenue:.2f}元")
            
            return {
                'success': True,
                'symbol': symbol,
                'shares': shares,
                'price': sell_price,
                'amount': total_revenue,
                'order_id': f"SIM_{len(self.trades)}"
            }
            
        except Exception as e:
            self.logger.error(f"卖出失败: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def get_position(self, symbol: str) -> Dict:
        """获取持仓信息"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            current_price = self.get_current_price(symbol)
            if current_price:
                market_value = pos['shares'] * current_price
                profit = market_value - pos['shares'] * pos['cost']
                profit_pct = (profit / (pos['shares'] * pos['cost'])) * 100 if pos['shares'] > 0 else 0
            else:
                market_value = 0
                profit = 0
                profit_pct = 0
            
            return {
                'symbol': symbol,
                'shares': pos['shares'],
                'cost': pos['cost'],
                'market_price': current_price,
                'market_value': market_value,
                'profit': profit,
                'profit_pct': profit_pct
            }
        else:
            return {
                'symbol': symbol,
                'shares': 0,
                'cost': 0,
                'market_price': self.get_current_price(symbol),
                'market_value': 0,
                'profit': 0,
                'profit_pct': 0
            }
    
    def get_balance(self) -> Dict:
        """获取账户余额"""
        total_value = self.cash
        positions_value = 0
        
        for symbol in self.positions:
            pos = self.get_position(symbol)
            total_value += pos['market_value']
            positions_value += pos['market_value']
        
        return {
            'cash': self.cash,
            'positions_value': positions_value,
            'total_value': total_value
        }
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        if self.data_source is None:
            self.logger.warning("未设置数据源，无法获取实时价格")
            return None
        
        try:
            # 获取最新数据
            today = datetime.now().strftime('%Y%m%d')
            data = self.data_source.get_stock_data(symbol, today, today)
            if not data.empty:
                return float(data['close'].iloc[-1])
            return None
        except Exception as e:
            self.logger.error(f"获取 {symbol} 价格失败: {str(e)}")
            return None

