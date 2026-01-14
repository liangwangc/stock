"""
预测参数配置功能测试脚本
"""
import sys
import os

# Windows控制台编码处理
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from utils.prediction_config_manager import PredictionConfigManager
from utils.logger import get_logger
from config import PREDICTION_CONFIG, INDICATOR_CONFIG, NEWS_CONFIG, TRADING_CONFIG

logger = get_logger(__name__)


def test_config_manager_init():
    """测试配置管理器初始化"""
    print("\n" + "=" * 60)
    print("测试1: 配置管理器初始化")
    print("=" * 60)
    
    try:
        manager = PredictionConfigManager()
        print("[OK] 配置管理器初始化成功")
        return manager
    except Exception as e:
        print(f"[ERROR] 配置管理器初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_create_default_config(manager):
    """测试创建默认配置"""
    print("\n" + "=" * 60)
    print("测试2: 创建默认配置")
    print("=" * 60)
    
    if not manager:
        print("[SKIP] 配置管理器未初始化，跳过测试")
        return None
    
    try:
        values = {
            'prediction': PREDICTION_CONFIG.copy(),
            'indicator': INDICATOR_CONFIG.copy(),
            'news': NEWS_CONFIG.copy(),
            'trading': TRADING_CONFIG.copy()
        }
        
        config_id = manager.create_config(
            config_name='测试默认配置',
            description='测试用的默认配置',
            values=values,
            user_id=None,
            is_default=True
        )
        
        if config_id:
            print(f"[OK] 默认配置创建成功，配置ID: {config_id}")
            return config_id
        else:
            print("[ERROR] 默认配置创建失败")
            return None
    except Exception as e:
        print(f"[ERROR] 创建默认配置时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_get_config(manager, config_id):
    """测试获取配置"""
    print("\n" + "=" * 60)
    print("测试3: 获取配置")
    print("=" * 60)
    
    if not manager:
        print("[SKIP] 配置管理器未初始化，跳过测试")
        return False
    
    try:
        config = manager.get_config(config_id)
        if config:
            print("[OK] 获取配置成功")
            print(f"   - 预测配置: {len(config.get('prediction', {}))} 个参数")
            print(f"   - 技术指标配置: {len(config.get('indicator', {}))} 个参数")
            return True
        else:
            print("[ERROR] 获取配置失败")
            return False
    except Exception as e:
        print(f"[ERROR] 获取配置时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_validate_config(manager):
    """测试配置验证"""
    print("\n" + "=" * 60)
    print("测试4: 配置验证")
    print("=" * 60)
    
    if not manager:
        print("[SKIP] 配置管理器未初始化，跳过测试")
        return False
    
    try:
        # 测试正确的配置
        valid_values = {
            'prediction': {
                'news_weight': 0.25,
                'capital_flow_weight': 0.18,
                'market_weight': 0.17,
                'technical_weight': 0.20,
                'sector_rotation_weight': 0.05,
                'history_weight': 0.08,
                'us_sector_weight': 0.05,
                'valuation_weight': 0.02,
                'min_confidence': 0.5,
                'lookback_days': 60
            },
            'indicator': INDICATOR_CONFIG.copy()
        }
        
        is_valid, error_msg = manager.validate_config(valid_values)
        if is_valid:
            print("[OK] 正确配置验证通过")
        else:
            print(f"[ERROR] 正确配置验证失败: {error_msg}")
            return False
        
        # 测试错误的配置（权重总和不为1）
        invalid_values = {
            'prediction': {
                'news_weight': 0.30,
                'capital_flow_weight': 0.30,
                'market_weight': 0.30,
                'technical_weight': 0.20,
                'sector_rotation_weight': 0.05,
                'history_weight': 0.08,
                'us_sector_weight': 0.05,
                'valuation_weight': 0.02
            },
            'indicator': INDICATOR_CONFIG.copy()
        }
        
        is_valid, error_msg = manager.validate_config(invalid_values)
        if not is_valid:
            print(f"[OK] 错误配置验证失败（符合预期）: {error_msg}")
        else:
            print("[ERROR] 错误配置验证通过（不符合预期）")
            return False
        
        return True
    except Exception as e:
        print(f"[ERROR] 配置验证时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_activate_config(manager, config_id):
    """测试激活配置"""
    print("\n" + "=" * 60)
    print("测试5: 激活配置")
    print("=" * 60)
    
    if not manager:
        print("[SKIP] 配置管理器未初始化，跳过测试")
        return False
    
    if not config_id:
        print("[ERROR] 配置ID不存在，跳过测试")
        return False
    
    try:
        success = manager.activate_config(config_id, user_id=None)
        if success:
            print("[OK] 配置激活成功")
            
            # 验证激活状态
            active_id = manager.get_active_config_id()
            if active_id == config_id:
                print(f"[OK] 激活状态验证成功（激活的配置ID: {active_id}）")
                return True
            else:
                print(f"[ERROR] 激活状态验证失败（期望: {config_id}, 实际: {active_id}）")
                return False
        else:
            print("[ERROR] 配置激活失败")
            return False
    except Exception as e:
        print(f"[ERROR] 激活配置时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_get_all_configs(manager):
    """测试获取所有配置"""
    print("\n" + "=" * 60)
    print("测试6: 获取所有配置")
    print("=" * 60)
    
    if not manager:
        print("[SKIP] 配置管理器未初始化，跳过测试")
        return False
    
    try:
        configs = manager.get_all_configs()
        print(f"[OK] 获取配置列表成功，共 {len(configs)} 个配置")
        for config in configs:
            status = "已激活" if config.get('is_active') == 1 else "未激活"
            print(f"   - {config.get('config_name')} ({status})")
        return True
    except Exception as e:
        print(f"[ERROR] 获取配置列表时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_update_config(manager, config_id):
    """测试更新配置"""
    print("\n" + "=" * 60)
    print("测试7: 更新配置")
    print("=" * 60)
    
    if not manager:
        print("[SKIP] 配置管理器未初始化，跳过测试")
        return False
    
    if not config_id:
        print("[ERROR] 配置ID不存在，跳过测试")
        return False
    
    try:
        # 修改部分配置值
        new_values = {
            'prediction': {
                'news_weight': 0.30,
                'capital_flow_weight': 0.15,
                'market_weight': 0.15,
                'technical_weight': 0.25,
                'sector_rotation_weight': 0.05,
                'history_weight': 0.05,
                'us_sector_weight': 0.03,
                'valuation_weight': 0.02,
                'min_confidence': 0.55,
                'lookback_days': 90
            },
            'indicator': {
                'ma_short': 10,
                'ma_long': 30,
                'rsi_period': 14
            }
        }
        
        success = manager.update_config(
            config_id=config_id,
            config_name='测试更新后的配置',
            description='测试更新功能',
            values=new_values,
            user_id=None
        )
        
        if success:
            print("[OK] 配置更新成功")
            
            # 验证更新后的值
            config = manager.get_config(config_id)
            if config and config.get('prediction', {}).get('news_weight') == 0.30:
                print("[OK] 更新后的值验证成功")
                return True
            else:
                print("[ERROR] 更新后的值验证失败")
                return False
        else:
            print("[ERROR] 配置更新失败")
            return False
    except Exception as e:
        print(f"[ERROR] 更新配置时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_config_history(manager, config_id):
    """测试配置历史"""
    print("\n" + "=" * 60)
    print("测试8: 配置历史")
    print("=" * 60)
    
    if not manager:
        print("[SKIP] 配置管理器未初始化，跳过测试")
        return False
    
    if not config_id:
        print("[ERROR] 配置ID不存在，跳过测试")
        return False
    
    try:
        history = manager.get_config_history(config_id, limit=10)
        print(f"[OK] 获取配置历史成功，共 {len(history)} 条记录")
        for h in history[:3]:  # 只显示前3条
            print(f"   - {h.get('action')} at {h.get('created_at')}")
        return True
    except Exception as e:
        print(f"[ERROR] 获取配置历史时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_stock_predictor_config_loading():
    """测试StockPredictor配置加载"""
    print("\n" + "=" * 60)
    print("测试9: StockPredictor配置加载")
    print("=" * 60)
    
    try:
        from predictor.stock_predictor import StockPredictor
        predictor = StockPredictor()
        
        print("[OK] StockPredictor初始化成功")
        print(f"   - 预测配置: {len(predictor.config)} 个参数")
        print(f"   - 技术指标配置: {len(predictor.indicator_config)} 个参数")
        
        # 检查配置是否从数据库加载
        if predictor.config.get('news_weight') == 0.30:
            print("[OK] 配置已从数据库加载（news_weight = 0.30）")
            return True
        else:
            print(f"   配置值: news_weight = {predictor.config.get('news_weight')}")
            print("   [WARN] 配置可能来自config.py默认值（如果数据库中没有激活的配置，这是正常的）")
            return True
    except Exception as e:
        print(f"[ERROR] StockPredictor配置加载测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("预测参数配置功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 配置管理器初始化
    manager = test_config_manager_init()
    results.append(('配置管理器初始化', manager is not None))
    
    # 测试2: 创建默认配置
    config_id = test_create_default_config(manager)
    results.append(('创建默认配置', config_id is not None))
    
    # 测试3: 获取配置
    if config_id:
        results.append(('获取配置', test_get_config(manager, config_id)))
    
    # 测试4: 配置验证
    results.append(('配置验证', test_validate_config(manager)))
    
    # 测试5: 激活配置
    if config_id:
        results.append(('激活配置', test_activate_config(manager, config_id)))
    
    # 测试6: 获取所有配置
    results.append(('获取所有配置', test_get_all_configs(manager)))
    
    # 测试7: 更新配置
    if config_id:
        results.append(('更新配置', test_update_config(manager, config_id)))
    
    # 测试8: 配置历史
    if config_id:
        results.append(('配置历史', test_config_history(manager, config_id)))
    
    # 测试9: StockPredictor配置加载
    results.append(('StockPredictor配置加载', test_stock_predictor_config_loading()))
    
    # 输出测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "[OK] 通过" if result else "[ERROR] 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
