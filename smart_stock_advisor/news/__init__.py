"""新闻模块（链接到quant_trading_platform）"""

import sys
import os

# 添加quant_trading_platform到路径
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
quant_platform_path = os.path.join(parent_dir, 'quant_trading_platform')
if os.path.exists(quant_platform_path):
    sys.path.insert(0, quant_platform_path)

try:
    from quant_trading_platform.news import UnifiedNewsSource, NewsSentimentAnalyzer
    __all__ = ['UnifiedNewsSource', 'NewsSentimentAnalyzer']
except ImportError:
    # 如果导入失败，尝试直接导入
    try:
        from news import UnifiedNewsSource, NewsSentimentAnalyzer
        __all__ = ['UnifiedNewsSource', 'NewsSentimentAnalyzer']
    except ImportError:
        __all__ = []
        print("警告: 新闻模块不可用")



