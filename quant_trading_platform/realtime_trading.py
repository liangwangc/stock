"""
实时交易主程序
使用模拟交易接口进行实时交易测试
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading.realtime_trader import main_realtime_trading

if __name__ == "__main__":
    main_realtime_trading()

