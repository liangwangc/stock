"""
将config.py中的默认配置导入到数据库
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.prediction_config_manager import PredictionConfigManager
from config import PREDICTION_CONFIG, INDICATOR_CONFIG, NEWS_CONFIG, TRADING_CONFIG
from utils.logger import get_logger

logger = get_logger(__name__)


def migrate_config_to_db():
    """将config.py中的配置导入数据库"""
    try:
        manager = PredictionConfigManager()
        
        # 准备配置值
        values = {
            'prediction': PREDICTION_CONFIG.copy(),
            'indicator': INDICATOR_CONFIG.copy(),
            'news': NEWS_CONFIG.copy(),
            'trading': TRADING_CONFIG.copy()
        }
        
        # 检查是否已存在默认配置
        configs = manager.get_all_configs()
        default_config = None
        for config in configs:
            if config.get('config_name') == '默认配置' or config.get('is_default') == 1:
                default_config = config
                break
        
        if default_config:
            logger.info(f"找到现有默认配置（ID: {default_config['id']}），将更新它...")
            success = manager.update_config(
                config_id=default_config['id'],
                config_name='默认配置',
                description='从config.py导入的默认配置',
                values=values,
                user_id=None
            )
            if success:
                # 如果当前没有激活的配置，激活这个配置
                if manager.get_active_config_id() is None:
                    manager.activate_config(default_config['id'])
                logger.info("默认配置更新成功")
            else:
                logger.error("默认配置更新失败")
        else:
            logger.info("创建新的默认配置...")
            config_id = manager.create_config(
                config_name='默认配置',
                description='从config.py导入的默认配置',
                values=values,
                user_id=None,
                is_default=True
            )
            
            if config_id:
                # 激活配置
                manager.activate_config(config_id)
                logger.info(f"默认配置创建并激活成功（ID: {config_id}）")
            else:
                logger.error("默认配置创建失败")
        
        logger.info("配置迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"配置迁移失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("配置迁移工具：将config.py中的配置导入到数据库")
    print("=" * 60)
    
    success = migrate_config_to_db()
    
    if success:
        print("\n✅ 配置迁移成功！")
        print("您可以在设置页面查看和修改预测参数配置。")
    else:
        print("\n❌ 配置迁移失败，请查看日志了解详情。")
    
    sys.exit(0 if success else 1)
