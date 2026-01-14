"""
策略基类
"""
from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """策略基类，所有策略都需要继承此类"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 包含OHLCV数据的DataFrame
            
        Returns:
            DataFrame with 'signal' column:
                - 1: 买入信号
                - -1: 卖出信号
                - 0: 持有/无信号
        """
        pass
    
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """准备数据（可以在这里计算技术指标等）"""
        return data.copy()

