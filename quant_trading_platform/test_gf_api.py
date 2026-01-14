"""
广发证券API配置测试脚本
用于测试API配置和连接
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import GF_API_CONFIG
from utils.logger import get_logger

logger = get_logger(__name__)

def test_config():
    """测试API配置"""
    logger.info("=" * 60)
    logger.info("广发证券API配置测试")
    logger.info("=" * 60)
    
    # 检查配置是否启用
    if not GF_API_CONFIG.get("enabled", False):
        logger.error("[X] API未启用，请在config.py中设置 enabled=True")
        return False
    
    # 检查必需参数
    required_keys = ["api_key", "api_secret", "app_id"]
    missing_keys = []
    
    for key in required_keys:
        value = GF_API_CONFIG.get(key, "")
        if not value or value == "":
            missing_keys.append(key)
        else:
            # 显示配置（部分隐藏以保护隐私）
            display_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "***"
            logger.info(f"[OK] {key}: {display_value}")
    
    if missing_keys:
        logger.error(f"[X] 缺少必需的配置项: {', '.join(missing_keys)}")
        logger.error("   请在config.py的GF_API_CONFIG中填写这些值")
        return False
    
    logger.info("[OK] 配置检查通过")
    return True

def test_import():
    """测试API客户端库是否已安装"""
    logger.info("\n检查API客户端库...")
    
    try:
        import gf_api_client
        logger.info("[OK] gf-api-client 已安装")
        logger.info(f"   版本: {getattr(gf_api_client, '__version__', '未知')}")
        return True
    except ImportError:
        logger.error("[X] gf-api-client 未安装")
        logger.error("   请运行: pip install gf-api-client")
        return False

def test_api_connection():
    """测试API连接"""
    logger.info("\n测试API连接...")
    
    try:
        from trading.gf_trader import GFTrader
        
        # 尝试创建交易接口
        trader = GFTrader(
            api_key=GF_API_CONFIG["api_key"],
            api_secret=GF_API_CONFIG["api_secret"],
            app_id=GF_API_CONFIG["app_id"],
            base_url=GF_API_CONFIG.get("base_url", "https://openapi.gf.com.cn")
        )
        
        logger.info("[OK] API客户端初始化成功")
        
        # 测试查询账户信息
        logger.info("\n测试查询账户信息...")
        try:
            balance = trader.get_balance()
            logger.info(f"[OK] 账户查询成功")
            logger.info(f"   可用资金: {balance.get('cash', 0):.2f}元")
            logger.info(f"   总资产: {balance.get('total_value', 0):.2f}元")
            return True
        except Exception as e:
            logger.error(f"[X] 账户查询失败: {str(e)}")
            logger.warning("   这可能是因为:")
            logger.warning("   1. API密钥不正确")
            logger.warning("   2. 网络连接问题")
            logger.warning("   3. API服务暂时不可用")
            logger.warning("   4. 账户权限不足")
            return False
            
    except ImportError as e:
        logger.error(f"[X] 导入失败: {str(e)}")
        logger.error("   请确保gf-api-client已正确安装")
        return False
    except Exception as e:
        logger.error(f"[X] API连接失败: {str(e)}")
        logger.warning("   请检查API配置和网络连接")
        return False

def main():
    """主测试函数"""
    logger.info("\n开始测试...\n")
    
    # 测试1: 配置检查
    config_ok = test_config()
    if not config_ok:
        logger.error("\n[X] 配置检查失败，请先完善配置")
        return
    
    # 测试2: 库导入检查
    import_ok = test_import()
    if not import_ok:
        logger.error("\n[X] 库导入失败，请先安装依赖")
        return
    
    # 测试3: API连接测试
    connection_ok = test_api_connection()
    
    logger.info("\n" + "=" * 60)
    if connection_ok:
        logger.info("[OK] 所有测试通过！API连接正常")
        logger.info("   现在可以运行: python trading/gf_realtime_trading.py")
    else:
        logger.info("[X] 部分测试失败，请检查上述错误信息")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()

