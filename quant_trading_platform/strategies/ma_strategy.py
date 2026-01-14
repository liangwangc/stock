"""
移动平均线策略
"""
import pandas as pd
from .base_strategy import BaseStrategy
from indicators.technical_indicators import SMA

class MovingAverageStrategy(BaseStrategy):
    """双移动平均线策略：短期均线上穿长期均线时买入，下穿时卖出"""
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__("移动平均线策略")
        self.short_period = short_period
        self.long_period = long_period
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = data.copy()
        
        # 计算移动平均线
        df['ma_short'] = SMA(df['close'], self.short_period)
        df['ma_long'] = SMA(df['close'], self.long_period)
        
        # 生成信号
        signals = pd.DataFrame(index=df.index)
        signals['signal'] = 0
        
        # 金叉：短期均线上穿长期均线，买入
        signals.loc[df['ma_short'] > df['ma_long'], 'signal'] = 1
        # 死叉：短期均线下穿长期均线，卖出
        signals.loc[df['ma_short'] < df['ma_long'], 'signal'] = -1
        
        # 只在交叉点产生信号（避免重复信号）
        signals['signal'] = signals['signal'].diff()
        signals['signal'] = signals['signal'].fillna(0)
        
        return signals

