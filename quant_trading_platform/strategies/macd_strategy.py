"""
MACD策略
"""
import pandas as pd
from .base_strategy import BaseStrategy
from indicators.technical_indicators import MACD

class MACDStrategy(BaseStrategy):
    """MACD策略：MACD线上穿信号线时买入，下穿时卖出"""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD策略")
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = data.copy()
        
        # 计算MACD
        macd_data = MACD(df['close'], self.fast, self.slow, self.signal)
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        
        # 生成信号
        signals = pd.DataFrame(index=df.index)
        signals['signal'] = 0
        
        # MACD线上穿信号线，买入
        signals.loc[df['macd'] > df['macd_signal'], 'signal'] = 1
        # MACD线下穿信号线，卖出
        signals.loc[df['macd'] < df['macd_signal'], 'signal'] = -1
        
        # 只在交叉点产生信号
        signals['signal'] = signals['signal'].diff()
        signals['signal'] = signals['signal'].fillna(0)
        
        return signals

