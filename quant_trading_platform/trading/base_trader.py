"""
交易接口基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd

class BaseTrader(ABC):
    """交易接口基类，所有交易接口都需要继承此类"""
    
    @abstractmethod
    def buy(self, symbol: str, amount: float, price: Optional[float] = None) -> Dict:
        """
        买入股票
        
        Args:
            symbol: 股票代码
            amount: 买入金额（元）
            price: 买入价格，如果为None则使用市价
            
        Returns:
            交易结果字典，包含订单号、成交价格、成交数量等
        """
        pass
    
    @abstractmethod
    def sell(self, symbol: str, shares: int, price: Optional[float] = None) -> Dict:
        """
        卖出股票
        
        Args:
            symbol: 股票代码
            shares: 卖出股数
            price: 卖出价格，如果为None则使用市价
            
        Returns:
            交易结果字典，包含订单号、成交价格、成交数量等
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Dict:
        """
        获取持仓信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            持仓信息字典，包含持仓数量、成本价等
        """
        pass
    
    @abstractmethod
    def get_balance(self) -> Dict:
        """
        获取账户余额
        
        Returns:
            账户信息字典，包含可用资金、总资产等
        """
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """
        获取当前价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            当前价格
        """
        pass

