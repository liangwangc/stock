"""
数据源基类
"""
from abc import ABC, abstractmethod
import pandas as pd

class BaseDataSource(ABC):
    """数据源基类"""
    
    @abstractmethod
    def get_stock_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> pd.DataFrame:
        """
        获取股票数据
        
        Args:
            symbol: 股票代码（如：000001）
            start_date: 开始日期（格式：YYYYMMDD）
            end_date: 结束日期（格式：YYYYMMDD）
            period: 周期（daily, weekly, monthly）
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        pass
    
    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取股票列表
        
        Returns:
            DataFrame with stock symbols and names
        """
        pass

