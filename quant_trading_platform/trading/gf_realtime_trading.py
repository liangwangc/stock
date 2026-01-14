"""
广发证券实时交易主程序
使用广发证券API进行实盘交易
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.gf_trader import GFTrader
from trading.realtime_trader import RealtimeTrader
from strategies import MACDStrategy
from config import GF_API_CONFIG, DEFAULT_STOCKS
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """广发证券实时交易主函数"""
    logger.info("=" * 60)
    logger.info("广发证券实时交易系统")
    logger.info("=" * 60)
    
    # 检查配置
    if not GF_API_CONFIG.get("enabled", False):
        logger.error("❌ 广发证券API未启用，请在config.py中配置GF_API_CONFIG")
        logger.error("   需要设置: api_key, api_secret, app_id, enabled=True")
        return
    
    if not all([GF_API_CONFIG.get("api_key"), 
                GF_API_CONFIG.get("api_secret"), 
                GF_API_CONFIG.get("app_id")]):
        logger.error("❌ 广发证券API配置不完整，请检查config.py中的GF_API_CONFIG")
        return
    
    try:
        # 初始化广发证券交易接口
        logger.info("正在连接广发证券API...")
        trader = GFTrader(
            api_key=GF_API_CONFIG["api_key"],
            api_secret=GF_API_CONFIG["api_secret"],
            app_id=GF_API_CONFIG["app_id"],
            base_url=GF_API_CONFIG.get("base_url", "https://openapi.gf.com.cn")
        )
        
        # 查询账户信息
        balance = trader.get_balance()
        logger.info(f"账户信息 - 可用资金: {balance['cash']:.2f}元, "
                   f"总资产: {balance['total_value']:.2f}元")
        
        # 选择策略
        strategy = MACDStrategy()
        
        # 选择股票
        symbol = DEFAULT_STOCKS[0]
        
        # 创建实时交易管理器
        realtime_trader = RealtimeTrader(
            trader=trader,
            strategy=strategy,
            symbol=symbol,
            check_interval=300  # 每5分钟检查一次
        )
        
        logger.warning("⚠️  警告：这是实盘交易，将使用真实资金！")
        logger.info("按 Ctrl+C 停止交易")
        
        # 启动交易
        realtime_trader.start()
        
    except ImportError as e:
        logger.error(f"❌ 导入错误: {str(e)}")
        logger.error("请先安装广发证券API客户端: pip install gf-api-client")
    except Exception as e:
        logger.error(f"❌ 启动失败: {str(e)}")
        logger.error("请检查API配置和网络连接")


if __name__ == "__main__":
    main()

