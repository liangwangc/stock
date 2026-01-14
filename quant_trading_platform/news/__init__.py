"""新闻模块"""

from .news_source import BaseNewsSource, AkshareNewsSource
from .sentiment_analyzer import NewsSentimentAnalyzer
from .jin10_news_source import Jin10NewsSource
from .caixin_news_source import CaixinNewsSource
from .securities_news_source import SecuritiesNewsSource
from .unified_news_source import UnifiedNewsSource

__all__ = [
    'BaseNewsSource', 
    'AkshareNewsSource', 
    'NewsSentimentAnalyzer',
    'Jin10NewsSource',
    'CaixinNewsSource',
    'SecuritiesNewsSource',
    'UnifiedNewsSource'
]

