"""
量化交易平台主程序
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 用来正常显示中文标签
matplotlib.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

from config import (
    DEFAULT_STOCKS, START_DATE, END_DATE,
    DEFAULT_CASH, DEFAULT_COMMISSION, DEFAULT_SLIPPAGE
)
from data_source import AkshareDataSource
from strategies import MovingAverageStrategy, MACDStrategy
from backtest import BacktestEngine
from utils.logger import get_logger

logger = get_logger(__name__)

def plot_results(results: pd.DataFrame, symbol: str, strategy_name: str):
    """绘制回测结果"""
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    # 第一张图：组合价值对比
    ax1 = axes[0]
    ax1.plot(results.index, results['total_value'], label='策略收益', linewidth=2)
    ax1.plot(results.index, results['close_price'] / results['close_price'].iloc[0] * DEFAULT_CASH, 
             label='基准收益（买入持有）', linewidth=2, alpha=0.7)
    ax1.set_title(f'{symbol} - {strategy_name} 回测结果', fontsize=14, fontweight='bold')
    ax1.set_ylabel('组合价值（元）', fontsize=12)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 第二张图：累计收益率
    ax2 = axes[1]
    ax2.plot(results.index, results['cumulative_returns'] * 100, label='策略累计收益率', linewidth=2)
    ax2.plot(results.index, results['benchmark_cumulative_returns'] * 100, 
             label='基准累计收益率', linewidth=2, alpha=0.7)
    ax2.set_xlabel('日期', fontsize=12)
    ax2.set_ylabel('累计收益率（%）', fontsize=12)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'backtest_results_{symbol}.png', dpi=300, bbox_inches='tight')
    logger.info(f"回测结果图已保存: backtest_results_{symbol}.png")
    plt.show()

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("量化交易平台启动")
    logger.info("=" * 60)
    
    # 初始化数据源
    data_source = AkshareDataSource()
    
    # 选择策略（可以修改这里切换策略）
    # strategy = MovingAverageStrategy(short_period=5, long_period=20)
    strategy = MACDStrategy()
    
    # 初始化回测引擎
    backtest_engine = BacktestEngine(
        initial_cash=DEFAULT_CASH,
        commission=DEFAULT_COMMISSION,
        slippage=DEFAULT_SLIPPAGE
    )
    
    # 选择一只股票进行回测（可以修改为其他股票代码）
    symbol = DEFAULT_STOCKS[0]  # 使用第一只股票
    logger.info(f"回测股票: {symbol}")
    
    # 获取数据
    logger.info(f"正在获取 {symbol} 的历史数据...")
    data = data_source.get_stock_data(symbol, START_DATE, END_DATE)
    
    if data.empty:
        logger.error(f"无法获取 {symbol} 的数据，请检查网络连接或股票代码")
        return
    
    logger.info(f"成功获取 {len(data)} 条数据记录")
    
    # 运行回测
    results = backtest_engine.run(data, strategy)
    
    # 计算性能指标
    metrics = backtest_engine.get_performance_metrics(results)
    
    # 打印性能指标
    logger.info("\n" + "=" * 60)
    logger.info("回测性能指标")
    logger.info("=" * 60)
    for key, value in metrics.items():
        logger.info(f"{key}: {value}")
    logger.info("=" * 60 + "\n")
    
    # 显示交易记录
    if hasattr(backtest_engine, 'trades') and len(backtest_engine.trades) > 0:
        logger.info("交易记录:")
        logger.info(backtest_engine.trades.to_string())
        logger.info("")
    
    # 绘制结果
    try:
        plot_results(results, symbol, strategy.name)
    except Exception as e:
        logger.warning(f"绘图失败: {str(e)}，可能因为图形界面不可用")
    
    logger.info("回测完成！")

if __name__ == "__main__":
    main()

