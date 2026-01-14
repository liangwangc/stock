"""实盘交易模块"""

from .base_trader import BaseTrader
from .simulated_trader import SimulatedTrader

# 尝试导入广发证券接口（如果可用）
try:
    from .gf_trader import GFTrader
    __all__ = ['BaseTrader', 'SimulatedTrader', 'GFTrader']
except ImportError:
    __all__ = ['BaseTrader', 'SimulatedTrader']

