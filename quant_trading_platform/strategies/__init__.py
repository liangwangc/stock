"""策略模块"""

from .base_strategy import BaseStrategy
from .ma_strategy import MovingAverageStrategy
from .macd_strategy import MACDStrategy
from .news_strategy import NewsBasedStrategy, NewsRealtimeStrategy

__all__ = ['BaseStrategy', 'MovingAverageStrategy', 'MACDStrategy', 
           'NewsBasedStrategy', 'NewsRealtimeStrategy']

